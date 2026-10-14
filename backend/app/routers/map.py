from fastapi import APIRouter, Request
from starlette import status

from app.dependencies import db_dependency, user_dependency
from app.limiter import limiter
from app.models import Courses, UserCourses, Users, course_display_name

router = APIRouter(prefix="/map", tags=["map"])


def _point(course_id, lat, lon, club, name, year) -> list:
    return [course_id, round(lat, 5), round(lon, 5), course_display_name(club, name), year]


def _points_query(db):
    return (
        db.query(
            Courses.id,
            Courses.latitude,
            Courses.longitude,
            Courses.club_name,
            Courses.course_name,
            UserCourses.year,
        )
        .join(UserCourses, UserCourses.course_id == Courses.id)
        .filter(Courses.latitude.isnot(None), Courses.longitude.isnot(None))
    )


def _dedupe(rows) -> list:
    """One point per course, keeping the latest year. Databases created before
    uq_user_course still have the old (user, course, year) constraint, so a
    user can hold the same course more than once."""
    points: dict[int, list] = {}
    for row in rows:
        point = _point(*row)
        existing = points.get(point[0])
        if existing is None or (point[4] or 0) > (existing[4] or 0):
            points[point[0]] = point
    return list(points.values())


# Plain `def` (not async): these do sync DB work, which FastAPI runs in its
# threadpool instead of blocking the event loop. Names are returned unescaped;
# the client renders them as text, never as HTML.


@router.get("/points", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def user_points(request: Request, user: user_dependency, db: db_dependency):
    """The current user's courses: {"fields": [...], "points": [[id, lat, lon, name, year], ...]}."""
    rows = _points_query(db).filter(UserCourses.user_id == user.get("id")).order_by(Courses.id)
    return {"fields": ["id", "lat", "lon", "name", "year"], "points": _dedupe(rows)}


@router.get("/all_points", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def all_users_points(request: Request, user: user_dependency, db: db_dependency):
    """Every active user's courses, grouped by user in user-id order:
    {"fields": [...], "users": [{"username": ..., "points": [[id, lat, lon, name, year], ...]}, ...]}.
    """
    rows = (
        _points_query(db)
        .add_columns(Users.username)
        .join(Users, Users.id == UserCourses.user_id)
        .filter(Users.is_active.is_(True))
        .order_by(Users.id, Courses.id)
    )
    users: dict[str, list] = {}
    for *row, username in rows:
        users.setdefault(username, []).append(row)
    return {
        "fields": ["id", "lat", "lon", "name", "year"],
        "users": [{"username": name, "points": _dedupe(user_rows)} for name, user_rows in users.items()],
    }
