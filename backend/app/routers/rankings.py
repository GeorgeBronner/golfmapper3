from fastapi import APIRouter, HTTPException, Request
from starlette import status

from app.dependencies import db_dependency, user_dependency
from app.limiter import limiter
from app.models import Courses, RankingEditions, RankingEntries, RankingLists, UserCourses, course_display_name

router = APIRouter(prefix="/rankings", tags=["rankings"])

# Plain `def` (not async): sync DB work runs in FastAPI's threadpool.


def _played_years(rows) -> dict[int, int | None]:
    """Latest known year per course from (course_id, year) rows.

    Older databases lack uq_user_course, so a course can appear more than once.
    """
    played: dict[int, int | None] = {}
    for course_id, year in rows:
        if year is not None and (played.get(course_id) or 0) < year:
            played[course_id] = year
        else:
            played.setdefault(course_id, None)
    return played


def _edition_dict(edition: RankingEditions) -> dict:
    return {
        "id": edition.id,
        "label": edition.label,
        "start_year": edition.start_year,
        "published_on": edition.published_on,
        "source_url": edition.source_url,
        "notes": edition.notes,
    }


@router.get("", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def list_rankings(request: Request, user: user_dependency, db: db_dependency):
    """Every ranking list with its editions, newest edition first."""
    lists = db.query(RankingLists).order_by(RankingLists.id).all()
    editions = db.query(RankingEditions).order_by(RankingEditions.start_year.desc()).all()
    by_list: dict[int, list] = {}
    for edition in editions:
        by_list.setdefault(edition.list_id, []).append(_edition_dict(edition))
    return [
        {
            "id": lst.id,
            "slug": lst.slug,
            "name": lst.name,
            "publisher": lst.publisher,
            "scope": lst.scope,
            "size": lst.size,
            "editions": by_list.get(lst.id, []),
        }
        for lst in lists
    ]


@router.get("/editions/{edition_id}", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def edition_entries(request: Request, edition_id: int, user: user_dependency, db: db_dependency):
    """One edition's entries in rank order, each flagged with whether the current user has played it."""
    edition = db.get(RankingEditions, edition_id)
    if edition is None:
        raise HTTPException(status_code=404, detail="Edition not found")
    played = {row[0] for row in db.query(UserCourses.course_id).filter(UserCourses.user_id == user.get("id"))}
    rows = (
        db.query(RankingEntries, Courses)
        .join(Courses, Courses.id == RankingEntries.course_id)
        .filter(RankingEntries.edition_id == edition_id)
        .order_by(RankingEntries.rank)
    )
    return {
        **_edition_dict(edition),
        "list_id": edition.list_id,
        "entries": [
            {
                "rank": entry.rank,
                "prior_rank": entry.prior_rank,
                "published_name": entry.published_name,
                "points": entry.points,
                "course_id": course.id,
                "name": course_display_name(course.club_name, course.course_name),
                "city": course.city,
                "state": course.state,
                "played": course.id in played,
            }
            for entry, course in rows
        ],
    }


@router.get("/courses/{course_id}", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def course_history(request: Request, course_id: int, user: user_dependency, db: db_dependency):
    """A course's rank in every edition it appeared in, oldest first."""
    rows = (
        db.query(RankingEntries, RankingEditions, RankingLists)
        .join(RankingEditions, RankingEditions.id == RankingEntries.edition_id)
        .join(RankingLists, RankingLists.id == RankingEditions.list_id)
        .filter(RankingEntries.course_id == course_id)
        .order_by(RankingLists.id, RankingEditions.start_year)
    )
    return [
        {
            "list_id": lst.id,
            "list": lst.name,
            "edition_id": edition.id,
            "edition": edition.label,
            "start_year": edition.start_year,
            "rank": entry.rank,
            "prior_rank": entry.prior_rank,
            "published_name": entry.published_name,
            "points": entry.points,
        }
        for entry, edition, lst in rows
    ]


@router.get("/lists/{list_id}/progress", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def list_progress(request: Request, list_id: int, user: user_dependency, db: db_dependency):
    """The current user's progress on one ranking list, for the stats page.

    `ever_listed` is how many distinct courses have appeared in any edition.
    `current` covers the newest edition (totals, plus ranked/played per state).
    `editions` gives played/total for every edition. `courses` is every course
    the user has played that appeared in any edition, with the year they played
    it and its rank in each edition, so the client can split rounds by whether
    the course was ranked at the time.
    """
    lst = db.get(RankingLists, list_id)
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")
    editions = (
        db.query(RankingEditions)
        .filter(RankingEditions.list_id == list_id)
        .order_by(RankingEditions.start_year.desc())
        .all()
    )
    played = _played_years(
        db.query(UserCourses.course_id, UserCourses.year).filter(UserCourses.user_id == user.get("id"))
    )
    label_of = {e.id: e.label for e in editions}
    rows = (
        db.query(RankingEntries, Courses)
        .join(Courses, Courses.id == RankingEntries.course_id)
        .filter(RankingEntries.edition_id.in_(label_of))
        .all()
    )

    totals = {e.id: {"total": 0, "played": 0} for e in editions}
    ranked_courses: dict[int, dict] = {}
    ever_listed = {course.id for _, course in rows}
    for entry, course in rows:
        totals[entry.edition_id]["total"] += 1
        if course.id not in played:
            continue
        totals[entry.edition_id]["played"] += 1
        item = ranked_courses.setdefault(
            course.id,
            {
                "course_id": course.id,
                "name": course_display_name(course.club_name, course.course_name),
                "city": course.city,
                "state": course.state,
                "year": played[course.id],
                "current_rank": None,
                "ranks": {},
            },
        )
        item["ranks"][label_of[entry.edition_id]] = entry.rank
        if editions and entry.edition_id == editions[0].id:
            item["current_rank"] = entry.rank

    current = None
    if editions:
        by_state: dict[str, dict] = {}
        for entry, course in rows:
            if entry.edition_id != editions[0].id:
                continue
            bucket = by_state.setdefault((course.state or "").strip().upper(), {"ranked": 0, "played": 0})
            bucket["ranked"] += 1
            bucket["played"] += course.id in played
        current = {
            **_edition_dict(editions[0]),
            **totals[editions[0].id],
            "by_state": by_state,
        }

    return {
        "list_id": lst.id,
        "name": lst.name,
        "size": lst.size,
        "ever_listed": len(ever_listed),
        "current": current,
        "editions": [{**_edition_dict(e), **totals[e.id]} for e in editions],
        "courses": sorted(
            ranked_courses.values(),
            key=lambda c: (c["current_rank"] is None, c["current_rank"] or 0, c["name"]),
        ),
    }
