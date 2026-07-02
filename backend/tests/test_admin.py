import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Users

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
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── Activate / deactivate users ───────────────────────────────────────────────

@pytest.fixture
def second_user():
    db = TestingSessionLocal()
    db.add(Users(
        id=2, email="other@mail.com", username="other", first_name="o", last_name="u",
        hashed_password="not-used", is_active=True, role="user",
    ))
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
