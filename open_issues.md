# Open Issues

Findings from a full codebase review focused on frontend-to-backend API calls (auth/authz, input validation, frontend API usage, infra/config). Every finding below was independently re-verified against the source before inclusion.

## Critical

### 1. ✅ FIXED — CSP blocks the map feature entirely — `/map` renders blank for every user
`backend/app/main.py:69-79`

The CSP added in commit `053cf06` sets `script-src 'self'` with no CDN allowance or nonce. Folium's generated map HTML is injected into the frontend via `<iframe srcDoc=...>` (`frontend/src/components/Map.jsx:88-96`), and a `srcdoc` iframe with no CSP of its own inherits the parent page's CSP. Folium's output requires 4 external scripts (Leaflet, jQuery, Bootstrap, awesome-markers CDNs) plus inline `L.map(...)` init — all blocked. Verified by actually generating a folium map and inspecting the emitted `<script>` tags.

**The app's core feature (the map) is currently completely broken for all users.**

**Fix:** the SPA shell (`_serve_spa_shell` in `main.py`) now stamps a fresh CSP nonce into a `<meta>` tag on every request and sets `script-src 'self' 'nonce-<x>' <folium CDN hosts>` for that response only (every other response keeps the strict, nonce-free default CSP). The frontend (`utils/cspNonce.js`, wired into `Map.jsx`/`AllUsersMap.jsx`) copies that nonce onto the fetched map HTML's `<script>` tags before handing it to the iframe. Also fixed the related `img-src` gap (folium's default tiles come from the bare `tile.openstreetmap.org`, not a subdomain) and added the `cdnjs.cloudflare.com`/`netdna.bootstrapcdn.com` hosts folium's CSS needs to `style-src`.

## High

### 2. ✅ FIXED — Stolen JWTs survive a password change and can be refreshed forever
`backend/app/routers/auth.py:130-139`

There's no token revocation/versioning. A leaked token (stored in plain `localStorage`) stays valid through its full 90-minute life even after the victim changes their password, and `POST /auth/refresh` — unlike every other `/auth` endpoint — has no rate limit and no re-auth check, so an attacker can keep renewing it indefinitely. Only an admin deactivating the account stops it.

**Fix:** added a `token_version` column on `Users` (migrated onto existing databases via `database.ensure_columns`, since the project has no migration tool). It's embedded in every JWT as `tv` and checked in `get_current_user` against the current DB value — a mismatch is rejected the same as an invalid token. Self-service password change (`users.py`), admin-triggered password reset (`admin.py`), and the forgot/reset-password flow (`password_reset.py`) all bump it, so any token issued before a password change stops working immediately (including refreshed ones, since `/auth/refresh` goes through `get_current_user`). Also added a `20/minute` rate limit to `/auth/refresh`, which previously had none.

### 3. ✅ FIXED — CORS `allow_methods` omits PATCH — breaks 4 real endpoints, reachable today
`backend/app/main.py:94-100`

`allow_methods=["GET","POST","PUT","DELETE"]` but 4 real `@router.patch` endpoints exist (admin role/password/active toggles in `admin.py:145,165,180`, course-year edit in `user_courses.py:147`) and are called from `AdminUsers.jsx` / `CourseList.jsx`. PATCH always triggers a CORS preflight, which Starlette rejects outright when the method isn't listed. This isn't just a theoretical split-origin-prod issue — the checked-in local dev setup (`VITE_BACKEND_SERVER_IP=localhost:8005` vs Vite on a different port) already makes these cross-origin, so this is live-broken in local dev too.

**Fix:** added `"PATCH"` to `allow_methods` in the `CORSMiddleware` config.

## Medium

### 4. No rate limiting on authenticated, resource-intensive endpoints
`backend/app/routers/map.py:111-128`

Map generation (folium + disk I/O), course-request submission, and course-add endpoints have zero `@limiter` protection, unlike `auth.py`/`password_reset.py`. A single scripted account can hammer these for CPU/disk exhaustion or flood the admin review queue.

### 5. Free-text course-request fields have no `max_length` and no body-size cap
`backend/app/routers/course_requests.py:19-33`

`club_name`, `course_name`, `address`, etc. are bare `str`, no length limit anywhere in the ASGI stack, and this route has no rate limit either. Any authenticated user can repeatedly POST arbitrarily large JSON bodies.

### 6. Global 401 interceptor hard-redirects and silently discards in-progress form data
`frontend/src/services/api.js:22`

On any non-whitelisted 401, `window.location.href = '/'` fires a full page reload, wiping unsaved form state (e.g. a half-filled "Add Course" form) with zero warning, since JWTs expire after 90 min mid-session.

### 7. Delete/year-update failures on the course list are silently swallowed
`frontend/src/components/CourseList.jsx:23`

`.catch(error => console.error(error))` only; no alert/error state shown, unlike almost every other mutating call in the codebase. Users get no feedback that a delete or edit failed.

### 8. "Regenerate Map" navigates to `/map` even when generation failed
`frontend/src/utils/mapUtils.js:3`

The catch handler swallows the error and resolves anyway, so `CourseForm.jsx`'s `.then()` chain always navigates, masking backend failures.

### 9. Vite dev proxy rewrite strips `/api` instead of `/api/v1`
`frontend/vite.config.js:34-38`

On a fresh clone following the documented `npm run dev` flow (no local `.env` override), API calls get rewritten to a path the backend doesn't serve and silently fall through to the SPA catch-all, returning HTML instead of JSON for every API call.

## Low

### 10. Password-reset endpoint has a timing side channel that reveals registered emails
`backend/app/routers/password_reset.py:74-115`

Despite an identical response body, matching emails trigger extra DB writes plus a synchronous outbound email API call, creating a measurable latency gap that defeats the anti-enumeration design (rate-limited, so only a partial mitigation).

### 11. TOCTOU race on duplicate pending location-change requests
`backend/app/routers/course_requests.py:102-144`

Check-then-insert with no backing `UniqueConstraint` in the schema, so the `except IntegrityError` handler is dead code; concurrent requests can create duplicate pending rows.

### 12. `garmin_id` missing `ge=1` bound, inconsistent with the rest of the codebase
`backend/app/routers/user_courses.py:39-45`

Harmless today (fails via 404 lookup) but inconsistent with the `Field(..., ge=1)` convention used everywhere else.

### 13. No request-sequencing guards on some manual-refresh flows (stale data on double-click)
`frontend/src/components/CourseSearch.jsx:55`, and `AdminUsers.jsx`'s `loadUsers`

Unlike `AdminReviewRequests.jsx`/`Map.jsx`/`AllUsersMap.jsx`, which use sequence refs, these can show stale data on out-of-order responses.

### 14. CSP `img-src` wildcard doesn't match folium's actual tile host
`backend/app/main.py:74`

Allows `https://*.tile.openstreetmap.org` but folium's default tile layer requests the bare `https://tile.openstreetmap.org` (no subdomain), which the wildcard doesn't cover per CSP matching rules. Even after fixing #1, tiles would still be gray/missing.

---

**Suggested priority**: fix #1 (map completely broken) and #3 (PATCH/CORS breaks admin + course-year edits) first — both are live breakage, not theoretical. #2 (token revocation) is the one real security gap worth planning for, though it requires an architectural change (token versioning or a revocation list).
