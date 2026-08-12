import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, ensure_columns
from app.limiter import limiter
from app.models import Base
from app.routers import admin, auth, course_requests, garmin_courses, map, password_reset, user_courses, users

try:
    import sentry_sdk

    sentry_sdk_available = True
except ImportError:
    sentry_sdk_available = False


# --- Structured logging ---
class _JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())
logging.basicConfig(handlers=[_handler], level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

# --- Sentry ---
if sentry_sdk_available and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.TRACES_SAMPLE_RATE,
        profiles_sample_rate=0.0,
    )

app = FastAPI()
add_pagination(app)
Base.metadata.create_all(bind=engine)
ensure_columns("users", {"token_version": "INTEGER NOT NULL DEFAULT 0"})
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# FastAPI's default 422 body puts a list of Pydantic error objects in
# `detail`. Several frontend components render `err.response.data.detail`
# directly as a string, which crashes React ("Objects are not valid as a
# React child") the moment any validated field actually fails validation.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p != "body")
    message = f"{field}: {first['msg']}" if field else first["msg"]
    return JSONResponse(status_code=422, content={"detail": message})


# --- Security headers ---
# Set here rather than relying on the reverse proxy, so they apply
# consistently regardless of which NPM host config is deployed.
#
# The golf-course map is server-rendered by folium and embedded in the SPA
# via <iframe srcDoc=...> (see Map.jsx / AllUsersMap.jsx) rather than a
# same-origin navigation, so the browser treats it as an about:srcdoc
# document with no CSP of its own — it inherits the SPA shell's policy
# wholesale. Folium's output needs a fixed set of third-party script/style
# hosts plus two inline <script> blocks (its Leaflet init code, which
# embeds real course coordinates and so can't be hashed ahead of time).
# Rather than blanket 'unsafe-inline' for the whole app, the SPA shell gets
# a fresh nonce per request; the frontend copies that nonce onto the
# fetched map HTML's <script> tags before handing it to the iframe.
_MAP_SCRIPT_HOSTS = "https://cdn.jsdelivr.net https://code.jquery.com https://cdnjs.cloudflare.com"
_MAP_STYLE_HOSTS = "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://netdna.bootstrapcdn.com"


def build_csp(nonce: str | None = None) -> str:
    script_src = "script-src 'self'" + (f" 'nonce-{nonce}' {_MAP_SCRIPT_HOSTS}" if nonce else "")
    return (
        "default-src 'self'; "
        f"{script_src}; "
        f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com {_MAP_STYLE_HOSTS}; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://*.tile.openstreetmap.org https://tile.openstreetmap.org; "
        "connect-src 'self' https://nominatim.openstreetmap.org; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )


CSP = build_csp()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # The SPA-shell routes set their own (nonced) CSP; don't clobber it.
    if "content-security-policy" not in response.headers:
        response.headers["Content-Security-Policy"] = CSP
    response.headers["Strict-Transport-Security"] = "max-age=63072000; preload"
    return response


# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Static files ---
static_path = Path(settings.STATIC_FILES_DIR).resolve()
assets_path = static_path / "assets"

# Read once at startup rather than per-request: it's a static build artifact
# that doesn't change while the process is running, and reading it from disk
# inside an async route handler would block the event loop on every request.
_index_file = static_path / "index.html"
_INDEX_HTML = _index_file.read_text(encoding="utf-8") if _index_file.exists() else None


# --- Health check (outside /api/v1 intentionally) ---
@app.get("/healthy", status_code=200)
def health_check():
    return {"message": "I'm healthy"}


def _serve_spa_shell():
    if _INDEX_HTML is None:
        return {"detail": "Frontend not available"}
    # A fresh nonce per request lets this response's CSP allow the map's
    # inline init scripts (see build_csp) without a blanket 'unsafe-inline'.
    nonce = secrets.token_urlsafe(16)
    html = _INDEX_HTML.replace("<head>", f'<head><meta name="csp-nonce" content="{nonce}">', 1)
    response = HTMLResponse(html)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Content-Security-Policy"] = build_csp(nonce=nonce)
    return response


# --- Root SPA handler ---
@app.get("/", include_in_schema=False)
async def serve_root_frontend():
    return _serve_spa_shell()


# --- API routers under /api/v1 ---
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(garmin_courses.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(user_courses.router, prefix=API_PREFIX)
app.include_router(map.router, prefix=API_PREFIX)
app.include_router(password_reset.router, prefix=API_PREFIX)
app.include_router(course_requests.router, prefix=API_PREFIX)

# --- Static assets ---
if assets_path.exists() and assets_path.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")


# --- SPA catch-all: serve index.html for any non-API path ---
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(request: Request, full_path: str):
    if request.url.path.startswith(API_PREFIX + "/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return _serve_spa_shell()
