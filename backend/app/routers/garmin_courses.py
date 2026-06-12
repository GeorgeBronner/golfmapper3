from fastapi import APIRouter, HTTPException, Path
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from starlette import status

from app.dependencies import db_dependency, user_dependency
from app.models import Courses

router = APIRouter(prefix="/garmin_courses", tags=["garmin_courses"])


class CourseBase(BaseModel):
    id: int
    display_name: str
    club_name: str | None
    course_name: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    latitude: float | None
    longitude: float | None

    model_config = ConfigDict(from_attributes=True)


@router.get("/readall", status_code=status.HTTP_200_OK, response_model=list[CourseBase])
async def readall(user: user_dependency, db: db_dependency):
    return db.query(Courses).all()


@router.get("/readall_page", status_code=status.HTTP_200_OK, response_model=Page[CourseBase])
async def readall_page(user: user_dependency, db: db_dependency):
    return paginate(db, select(Courses))


@router.get("/course/{course_id}", status_code=status.HTTP_200_OK, response_model=CourseBase)
async def read_course(user: user_dependency, db: db_dependency, course_id: int = Path(ge=1)):
    course_model = db.query(Courses).filter(Courses.id == course_id).first()
    if course_model is not None:
        return course_model
    raise HTTPException(status_code=404, detail="Course not found")
