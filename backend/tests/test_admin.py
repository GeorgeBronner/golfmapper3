from fastapi import status

from app.dependencies import get_current_user, get_db

from .utils import app, client, override_get_current_user, override_get_db

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
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


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
    response = client.put("/api/v1/admin/courses/200/info", json={
        "club_name": "Updated Club",
        "course_name": "Updated Course",
        "city": "New City",
        "state": "CA",
        "country": "US",
    })
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
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
