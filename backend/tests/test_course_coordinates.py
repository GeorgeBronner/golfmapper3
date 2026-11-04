"""Every endpoint that adds or moves a course must require valid coordinates."""

import sys
from pathlib import Path

import pytest
from fastapi import status
from pydantic import ValidationError
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


# ── Map course entry tool (backend/scripts/map_course_entry.py) ───────────────


@pytest.fixture(scope="module")
def entry_course_model():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from map_course_entry import CourseCreate

    return CourseCreate


ENTRY_FIELDS = {"club_name": "Club", "course_name": "Course", "city": "Dallas", "state": "TX", "country": "USA"}


@pytest.mark.parametrize(
    "lat,lon",
    [(0, 0), (90, 180), (-90, -180), (32.5, -97.25)],
    ids=["zero", "upper-bounds", "lower-bounds", "typical"],
)
def test_entry_tool_accepts_valid_coordinates(entry_course_model, lat, lon):
    course = entry_course_model(**ENTRY_FIELDS, latitude=lat, longitude=lon)
    assert (course.latitude, course.longitude) == (lat, lon)


@pytest.mark.parametrize(
    "lat,lon",
    [(90.1, 0), (-90.1, 0), (0, 180.1), (0, -180.1), ("abc", 0), (0, "abc"), (None, 0), (0, None)],
    ids=["lat-high", "lat-low", "lon-high", "lon-low", "lat-text", "lon-text", "lat-null", "lon-null"],
)
def test_entry_tool_rejects_bad_coordinates(entry_course_model, lat, lon):
    with pytest.raises(ValidationError):
        entry_course_model(**ENTRY_FIELDS, latitude=lat, longitude=lon)
