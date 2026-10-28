import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses, RankingEditions, RankingEntries, RankingLists, UserCourses
from app.routers.rankings import _played_years

from .utils import TestingSessionLocal, app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture
def rankings_data():
    db = TestingSessionLocal()
    db.add_all(
        [
            Courses(
                id=1, club_name="Pebble Beach", course_name="Pebble Beach Golf Links", city="Pebble Beach", state="CA"
            ),
            Courses(id=2, club_name="Erin Hills", course_name="Erin Hills", city="Erin", state="WI"),
            RankingLists(id=1, slug="gd-pub", name="Top Public", publisher="Golf Digest", scope="us-public", size=100),
            RankingEditions(id=1, list_id=1, label="2023-24", start_year=2023),
            RankingEditions(id=2, list_id=1, label="2025-26", start_year=2025),
            RankingEntries(edition_id=1, course_id=1, rank=1, published_name="Pebble Beach Golf Links", points=70.5),
            RankingEntries(edition_id=1, course_id=2, rank=2, prior_rank="T5", published_name="Erin Hills"),
            RankingEntries(edition_id=2, course_id=1, rank=1, prior_rank="1", published_name="Pebble Beach Golf Links"),
            UserCourses(course_id=2, user_id=1, year=2024),
        ]
    )
    db.commit()
    db.close()
    yield
    with engine.connect() as con:
        for table in ("user_courses", "ranking_entries", "ranking_editions", "ranking_lists", "courses"):
            con.execute(text(f"DELETE FROM {table};"))
        con.commit()


def test_list_rankings_newest_edition_first(rankings_data):
    res = client.get("/api/v1/rankings")
    assert res.status_code == status.HTTP_200_OK
    [lst] = res.json()
    assert lst["slug"] == "gd-pub"
    assert [e["label"] for e in lst["editions"]] == ["2025-26", "2023-24"]


def test_edition_entries_flags_played_courses(rankings_data):
    res = client.get("/api/v1/rankings/editions/1")
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert [e["rank"] for e in body["entries"]] == [1, 2]
    assert [e["played"] for e in body["entries"]] == [False, True]
    assert body["entries"][1]["prior_rank"] == "T5"
    assert body["entries"][0]["name"] == "Pebble Beach - Pebble Beach Golf Links"


def test_edition_not_found(rankings_data):
    assert client.get("/api/v1/rankings/editions/999").status_code == status.HTTP_404_NOT_FOUND


def test_course_history_oldest_first(rankings_data):
    res = client.get("/api/v1/rankings/courses/1")
    assert res.status_code == status.HTTP_200_OK
    assert [(h["edition"], h["rank"]) for h in res.json()] == [("2023-24", 1), ("2025-26", 1)]


def test_course_history_empty_for_unranked_course(rankings_data):
    res = client.get("/api/v1/rankings/courses/12345")
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == []


def test_progress_list_not_found(rankings_data):
    assert client.get("/api/v1/rankings/lists/999/progress").status_code == status.HTTP_404_NOT_FOUND


def test_progress_counts_per_edition_and_flags_dropped_courses(rankings_data):
    # The user played Erin Hills (2024), which is in 2023-24 but not the current 2025-26.
    body = client.get("/api/v1/rankings/lists/1/progress").json()
    assert body["name"] == "Top Public"
    assert body["current"]["label"] == "2025-26"
    assert body["ever_listed"] == 2
    assert (body["current"]["total"], body["current"]["played"]) == (1, 0)
    assert [(e["label"], e["total"], e["played"]) for e in body["editions"]] == [("2025-26", 1, 0), ("2023-24", 2, 1)]
    [course] = body["courses"]
    assert (course["course_id"], course["year"], course["current_rank"]) == (2, 2024, None)
    assert course["ranks"] == {"2023-24": 2}


def test_progress_by_state_and_current_rank(rankings_data):
    db = TestingSessionLocal()
    db.add(UserCourses(course_id=1, user_id=1, year=2019))
    db.commit()
    db.close()

    body = client.get("/api/v1/rankings/lists/1/progress").json()
    assert body["current"]["by_state"] == {"CA": {"ranked": 1, "played": 1}}
    # Ranked courses come first, in current-rank order; dropped ones follow.
    assert [c["course_id"] for c in body["courses"]] == [1, 2]
    assert body["courses"][0]["current_rank"] == 1
    assert body["courses"][0]["ranks"] == {"2023-24": 1, "2025-26": 1}
    assert body["courses"][0]["year"] == 2019


def test_progress_ignores_other_users_courses(rankings_data):
    db = TestingSessionLocal()
    db.add(UserCourses(course_id=1, user_id=2, year=2020))
    db.commit()
    db.close()

    body = client.get("/api/v1/rankings/lists/1/progress").json()
    assert [c["course_id"] for c in body["courses"]] == [2]
    assert body["current"]["played"] == 0


def test_progress_list_without_editions(rankings_data):
    db = TestingSessionLocal()
    db.add(RankingLists(id=2, slug="empty", name="Empty", publisher="X", scope="x"))
    db.commit()
    db.close()
    try:
        body = client.get("/api/v1/rankings/lists/2/progress").json()
        assert body == {
            "list_id": 2,
            "name": "Empty",
            "size": None,
            "ever_listed": 0,
            "current": None,
            "editions": [],
            "courses": [],
        }
    finally:
        db = TestingSessionLocal()
        db.query(RankingLists).filter_by(id=2).delete()
        db.commit()
        db.close()


def test_played_years_keeps_latest_year_for_duplicate_rows():
    assert _played_years([(1, 2018), (1, 2022), (1, 2020), (2, None), (3, None), (3, 2015)]) == {
        1: 2022,
        2: None,
        3: 2015,
    }


def test_progress_year_is_null_when_unknown(rankings_data):
    db = TestingSessionLocal()
    db.add(UserCourses(course_id=1, user_id=1, year=None))
    db.commit()
    db.close()

    body = client.get("/api/v1/rankings/lists/1/progress").json()
    assert body["courses"][0]["year"] is None


def test_progress_by_state_normalizes_state_text(rankings_data):
    db = TestingSessionLocal()
    db.get(Courses, 1).state = " ca "
    db.add(UserCourses(course_id=1, user_id=1, year=2019))
    db.commit()
    db.close()

    body = client.get("/api/v1/rankings/lists/1/progress").json()
    assert body["current"]["by_state"] == {"CA": {"ranked": 1, "played": 1}}
