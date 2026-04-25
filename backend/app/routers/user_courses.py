import os
from pathlib import Path as FilePath
from fastapi import APIRouter, HTTPException, Path
from starlette import status
from pydantic import BaseModel, Field, field_validator
from app.models import Courses, UserCourses
from app.dependencies import db_dependency, user_dependency

_MAP_DIR = FilePath(os.getenv("MAP_FILES_DIR", "./static/user_maps"))


def _invalidate_user_map(user_id: int) -> None:
    (_MAP_DIR / f"user_map_{user_id}.html").unlink(missing_ok=True)


router = APIRouter(prefix="/user_courses", tags=["user_courses"])


class UserCourseRequest(BaseModel):
    garmin_id: int = Field(...)
    year: int = Field(...)

    @field_validator('year')
    def check_year(cls, v):
        if v < 1900 or v > 2070:
            return None
        return v


class CourseResponse(BaseModel):
    id: int
    display_name: str
    club_name: str
    course_name: str
    address: str | None
    city: str
    state: str
    country: str
    latitude: float
    longitude: float
    created_at: str | None = None
    year: int | None = None

    class Config:
        from_attributes = True


@router.get("/readall_ids", status_code=status.HTTP_200_OK)
async def readall_ids(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return db.query(UserCourses).filter(UserCourses.user_id == user.get("id")).all()


@router.get("/readall_ids_w_year", status_code=status.HTTP_200_OK, response_model=list[CourseResponse])
async def readall_ids_w_year(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    results = (
        db.query(Courses, UserCourses.year)
        .join(UserCourses, Courses.id == UserCourses.course_id)
        .filter(UserCourses.user_id == user.get("id"))
        .all()
    )
    courses = []
    for course, year in results:
        course.year = year
        courses.append(course)
    return courses


@router.get("/readall", status_code=status.HTTP_200_OK, response_model=list[CourseResponse])
async def readall(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    course_ids = (
        db.query(UserCourses.course_id)
        .filter(UserCourses.user_id == user.get("id"))
        .distinct()
        .all()
    )
    course_ids = [course_id for course_id, in course_ids]
    return db.query(Courses).filter(Courses.id.in_(course_ids)).all()


@router.post("/add_course", status_code=status.HTTP_201_CREATED)
async def add_user_course(user: user_dependency, db: db_dependency, user_course_request: UserCourseRequest):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_course_model = UserCourses(
        course_id=user_course_request.garmin_id,
        year=user_course_request.year,
        user_id=user.get("id"),
    )
    db.add(user_course_model)
    db.commit()
    _invalidate_user_map(user.get("id"))


@router.delete("/delete/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_course(user: user_dependency, db: db_dependency, course_id: int = Path(ge=1)):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_course_model = (
        db.query(UserCourses)
        .filter(UserCourses.course_id == course_id, UserCourses.user_id == user.get("id"))
        .first()
    )
    if user_course_model is None:
        raise HTTPException(status_code=404, detail="Course_id not found")
    db.delete(user_course_model)
    db.commit()
    _invalidate_user_map(user.get("id"))
