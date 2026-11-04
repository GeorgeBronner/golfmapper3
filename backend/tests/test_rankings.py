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
                id=1,
                club_name="Pebble Beach",
                course_name="Pebble Beach Golf Links",
                city="Pebble Beach",
                state="CA",
                country="USA",
            ),
            Courses(id=2, club_name="Erin Hills", course_name="Erin Hills", city="Erin", state="WI", country="USA"),
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
    # The play year comes with the played flag, and the country with the state.
    assert [e["year"] for e in body["entries"]] == [None, 2024]
    assert [e["country"] for e in body["entries"]] == ["USA", "USA"]


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
    assert body["current"]["by_country"] == {"USA": {"ranked": 1, "played": 1}}
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


def test_progress_by_state_ignores_non_us_courses_with_colliding_state_codes():
    # Non-US courses store regional codes in `state` (KY = County Kerry): they must not count as Kentucky.
    db = TestingSessionLocal()
    db.add_all(
        [
            Courses(id=1, club_name="Ballybunion", course_name="Old", city="Ballybunion", state="KY", country="IRL"),
            Courses(
                id=2, club_name="Valderrama", course_name="Valderrama", city="Sotogrande", state="CA", country="ESP"
            ),
            Courses(id=3, club_name="Valhalla", course_name="Valhalla", city="Louisville", state="KY", country="USA"),
            RankingLists(id=1, slug="world", name="World", publisher="Golf Digest", scope="world", size=100),
            RankingEditions(id=1, list_id=1, label="2026-27", start_year=2026),
            RankingEntries(edition_id=1, course_id=1, rank=1, published_name="Ballybunion"),
            RankingEntries(edition_id=1, course_id=2, rank=2, published_name="Valderrama"),
            RankingEntries(edition_id=1, course_id=3, rank=3, published_name="Valhalla"),
            UserCourses(course_id=1, user_id=1, year=2024),
        ]
    )
    db.commit()
    db.close()
    try:
        current = client.get("/api/v1/rankings/lists/1/progress").json()["current"]
        assert current["by_state"] == {"KY": {"ranked": 1, "played": 0}}
        assert current["by_country"] == {
            "IRL": {"ranked": 1, "played": 1},
            "ESP": {"ranked": 1, "played": 0},
            "USA": {"ranked": 1, "played": 0},
        }
    finally:
        with engine.connect() as con:
            for table in ("user_courses", "ranking_entries", "ranking_editions", "ranking_lists", "courses"):
                con.execute(text(f"DELETE FROM {table};"))
            con.commit()


@pytest.fixture
def state_lists():
    db = TestingSessionLocal()
    db.add_all(
        [
            Courses(
                id=1, club_name="Kiawah Island", course_name="Ocean Course", city="Kiawah", state="SC", country="USA"
            ),
            Courses(id=2, club_name="Congaree", course_name="Congaree", city="Ridgeland", state="SC", country="USA"),
            Courses(
                id=3, club_name="Pebble Beach", course_name="Links", city="Pebble Beach", state="CA", country="USA"
            ),
            RankingLists(
                id=1, slug="bis-sc", name="Best Courses in South Carolina", publisher="GD", scope="us-state-SC"
            ),
            RankingLists(id=2, slug="bis-ca", name="Best Courses in California", publisher="GD", scope="us-state-CA"),
            RankingLists(id=3, slug="pub", name="Top Public", publisher="GD", scope="us-public", size=100),
            RankingEditions(id=1, list_id=1, label="2023-24", start_year=2023),
            RankingEditions(id=2, list_id=1, label="2025-26", start_year=2025),
            RankingEditions(id=3, list_id=2, label="2025-26", start_year=2025),
            RankingEditions(id=4, list_id=3, label="2025-26", start_year=2025),
            RankingEntries(edition_id=1, course_id=2, rank=1, published_name="Congaree"),
            RankingEntries(edition_id=2, course_id=2, rank=1, published_name="Congaree", access="private"),
            RankingEntries(
                edition_id=2, course_id=1, rank=2, published_name="Kiawah", access="public", rank_label="T2"
            ),
            RankingEntries(edition_id=3, course_id=3, rank=1, published_name="Pebble", access="public"),
            RankingEntries(edition_id=4, course_id=3, rank=1, published_name="Pebble"),
            UserCourses(course_id=1, user_id=1, year=2021),
            UserCourses(course_id=3, user_id=2, year=2020),
        ]
    )
    db.commit()
    db.close()
    yield
    with engine.connect() as con:
        for table in ("user_courses", "ranking_entries", "ranking_editions", "ranking_lists", "courses"):
            con.execute(text(f"DELETE FROM {table};"))
        con.commit()


def test_states_progress_uses_each_states_newest_edition(state_lists):
    res = client.get("/api/v1/rankings/states/progress")
    assert res.status_code == status.HTTP_200_OK
    states = res.json()["states"]
    # Only the state lists, keyed by code; the US Public list is not included.
    assert sorted(states) == ["CA", "SC"]
    assert states["SC"]["label"] == "2025-26"
    assert [(e["rank"], e["name"]) for e in states["SC"]["entries"]] == [
        (1, "Congaree"),
        (2, "Kiawah Island - Ocean Course"),
    ]


def test_states_progress_flags_played_courses_for_the_current_user_only(state_lists):
    states = client.get("/api/v1/rankings/states/progress").json()["states"]
    sc = {e["course_id"]: e for e in states["SC"]["entries"]}
    assert (sc[1]["played"], sc[1]["year"], sc[1]["rank_label"]) == (True, 2021, "T2")
    assert (sc[2]["played"], sc[2]["year"], sc[2]["access"]) == (False, None, "private")
    # User 2 played the California course, not user 1.
    assert states["CA"]["entries"][0]["played"] is False
