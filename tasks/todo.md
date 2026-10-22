# Courses sharing one coordinate (2026-10-20)

Context: the 2026-10-20 location audit fixed courses in the wrong country/state/region, but not courses placed at a
shared point. Kiawah Island showed the pattern: all five resort courses sat on one address point, the Ocean Course
6 km from its real location (now fixed, each course placed individually).

Current DB: 2,120 points shared by 5,835 rows. 1,835 points have a single club name (mostly nine-hole combinations of
one course — `Red/Blue`, `Silla-Mitras` — which correctly share a point, plus multi-course resorts like Kiawah);
285 points have 2–4 different club names (e.g. `Arlington Golf Association` holding four separate municipal courses).

Report (moves, deletes, remaining rows with best guess + confidence): https://claude.ai/artifact/4H7E7Vk7k7Kp5y3R8fShMe

- [x] Script the candidate list and categorize each shared point: A nine-hole combos (604 groups, leave), B duplicate
      rows (22), C one club with several named courses (1,244), D main + short course (95, leave), E different clubs (153).
- [x] Fetch candidates per C/E row from four sources and fuzzy-match club/course names: OSM `leisure=golf_course`
      polygons (Overpass), golfcoursebrowser.com `/data/courses.json`, OpenGolfAPI per-state lists, Nominatim search.
- [x] Move a row only when sure: matching named OSM polygon (≤ 1.5 km if the polygon name has no club word), or two
      sources within 300 m with one inside an OSM golf polygon. 519 moves; a 40-row spot check found 38 right.
      State/country re-derived via `nominatim_to_geo` (24 changes: 23 GB counties, Pointe West USA/MI → CAN/ON).
- [x] Delete 21 duplicate B rows (0 `user_courses` / `course_requests` refs; guarded `DELETE`).
- [x] Dry-run on a copy with guarded statements: 22,933 → 22,912 courses, shared points 2,121 → 1,775, integrity ok,
      632 `user_courses` intact.
- [x] Applied 2026-10-22 via the usual swap (prod hash `1d8a3ebc…` verified, backup `golf_mapper.db.bak-2026-10-21`,
      new hash `79f5bcc9…`, backend started clean) and committed the DB to `keys`.
- [ ] Manual review of the 2,939 remaining rows (played first, then by confidence) with the local tool in
      `tools/coord_review/` (`uv run --project backend python tools/coord_review/review.py`, http://127.0.0.1:8890).
      Decisions go to `data/decisions.json`; apply the `save` ones with `apply.py <db copy>` (guarded) and the usual swap.
      2026-10-22: first batch applied: 66 moves (43 played courses), Goodwood The Downs ESX → WSX, 20 "no decision";
      prod hash `52d4ae11…`, backup `golf_mapper.db.bak-2026-10-22`, `keys` commit `64a8ee9`. Keep the folder for more rounds;
      after applying, mark the batch with `"applied"` in `data/decisions.json` and restart the review server.

Lessons:
- golfcoursebrowser copies OpenGolfAPI, and OpenGolfAPI shares 1,827 points with this DB (same upstream), so
  agreement between those two alone is not evidence: 49 of 116 such pairs were identical, spot checks wrong by ~9 km.
- An OSM polygon matching only on a generic course word (`Old Course`, `Moonah`) can be a neighbouring club.
- 90 more duplicate rows (Garmin re-ratings: `Concord Golf Club 2018`, `Legacy/Sunset Old`, M/W tee variants) sit in
  the other categories, mostly COL/ITA/CAN. Not deleted; candidates for a dedupe task.
- Overpass: bbox queries batched ~15 groups per request are much faster than `around:`; expect 502/504 retries.

# Course country/state normalization at entry (2026-10-13)

Context: the 2026-10-13 course data cleanup found that rows added through the entry tools store
non-standard geo values (e.g. `United States`, `Nova Scotia`, `Quintana Roo`, `Crete`, `QR`).
DB convention is `country` = ISO 3166-1 alpha-3 and `state` = the ISO 3166-2 subdivision code
without the country prefix (`FL`, `NS`, `ROO`, `11`). Countries with no ISO subdivisions
(JEY, GGY, IMN, CXR, NFK, SXM) store an empty state.

- [x] `frontend/src/utils/geoLookup.js` — Mexico map used non-ISO codes (`QR`, `CDMX`, …). The name maps
      are gone: state now always comes from Nominatim's ISO keys (see next item), so MX gives `ROO`, `CMX`.
- [x] `geoLookup.js` `nominatimToGeoFields` — state from `ISO3166-2-lvl4` with the `XX-` prefix stripped,
      except GB/IE which use `lvl6` (county: `SRY`, `D`) to match existing rows. Never falls back to a full
      state name (blank instead). Sint Maarten/Aruba/Curaçao (reported under `nl` with only `lvl3`) map to
      SXM/ABW/CUW; US territories map to `USA` + `PR`/`GU`/`VI`/`MP`/`AS` like the existing rows.
- [x] `backend/scripts/map_course_entry.py` — uses the shared `backend/app/geo.py` (`nominatim_to_geo`,
      alpha-2→alpha-3 table); the state/province name dicts are removed. Client-side checks the country
      against the ISO list (injected from `geo.py`) and the state format.
- [x] Empty state allowed (entry script no longer requires it; React forms never did).
- [x] Backend validation — `CountryCode`/`StateCode` types in `app/geo.py` on admin create/update and
      new-course requests: country must be an ISO alpha-3 code, state empty or 1–3 uppercase
      alphanumerics, and empty for countries with no subdivisions. Input is trimmed/upper-cased; bad values → 422.
- [x] Frontend validation — `GeoCodeInputs.jsx`: country is a picker of ISO alpha-3 codes (legacy invalid
      values shown flagged), state upper-cases as typed; Add Course, Request New Course and Edit Course Info
      block saving until `validateGeoFields` passes.
- [x] Tests — `backend/tests/test_geo.py`, `frontend/src/utils/geoLookup.test.js`,
      `frontend/src/components/AdminEditCourseInfo.test.jsx`.

Review: verified the ISO key levels against live Nominatim reverse lookups (Surrey, Dublin, Belfast, Rome,
Cancún, Halifax, Jersey, Sint Maarten, Taipei, Seoul…) and against the codes already in the DB. Backend 83
tests and frontend 28 tests pass; `vite build` ok. Italy's DB rows mix region and province codes — new
entries will get the region (`lvl4`), matching the majority.

# opencode_issues.md review — branch opencode_refactor_7-23-26 (2026-07-23)

## Decision summary

### Fixing
- [x] #1 Escape user input before `innerHTML` in map_course_entry.py confirmation dialog
- [x] #2 (mitigation) Strip reset token from browser URL after read (ResetPassword.jsx); Referrer-Policy header via #7. Token is already hashed at rest, single-use, 15-min expiry — emailed link with query param is the standard flow.
- [x] #4 Backend email validation via pydantic `EmailStr` (+ email-validator dep)
- [x] #5 Rate limit user registration (5/minute)
- [x] #7 Security headers middleware: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- [x] #8 `html.escape()` user name in password reset email HTML
- [x] #10 Password confirmation field on registration form
- [x] #11 `user_info` 404 guard instead of 500 on missing user
- [x] #12 Shared Leaflet default-icon util (5 components deduped)
- [x] #13 Bind standalone map script to 127.0.0.1 instead of 0.0.0.0
- [x] #14 Close DB session in manual_GPS_edit.py
- [x] #16 Block admin self-demotion (mirror update_user_active guard)
- [x] #17 Year validation upper bound = current year + 1 (was 2070)
- [x] #19 `datetime.utcnow()` → `datetime.now(timezone.utc)` in map_course_entry.py
- [x] #21 `maxLength` on registration inputs (done alongside #10)
- [x] Tests for new guards (self-demotion, email validation)

### Not fixing (rationale)
- #3/"rotate secrets": no leaked secrets found in repo; reset tokens already hashed. Nothing to rotate from code.
- #6 Pagination: paginated endpoint `/garmin_courses/readall_page` already exists; switching CourseSearch to server-side pagination is a feature change; dataset is small.
- #9 localStorage → HTTP-only cookies: auth architecture change (CSRF handling, refresh flow). Separate effort.
- #15 CORS IPs: deliberate dev hosts, already overridable via `CORS_ORIGINS` env var (documented in config.py).
- #18 Test isolation: tests are not run in parallel (no pytest-xdist); speculative.
- #20 window.location.href on 401: standard interceptor pattern; router isn't reachable from api.js.
- #22 backend/dist gitignore: verified already ignored (`dist/` rule, git check-ignore confirms).
- #23 Deploy workflow: infra choice, out of scope for a code branch.
- CSP/HSTS: belong at the reverse proxy for this deployment; a wrong CSP breaks Leaflet/OSM tiles. Deferred deliberately.

## Review

All 15 selected items fixed on branch `opencode_refactor_7-23-26`.

Verification:
- `uv run pytest`: 58 passed (incl. 4 new tests: self-demotion blocked, role update works, invalid email → 422, valid email → 201)
- `uv run ruff check .`: clean. Pre-existing `ruff format` drift on main left untouched; only formatted the one file where new code drifted (tests/test_auth.py).
- `npm run build:local`: builds clean; shared leafletIcons chunk emitted.

Notes:
- New backend dependency: `email-validator` (for pydantic `EmailStr`).
- Registration now rate-limited 5/minute per client IP.
- Reset-token-in-URL is mitigated (Referrer-Policy header + token scrubbed from address bar after page load), not redesigned — an emailed link fundamentally requires a token in the URL.
