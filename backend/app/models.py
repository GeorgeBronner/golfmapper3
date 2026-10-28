from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


def course_display_name(club_name: str | None, course_name: str | None) -> str:
    """Shared by Courses.display_name and column-only queries (map points)
    that never load a full Courses object."""
    if club_name and course_name and club_name != course_name:
        return f"{club_name} - {course_name}"
    return course_name or club_name or ""


class Courses(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    club_name = Column(String)
    course_name = Column(String)
    created_at = Column(DateTime, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    user_courses = relationship("UserCourses", back_populates="course", cascade="all, delete-orphan")

    @property
    def display_name(self):
        return course_display_name(self.club_name, self.course_name)

    def __repr__(self):
        return f"<course: {self.display_name}, {self.state}>"


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
    # Bumped whenever the password changes, so tokens issued before the
    # change stop working instead of remaining valid until they expire.
    token_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    courses = relationship("UserCourses", back_populates="user", cascade="all, delete-orphan")


class UserCourses(Base):
    def __repr__(self):
        return f"Course ({self.course_id}, {self.user_id}, {self.year})"

    __tablename__ = "user_courses"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("Users", back_populates="courses")
    course = relationship("Courses", back_populates="user_courses")

    __table_args__ = (
        # One entry per course per user (applies to freshly created databases;
        # existing DBs keep the old constraint — the application-level check in
        # add_user_course enforces the rule either way).
        UniqueConstraint("user_id", "course_id", name="uq_user_course"),
    )


class CourseRequests(Base):
    __tablename__ = "course_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String, nullable=False)  # "new_course" | "location_change"
    status = Column(String, default="pending", nullable=False)  # "pending" | "approved" | "rejected"

    submitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Only for location_change
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    original_latitude = Column(Float, nullable=True)
    original_longitude = Column(Float, nullable=True)

    # Proposed values (all fields for new_course; lat/lng for location_change)
    club_name = Column(String, nullable=True)
    course_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Admin review
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_message = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    approved_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    submitted_by = relationship("Users", foreign_keys=[submitted_by_user_id])
    reviewed_by = relationship("Users", foreign_keys=[reviewed_by_user_id])
    course = relationship("Courses", foreign_keys=[course_id])

    __table_args__ = (
        # One pending location-change request per (user, course) — status is
        # mutable (pending -> approved/rejected), so this has to be a partial
        # index rather than a plain UniqueConstraint. Applies to freshly
        # created databases only, same as uq_user_course above; the
        # application-level check in submit_location_change enforces the
        # rule for the existing production DB either way.
        Index(
            "uq_pending_location_change",
            "submitted_by_user_id",
            "request_type",
            "course_id",
            unique=True,
            sqlite_where=status == "pending",
            postgresql_where=status == "pending",
        ),
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    __table_args__ = (Index("ix_prt_token_hash", "token_hash"),)


class RankingLists(Base):
    __tablename__ = "ranking_lists"

    id = Column(Integer, primary_key=True)
    # Stable key, e.g. "golf-digest-us-public"; the seed script matches on it.
    slug = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    publisher = Column(String, nullable=False)
    scope = Column(String, nullable=False)  # e.g. "us-public"
    size = Column(Integer, nullable=True)

    editions = relationship("RankingEditions", back_populates="list", cascade="all, delete-orphan")


class RankingEditions(Base):
    __tablename__ = "ranking_editions"

    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("ranking_lists.id"), nullable=False, index=True)
    label = Column(String, nullable=False)  # "2021-22"
    start_year = Column(Integer, nullable=False)  # sort key: first year of the edition
    published_on = Column(String, nullable=True)  # "2021-09" or "2013-01-07"; precision varies
    source_url = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    list = relationship("RankingLists", back_populates="editions")
    entries = relationship("RankingEntries", back_populates="edition", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("list_id", "label", name="uq_ranking_edition_label"),)


class RankingEntries(Base):
    __tablename__ = "ranking_entries"

    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey("ranking_editions.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    prior_rank = Column(String, nullable=True)  # as printed: "12", "T48", "NEW", "NR"
    # Names change between editions (Longaberger is now The Virtues).
    published_name = Column(String, nullable=False)
    points = Column(Float, nullable=True)

    edition = relationship("RankingEditions", back_populates="entries")
    course = relationship("Courses")

    __table_args__ = (
        UniqueConstraint("edition_id", "course_id", name="uq_ranking_entry_course"),
        UniqueConstraint("edition_id", "rank", name="uq_ranking_entry_rank"),
    )
