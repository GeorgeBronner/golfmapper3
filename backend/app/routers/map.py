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


# Plain `def` (not async): these do sync DB work, which FastAPI runs in its
# threadpool instead of blocking the event loop. Names are returned unescaped;
# the client renders them as text, never as HTML.


@router.get("/points", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def user_points(request: Request, user: user_dependency, db: db_dependency):
    """The current user's courses: {"fields": [...], "points": [[id, lat, lon, name, year], ...]}."""
    rows = _points_query(db).filter(UserCourses.user_id == user.get("id")).order_by(Courses.id)
    return {"fields": ["id", "lat", "lon", "name", "year"], "points": [_point(*row) for row in rows]}


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
    for *point, username in rows:
        users.setdefault(username, []).append(_point(*point))
    return {
        "fields": ["id", "lat", "lon", "name", "year"],
        "users": [{"username": name, "points": points} for name, points in users.items()],
    }
