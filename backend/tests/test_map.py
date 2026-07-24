import pytest
from sqlalchemy import text

from app.models import Courses, UserCourses, Users
from app.routers.map import generate_all_users_map, generate_user_map

from .utils import TestingSessionLocal, engine

XSS_NAME = '<script>alert("xss")</script>'
XSS_USERNAME = "<img src=x onerror=alert(1)>"


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
