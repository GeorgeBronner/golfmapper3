from datetime import datetime

import bcrypt
import pytest
from sqlalchemy import text

from app.models import Courses, UserCourses, Users

from .utils import TestingSessionLocal, engine


@pytest.fixture
def test_user_courses():
    garmin_course = Courses(
        id=200,
        club_name="RTJ Golf Trail at Magnolia Grove",
        course_name="Falls",
        address="7001 MAGNOLIA GROVE PKY",
        city="Mobile",
        state="Alabama",
        country="US",
        latitude=30.740501,
        longitude=-88.20578,
    )
    user_course = UserCourses(id=1, course_id=200, user_id=1, year=2021)
    db = TestingSessionLocal()
    db.add(garmin_course)
    db.add(user_course)
    db.commit()
    yield user_course
    with engine.connect() as con:
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.commit()


@pytest.fixture
def test_user_courses_with_datetime():
    garmin_course = Courses(
        id=201,
        club_name="RTJ Golf Trail at Magnolia Grove",
        course_name="Falls",
        address="7001 MAGNOLIA GROVE PKY",
        city="Mobile",
        state="Alabama",
        country="US",
        latitude=30.740501,
        longitude=-88.20578,
        created_at=datetime(2026, 1, 7, 5, 16, 9),
    )
    user_course = UserCourses(id=2, course_id=201, user_id=1, year=2024)
    db = TestingSessionLocal()
    db.add(garmin_course)
    db.add(user_course)
    db.commit()
    yield user_course
    with engine.connect() as con:
        con.execute(text("DELETE FROM user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.commit()


@pytest.fixture
def test_user():
    user = Users(
        id=1,
        email="georgetest@mail.com",
        username="georgetest",
        first_name="firsttest",
        last_name="lasttest",
        hashed_password=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
        is_active=True,
        role="admin",
    )
    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    yield user
    with engine.connect() as con:
        con.execute(text("DELETE FROM users;"))
        con.commit()
