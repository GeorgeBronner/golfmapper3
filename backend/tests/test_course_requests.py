import bcrypt
import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses, UserCourses, Users

from .utils import TestingSessionLocal, app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

# override_get_current_user returns id=1, role="admin"
ADMIN_USER = {"username": "georgetest", "id": 1, "role": "admin"}
NORMAL_USER = {"username": "normaluser", "id": 2, "role": "user"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_requests():
    """Wipe course_requests (and dependent tables) between every test."""
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM course_requests;"))
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.execute(text("DELETE FROM users;"))
        con.commit()


@pytest.fixture
def admin_user():
    user = Users(
        id=1, email="admin@test.com", username="georgetest",
        first_name="Admin", last_name="User",
        hashed_password=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
        is_active=True, role="admin",
    )
    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def normal_user():
    user = Users(
        id=2, email="normal@test.com", username="normaluser",
        first_name="Normal", last_name="User",
        hashed_password=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
        is_active=True, role="user",
    )
    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def existing_course():
    course = Courses(
        id=300, club_name="Test Club", course_name="Test Course",
        city="Testville", state="TX", country="US",
        latitude=30.0, longitude=-97.0,
    )
    db = TestingSessionLocal()
    db.add(course)
    db.commit()
    return course


# ── Submit new course ─────────────────────────────────────────────────────────

def test_submit_new_course(admin_user):
    resp = client.post("/api/v1/course-requests/new-course", json={
        "club_name": "New Club",
        "course_name": "New Course",
        "city": "Dallas",
        "state": "TX",
        "country": "US",
        "latitude": 32.7767,
        "longitude": -96.7970,
    })
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["request_type"] == "new_course"
    assert data["status"] == "pending"
    assert data["latitude"] == pytest.approx(32.7767)
    assert data["club_name"] == "New Club"


def test_submit_new_course_unauthenticated():
    # Remove the auth override so the real bearer-token dependency runs:
    # a request without an Authorization header must get a 401.
    app.dependency_overrides.pop(get_current_user, None)
    try:
        resp = client.post("/api/v1/course-requests/new-course", json={
            "club_name": "Some Club", "latitude": 32.0, "longitude": -97.0,
        })
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_submit_new_course_requires_name(admin_user):
    resp = client.post("/api/v1/course-requests/new-course", json={
        "latitude": 32.0, "longitude": -97.0,
    })
    assert resp.status_code == 422


# ── Submit location change ────────────────────────────────────────────────────

def test_submit_location_change(admin_user, existing_course):
    resp = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300,
        "latitude": 31.0,
        "longitude": -96.0,
    })
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["request_type"] == "location_change"
    assert data["status"] == "pending"
    assert data["course_id"] == 300
    assert data["original_latitude"] == pytest.approx(30.0)
    assert data["original_longitude"] == pytest.approx(-97.0)
    assert data["latitude"] == pytest.approx(31.0)


def test_submit_location_change_course_not_found(admin_user):
    resp = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 9999,
        "latitude": 31.0,
        "longitude": -96.0,
    })
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_submit_location_change_duplicate_pending_blocked(admin_user, existing_course):
    payload = {"course_id": 300, "latitude": 31.0, "longitude": -96.0}
    client.post("/api/v1/course-requests/location-change", json=payload)
    resp = client.post("/api/v1/course-requests/location-change", json=payload)
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert "pending" in resp.json()["detail"].lower()


# ── My requests ───────────────────────────────────────────────────────────────

def test_my_requests_only_own(admin_user, normal_user, existing_course):
    # Admin user (id=1) submits one request
    client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.0, "longitude": -96.0,
    })

    # Switch to normal user (id=2) who submits a different request and checks their own list
    app.dependency_overrides[get_current_user] = lambda: NORMAL_USER
    try:
        client.post("/api/v1/course-requests/new-course", json={
            "club_name": "Other Club", "latitude": 29.0, "longitude": -95.0,
        })
        resp = client.get("/api/v1/course-requests/my-requests")
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user

    data = resp.json()
    assert len(data) == 1
    assert data[0]["request_type"] == "new_course"
    assert data[0]["club_name"] == "Other Club"


# ── Admin approve ─────────────────────────────────────────────────────────────

def test_admin_approve_new_course_creates_course_and_user_courses(admin_user):
    submit = client.post("/api/v1/course-requests/new-course", json={
        "club_name": "Approved Club", "course_name": "Approved Course",
        "city": "Houston", "state": "TX", "country": "US",
        "latitude": 29.7604, "longitude": -95.3698,
    })
    req_id = submit.json()["id"]

    resp = client.post(f"/api/v1/course-requests/admin/{req_id}/approve")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "approved"
    assert data["approved_course_id"] is not None

    # Course should now exist in the DB
    db = TestingSessionLocal()
    course = db.query(Courses).filter(Courses.club_name == "Approved Club").first()
    assert course is not None
    assert course.latitude == pytest.approx(29.7604)
    assert data["approved_course_id"] == course.id

    # And be added to the submitting user's course list
    uc = db.query(UserCourses).filter(UserCourses.course_id == course.id, UserCourses.user_id == 1).first()
    assert uc is not None
    assert uc.year is None
    db.close()


def test_admin_approve_location_change_updates_course(admin_user, existing_course):
    submit = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.5, "longitude": -96.5,
    })
    req_id = submit.json()["id"]

    resp = client.post(f"/api/v1/course-requests/admin/{req_id}/approve")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "approved"

    db = TestingSessionLocal()
    course = db.query(Courses).filter(Courses.id == 300).first()
    assert course.latitude == pytest.approx(31.5)
    assert course.longitude == pytest.approx(-96.5)
    db.close()


def test_admin_approve_already_actioned_returns_409(admin_user, existing_course):
    submit = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.5, "longitude": -96.5,
    })
    req_id = submit.json()["id"]
    client.post(f"/api/v1/course-requests/admin/{req_id}/approve")

    resp = client.post(f"/api/v1/course-requests/admin/{req_id}/approve")
    assert resp.status_code == status.HTTP_409_CONFLICT


# ── Admin reject ──────────────────────────────────────────────────────────────

def test_admin_reject_stores_message(admin_user, existing_course):
    submit = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.0, "longitude": -96.0,
    })
    req_id = submit.json()["id"]

    resp = client.post(f"/api/v1/course-requests/admin/{req_id}/reject", json={
        "message": "Location appears incorrect."
    })
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["review_message"] == "Location appears incorrect."


def test_admin_reject_requires_message(admin_user, existing_course):
    submit = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.0, "longitude": -96.0,
    })
    req_id = submit.json()["id"]

    resp = client.post(f"/api/v1/course-requests/admin/{req_id}/reject", json={"message": ""})
    assert resp.status_code == 422


def test_admin_reject_already_actioned_returns_409(admin_user, existing_course):
    submit = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.0, "longitude": -96.0,
    })
    req_id = submit.json()["id"]
    client.post(f"/api/v1/course-requests/admin/{req_id}/reject", json={"message": "No."})

    resp = client.post(f"/api/v1/course-requests/admin/{req_id}/reject", json={"message": "Again."})
    assert resp.status_code == status.HTTP_409_CONFLICT


# ── Admin list ────────────────────────────────────────────────────────────────

def test_admin_list_pending_only_by_default(admin_user, existing_course):
    submit = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.0, "longitude": -96.0,
    })
    req_id = submit.json()["id"]
    client.post(f"/api/v1/course-requests/admin/{req_id}/reject", json={"message": "No."})

    resp = client.get("/api/v1/course-requests/admin/all")
    assert resp.status_code == status.HTTP_200_OK
    # Rejected request should not appear in default pending-only view
    assert all(r["status"] == "pending" for r in resp.json())


def test_admin_list_all_when_flag_false(admin_user, existing_course):
    submit = client.post("/api/v1/course-requests/location-change", json={
        "course_id": 300, "latitude": 31.0, "longitude": -96.0,
    })
    req_id = submit.json()["id"]
    client.post(f"/api/v1/course-requests/admin/{req_id}/reject", json={"message": "No."})

    resp = client.get("/api/v1/course-requests/admin/all?pending_only=false")
    assert resp.status_code == status.HTTP_200_OK
    assert any(r["status"] == "rejected" for r in resp.json())


def test_non_admin_cannot_access_admin_list(admin_user):
    app.dependency_overrides[get_current_user] = lambda: NORMAL_USER
    try:
        resp = client.get("/api/v1/course-requests/admin/all")
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user
    assert resp.status_code == status.HTTP_403_FORBIDDEN
