# New Map System

Replace server-side folium map generation with a compact JSON points API rendered client-side by `react-leaflet` (already a dependency). Primary new feature: an admin map of every course in a given state without a multi-megabyte HTML payload.

## Background

Current approach (`backend/app/routers/map.py`):

- Folium builds a full HTML page with one `CircleMarker` + popup per course.
- User map is cached to disk as `MAP_FILES_DIR/user_map_{id}.html`; all-users map is rebuilt on every request.
- Frontend (`Map.jsx`, `AllUsersMap.jsx`) fetches the HTML and shows it via `<iframe srcDoc sandbox="allow-scripts">`.
- `frontend/src/utils/cspNonce.js` stamps the CSP nonce onto exactly the first 6 `<script>` tags (folium's boilerplate count); `backend/app/main.py` `build_csp` / `_serve_spa_shell` issue a per-request nonce and allow folium's CDN hosts. `backend/tests/test_map.py` pins the script count.

Measured output size (folium 0.20.0, synthetic Florida data, `get_root().render()`):

| Approach | bytes/course raw / gzip | 2,000 courses | 15,000 courses | gen time @15k |
|---|---|---|---|---|
| Current (CircleMarker per course) | ~1,065 / ~114 | 2.1 MB | 16 MB | 6.6 s |
| Compact JSON arrays `[id, lat, lon, name]` | ~49 / ~14 | 97 KB | 740 KB (~210 KB gzip) | 0.05 s |

Known issues this change fixes or must fix along the way:

- Cached user maps are not invalidated when an admin edits a course location (`admin.py` location update), approves a location change (`course_requests.py` review endpoint), or deletes a course. Removing the file cache removes this bug class.
- `/map/allmap` is available to any authenticated user (`user_dependency`) and exposes every active user's username + course list. Decide intended visibility (see Open questions); default for this work: keep it available to authenticated users but do not widen what it exposes.
- Folium render + sync SQLAlchemy queries run inside `async def` routes, blocking the event loop. New endpoints should be plain `def` (FastAPI runs them in a threadpool), matching how sync DB work should be done here.
- Fragile nonce stamping tied to folium's script count.

## Target design

```
Browser (react-leaflet, preferCanvas)  ──GET JSON──▶  FastAPI points endpoints  ──▶  DB
        └─ popup detail fetched by id on click (optional)
```

- Backend returns compact point data; no HTML generation.
- One reusable frontend component `CourseMap` renders points with the Leaflet canvas renderer, optional clustering for large sets, optional per-group colors + legend.
- Folium, iframes, nonce stamping, and `static/user_maps/` are removed.

## Steps

Each step should land as its own commit (or PR) with tests passing. Run backend tests with the project's existing setup (`backend/` uses `uv`, `pyproject.toml`, tests in `backend/tests/`) and frontend tests with `npm test` in `frontend/`.

### Step 1 — Backend: points endpoints + compression

1. Add `GZipMiddleware` in `backend/app/main.py` (`from starlette.middleware.gzip import GZipMiddleware`, `minimum_size=1000`). Confirm it composes with the existing `security_headers` / `limit_body_size` middlewares and CORS.
2. Admin endpoint in `backend/app/routers/admin.py`:
   - `GET /api/v1/admin/courses/points?state=FL&country=...` guarded by `admin_dependency`.
   - `state` optional; if omitted, return all courses with coordinates (whole-dataset view). Match `state` case-insensitively and trimmed (`func.upper(func.trim(Courses.state)) == state.strip().upper()`), since `state` is free text. Accept `country` optionally the same way.
   - Query only the needed columns (`Courses.id, latitude, longitude, display name parts`), filter `latitude/longitude IS NOT NULL`.
   - Response shape (compact, documented in the endpoint docstring):
     ```json
     {"fields": ["id", "lat", "lon", "name"], "points": [[123, 27.95, -82.46, "Some Club - North"], ...]}
     ```
     Use the same display-name logic as `Courses.display_name` (check `models.py`) so names match the rest of the app. Round lat/lon to 5 decimals.
   - Rate-limit consistent with other endpoints (`@limiter.limit(...)`, requires `request: Request` param).
3. Distinct-states helper endpoint for the admin UI dropdown: `GET /api/v1/admin/courses/states` → `[{"state": "FL", "country": "USA", "count": 1234}, ...]` (normalized upper/trim, grouped).
4. User-facing points endpoints in `backend/app/routers/map.py` (keep the `/map` prefix):
   - `GET /api/v1/map/points` → current user's courses: `{"fields": ["id","lat","lon","name","year"], "points": [...]}` (reuse the query logic in `user_courses.readall` or a direct column query).
   - `GET /api/v1/map/all_points` → `{"users": [{"username": "...", "points": [[id, lat, lon, name, year], ...]}, ...]}` for active users, same data the all-users map shows today. Keep the current auth level (`user_dependency`) unless the Open question below is resolved otherwise.
   - No HTML escaping server-side — the client must render names as text (see Step 2).
5. Performance: add an index on `Courses.state` if the schema setup supports it. There is no Alembic in this project — check `backend/app/database.py` / `main.py` for how tables are created (likely `Base.metadata.create_all`), which does not add indexes to existing tables. If so, either add `index=True` on the model **and** document a one-off `CREATE INDEX IF NOT EXISTS ix_courses_state ON courses (state);` for prod in the PR description, or skip the index (at ~15k rows a scan is fine). Do not run anything against prod.
6. Tests (`backend/tests/test_admin.py`, `test_map.py`): admin-only access (non-admin → 403), state filter incl. case/whitespace variants, courses without coordinates excluded, response shape, gzip applied when `Accept-Encoding: gzip` and response > minimum size, user points only include the requesting user's courses, inactive users excluded from all_points.

### Step 2 — Frontend: reusable `CourseMap` + admin state map

1. Add `react-leaflet-cluster` (v4.x supports React 19 / react-leaflet 5 / Leaflet 1.9; verify on npm before installing and import its CSS: `react-leaflet-cluster/dist/assets/MarkerCluster.css` and `MarkerCluster.Default.css` or as its README specifies). If it proves incompatible, fall back to `supercluster` driven from map `moveend`/`zoomend`.
2. `frontend/src/components/CourseMap.jsx`:
   - Props: `groups: [{ name, color, points: [{id, lat, lon, name, year?}] }]`, `cluster` (bool, default: auto-enable when total points > ~3000), `fitToPoints` (bool), `showLegend` (bool).
   - `<MapContainer preferCanvas center={[40,-90]} zoom={4}>` + OSM `TileLayer` (same tile URL already allowed by CSP `img-src`), `ScaleControl`.
   - Unclustered: `CircleMarker` (radius 7, fill, opacity ~0.7 to match current look). Clustered: markers inside `MarkerClusterGroup` with `chunkedLoading`. Note: clustering works on `Marker`s; if using CircleMarkers with clustering is not supported by the wrapper, use small `L.divIcon` dot markers for the clustered mode.
   - Popups: render course name (and year if present) as React text children — never `dangerouslySetInnerHTML`. Optionally include course id like the current user map popup.
   - Fit bounds to points on load when `fitToPoints`.
   - Legend / layer toggle for multiple groups (replaces folium `LayerControl`): simple overlay list with color dot + username + checkbox to show/hide a group.
   - Reuse `frontend/src/utils/leafletIcons.js` if default markers are used anywhere.
3. Admin page `frontend/src/components/AdminCourseMap.jsx`:
   - State dropdown populated from `/admin/courses/states` (show counts), plus an "All" option with a warning on size.
   - Fetches `/admin/courses/points?state=XX`, maps the compact arrays to objects, renders `CourseMap` with one group, `fitToPoints`.
   - Shows course count and loading/error states (follow patterns in other admin components and `Map.jsx`, e.g. the stale-request guard via `activeCallRef`).
   - Route `/admin/course-map` in `frontend/src/router.jsx` (inside the admin-protected section, same as other admin routes) and a link in `frontend/src/components/AdminNav.jsx` ("Course Map").
4. Tests (vitest, see existing tests for setup): compact-array → object conversion, popup text is escaped (render a name containing `<img onerror>` and assert it appears as text), state dropdown triggers fetch.

### Step 3 — Migrate user and all-users maps, remove folium

1. Rewrite `frontend/src/components/Map.jsx` to fetch `/map/points` and render `CourseMap` (single group, red, as today). The "Regenerate" action becomes a simple refetch (or remove it). Remove iframe + `nonceScriptTags`.
2. Rewrite `frontend/src/components/AllUsersMap.jsx` to fetch `/map/all_points` and render `CourseMap` with one group per user using the existing palette from `map.py` `_USER_COLORS` (move palette to the frontend), legend enabled.
3. Remove backend HTML map code: `generate_user_map`, `generate_all_users_map`, `/map/usermap`, `/map/user_map_generate`, `/map/allmap`, `_invalidate_user_map` and its call sites in `user_courses.py`, `MAP_DIR`/`MAP_FILES_DIR` setting (`config.py`), `backend/app/static/user_maps/`, and `folium` from `backend/pyproject.toml` (update `uv.lock` via `uv`). Grep for any other references (docker-compose volumes, Dockerfile, `.gitignore`, docs) to `user_maps` / `MAP_FILES_DIR` and clean them up. Check the homelab deploy docs referenced in project memory aren't relying on a `user_maps` volume — if they are, note it in the PR description rather than editing that repo.
4. Remove the CSP nonce machinery that only existed for folium:
   - `frontend/src/utils/cspNonce.js` and its usages.
   - In `backend/app/main.py`: `_MAP_SCRIPT_HOSTS`, `_MAP_STYLE_HOSTS`, nonce param of `build_csp`, nonce injection in `_serve_spa_shell` (keep the `Cache-Control` header), and the explanatory comment block. CSP becomes a single static policy with `script-src 'self'`. Verify Leaflet CSS/images are bundled by Vite (served from `'self'`) and OSM tiles remain in `img-src`; `style-src 'unsafe-inline'` is still needed for Leaflet's inline styles.
   - Update `backend/tests/test_main.py` / `test_map.py` assertions that reference the nonce or script count.
5. Leave `backend/scripts/map_course_entry.py` (standalone dev tool) alone unless it imports removed code.

### Step 4 — Verify

- Backend and frontend test suites pass; `npm run build` succeeds.
- Run the app locally (`npm run build:local` + backend on 8005, or the dev setup in the README) and manually check: admin course map for a state, "All", user map, all-users map with legend toggling, popups, no CSP violations in the browser console.
- Record payload size of `/admin/courses/points` (all) with and without gzip in the PR description.

## Open questions for the user (do not block on these; use the defaults)

1. Should `/map/all_points` (all users' course histories) be admin-only? Default: unchanged auth level, flag in PR.
2. Normalize `Courses.state` values in the DB (e.g. "Florida" → "FL")? Default: no data migration; normalize only at query time.
3. Clustering threshold for the admin map. Default: auto-cluster above ~3,000 points.

## Out of scope

MapLibre GL, vector tiles (PostGIS/Martin/PMTiles), deck.gl. Revisit only if canvas + clustering is measurably insufficient for the full dataset.
