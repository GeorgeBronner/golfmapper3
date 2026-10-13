import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses, UserCourses, Users
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
