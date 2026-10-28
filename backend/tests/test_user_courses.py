import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses, UserCourses

from .utils import TestingSessionLocal, app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


def test_readall_authenticated(test_user_courses):
    response = client.get("/api/v1/user_courses/readall")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": 200,
            "user_course_id": None,
            "display_name": "RTJ Golf Trail at Magnolia Grove - Falls",
            "club_name": "RTJ Golf Trail at Magnolia Grove",
            "course_name": "Falls",
            "address": "7001 MAGNOLIA GROVE PKY",
            "city": "Mobile",
            "state": "Alabama",
            "country": "US",
            "latitude": 30.740501,
            "longitude": -88.20578,
            "created_at": None,
            "year": None,
        }
    ]


def test_read_one_authenticated(test_user_courses):
    response = client.get("/api/v1/user_courses/readall_ids")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{"course_id": 200, "user_id": 1, "year": 2021, "id": 1}]


def test_add_course_duplicate_returns_409(test_user_courses):
    response = client.post("/api/v1/user_courses/add_course", json={"garmin_id": 200, "year": 2021})
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already added" in response.json()["detail"]


def test_add_course_same_course_different_year_returns_409(test_user_courses):
    # A course can only be added once per user, regardless of year.
    response = client.post("/api/v1/user_courses/add_course", json={"garmin_id": 200, "year": 2023})
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already added" in response.json()["detail"]


def test_add_course_nonexistent_course_returns_404(test_user_courses):
    response = client.post("/api/v1/user_courses/add_course", json={"garmin_id": 99999, "year": 2023})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Course not found"


@pytest.fixture
def sparse_course():
    # Mirrors a course created from an approved new-course request: only one
    # name and coordinates, everything else NULL.
    db = TestingSessionLocal()
    db.add(
        Courses(
            id=300,
            club_name=None,
            course_name="Solo Course",
            city=None,
            state=None,
            country=None,
            latitude=30.0,
            longitude=-88.0,
        )
    )
    db.add(UserCourses(id=3, course_id=300, user_id=1, year=2025))
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.commit()


def test_readall_with_null_fields_returns_200(sparse_course):
    # Regression: CourseResponse required club_name/city/state/country, so one
    # course with NULLs in those columns 500'd the whole course list.
    for endpoint in ("/api/v1/user_courses/readall", "/api/v1/user_courses/readall_ids_w_year"):
        response = client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK, endpoint
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Solo Course"
        assert data[0]["club_name"] is None
        assert data[0]["city"] is None


def test_readall_ids_w_year_datetime_created_at(test_user_courses_with_datetime):
    # Regression: CourseResponse.created_at must accept datetime objects, not just str.
    # A str type annotation caused Pydantic v2 to raise string_type validation errors
    # and return 500 when the DB had real datetime values in courses.created_at.
    response = client.get("/api/v1/user_courses/readall_ids_w_year")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["created_at"] is not None
    assert data[0]["year"] == 2024


@pytest.fixture
def unmapped_course():
    db = TestingSessionLocal()
    db.add(
        Courses(id=400, club_name="No Pin", course_name="Yet", state="CA", country="USA", latitude=None, longitude=None)
    )
    db.add(
        Courses(
            id=401, club_name="Pinned", course_name="Course", state="CA", country="USA", latitude=30.0, longitude=-88.0
        )
    )
    db.add(UserCourses(id=4, course_id=400, user_id=1, year=2022))
    db.add(UserCourses(id=5, course_id=401, user_id=1, year=2023))
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.commit()


def test_readall_ids_w_year_skips_unmapped_courses_by_default(unmapped_course):
    data = client.get("/api/v1/user_courses/readall_ids_w_year").json()
    assert [c["id"] for c in data] == [401]


def test_readall_ids_w_year_can_include_unmapped_courses(unmapped_course):
    response = client.get("/api/v1/user_courses/readall_ids_w_year", params={"include_unmapped": True})
    assert response.status_code == status.HTTP_200_OK
    data = {c["id"]: c for c in response.json()}
    assert set(data) == {400, 401}
    assert data[400]["latitude"] is None
    assert data[400]["year"] == 2022
