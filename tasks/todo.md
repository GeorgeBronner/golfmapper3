# Course country/state normalization at entry (2026-10-13)

Context: the 2026-10-13 course data cleanup found that rows added through the entry tools store
non-standard geo values (e.g. `United States`, `Nova Scotia`, `Quintana Roo`, `Crete`, `QR`).
DB convention is `country` = ISO 3166-1 alpha-3 and `state` = the ISO 3166-2 subdivision code
without the country prefix (`FL`, `NS`, `ROO`, `11`). Countries with no ISO subdivisions
(JEY, GGY, IMN, CXR, NFK, SXM) store an empty state.

- [ ] `frontend/src/utils/geoLookup.js:96` — Mexico map uses non-ISO codes (`QR`, `AGS`, `CAMP`,
      `CHIS`, `CHIH`, `COAH`, `DGO`, `GTO`, `HGO`, `MICH`, `NL`, `QRO`, `TAMPS`, `TLAX`, `CDMX`, `BC`).
      Switch to ISO 3166-2:MX (`ROO`, `AGU`, `CAM`, `CHP`, `CHH`, `COA`, `DUR`, `GUA`, `HID`, `MIC`,
      `NLE`, `QUE`, `TAM`, `TLA`, `CMX`, `BCN`) to match the 139 existing MEX rows.
- [ ] `geoLookup.js` `nominatimToGeoFields` — prefer Nominatim's `address["ISO3166-2-lvl4"]`
      (fallback `ISO3166-2-lvl6`) and strip the `XX-` prefix, so every country gets a code instead of
      only US/CA/AU/MX falling back to the full state name. Keep the name maps as fallback only.
- [ ] `backend/scripts/map_course_entry.py:185-195` — same fix server-side: derive state from
      `ISO3166-2-lvl4`, and convert `address.country_code` to alpha-3 (currently stores the full
      country name, e.g. `United States`). Reuse one alpha-2→alpha-3 table rather than a third copy.
- [ ] Allow an empty state for countries with no ISO subdivisions (entry forms currently require state).
- [ ] Optional: backend validation on course create/update — `country` must be 3 uppercase letters,
      `state` must be empty or ≤3 uppercase alphanumerics — so bad values are rejected at write time.
- [ ] Tests for the normalization helpers (US, CA, MX, a country with no subdivisions).

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
