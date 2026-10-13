import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.models import Courses, UserCourses, Users
from app.routers.map import generate_all_users_map, generate_user_map

from .utils import TestingSessionLocal, app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

XSS_NAME = '<script>alert("xss")</script>'
XSS_USERNAME = "<img src=x onerror=alert(1)>"

# frontend/src/utils/cspNonce.js only CSP-nonces the first N "<script" tags
# in the map HTML it receives, on the assumption that folium's own
# boilerplate (CDN links + init script) always renders exactly N tags,
# independent of marker/layer count — so anything smuggled in beyond that
# via a future escaping bug is left un-nonced and CSP blocks it. If folium
# ever changes what it emits, this must be updated in lockstep with the
# frontend constant, not just bumped to make the test pass.
TRUSTED_MAP_SCRIPT_COUNT = 6


@pytest.fixture
def xss_user_course():
    db = TestingSessionLocal()
    user = Users(
        id=1,
        email="xss@mail.com",
        username=XSS_USERNAME,
        first_name="x",
        last_name="y",
        hashed_password="not-used",
        is_active=True,
        role="user",
    )
    course = Courses(
        id=300,
        club_name=XSS_NAME,
        course_name=None,
        city="Mobile",
        state="AL",
        country="USA",
        latitude=30.740501,
        longitude=-88.20578,
    )
    db.add_all([user, course, UserCourses(id=1, course_id=300, user_id=1, year=2024)])
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.execute(text("DELETE FROM users;"))
        con.commit()


def test_all_users_map_escapes_user_content(xss_user_course):
    html_out = generate_all_users_map(TestingSessionLocal())
    # Raw payloads must not survive into the rendered map document.
    assert XSS_NAME not in html_out
    assert XSS_USERNAME not in html_out
    # Layer names are JSON-embedded by folium ("<" becomes backslash-u003c)
    # but Leaflet innerHTML's the decoded string, so the payload must be
    # HTML-escaped, not merely JSON-escaped.
    assert "\\u003cimg" not in html_out
    # The escaped forms should be present instead.
    assert "&lt;script&gt;" in html_out
    assert "\\u0026lt;img" in html_out or "&lt;img" in html_out


@pytest.mark.asyncio
async def test_user_map_escapes_course_names(xss_user_course):
    user = {"id": 1, "username": "safe_name"}
    map_path = await generate_user_map(user, TestingSessionLocal())
    try:
        html_out = map_path.read_text(encoding="utf-8")
        assert XSS_NAME not in html_out
        assert "&lt;script&gt;" in html_out
    finally:
        map_path.unlink(missing_ok=True)


def test_all_users_map_script_tag_count_matches_frontend_trust_boundary(xss_user_course):
    html_out = generate_all_users_map(TestingSessionLocal())
    assert html_out.count("<script") == TRUSTED_MAP_SCRIPT_COUNT


@pytest.mark.asyncio
async def test_user_map_script_tag_count_matches_frontend_trust_boundary(xss_user_course):
    user = {"id": 1, "username": "safe_name"}
    map_path = await generate_user_map(user, TestingSessionLocal())
    try:
        html_out = map_path.read_text(encoding="utf-8")
        assert html_out.count("<script") == TRUSTED_MAP_SCRIPT_COUNT
    finally:
        map_path.unlink(missing_ok=True)


# ── JSON points endpoints ─────────────────────────────────────────────────────


@pytest.fixture
def points_data():
    db = TestingSessionLocal()
    db.add_all(
        [
            Users(
                id=1,
                email="a@mail.com",
                username="alice",
                first_name="a",
                last_name="a",
                hashed_password="x",
                is_active=True,
                role="user",
            ),
            Users(
                id=2,
                email="b@mail.com",
                username="bob",
                first_name="b",
                last_name="b",
                hashed_password="x",
                is_active=True,
                role="user",
            ),
            Users(
                id=3,
                email="c@mail.com",
                username="carol",
                first_name="c",
                last_name="c",
                hashed_password="x",
                is_active=False,
                role="user",
            ),
            Courses(id=401, club_name=XSS_NAME, course_name=None, state="AL", latitude=30.740501, longitude=-88.20578),
            Courses(id=402, club_name="Club", course_name="West", state="AL", latitude=31.0, longitude=-87.0),
            Courses(id=403, club_name="Nowhere", course_name=None, state="AL", latitude=None, longitude=None),
            UserCourses(id=1, course_id=401, user_id=1, year=2024),
            UserCourses(id=2, course_id=403, user_id=1, year=2023),
            UserCourses(id=3, course_id=402, user_id=2, year=None),
            UserCourses(id=4, course_id=402, user_id=3, year=2020),
        ]
    )
    db.commit()
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.execute(text("DELETE FROM users;"))
        con.commit()


def test_user_points_only_own_courses_with_coordinates(points_data):
    response = client.get("/api/v1/map/points")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "fields": ["id", "lat", "lon", "name", "year"],
        # Raw name: escaping is the client's job (rendered as text).
        "points": [[401, 30.7405, -88.20578, XSS_NAME, 2024]],
    }


def test_all_points_groups_active_users(points_data):
    response = client.get("/api/v1/map/all_points")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["fields"] == ["id", "lat", "lon", "name", "year"]
    assert data["users"] == [
        {"username": "alice", "points": [[401, 30.7405, -88.20578, XSS_NAME, 2024]]},
        {"username": "bob", "points": [[402, 31.0, -87.0, "Club - West", None]]},
    ]
