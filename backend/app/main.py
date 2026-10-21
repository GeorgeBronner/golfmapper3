import json
import logging
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
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.database import engine, ensure_columns, ensure_index
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
Base.metadata.create_all(bind=engine)
ensure_columns("users", {"token_version": "INTEGER NOT NULL DEFAULT 0"})
# create_all only creates the partial unique index below on fresh databases;
# this backfills it onto ones that predate it (see ensure_index's docstring).
ensure_index(
    "uq_pending_location_change",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_location_change "
    "ON course_requests (submitted_by_user_id, request_type, course_id) "
    "WHERE status = 'pending'",
)
# Admin course map filters on upper(trim(state)) (see admin.course_points).
ensure_index(
    "ix_courses_state_norm",
    "CREATE INDEX IF NOT EXISTS ix_courses_state_norm ON courses (upper(trim(state)))",
)
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
# style-src keeps 'unsafe-inline' for Leaflet, which positions map panes,
# tiles and markers with inline styles; cdn.jsdelivr.net serves Bootstrap's
# CSS (index.html). Remote images are map tiles: OSM for the street map,
# Esri World Imagery for the satellite layer (components/BaseLayers.jsx).
CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https://*.tile.openstreetmap.org https://tile.openstreetmap.org "
    "https://server.arcgisonline.com; "
    "connect-src 'self' https://nominatim.openstreetmap.org; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)


# Pydantic's max_length only bounds the declared fields it validates —
# extra/unknown JSON fields aren't rejected by default, so a request can carry
# an arbitrarily large body alongside otherwise-valid data. Nothing else in
# the stack enforces a size limit (Uvicorn has none by default), so reject
# oversized requests here before they're parsed.
MAX_BODY_BYTES = 1 * 1024 * 1024


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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

# Added last so it's outermost: compresses the final body (map point payloads
# run to hundreds of KB) after the header middlewares above have run.
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
    response = HTMLResponse(_INDEX_HTML)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
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
# Must run after the routers are included: it only wires pagination params
# into routes that already exist on the app.
add_pagination(app)

# --- Static assets ---
if assets_path.exists() and assets_path.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")


# --- SPA catch-all: serve index.html for any non-API path ---
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(request: Request, full_path: str):
    if request.url.path.startswith(API_PREFIX + "/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return _serve_spa_shell()
