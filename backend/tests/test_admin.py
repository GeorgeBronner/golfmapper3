import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses, Users

from .utils import TestingSessionLocal, app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


def test_admin_root_as_admin():
    response = client.get("/api/v1/admin/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Hello Admin"}


def test_admin_root_as_non_admin():
    app.dependency_overrides[get_current_user] = lambda: {"username": "other", "id": 2, "role": "user"}
    response = client.get("/api/v1/admin/")
    app.dependency_overrides[get_current_user] = override_get_current_user
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_read_all_courses(test_user_courses):
    response = client.get("/api/v1/admin/courses")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert any(c["id"] == 200 for c in data)


def test_admin_delete_course(test_user_courses):
    response = client.delete("/api/v1/admin/courses/200")
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_admin_delete_course_not_found():
    response = client.delete("/api/v1/admin/courses/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


# ── Edit course info ──────────────────────────────────────────────────────────


def test_admin_update_course_info(test_user_courses):
    response = client.put(
        "/api/v1/admin/courses/200/info",
        json={
            "club_name": "Updated Club",
            "course_name": "Updated Course",
            "city": "New City",
            "state": "CA",
            "country": "USA",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["club_name"] == "Updated Club"
    assert data["course_name"] == "Updated Course"
    assert data["city"] == "New City"
    assert data["state"] == "CA"


def test_admin_update_course_info_partial(test_user_courses):
    response = client.put("/api/v1/admin/courses/200/info", json={"city": "Partial City"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["city"] == "Partial City"
    # Other fields unchanged
    assert data["club_name"] == "RTJ Golf Trail at Magnolia Grove"


def test_admin_update_course_info_not_found():
    response = client.put("/api/v1/admin/courses/99999/info", json={"city": "Nowhere"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


def test_admin_update_course_info_non_admin(test_user_courses):
    app.dependency_overrides[get_current_user] = lambda: {"username": "other", "id": 2, "role": "user"}
    try:
        response = client.put("/api/v1/admin/courses/200/info", json={"city": "Sneaky"})
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── Activate / deactivate users ───────────────────────────────────────────────


@pytest.fixture
def second_user():
    db = TestingSessionLocal()
    db.add(
        Users(
            id=2,
            email="other@mail.com",
            username="other",
            first_name="o",
            last_name="u",
            hashed_password="not-used",
            is_active=True,
            role="user",
        )
    )
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM users;"))
        con.commit()


def test_admin_deactivate_and_reactivate_user(second_user):
    response = client.patch("/api/v1/admin/users/2/active", json={"is_active": False})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] is False

    response = client.patch("/api/v1/admin/users/2/active", json={"is_active": True})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] is True


def test_admin_cannot_deactivate_self():
    # override_get_current_user is user id 1
    response = client.patch("/api/v1/admin/users/1/active", json={"is_active": False})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_admin_deactivate_user_not_found():
    response = client.patch("/api/v1/admin/users/99999/active", json={"is_active": False})
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ── Role changes ──────────────────────────────────────────────────────────────


def test_admin_update_user_role(second_user):
    response = client.patch("/api/v1/admin/users/2/role", json={"role": "admin"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["role"] == "admin"


def test_admin_cannot_demote_self():
    # override_get_current_user is user id 1
    response = client.patch("/api/v1/admin/users/1/role", json={"role": "user"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "You cannot remove your own admin role"}


# ── Course map points ─────────────────────────────────────────────────────────


@pytest.fixture
def map_courses():
    db = TestingSessionLocal()
    db.add_all(
        [
            Courses(
                id=501,
                club_name="Tampa Club",
                course_name="North",
                state="FL",
                country="USA",
                latitude=27.9506123,
                longitude=-82.4571987,
            ),
            Courses(
                id=502,
                club_name="Miami Club",
                course_name="Miami Club",
                state=" fl ",
                country="usa",
                latitude=25.7617,
                longitude=-80.1918,
            ),
            Courses(
                id=503,
                club_name="No Coords",
                course_name=None,
                state="FL",
                country="USA",
                latitude=None,
                longitude=None,
            ),
            Courses(
                id=504,
                club_name="Peach",
                course_name="East",
                state="GA",
                country="USA",
                latitude=33.749,
                longitude=-84.388,
            ),
            Courses(
                id=506,
                club_name="Blank Country",
                state="WA",
                country="  ",
                latitude=47.6,
                longitude=-122.3,
            ),
            Courses(
                id=507,
                club_name="Null Country",
                state="WA",
                country=None,
                latitude=47.7,
                longitude=-122.4,
            ),
            Courses(
                id=508,
                club_name="US Washington",
                state="WA",
                country="USA",
                latitude=47.8,
                longitude=-122.5,
            ),
            Courses(
                id=509,
                club_name="Toronto Club",
                state="ON",
                country="CAN",
                latitude=43.65,
                longitude=-79.38,
            ),
            Courses(
                id=510,
                club_name="Vancouver Club",
                state="BC",
                country=" can",
                latitude=49.28,
                longitude=-123.12,
            ),
            Courses(
                id=511,
                club_name="St Andrews",
                state="Fife",
                country="GBR",
                latitude=56.34,
                longitude=-2.80,
            ),
            Courses(
                id=505,
                club_name="Stateless",
                course_name=None,
                state=None,
                country="USA",
                latitude=40.0,
                longitude=-90.0,
            ),
        ]
    )
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM courses;"))
        con.commit()


def test_course_points_requires_admin(map_courses):
    app.dependency_overrides[get_current_user] = lambda: {"username": "other", "id": 2, "role": "user"}
    try:
        assert client.get("/api/v1/admin/courses/points").status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/admin/courses/regions").status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user


def test_course_points_all_excludes_missing_coordinates(map_courses):
    response = client.get("/api/v1/admin/courses/points")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["fields"] == ["id", "lat", "lon", "name"]
    assert [p[0] for p in data["points"]] == [501, 502, 504, 505, 506, 507, 508, 509, 510, 511]


@pytest.mark.parametrize("state", ["FL", "fl", "  Fl "])
def test_course_points_state_filter_normalizes(map_courses, state):
    response = client.get("/api/v1/admin/courses/points", params={"state": state})
    assert response.status_code == status.HTTP_200_OK
    points = response.json()["points"]
    assert points == [
        [501, 27.95061, -82.4572, "Tampa Club - North"],
        [502, 25.7617, -80.1918, "Miami Club"],
    ]


def test_course_points_country_filter(map_courses):
    response = client.get("/api/v1/admin/courses/points", params={"state": "fl", "country": "CAN"})
    assert response.json()["points"] == []
    response = client.get("/api/v1/admin/courses/points", params={"state": "fl", "country": " USA"})
    assert len(response.json()["points"]) == 2


def test_course_points_empty_country_matches_missing_country(map_courses):
    response = client.get("/api/v1/admin/courses/points", params={"state": "WA", "country": ""})
    assert sorted(p[0] for p in response.json()["points"]) == [506, 507]


def test_course_regions_lists_us_states_then_countries(map_courses):
    response = client.get("/api/v1/admin/courses/regions")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        # Only US states — provinces/regions of other countries aren't listed.
        "us_states": [
            {"state": "FL", "count": 2},
            {"state": "GA", "count": 1},
            {"state": "WA", "count": 1},
        ],
        "countries": [
            {"country": "CAN", "count": 2},
            {"country": "GBR", "count": 1},
            {"country": "USA", "count": 5},
            {"country": None, "count": 2},
        ],
    }


def test_course_points_whole_country(map_courses):
    response = client.get("/api/v1/admin/courses/points", params={"country": "CAN"})
    assert [p[0] for p in response.json()["points"]] == [509, 510]


def test_course_points_gzipped_when_large(map_courses):
    db = TestingSessionLocal()
    db.add_all(
        [
            Courses(id=600 + i, club_name=f"Bulk {i}", state="TX", country="USA", latitude=30.0, longitude=-97.0)
            for i in range(50)
        ]
    )
    db.commit()
    response = client.get("/api/v1/admin/courses/points", params={"state": "TX"}, headers={"Accept-Encoding": "gzip"})
    assert response.headers.get("content-encoding") == "gzip"
    assert len(response.json()["points"]) == 50
    # Security headers still applied to the compressed response.
    assert "Content-Security-Policy" in response.headers
