# Security sweep (2026-11-14)

Findings and fixes are in `tasks/security-sweep-11-14-26.md`: 2 high, 7 medium, 8 low, plus one broken-Sentry note.
Nothing critical.

- [x] High: lock down the self-hosted runner on the public repo (#1) and close public `/metrics`, `/docs` and
      `/openapi.json` (#2). Confirm #2 on production after the next deploy.
- [ ] Medium: items 3-9 (rate-limit client IP, session lifetime, password-change limit, shared-map exposure,
      registration field limits, body-size limit, container hardening).
- [ ] Low: items 10-17, and allow Sentry in the CSP `connect-src`.

# Rankings and stats: remaining work (2026-11-09)

Carried over from the retired `plans/top100-lists/todos.md` and `plans/stats-refresh/todos.md`. Everything else in
those two plans is done and deployed (PRs #35-#41). The CSVs in `plans/top100-lists/` are still the seed input for
`backend/scripts/seed_rankings.py` (`plans/` is gitignored): back that folder up.

Audit 2026-11-09, `course.state` read as a US state: **no code change needed.** Checked against the local DB
(identical to production): every `country` is a 3-letter upper-case ISO code (82 values), every USA state is 2 letters,
all 3,000+ ranked US entries sit in USA, no course lacks coordinates, and each Best in State entry's state equals its
list's state. Every reader checks country first (`rankings.py` `_is_us`, `statsData.js`, `Rankings.jsx`,
admin `course_regions`); map popups and `mapPoints.js` do not use state. Non-US courses do reuse US codes (335 courses),
so keep country in any new filter. Notes:
- US territories (GU, MP, PR, VI: 53 courses, 1 played) are `USA` but not on the state tile map, so they count in
  country totals only. No ranked course is in one. Fine unless one is ranked later.

Worth doing
- [ ] Check the stats page in the running app (`run` skill): World country map, Best in State chart styles, phone layout.
- [ ] Back up `plans/top100-lists/` (or commit the CSVs somewhere): the seed script reads them from the gitignored folder.

Data checks (optional)
- [ ] Low-confidence matches: Hartford Red/Blue (29492), Cantigny (24328), Hawk Hollow (28802), UNM Championship (21967,
      coordinates look about 3 km off).
- [ ] Confirm Pinehurst No. 10 coordinates (30358: 35.151159, -79.456848; one listing only).
- [ ] Spot-check OSM-geocoded world rows: Naruo, Spring City, Kinloch (NZ), Ocean Dunes, Emirates; Te Arai North and
      South share one coordinate.
- [ ] Approximate coordinates (town or resort level; decided good enough 2026-11-02): Ladera, Riverton Pointe, The Trophy
      Club, White Oak Dye course, Ba Na Hills, Ho Tram, Cabot Saint Lucia.
- [ ] `readall_ids_w_year` omits courses without coordinates, so stats totals could differ slightly from the course list
      (no course lacks coordinates today).
- [ ] Source gaps, only if a better source appears: Circling Raven (2015-16 #96) has no yards, par or points; 2021-22 has
      only rank, course and state; 2019-20 prior ranks mostly blank; 2023-24 and 2025-26 have no yards or par; 2025-26
      has no points; 2013-14 Crosswater (#49) has no printed rank, kept as 49. Cosmetic: sheet headers say `2021/22`.
      Settled: 2021-22 has no rank 54 (Point O'Woods was removed as private); leave it blank.

Features (backlog, build together with the frontend that uses them)
- [ ] Next up / gaps: unplayed ranked courses, best rank first, nearest the user's usual states.
- [ ] Rank movement for played courses (up, down, new, dropped) from edition history.
- [ ] Share card, public vs private split, top clubs.
- [ ] Admin way to add new editions (CSV import using the formats in `plans/top100-lists/`); needed when the next Golf
      Digest editions (2026-27) come out.
- [ ] Best in State 2021-22 and older editions (state pages probably not archived).
- [ ] Other lists, never requested: GOLF Magazine (golf.com free tables), Golfweek (golfweek.usatoday.com), Second 100.

Production and DB (kept from the plans)
- Ask before touching production or pushing the DB; back up first. Recipe: `golfmapper_db_check` skill; prod deploy
  needs nvm Node 22 over SSH (see the `oracle-prod-deploy` memory). Local DB:
  `E:\Documents\Coding\myProjects\keys\golfMapperDB\golf_mapper.db`, equal to production (sha256 `e21a645e...`).

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
      after the swap, stop the review server and run `apply.py --mark <live DB copy>` (see the tool README).

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
