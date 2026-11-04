import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses, RankingEditions, RankingEntries, RankingLists, UserCourses, Users
from app.routers.map import _dedupe

from .utils import TestingSessionLocal, app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

XSS_NAME = '<script>alert("xss")</script>'


# ── JSON points endpoints ─────────────────────────────────────────────────────


@pytest.fixture
def points_data():
    db = TestingSessionLocal()
    db.add_all(
        [
            Users(
                id=1,
                email="a@mail.com",
                username="alice",
                first_name="a",
                last_name="a",
                hashed_password="x",
                is_active=True,
                role="user",
            ),
            Users(
                id=2,
                email="b@mail.com",
                username="bob",
                first_name="b",
                last_name="b",
                hashed_password="x",
                is_active=True,
                role="user",
            ),
            Users(
                id=3,
                email="c@mail.com",
                username="carol",
                first_name="c",
                last_name="c",
                hashed_password="x",
                is_active=False,
                role="user",
            ),
            Courses(id=401, club_name=XSS_NAME, course_name=None, state="AL", latitude=30.740501, longitude=-88.20578),
            Courses(id=402, club_name="Club", course_name="West", state="AL", latitude=31.0, longitude=-87.0),
            Courses(id=403, club_name="Nowhere", course_name=None, state="AL", latitude=None, longitude=None),
            UserCourses(id=1, course_id=401, user_id=1, year=2024),
            UserCourses(id=2, course_id=403, user_id=1, year=2023),
            UserCourses(id=3, course_id=402, user_id=2, year=None),
            UserCourses(id=4, course_id=402, user_id=3, year=2020),
        ]
    )
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.execute(text("DELETE FROM users;"))
        con.commit()


def test_user_points_only_own_courses_with_coordinates(points_data):
    response = client.get("/api/v1/map/points")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "fields": ["id", "lat", "lon", "name", "year"],
        # Raw name: escaping is the client's job (rendered as text).
        "points": [[401, 30.7405, -88.20578, XSS_NAME, 2024]],
    }


def test_all_points_groups_active_users(points_data):
    response = client.get("/api/v1/map/all_points")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["fields"] == ["id", "lat", "lon", "name", "year"]
    assert data["users"] == [
        {"username": "alice", "points": [[401, 30.7405, -88.20578, XSS_NAME, 2024]]},
        {"username": "bob", "points": [[402, 31.0, -87.0, "Club - West", None]]},
    ]


@pytest.fixture
def ranking_data(points_data):
    db = TestingSessionLocal()
    db.add_all(
        [
            RankingLists(id=1, slug="l", name="Test List", publisher="Pub", scope="us-public", size=100),
            RankingLists(id=2, slug="empty", name="Empty List", publisher="Pub", scope="us-public"),
            RankingEditions(id=1, list_id=1, label="2023-24", start_year=2023),
            RankingEditions(id=2, list_id=1, label="2025-26", start_year=2025),
            # Old edition: must not appear. 403 has no coordinates: must be left out.
            RankingEntries(edition_id=1, course_id=401, rank=1, published_name="Old"),
            RankingEntries(edition_id=2, course_id=402, rank=1, access="public", published_name="West"),
            RankingEntries(edition_id=2, course_id=401, rank=2, rank_label="T2", published_name="Xss"),
            RankingEntries(edition_id=2, course_id=403, rank=3, published_name="Nowhere"),
        ]
    )
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM ranking_entries;"))
        con.execute(text("DELETE FROM ranking_editions;"))
        con.execute(text("DELETE FROM ranking_lists;"))
        con.commit()


def test_ranking_points_newest_edition_in_rank_order(ranking_data):
    response = client.get("/api/v1/map/rankings/1/points")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "fields": ["id", "lat", "lon", "name", "year", "rank", "rank_label", "access"],
        "list": "Test List",
        "edition_id": 2,
        "edition": "2025-26",
        "points": [
            [402, 31.0, -87.0, "Club - West", 2025, 1, None, "public"],
            [401, 30.7405, -88.20578, XSS_NAME, 2025, 2, "T2", None],
        ],
    }


def test_ranking_points_for_a_chosen_edition(ranking_data):
    data = client.get("/api/v1/map/rankings/1/points?edition_id=1").json()
    assert data["edition"] == "2023-24"
    assert data["points"] == [[401, 30.7405, -88.20578, XSS_NAME, 2023, 1, None, None]]


def test_ranking_points_edition_of_another_list_is_404(ranking_data):
    assert client.get("/api/v1/map/rankings/2/points?edition_id=1").status_code == status.HTTP_404_NOT_FOUND


def test_ranking_points_list_without_editions(ranking_data):
    data = client.get("/api/v1/map/rankings/2/points").json()
    assert data["edition"] is None
    assert data["points"] == []


def test_ranking_points_unknown_list_is_404(ranking_data):
    assert client.get("/api/v1/map/rankings/99/points").status_code == status.HTTP_404_NOT_FOUND


@pytest.fixture
def state_data(points_data):
    """Two state lists (TX, AL) with 2023-24 and 2025-26 editions, plus a non-state list that must be ignored."""
    db = TestingSessionLocal()
    db.add_all(
        [
            RankingLists(id=10, slug="bis-tx", name="Best Courses in Texas", publisher="GD", scope="us-state-TX"),
            RankingLists(id=11, slug="bis-al", name="Best Courses in Alabama", publisher="GD", scope="us-state-AL"),
            RankingLists(id=12, slug="world", name="World", publisher="GD", scope="world", size=100),
            RankingEditions(id=10, list_id=10, label="2023-24", start_year=2023),
            RankingEditions(id=11, list_id=10, label="2025-26", start_year=2025),
            RankingEditions(id=12, list_id=11, label="2025-26", start_year=2025),
            RankingEditions(id=13, list_id=12, label="2026-27", start_year=2026),
            RankingEntries(edition_id=10, course_id=401, rank=1, published_name="Old"),
            RankingEntries(edition_id=11, course_id=401, rank=2, access="private", published_name="Xss"),
            RankingEntries(edition_id=11, course_id=403, rank=1, published_name="Nowhere"),
            RankingEntries(edition_id=12, course_id=402, rank=1, rank_label="T1", access="public", published_name="W"),
            RankingEntries(edition_id=13, course_id=402, rank=5, published_name="World"),
        ]
    )
    db.commit()
    yield
    with engine.connect() as con:
        for table in ("ranking_entries", "ranking_editions", "ranking_lists"):
            con.execute(text(f"DELETE FROM {table};"))
        con.commit()


def test_state_ranking_points_newest_edition_across_states(state_data):
    response = client.get("/api/v1/map/rankings/states/points")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["fields"] == ["id", "lat", "lon", "name", "year", "rank", "rank_label", "access", "list"]
    assert data["edition"] == "2025-26"  # the world list's 2026-27 is not a state list
    # Ordered by state list name, then rank; 403 has no coordinates.
    assert data["points"] == [
        [402, 31.0, -87.0, "Club - West", 2025, 1, "T1", "public", "Best Courses in Alabama"],
        [401, 30.7405, -88.20578, XSS_NAME, 2025, 2, None, "private", "Best Courses in Texas"],
    ]


def test_state_ranking_points_for_an_older_edition(state_data):
    data = client.get("/api/v1/map/rankings/states/points?edition=2023-24").json()
    assert data["edition"] == "2023-24"
    assert [p[0] for p in data["points"]] == [401]


def test_state_ranking_points_unknown_edition_is_404(state_data):
    assert client.get("/api/v1/map/rankings/states/points?edition=1999-00").status_code == status.HTTP_404_NOT_FOUND


def test_state_ranking_points_without_state_lists(points_data):
    data = client.get("/api/v1/map/rankings/states/points").json()
    assert data["edition"] is None and data["points"] == []


def test_dedupe_keeps_one_point_per_course_with_latest_year():
    # Legacy DBs (old user/course/year constraint) can hold a course several
    # times for one user; the test schema can't, so exercise the helper.
    rows = [
        (401, 30.0, -88.0, "Club", None, 2023),
        (401, 30.0, -88.0, "Club", None, None),
        (401, 30.0, -88.0, "Club", None, 2024),
        (402, 31.0, -87.0, "Other", None, None),
    ]
    assert _dedupe(rows) == [[401, 30.0, -88.0, "Club", 2024], [402, 31.0, -87.0, "Other", None]]
