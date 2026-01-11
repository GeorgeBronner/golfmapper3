from sqlalchemy.orm import relationship

from app.database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float


class Courses(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    club_name = Column(String)
    course_name = Column(String)
    created_at = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    @property
    def display_name(self):
        """Returns formatted course name: 'Club - Course' if different, else just course name"""
        if self.club_name and self.course_name and self.club_name != self.course_name:
            return f"{self.club_name} - {self.course_name}"
        elif self.course_name:
            return self.course_name
        elif self.club_name:
            return self.club_name
        return ""

    def __repr__(self):
        return f'<course: {self.display_name}, {self.state}>'

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

    __tablename__ = "user_courses"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    year = Column(Integer, nullable=True)