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
