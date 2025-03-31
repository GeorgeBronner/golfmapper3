import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi_pagination import add_pagination
from app.database import engine
from app.routers import garmin_courses, garmin_courses_no_auth, auth, admin, users, user_courses, user_courses_no_auth, map
from app.models import Base
import sentry_sdk

# Load environment variables
load_dotenv()

if os.getenv("SENTRY_DSN", ""):
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
  "https://10.9.8.221:3000",
  "https://10.9.8.223:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.get("/healthy", status_code=200)(lambda: {"message": "I'm healthy"})
app.include_router(auth.router)
app.include_router(garmin_courses.router)
# app.include_router(garmin_courses_no_auth.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(user_courses.router)
# app.include_router(user_courses_no_auth.router)
app.include_router(map.router)