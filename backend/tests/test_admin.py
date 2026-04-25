from .utils import *
from app.dependencies import get_db, get_current_user
from fastapi import status

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


def test_admin_root_as_admin():
    response = client.get("/admin/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Hello Admin"}


def test_admin_root_as_non_admin():
    app.dependency_overrides[get_current_user] = lambda: {"username": "other", "id": 2, "role": "user"}
    response = client.get("/admin/")
    app.dependency_overrides[get_current_user] = override_get_current_user
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_read_all_courses(test_user_courses):
    response = client.get("/admin/courses")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert any(c["id"] == 200 for c in data)


def test_admin_delete_course(test_user_courses):
    response = client.delete("/admin/courses/200")
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_admin_delete_course_not_found():
    response = client.delete("/admin/courses/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}
