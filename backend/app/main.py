import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine
from app.limiter import limiter
from app.routers import garmin_courses, auth, admin, users, user_courses, map
from app.models import Base

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

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Static files ---
static_path = Path(settings.STATIC_FILES_DIR).resolve()
assets_path = static_path / "assets"

# --- Health check (outside /api/v1 intentionally) ---
@app.get("/healthy", status_code=200)
def health_check():
    return {"message": "I'm healthy"}

# --- Root SPA handler ---
@app.get("/", include_in_schema=False)
async def serve_root_frontend():
    index_file = static_path / "index.html"
    if index_file.exists():
        response = FileResponse(str(index_file))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    return {"detail": "Frontend not available"}

# --- API routers under /api/v1 ---
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(garmin_courses.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(user_courses.router, prefix=API_PREFIX)
app.include_router(map.router, prefix=API_PREFIX)

# --- Static assets ---
if assets_path.exists() and assets_path.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

# --- SPA catch-all: serve index.html for any non-API path ---
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(request: Request, full_path: str):
    if request.url.path.startswith(API_PREFIX + "/"):
        return {"detail": "Not Found"}
    index_file = static_path / "index.html"
    if index_file.exists():
        response = FileResponse(str(index_file))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    return {"detail": "Frontend not available"}
