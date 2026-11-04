from fastapi import APIRouter, HTTPException, Request
from starlette import status

from app.dependencies import db_dependency, user_dependency
from app.limiter import limiter
from app.models import (
    Courses,
    RankingEditions,
    RankingEntries,
    RankingLists,
    UserCourses,
    Users,
    course_display_name,
)

router = APIRouter(prefix="/map", tags=["map"])

# The old stand-in for Golf Digest's list: a fake user holding the ranked courses.
# The rankings tables replace it, so the all-users map skips it. Remove this
# (and the user) together.
LEGACY_TOP100_USERNAME = "top100"


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
        .filter(Users.is_active.is_(True), Users.username != LEGACY_TOP100_USERNAME)
        .order_by(Users.id, Courses.id)
    )
    users: dict[str, list] = {}
    for *row, username in rows:
        users.setdefault(username, []).append(row)
    return {
        "fields": ["id", "lat", "lon", "name", "year"],
        "users": [{"username": name, "points": _dedupe(user_rows)} for name, user_rows in users.items()],
    }


@router.get("/rankings/{list_id}/points", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def ranking_points(
    request: Request,
    list_id: int,
    user: user_dependency,
    db: db_dependency,
    edition_id: int | None = None,
):
    """One edition of a ranking list (the newest unless `edition_id` is given), for the all-users map:
    {"fields": [...], "list": name, "edition_id": id, "edition": label,
     "points": [[id, lat, lon, name, year, rank, rank_label], ...]} in rank order.
    `year` is the edition's start year and `rank_label` is set only for ties ("T53").
    Ranked courses without coordinates are left out.
    """
    lst = db.get(RankingLists, list_id)
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")
    editions = db.query(RankingEditions).filter(RankingEditions.list_id == list_id)
    if edition_id is not None:
        edition = editions.filter(RankingEditions.id == edition_id).first()
        if edition is None:
            raise HTTPException(status_code=404, detail="Edition not found")
    else:
        edition = editions.order_by(RankingEditions.start_year.desc()).first()
    points: list = []
    if edition is not None:
        rows = (
            db.query(
                Courses.id,
                Courses.latitude,
                Courses.longitude,
                Courses.club_name,
                Courses.course_name,
                RankingEntries.rank,
                RankingEntries.rank_label,
            )
            .join(RankingEntries, RankingEntries.course_id == Courses.id)
            .filter(
                RankingEntries.edition_id == edition.id,
                Courses.latitude.isnot(None),
                Courses.longitude.isnot(None),
            )
            .order_by(RankingEntries.rank)
        )
        points = [[*_point(*row[:5], edition.start_year), row[5], row[6]] for row in rows]
    return {
        "fields": ["id", "lat", "lon", "name", "year", "rank", "rank_label"],
        "list": lst.name,
        "edition_id": edition.id if edition else None,
        "edition": edition.label if edition else None,
        "points": points,
    }
