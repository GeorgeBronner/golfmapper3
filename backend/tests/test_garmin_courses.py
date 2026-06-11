from fastapi import status

from app.dependencies import get_current_user, get_db

from .utils import app, client, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


def test_readall_courses(test_user_courses):
    response = client.get("/api/v1/garmin_courses/readall")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert any(c["id"] == 200 for c in data)


def test_read_course_found(test_user_courses):
    response = client.get("/api/v1/garmin_courses/course/200")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == 200


def test_read_course_not_found():
    response = client.get("/api/v1/garmin_courses/course/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Course not found"
