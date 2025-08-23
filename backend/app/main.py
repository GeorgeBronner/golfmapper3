import os
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from app.database import engine
from app.routers import garmin_courses, garmin_courses_no_auth, auth, admin, users, user_courses, user_courses_no_auth, \
    map
from app.models import Base

# Import sentry_sdk conditionally to avoid errors if not installed
try:
    import sentry_sdk

    sentry_sdk_available = True
except ImportError:
    sentry_sdk_available = False

# Load environment variables
load_dotenv()

# Initialize Sentry if DSN is provided and sentry_sdk is available
if sentry_sdk_available and os.getenv("SENTRY_DSN", ""):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )

app = FastAPI()
add_pagination(app)
Base.metadata.create_all(bind=engine)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
    "http://localhost:8005",
    "http://127.0.0.1:8005",
    "https://localhost:8005",
    "https://localhost",
    "https://127.0.0.1",
    "https://127.0.0.1:8005",
    "https://10.9.8.221:3000",
    "http://10.9.8.221:3000",
    "https://golf.bronnerapp.com",
    "http://golf.bronnerapp.com",
    "https://golf.bronnerapp.com:80",
    "http://golf.bronnerapp.com:80",
    "https://132.145.156.224:3000",
    "http://132.145.156.224:3000",
    "https://backend.bronnerapp.com",
    "http://backend.bronnerapp.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the static files directory
static_dir = os.getenv("STATIC_FILES_DIR", "./dist")
static_path = Path(static_dir).resolve()
assets_path = static_path / "assets"

# Health check endpoint
@app.get("/healthy", status_code=200)
def health_check():
    return {"message": "I'm healthy"}

# Add explicit root handler BEFORE including any routers
@app.get("/", include_in_schema=False)
async def serve_root_frontend():
    index_file = static_path / "index.html"
    if index_file.exists():
        response = FileResponse(str(index_file))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    else:
        print(f"Warning: Frontend index file '{index_file}' not found")
        return {"detail": "Frontend not available"}

# Include routers after the root handler
app.include_router(auth.router)
app.include_router(garmin_courses.router)
# app.include_router(garmin_courses_no_auth.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(user_courses.router)
# app.include_router(user_courses_no_auth.router)
app.include_router(map.router)

# Mount static files only if directory exists
if assets_path.exists() and assets_path.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
else:
    print(f"Warning: Static assets directory '{assets_path}' not found, skipping mount")

# Add a catch-all route to serve the index.html for any unmatched routes (for SPA routing)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(request: Request, full_path: str):
    # Check if the path is an API route
    api_prefixes = ["/auth/", "/garmin_courses/", "/admin/", "/users/", "/user_courses/", "/map/"]
    request_path = request.url.path

    if any(request_path.startswith(prefix) for prefix in api_prefixes):
        return {"detail": "Not Found"}

    # Check if index.html exists before serving it
    index_file = static_path / "index.html"
    if index_file.exists():
        response = FileResponse(str(index_file))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    else:
        print(f"Warning: Frontend index file '{index_file}' not found")
        return {"detail": "Frontend not available"}