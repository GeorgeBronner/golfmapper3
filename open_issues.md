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

### 4. ✅ FIXED — No rate limiting on authenticated, resource-intensive endpoints
`backend/app/routers/map.py:111-128`

Map generation (folium + disk I/O), course-request submission, and course-add endpoints have zero `@limiter` protection, unlike `auth.py`/`password_reset.py`. A single scripted account can hammer these for CPU/disk exhaustion or flood the admin review queue.

**Fix:** added `@limiter.limit(...)` to `get_usermap`/`user_map_generate`/`get_allmap` (`30/minute` — started at `10/minute` but a code-review pass found that tripped 429s on ordinary double-clicks of "Regenerate Map", since each click fires two requests), `submit_new_course`/`submit_location_change` (`10/minute`), and `add_user_course` (`10/minute`). Also added an `autouse` fixture in `tests/conftest.py` that resets the shared `Limiter` between tests — it's a process-wide singleton, and one test file was already calling a newly-limited endpoint more than 10x.

### 5. ✅ FIXED — Free-text course-request fields have no `max_length` and no body-size cap
`backend/app/routers/course_requests.py:19-33`

`club_name`, `course_name`, `address`, etc. are bare `str`, no length limit anywhere in the ASGI stack, and this route has no rate limit either. Any authenticated user can repeatedly POST arbitrarily large JSON bodies.

**Fix:** added `max_length` to `NewCourseRequest`'s string fields (200/300/100 depending on field) and `RejectBody.message` (1000). Rate limiting from #4 covers the repeated-POST flooding angle. This surfaced a pre-existing, separate bug: FastAPI's default 422 body is a list of Pydantic error objects, and a couple of frontend components render `err.response.data.detail` directly as a string — which crashed the whole SPA (React "objects are not valid as a child") the moment a validated field actually failed. It was already reachable via the pre-existing lat/long bounds but effectively never hit through normal UI flow; the new `max_length` made it trivially reachable (paste a long address). Fixed at the root with a global `RequestValidationError` handler in `main.py` that reduces the error list to a single string message, rather than patching each frontend call site.

### 6. ✅ FIXED — Global 401 interceptor hard-redirects and silently discards in-progress form data
`frontend/src/services/api.js:22`

On any non-whitelisted 401, `window.location.href = '/'` fires a full page reload, wiping unsaved form state (e.g. a half-filled "Add Course" form) with zero warning, since JWTs expire after 90 min mid-session.

**Fix:** `api.js` now dispatches a `SESSION_EXPIRED_EVENT` (`frontend/src/constants/authEvents.js`) instead of redirecting directly. `AuthProvider.jsx` listens and clears its own token state (previously bypassed entirely). `App.jsx` listens and does an in-app `router.navigate('/', { replace: true })` (no hard reload) plus leaves a flash message in `sessionStorage` that `LoginPage.jsx` displays via its existing `error`/`alert-danger` state. Split across two listeners rather than one shared module deliberately — `App.jsx` already imports the router singleton, and having `AuthProvider.jsx` import it too would create a real circular import (`AuthProvider.jsx` → `router.jsx` → route components → `useAuth` from `AuthProvider.jsx`).

### 7. ✅ FIXED — Delete/year-update failures on the course list are silently swallowed
`frontend/src/components/CourseList.jsx:23`

`.catch(error => console.error(error))` only; no alert/error state shown, unlike almost every other mutating call in the codebase. Users get no feedback that a delete or edit failed.

**Fix:** added an `actionError` state, set on delete/year-update failure and rendered via the same `alert-danger` convention already used by this file's `fetchCourses` error state.

### 8. ✅ FIXED — "Regenerate Map" navigates to `/map` even when generation failed
`frontend/src/utils/mapUtils.js:3`

The catch handler swallows the error and resolves anyway, so `CourseForm.jsx`'s `.then()` chain always navigates, masking backend failures.

**Fix:** `generateUserMap` now rethrows instead of swallowing, and `CourseForm.jsx`'s button handler has a `.catch` that shows an error instead of navigating (and clears any stale success banner from a prior "Add Course" submit, so the two don't render contradictorily at once).

### 9. ✅ FIXED — Vite dev proxy rewrite strips `/api` instead of `/api/v1`
`frontend/vite.config.js:34-38`

On a fresh clone following the documented `npm run dev` flow (no local `.env` override), API calls get rewritten to a path the backend doesn't serve and silently fall through to the SPA catch-all, returning HTML instead of JSON for every API call.

**Fix:** removed the `rewrite` — the backend already mounts routers at `/api/v1`, matching what `services/api.js` requests, so no rewrite is needed. Also added `xfwd: true` to the proxy config (found in code review) — without it, the backend's rate limiter sees every proxied dev request as the same peer, so unrelated browser tabs would share one rate-limit bucket per endpoint.

## Low

### 10. ✅ FIXED (partial mitigation) — Password-reset endpoint has a timing side channel that reveals registered emails
`backend/app/routers/password_reset.py:74-115`

Despite an identical response body, matching emails trigger extra DB writes plus a synchronous outbound email API call, creating a measurable latency gap that defeats the anti-enumeration design (rate-limited, so only a partial mitigation).

**Fix:** the non-existent-email branch now `await`s a constant delay approximating the registered-email branch's email-send latency, gated on `settings.MAILTRAP_API_KEY` being configured — a code-review pass caught that sleeping unconditionally would, with no Mailtrap key set (the default dev/test config, where the registered branch already skips its own network call), turn into a *new*, perfectly reliable timing oracle in the opposite direction. Still an explicitly partial mitigation, same as before — a real fix would need constant-time DB work too.

### 11. Partially fixed — TOCTOU race on duplicate pending location-change requests
`backend/app/routers/course_requests.py:102-144`

Check-then-insert with no backing `UniqueConstraint` in the schema, so the `except IntegrityError` handler is dead code; concurrent requests can create duplicate pending rows.

**Fix:** added a partial unique index (`submitted_by_user_id`, `request_type`, `course_id` where `status = 'pending'`) to `CourseRequests` in `models.py`, so the existing `except IntegrityError` handler actually does something. Same caveat as `UserCourses.uq_user_course` before it: this only reaches freshly-created databases (`Base.metadata.create_all`), not the existing production DB — SQLite can't add it via `ALTER TABLE` and the project has no migration tool, so the live DB still relies solely on the check-then-insert. **Also found in code review but not fixed here:** `submit_new_course` has no equivalent guard at all, and the new index doesn't cover it either (SQL unique indexes treat `NULL course_id` — always `NULL` for new-course requests — as distinct every time), so duplicate new-course submissions are still fully possible. Wasn't in the original scope of this finding (which was specifically about location-change) and needs its own dedup key (e.g. normalized club/course name) rather than a copy-paste of this index — left as a follow-up.

### 12. ✅ FIXED — `garmin_id` missing `ge=1` bound, inconsistent with the rest of the codebase
`backend/app/routers/user_courses.py:39-45`

Harmless today (fails via 404 lookup) but inconsistent with the `Field(..., ge=1)` convention used everywhere else.

**Fix:** `garmin_id: int = Field(..., ge=1)`, matching `course_requests.py`'s `course_id`.

### 13. ✅ FIXED — No request-sequencing guards on some manual-refresh flows (stale data on double-click)
`frontend/src/components/CourseSearch.jsx:55`, and `AdminUsers.jsx`'s `loadUsers`

Unlike `AdminReviewRequests.jsx`/`Map.jsx`/`AllUsersMap.jsx`, which use sequence refs, these can show stale data on out-of-order responses.

**Fix:** `CourseSearch.jsx`'s `refreshData` got the `activeCallRef`/`callId` idiom from `Map.jsx`/`AllUsersMap.jsx` (single call site); `AdminUsers.jsx`'s `loadUsers` got the incrementing-`useRef` counter idiom from `AdminReviewRequests.jsx` (multiple call sites — mount, role toggle, active toggle). Deliberately kept as two different idioms rather than unifying into one shared hook — each already matches an existing precedent elsewhere in the codebase, and both were already coexisting before this change.

### 14. Already fixed (no action needed)
`backend/app/main.py:74`

Originally: CSP `img-src` allowed `https://*.tile.openstreetmap.org` but folium's default tile layer requests the bare `https://tile.openstreetmap.org` (no subdomain), which the wildcard doesn't cover per CSP matching rules. Verified this was already resolved as a side effect of #1's fix — `build_csp()` lists both the wildcard and the bare host.

---

**Remaining known gaps** (not fixed in this pass): the `submit_new_course` duplicate-submission gap noted under #11, and the production-DB caveat on the same fix. Both are pre-existing, not regressions.
