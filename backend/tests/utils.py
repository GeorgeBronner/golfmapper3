from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import pytest
from main import app
from database import Base
from models import UserCourses, Users, Courses
from routers.auth import bcrypt_context


SQLALCHEMY_DATABASE_URL = "sqlite:///./testdb.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return {"username": "george", "id": 1, "user_role": "admin"}


client = TestClient(app)

# id = Column(Integer, primary_key=True, index=True)
# course_id = Column(Integer, ForeignKey("courses.id"))
# user_id = Column(Integer, ForeignKey("users.id"))


@pytest.fixture
def test_user_courses():
    user_course = UserCourses(course_id=200, user_id=1, year=2021)
    garmin_course = Courses(
        id=200,
        g_course="RTJ Golf Trail at Magnolia Grove - Falls",
        g_address="  7001 MAGNOLIA GROVE PKY",
        g_country="US",
        g_longitude=-88.20578,
        g_city="Mobile",
        g_state="Alabama",
        g_latitude=30.740501,
    )
    db = TestingSessionLocal()
    db.add(user_course)
    db.add(garmin_course)
    db.commit()
    yield user_course
    with engine.connect() as con:
        con.execute(text("DELETE FROM new_user_courses;"))
        con.execute(text("DELETE FROM courses;"))
        con.commit()

# id = Column(Integer, primary_key=True, index=True)
# email = Column(String, unique=True)
# username = Column(String, unique=True)
# first_name = Column(String)
# last_name = Column(String)
# hashed_password = Column(String)
# is_active = Column(Boolean, default=True)
# role = Column(String)


@pytest.fixture
def test_user():
    user = Users(
        email="georgetest@mail.com",
        username="georgetest",
        first_name="firsttest",
        last_name="lasttest",
        hashed_password=bcrypt_context.hash("password"),
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
