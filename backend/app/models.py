from sqlalchemy.orm import relationship

from app.database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float


class Courses(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    g_course = Column(String(250))
    g_address = Column(String(250))
    g_city = Column(String(100))
    g_state = Column(String(40))
    g_country = Column(String(40))
    g_latitude = Column(Float)
    g_longitude = Column(Float)

    def __repr__(self):
        return f'<course: {self.g_course}, {self.g_state}>'

class Users(Base):

    def __repr__(self):
        return f"User({self.username}, {self.email}, {self.first_name}, {self.last_name}, {self.role})"

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String)


class UserCourses(Base):

    def __repr__(self):
        return f"Course ({self.course_id}, {self.user_id}, {self.year})"

    __tablename__ = "new_user_courses"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    year = Column(Integer, nullable=True)