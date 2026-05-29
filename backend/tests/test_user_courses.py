from fastapi import status

from app.dependencies import get_current_user, get_db

from .utils import app, client, override_get_current_user, override_get_db

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
    assert response.json() == [
        {'course_id': 200, 'user_id': 1, 'year': 2021, 'id': 1}
    ]


def test_add_course_duplicate_returns_409(test_user_courses):
    response = client.post("/api/v1/user_courses/add_course", json={"garmin_id": 200, "year": 2021})
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already logged" in response.json()["detail"]


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
