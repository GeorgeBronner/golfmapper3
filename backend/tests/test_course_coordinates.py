"""Every endpoint that adds or moves a course must require valid coordinates."""

import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses

from .utils import TestingSessionLocal, app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

BASE = "/api/v1"
GOOD = {"latitude": 32.0, "longitude": -97.0}

BAD_COORDS = [
    pytest.param({"longitude": -97.0}, id="missing-latitude"),
    pytest.param({"latitude": 32.0}, id="missing-longitude"),
    pytest.param({"latitude": None, "longitude": -97.0}, id="null-latitude"),
    pytest.param({"latitude": 32.0, "longitude": None}, id="null-longitude"),
    pytest.param({"latitude": 91.0, "longitude": -97.0}, id="latitude-too-high"),
    pytest.param({"latitude": -91.0, "longitude": -97.0}, id="latitude-too-low"),
    pytest.param({"latitude": 32.0, "longitude": 181.0}, id="longitude-too-high"),
    pytest.param({"latitude": 32.0, "longitude": -181.0}, id="longitude-too-low"),
    pytest.param({"latitude": "abc", "longitude": -97.0}, id="latitude-not-a-number"),
]

# (method, url, fields besides coordinates)
ENDPOINTS = [
    pytest.param("post", f"{BASE}/admin/courses", {"club_name": "Club"}, id="admin-create"),
    pytest.param("put", f"{BASE}/admin/courses/300/location", {}, id="admin-location"),
    pytest.param("post", f"{BASE}/course-requests/new-course", {"club_name": "Club"}, id="request-new-course"),
    pytest.param("post", f"{BASE}/course-requests/location-change", {"course_id": 300}, id="request-location-change"),
]


@pytest.fixture(autouse=True)
def course():
    db = TestingSessionLocal()
    db.add(Courses(id=300, club_name="Test Club", state="TX", country="US", latitude=30.0, longitude=-97.0))
    db.commit()
    db.close()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM course_requests;"))
        con.execute(text("DELETE FROM courses;"))
        con.commit()


@pytest.mark.parametrize("method,url,extra", ENDPOINTS)
@pytest.mark.parametrize("coords", BAD_COORDS)
def test_rejects_bad_coordinates(method, url, extra, coords):
    resp = getattr(client, method)(url, json={**extra, **coords})
    assert resp.status_code == 422


def test_admin_create_course_saves_coordinates():
    resp = client.post(f"{BASE}/admin/courses", json={"club_name": "Brand New", **GOOD})
    assert resp.status_code == status.HTTP_201_CREATED
    db = TestingSessionLocal()
    course = db.query(Courses).filter(Courses.club_name == "Brand New").one()
    assert (course.latitude, course.longitude) == (32.0, -97.0)
    db.close()


def test_admin_update_location_saves_coordinates():
    resp = client.put(f"{BASE}/admin/courses/300/location", json={"latitude": 40.5, "longitude": -80.25})
    assert resp.status_code == status.HTTP_200_OK
    db = TestingSessionLocal()
    course = db.query(Courses).filter(Courses.id == 300).one()
    assert (course.latitude, course.longitude) == (40.5, -80.25)
    db.close()
