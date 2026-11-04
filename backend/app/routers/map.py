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


# Each state's Best in State list is its own ranking list with this scope prefix.
STATE_SCOPE_PREFIX = "us-state-"


# Declared before /rankings/{list_id}/points so "states" is not parsed as a list id.
@router.get("/rankings/states/points", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def state_ranking_points(request: Request, user: user_dependency, db: db_dependency, edition: str | None = None):
    """Every state's list for one edition label (the newest unless `edition` is given), as one set of
    points for the all-users map: {"fields": [...], "edition": label,
    "points": [[id, lat, lon, name, year, rank, rank_label, access, list], ...]}.
    `list` is the state list's name ("Best Courses in Texas"). Courses without coordinates are left out.
    """
    labels = (
        db.query(RankingEditions.label, RankingEditions.start_year)
        .join(RankingLists, RankingLists.id == RankingEditions.list_id)
        .filter(RankingLists.scope.like(f"{STATE_SCOPE_PREFIX}%"))
        .distinct()
        .order_by(RankingEditions.start_year.desc())
        .all()
    )
    if edition is None:
        if not labels:
            return {"fields": _STATE_FIELDS, "edition": None, "points": []}
        edition, start_year = labels[0]
    else:
        match = [start_year for label, start_year in labels if label == edition]
        if not match:
            raise HTTPException(status_code=404, detail="Edition not found")
        start_year = match[0]
    rows = (
        db.query(
            Courses.id,
            Courses.latitude,
            Courses.longitude,
            Courses.club_name,
            Courses.course_name,
            RankingEntries.rank,
            RankingEntries.rank_label,
            RankingEntries.access,
            RankingLists.name,
        )
        .join(RankingEntries, RankingEntries.course_id == Courses.id)
        .join(RankingEditions, RankingEditions.id == RankingEntries.edition_id)
        .join(RankingLists, RankingLists.id == RankingEditions.list_id)
        .filter(
            RankingLists.scope.like(f"{STATE_SCOPE_PREFIX}%"),
            RankingEditions.label == edition,
            Courses.latitude.isnot(None),
            Courses.longitude.isnot(None),
        )
        .order_by(RankingLists.name, RankingEntries.rank)
    )
    return {
        "fields": _STATE_FIELDS,
        "edition": edition,
        "points": [[*_point(*row[:5], start_year), *row[5:]] for row in rows],
    }


_STATE_FIELDS = ["id", "lat", "lon", "name", "year", "rank", "rank_label", "access", "list"]


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
     "points": [[id, lat, lon, name, year, rank, rank_label, access], ...]} in rank order.
    `year` is the edition's start year, `rank_label` is set only for ties ("T53") and `access` is
    "public" or "private" when the list says so.
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
                RankingEntries.access,
            )
            .join(RankingEntries, RankingEntries.course_id == Courses.id)
            .filter(
                RankingEntries.edition_id == edition.id,
                Courses.latitude.isnot(None),
                Courses.longitude.isnot(None),
            )
            .order_by(RankingEntries.rank)
        )
        points = [[*_point(*row[:5], edition.start_year), *row[5:]] for row in rows]
    return {
        "fields": ["id", "lat", "lon", "name", "year", "rank", "rank_label", "access"],
        "list": lst.name,
        "edition_id": edition.id if edition else None,
        "edition": edition.label if edition else None,
        "points": points,
    }
