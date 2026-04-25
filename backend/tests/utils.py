from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.database import Base
from app.models import UserCourses, Users, Courses
import bcrypt


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return {"username": "georgetest", "id": 1, "role": "admin"}


client = TestClient(app)


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
