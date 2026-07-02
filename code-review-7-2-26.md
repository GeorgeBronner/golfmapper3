# GolfMapper3 — Full Code Review (2026-07-02)

Scope: entire backend (`backend/app/`, 16 files) and frontend (`frontend/src/`, all components/services/routes), plus tests and deployment config. Findings are categorized **Critical → High → Medium → Low**, with a separate section for suggested refactors that aren't bugs. Each item notes whether it's a **[Fix]** (behavior/security defect) or **[Refactor]** (quality/maintainability).

Overall: the codebase is in good shape — clean separation of routers, consistent dependency patterns, a solid `services/api.js` layer, thoughtful comments explaining non-obvious decisions (identity-map note in `user_courses.py`, rate-limit keying in `limiter.py`). The findings below are mostly gaps at the seams: map generation, token lifecycle, and validation mismatches between FE and BE.

---

## Critical

### C1. [Fix] Stored XSS in folium-generated maps → token theft
`backend/app/routers/map.py:34`, `map.py:76-80`, rendered via `frontend/src/components/Map.jsx:91` and `AllUsersMap.jsx:44`

Folium popups and `LayerControl` layer names render **raw HTML** (the code itself relies on this — the colored `<span>` dot is injected into the layer name at `map.py:72-76`). Two user-controlled strings flow into that HTML unescaped:

- **Username** → `fg = folium.FeatureGroup(name=dot + username)` (`map.py:76`). Any user can register with a username like `<img src=x onerror="...">`.
- **Course names** → `popup=label` where `label` comes from `course.display_name` (`map.py:78-80`, `map.py:34`). Course names originate from user-submitted new-course requests (and admin entry).

The all-users map HTML is served to **every user** (`/map/allmap`) and rendered in an `<iframe srcDoc={...}>`. A `srcDoc` iframe is **same-origin with the parent page**, so injected script can read `localStorage` and exfiltrate the JWT of every user who opens the All Users Map.

**Fix:**
1. `html.escape()` the username and course name/label before passing to `FeatureGroup(name=...)` and `popup=...` in both `generate_user_map` and `generate_all_users_map`.
2. Defense in depth: add `sandbox="allow-scripts"` (without `allow-same-origin`) to both map iframes — Leaflet still runs, but the frame loses access to the parent origin and `localStorage`.

---

## High

### H1. [Fix] `CourseResponse` non-optional fields 500 the entire My Courses page
`backend/app/routers/user_courses.py:43-58`

`CourseResponse` declares `club_name: str`, `course_name: str`, `city: str`, `state: str`, `country: str` as required non-null, but `Courses` rows can legitimately have NULLs in all of them:
- `NewCourseRequest` only requires *one* of club/course name and allows null city/state/country (`course_requests.py:18-32`); approval copies those NULLs into `Courses`.
- Admin `CourseCreate` allows all of them to be null (`admin.py:34-42`).

Once a user adds such a course, `GET /user_courses/readall` and `/readall_ids_w_year` raise a `ResponseValidationError` → **HTTP 500, and the user's course list page breaks entirely** (CourseList shows only the generic error). The map path happens to survive because `map.py` calls the `readall` function directly, bypassing response validation.

**Fix:** make these fields `str | None` in `CourseResponse` (matching `CourseBase` in `garmin_courses.py`, which got this right). The FE already renders missing values fine.

### H2. [Fix] bcrypt 5.0 raises on passwords > 72 bytes → unhandled 500s
`backend/app/routers/auth.py:36,89`, `users.py:42-44`, `admin.py:170`, `password_reset.py:146` (bcrypt 5.0.0 per `uv.lock`)

bcrypt 5.x raises `ValueError` for passwords longer than 72 bytes (4.x silently truncated). None of the call sites guard for this, so:
- Registration / password change / reset with a long password (e.g. a 100-char generated passphrase) → 500.
- **Login** with a long password → 500 instead of 401 — and since the 500 escapes the handler, the failed-login log/rate accounting path is inconsistent.

**Fix:** add `max_length=72` to the Pydantic password fields (`CreateUserRequest`, `UserVerification`, `PasswordReset`, `ResetPasswordRequest`) and wrap `checkpw` in `authenticate_user` so oversized input returns `False` rather than raising.

### H3. [Fix] `is_active` is never enforced
`backend/app/routers/auth.py:32-38,47-57`

`Users.is_active` exists and is filtered in the all-users map, but:
- `authenticate_user` doesn't check it — a deactivated user can log in.
- `get_current_user` never touches the DB — an existing token keeps working regardless.
- There is also **no admin endpoint to deactivate a user**, so the only account-disable lever an admin appears to have (the flag exists in `UserSummary`) does nothing even if set directly in the DB.

**Fix:** check `user.is_active` in `authenticate_user` (return `False` if inactive), and add an admin `PATCH /admin/users/{id}/active` endpoint if account disabling is a desired feature. For immediate revocation see H4.

### H4. [Fix] Token lifecycle: role changes and password resets don't invalidate existing JWTs
`backend/app/routers/auth.py:41-57,116-123`, `dependencies.py:13-18`

The role is trusted from the JWT claim and never re-checked against the DB:
- An admin demoted to `user` **retains full admin API access for up to 90 minutes** (and can keep extending via `/auth/refresh`, which issues fresh tokens indefinitely from any valid token).
- After a password reset (user-initiated or admin-forced, e.g. because the account was compromised), all previously issued tokens remain valid until expiry.

**Fix options** (pick per how much state you'll accept): (a) have `require_admin` re-read the role from the DB (one indexed PK lookup per admin request — cheap at this scale); (b) add a `token_version`/`updated_at` claim checked in `get_current_user`, bumped on password/role change. Option (a) is the simplest and also fixes the "deleted user still has a working token" edge.

---

## Medium

### M1. [Fix] Rate-limit key is spoofable via client-supplied `X-Forwarded-For`
`backend/app/limiter.py:6-14`

Taking the last XFF hop is correct **only when exactly one trusted proxy always sets the header**. When the app is reachable directly (local dev on :8005, or any path that bypasses nginx), an attacker sends their own `X-Forwarded-For` and rotates values to fully bypass the 10/min login limiter — the one control against credential brute-forcing. Conversely, with two proxy hops (e.g. Cloudflare tunnel → nginx) the last hop is the inner proxy's address and the limit becomes global again.

**Fix:** gate the XFF logic behind a setting (e.g. `TRUSTED_PROXY=true` in deployed environments, default false → use `get_remote_address`), or validate that the direct peer is a known proxy address before trusting the header.

### M2. [Fix] Map cache invalidation gaps — stale maps after admin actions
`backend/app/routers/user_courses.py:16-17` (the only invalidation), vs `admin.py:69-134`, `course_requests.py:169-211`

`user_map_{id}.html` files are only deleted when a user adds/deletes a course or edits a year. They are **not** invalidated when:
- An admin updates a course's location or info, or deletes a course (`admin.py`) — every user who played it keeps a stale/wrong map indefinitely.
- An admin approves a **location change** (same effect).
- An admin approves a **new course** request — a `UserCourses` row is created for the submitter (`course_requests.py:191-196`), but their cached map won't show it.

**Fix:** move `_invalidate_user_map` to a shared module; on course location change/delete, invalidate maps for all users holding that course (`SELECT DISTINCT user_id FROM user_courses WHERE course_id = ?`); on new-course approval, invalidate the submitter's map. Alternatively, drop the file cache entirely and render on demand like `/map/allmap` does (see R2).

### M3. [Fix] Registration: duplicate-check race and no server-side email validation
`backend/app/routers/auth.py:73-94`

- Check-then-insert without catching `IntegrityError`: two concurrent registrations with the same username/email → 500. Wrap the commit like `add_user_course` does (`user_courses.py:138-142`).
- `email: str` accepts anything; use `EmailStr` (pydantic `email-validator`) so garbage emails don't break password reset later.
- No rate limit on `POST /auth/` — trivial spam-account creation. Add `@limiter.limit(...)` like the other auth endpoints.

### M4. [Fix] FE/BE password minimum mismatch (6 vs 8)
`frontend/src/components/UserProfile.jsx:24,93` vs `backend/app/routers/users.py:29`

Profile page validates ≥6 chars, backend requires ≥8. A 6–7 char new password passes client checks, then the 422 is mapped to the generic "Failed to update password." — the user gets no hint why. Change the FE to 8 (`minLength={8}` and the JS check), matching Register/Reset pages.

### M5. [Fix] Registration form wipes user input on failure
`frontend/src/components/NewUser.jsx:21-28`

`setForm({ ...empty })` runs unconditionally after the try/catch, so on a 409 ("username taken") the user loses everything they typed. Also there's no submit-in-flight guard (double-click → double request) and no success feedback (silent redirect to login). Move the reset into the success path, add a `submitting` state, and consider a "Account created — sign in" message on `/`.

### M6. [Fix] `/metrics`, `/docs`, `/openapi.json` are publicly exposed
`backend/app/main.py:54,57`

Prometheus metrics (endpoint latencies, traffic patterns) and the full OpenAPI schema are unauthenticated. For a hobby app this is mostly information disclosure, but `/metrics` in particular should be scrape-only. Options: `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` in production via a setting, and protect `/metrics` (require an internal network / basic auth at nginx, or `Instrumentator(should_respect_env_var=True)`).

### M7. [Fix] Timing-based user enumeration + slow response in forgot-password
`backend/app/routers/password_reset.py:73-108`

The uniform response message is good, but when the email **is** registered the request synchronously calls the Mailtrap API (hundreds of ms to seconds); when it isn't, it returns immediately. That timing difference re-enables enumeration, and the user waits on the mail provider. Send the email in a background task (`fastapi.BackgroundTasks`) — commit the token first, then queue the send; both paths return in ~constant time.

### M8. [Refactor] No schema migrations — `create_all` only creates missing tables
`backend/app/main.py:56`, acknowledged in `models.py:90-94`

New columns/constraints on existing tables silently don't apply (the `uq_user_course` comment shows this has already bitten). As the model count grows, adopting Alembic removes a whole class of "works on fresh DB only" bugs and the need for application-level constraint workarounds.

---

## Low

### L1. [Fix] `GET /user/` returns 500 if the user row is gone
`backend/app/routers/users.py:32-34` — `.first()` can return `None`, which fails `UserResponse` validation. Add a 404 guard like `update_password` has.

### L2. [Fix] Dead `IntegrityError` handler in location-change submit
`backend/app/routers/course_requests.py:132-141` — there is no unique constraint on `CourseRequests`, so this except-branch can never fire; the race it targets (two concurrent identical pending requests) can still slip through. Either add the partial unique constraint or drop the dead handler.

### L3. [Fix] Deleting a course leaves pending location-change requests dangling
`backend/app/routers/admin.py:74-79` — only `status == "approved"` requests are cleaned up. Pending ones survive with a dangling `course_id`; they 404 on approve (handled) but clutter the review queue and must be rejected manually. Consider also deleting (or auto-rejecting with a message) pending requests for the deleted course.

### L4. [Fix] `update_course_info` stores `''` instead of `NULL`
`backend/app/routers/admin.py:113-114` — the FE always sends all six fields, so clearing a field saves an empty string. Normalize `'' → None` before `setattr` to keep `display_name` and NULL-filtering logic consistent.

### L5. [Fix] Admin `CourseCreate` lacks the at-least-one-name rule
`backend/app/routers/admin.py:34-42` vs `course_requests.py:28-32` — admins can create a fully unnamed course (`display_name` = `""`). Reuse the same `model_validator`.

### L6. [Fix] Admins can demote themselves
`frontend/src/components/AdminUsers.jsx:28-37`, `backend/app/routers/admin.py:142-157` — one click on your own row and (after token expiry) you're locked out of admin with no recovery path in the UI. Guard server-side (`if target.id == user["id"]: 400`) and/or hide the button for the current user.

### L7. [Fix] CourseList sort mishandles nulls and case
`frontend/src/components/CourseList.jsx:42-47` — `a[key] < b[key]` with `null` years/cities is always false (nulls scatter), and string comparison is case-sensitive (`'apple' > 'Zebra'`). Use `localeCompare` for strings and push nulls to the end.

### L8. [Fix] CORS config: plaintext-HTTP production origins, unnecessary credentials
`backend/app/config.py:25-50`, `main.py:64-70` — `http://golf.bronnerapp.com` etc. shouldn't be allowed origins in production (override via the env var per the comment, or trim the default list), and `allow_credentials=True` is unnecessary for bearer-token auth (no cookies) — dropping it slightly reduces CSRF-adjacent surface.

### L9. [Refactor] JWT payload parsing duplicated 3×
`frontend/src/components/AuthProvider.jsx:5-17`, `routes/ProtectedRoute.jsx:6-13`, `routes/AdminRoute.jsx:7-13` — three slightly different base64-decode implementations. Extract one `utils/jwt.js` with `getPayload(token)` / `isExpired(token)`; also note `atob` breaks on base64url payloads containing `-`/`_` (usernames with certain chars could make role detection silently fail). A shared helper that converts base64url → base64 fixes all three at once.

### L10. [Fix] ErrorBoundary swallows errors without reporting to Sentry
`frontend/src/components/ErrorBoundary.jsx` — Sentry is initialized in `index.jsx` but render errors caught here never reach it. Add `componentDidCatch(error, info) { Sentry.captureException(error); }` or use `Sentry.ErrorBoundary`.

### L11. [Refactor] `?rand=' + new Date()` cache-buster
`frontend/src/components/Map.jsx:35`, `AllUsersMap.jsx:18` — works but produces an encoded date-string URL; `Date.now()` is the conventional form.

### L12. [Fix] Review-map markers loaded from raw.githubusercontent.com
`frontend/src/components/AdminReviewRequests.jsx:16-29` — external runtime dependency for the admin review UI; if the repo moves, markers break. Vendor the two PNGs into `src/assets`.

### L13. [Refactor] Nominatim requests lack identification
`frontend/src/components/AdminAddCourse.jsx:27`, `CourseEditsNewCourse.jsx:28` — Nominatim's usage policy asks for an identifying `email=` param or custom User-Agent; low volume makes this tolerable, but adding `&email=...` is one line. The reverse-geocode `LocationPicker` is also copy-pasted between these two files — extract a shared component.

### L14. [Refactor] Postgres URL doesn't escape credentials
`backend/app/database.py:16-19` — a password containing `@`/`:`/`%` breaks the URL. Use `sqlalchemy.URL.create(...)`. (Moot while `USE_SQLITE_DB=True`, but a landmine for the Postgres path.)

### L15. [Refactor] FE test coverage is a single smoke-test file
`frontend/src/App.test.jsx` — backend has a real suite; frontend covers only LoginPage render + one redirect. The highest-value additions: CourseList (sort/delete/year-edit) and the auth interceptor behavior in `services/api.js`.

---

## Suggested refactors (non-bug, quality/performance)

### R1. Course search ships the entire course table to the browser
`frontend/src/components/CourseSearch.jsx:58` uses `/garmin_courses/readall` and filters client-side, while a paginated endpoint (`/readall_page`, `garmin_courses.py:34-36`) already exists and is unused. Fine at hundreds of courses; at Garmin-catalog scale (tens of thousands) it's a multi-MB JSON payload on every visit. Either move to server-side pagination + a search query param, or delete the unused paginated endpoint to avoid confusion.

### R2. All-users map is fully regenerated per request
`backend/app/routers/map.py:113-116` re-queries every user/course and re-renders folium HTML on each hit, while the per-user map uses a file cache with the invalidation gaps of M2. Consider unifying: a short TTL in-memory/file cache for `/allmap`, or on-demand rendering for both (folium render for a few hundred markers is fast) — which would also delete `_invalidate_user_map` and M2 entirely. Related: `map.py:24` calls the endpoint function `readall()` directly, coupling map generation to a route's implementation; extract the query into a plain helper both can use.

### R3. Consolidate duplicated auth-router plumbing
`auth.py` and `password_reset.py` each define their own `db_dependency` instead of importing from `app/dependencies.py` (the documented pattern). Only `dependencies.py` can't be used in `auth.py` itself (circular import) — `password_reset.py` has no such excuse.

### R4. `AdminAddCourse` vs `CourseEditsNewCourse`, `AdminEditCourse` vs `CourseEditsLocationChange`
Each pair is ~90% identical (map + form + leaflet icon setup). Extract shared `CourseLocationForm` / `LocationPickerMap` components; the four files shrink to thin wrappers differing only in the submit endpoint and copy.

### R5. Leaflet default-icon patch repeated in 5 files
The `delete L.Icon.Default.prototype._getIconUrl` + `mergeOptions` block appears in every leaflet-using component. Move it to a single `utils/leafletSetup.js` imported once.

### R6. `datetime.now(timezone.utc)` inline vs `models._now`
`admin.py:95`, `course_requests.py:187,208,230` re-spell what `models._now()` already provides. Trivial, but one canonical clock helper makes future "freeze time in tests" work easier.

---

## Priority fix order (suggested)

1. **C1** — escape folium popup/layer-name HTML + sandbox the iframes (small change, closes token theft).
2. **H1** — make `CourseResponse` fields optional (one-line-per-field; un-breaks My Courses for affected users).
3. **H2** — cap password length at 72 / guard `checkpw` (prevents 500s on auth paths).
4. **H3 + H4** — enforce `is_active` and re-check role/user from DB in `require_admin`/`get_current_user`.
5. **M1–M7** as a batch; **M8 (Alembic)** when the next schema change lands.
