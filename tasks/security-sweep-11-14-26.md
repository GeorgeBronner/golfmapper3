# Security sweep (2026-11-14)

Full-repo sweep on `main` at `dcd045b`: backend auth and authorization, backend input handling, frontend, and
secrets/config/deployment. Each finding below was checked against the code. Production was probed with a few read-only
GETs and the repo's GitHub settings were read with `gh`.

Result: nothing critical. No injection, no broken access control, no secrets in the tree or in git history. The two
High items are worth fixing soon; the rest is hardening.

## High

- [x] **1. Self-hosted runner on a public repo.** The repo is public and `.github/workflows/deploy-staging.yml` runs on
      the self-hosted runner `docker31`, which has Docker access and the staging `.env`. A fork PR can add its own
      workflow with `runs-on: self-hosted`; the only gate is GitHub's approval for first-time contributors
      (`approval_policy: first_time_contributors`), so one mistaken "Approve and run" gives code execution on that
      host. `main` has no branch protection.
      Fix: require approval for all outside contributors, or make the repo private, or move the deploy to a pull
      model. Add branch protection and `permissions: contents: read` to the workflow.
      Done 2026-11-14: approval policy is now `all_external_contributors` (confirmed with `gh`). Every fork PR now
      needs a manual approval, so the remaining risk is approving a malicious one. Ruleset `protect-main` (id
      27264965) now blocks deletion and force-pushes on `main` and requires a pull request (0 approvals, no bypass).
      `deploy-staging.yml` now sets `permissions: contents: read`.
- [x] **2. `/metrics`, `/docs` and `/openapi.json` are public on production.** All three returned 200 from
      `https://golf.bronnerapp.com` without authentication. They expose the full API map (admin routes included) and
      per-route request counts, status codes and latencies. Causes: `backend/app/main.py:59` (`FastAPI()` with default
      docs URLs) and `backend/app/main.py:76` (`Instrumentator().expose`).
      Fix: `docs_url=None, redoc_url=None, openapi_url=None` outside development; block `/metrics` at the proxy or
      require a token.
      `/metrics` done in code 2026-11-14 (not deployed yet): `hide_public_metrics` in `backend/app/main.py` returns
      404 when the request has `X-Forwarded-For`. Prometheus on oracle scrapes `gm3-backend:8005` directly, so it is
      unaffected. `/docs`, `/redoc` and `/openapi.json` are now disabled unless `ENVIRONMENT=development`
      (`_docs_config` in `main.py`); those paths fall through to the SPA shell. After deploy, confirm on production.

## Medium

- [ ] **3. Rate limiting probably keys on the wrong IP in production.** `backend/app/limiter.py:11-13` uses the last
      `X-Forwarded-For` hop, and production is behind Cloudflare. Unless the nginx proxy restores the real client IP,
      that hop is a Cloudflare edge address: users share buckets and an attacker gets a fresh bucket per edge.
      Unconfirmed (proxy config is not in the repo). On staging, `docker-compose-stage.yml:8` publishes 8005 on all
      interfaces, so anyone who can reach the port can spoof the header and bypass the limits.
      Fix: key on `CF-Connecting-IP` when the request comes from the proxy; bind staging to `127.0.0.1:8005:8005`.
- [ ] **4. Sessions never expire and cannot be revoked.** `/auth/refresh` (`backend/app/routers/auth.py:136-147`)
      reissues a 90-minute token from any valid token with no absolute cap. The token is in `localStorage`, logout is
      client-side only, and a password change is the only revocation.
      Fix: carry the original login time through refreshes and refuse after 7-30 days; add a "log out everywhere"
      endpoint that bumps `token_version`.
- [ ] **5. Password change has no rate limit.** `PUT /user/password` (`backend/app/routers/users.py:40`) is the only
      password-checking endpoint without `@limiter.limit`. With a stolen token, the current password can be
      brute-forced and the owner locked out.
      Fix: `@limiter.limit("5/minute")` like the other auth routes.
- [ ] **6. Any registered user can read every user's username and play history.** `GET /map/all_points`
      (`backend/app/routers/map.py:64-83`) returns this for all active users; registration is open with no email
      verification. The usernames are login names, so this is also a credential-stuffing list. If this is the intended
      shared map, the fix is a product decision.
      Fix: opt-in flag, or show display names instead of login names.
- [ ] **7. Registration fields are unbounded and unnormalised.** `CreateUserRequest`
      (`backend/app/routers/auth.py:74-79`) has no length or character limits on `username`, `first_name` or
      `last_name`. Uniqueness is case-sensitive, so `Admin` and `admin` can both exist and both appear on the shared
      map. Emails are matched case-sensitively too (`auth.py:90-93`, `password_reset.py:112`).
      Fix: length and pattern limits; lowercase usernames and emails on write and lookup.
- [ ] **8. The 1 MB body limit only checks `Content-Length`.** A chunked request skips the check in
      `backend/app/main.py:124-129`, leaving the proxy as the only backstop (its limit is unknown).
      Fix: count bytes while streaming, or set `client_max_body_size` at the proxy.
- [ ] **9. The container runs as root on floating images.** `backend/Dockerfile` has no `USER`, uses the unpinned
      `python:3.14-slim` tag and an unpinned `uv`, and `uv run` re-syncs at start. Code execution in the app would be
      root with write access to the bind-mounted database.
      Fix: non-root user, pin both, run `.venv/bin/uvicorn` directly.

## Low

- [ ] **10. Account enumeration.** Login returns faster for unknown usernames because bcrypt is skipped
      (`backend/app/routers/auth.py:32-40`); registration returns 409 for an existing email (`auth.py:96-99`). Item 6
      already leaks usernames, so the email leak is the part that matters.
- [ ] **11. Login throttling is per IP only.** No per-account lockout; the only password rule is 8 characters. The
      reset flow re-implements the length check by hand (`backend/app/routers/password_reset.py:166-175`) instead of
      using `NewPassword`.
- [ ] **12. Reset-email flooding.** `forgot-password` has no per-email cooldown, and each request invalidates the
      previous link, so a victim's reset can be kept from working.
- [ ] **13. CORS defaults are too broad.** `backend/app/config.py:30-55` allows localhost, a LAN IP, a public IP and
      plain-`http://` versions of the production hosts, with `allow_credentials=True` (not needed: auth is a bearer
      header). The 2026-07-23 review kept the dev hosts on purpose (#15); the smaller fix is to set `CORS_ORIGINS` in
      the production and staging compose files and drop `allow_credentials`.
- [ ] **14. Dependency advisories.** Backend (`pip-audit`): `certifi` 2026.7.22, `dnspython` 2.9.0 and
      `opentelemetry-api` 1.45.1 each have a patch release. Frontend (`npm audit`): `follow-redirects` via axios (not
      used by the browser build) and `happy-dom` (test-only).
      Fix: `uv lock --upgrade-package certifi --upgrade-package dnspython --upgrade-package opentelemetry-api` and
      `npm audit fix`.
- [ ] **15. Unthrottled full-table read.** `GET /garmin_courses/readall`
      (`backend/app/routers/garmin_courses.py:29-31`) returns every course with no rate limit.
- [ ] **16. Dev server exposure.** `frontend/vite.config.js:27-32` binds `0.0.0.0` with `allowedHosts: true`, which
      disables Vite's host check. Local dev only.
- [ ] **17. Smaller hardening gaps.**
      - HSTS has `preload` without `includeSubDomains` (`backend/app/main.py:139`), so it does not qualify for preload.
      - `.gitignore` lists database files by name rather than `*.db`; the compose default `backend/golf_mapper.db` is
        not covered.
      - `SECRET_KEY_AUTH` has no minimum-length check (`backend/app/routers/auth.py:22`).
      - `frontend/nginx.conf` and `frontend/Dockerfile` are stale and would ship without security headers if deployed.

## Not a vulnerability, but broken

- [ ] **Browser Sentry is blocked by the CSP.** `connect-src` (`backend/app/main.py:109`) allows only `'self'` and
      Nominatim, so frontend Sentry events and replays are dropped in production whenever a DSN is set. Add the Sentry
      ingest host or use a tunnel.

## Checked and clean

- Injection: all queries are ORM-parameterised; no command execution, deserialisation, SSRF or user-influenced file
  access. The SPA catch-all serves a cached string and never touches the filesystem.
- Authorization: every `/admin/*` and `/course-requests/admin/*` route uses `admin_dependency`, with the role read from
  the database on each request. Per-user endpoints are scoped to the caller; registration cannot set a role.
- Crypto: bcrypt for passwords, JWT pinned to HS256, reset tokens are 256-bit, hashed, single-use, 15-minute expiry.
- XSS: no HTML sinks in the frontend; the one HTML string (`frontend/src/components/CourseMap.jsx:25`) takes only
  palette colours, and `script-src 'self'` backs it up.
- Secrets: none in the working tree or in 111 commits of history; no database or `.env` file was ever tracked.

## Not verified

- The nginx proxy and Cloudflare configuration, which decides items 3 and 8.
- The strength of the deployed `SECRET_KEY_AUTH` (no `.env` file was read).
- A claim that huge integer IDs cause 500s on SQLite was not run and is left out.
- Token storage in `localStorage` was already reviewed and deferred on 2026-07-23 (#9); item 4 is the part of that
  risk worth acting on.
