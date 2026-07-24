from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from starlette import status

from app.dependencies import admin_dependency, db_dependency
from app.models import CourseRequests, Courses, UserCourses, Users
from app.routers.garmin_courses import CourseBase
from app.security import NewPassword, hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


class UserSummary(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    role: str


class PasswordReset(BaseModel):
    new_password: NewPassword


class ActiveUpdate(BaseModel):
    is_active: bool


class CourseCreate(BaseModel):
    club_name: str | None = None
    course_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class CourseInfoUpdate(BaseModel):
    club_name: str | None = None
    course_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


@router.get("/")
async def root(user: admin_dependency):
    return {"message": "Hello Admin"}


@router.get("/courses", status_code=status.HTTP_200_OK, response_model=list[CourseBase])
async def readall(user: admin_dependency, db: db_dependency):
    return db.query(Courses).all()


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(user: admin_dependency, db: db_dependency, course_id: int = Path(ge=1)):
    course_model = db.query(Courses).filter(Courses.id == course_id).first()
    if course_model is None:
        raise HTTPException(status_code=404, detail="Course not found")
    db.query(UserCourses).filter(UserCourses.course_id == course_id).delete(synchronize_session=False)
    db.query(CourseRequests).filter(
        (CourseRequests.course_id == course_id) | (CourseRequests.approved_course_id == course_id),
        CourseRequests.status == "approved",
    ).delete(synchronize_session=False)
    db.delete(course_model)
    db.commit()


@router.post("/courses", status_code=status.HTTP_201_CREATED, response_model=CourseBase)
async def create_course(user: admin_dependency, db: db_dependency, course_data: CourseCreate):
    course = Courses(
        club_name=course_data.club_name,
        course_name=course_data.course_name,
        address=course_data.address,
        city=course_data.city,
        state=course_data.state,
        country=course_data.country,
        latitude=course_data.latitude,
        longitude=course_data.longitude,
        created_at=datetime.now(timezone.utc),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.put("/courses/{course_id}/info", status_code=status.HTTP_200_OK, response_model=CourseBase)
async def update_course_info(
    user: admin_dependency,
    db: db_dependency,
    info: CourseInfoUpdate,
    course_id: int = Path(ge=1),
):
    course = db.query(Courses).filter(Courses.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    for field, value in info.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@router.put("/courses/{course_id}/location", status_code=status.HTTP_200_OK, response_model=CourseBase)
async def update_course_location(
    user: admin_dependency,
    db: db_dependency,
    location: LocationUpdate,
    course_id: int = Path(ge=1),
):
    course = db.query(Courses).filter(Courses.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    course.latitude = location.latitude
    course.longitude = location.longitude
    db.commit()
    db.refresh(course)
    return course


@router.get("/users", status_code=status.HTTP_200_OK, response_model=list[UserSummary])
async def list_users(user: admin_dependency, db: db_dependency):
    return db.query(Users).all()


@router.patch("/users/{user_id}/role", status_code=status.HTTP_200_OK, response_model=UserSummary)
async def update_user_role(
    user: admin_dependency,
    db: db_dependency,
    role_update: RoleUpdate,
    user_id: int = Path(ge=1),
):
    if role_update.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
    if user_id == user["id"] and role_update.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role")
    target = db.query(Users).filter(Users.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    target.role = role_update.role
    db.commit()
    db.refresh(target)
    return target


@router.patch("/users/{user_id}/password", status_code=status.HTTP_200_OK)
async def reset_user_password(
    user: admin_dependency,
    db: db_dependency,
    password_reset: PasswordReset,
    user_id: int = Path(ge=1),
):
    target = db.query(Users).filter(Users.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    target.hashed_password = hash_password(password_reset.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.patch("/users/{user_id}/active", status_code=status.HTTP_200_OK, response_model=UserSummary)
async def update_user_active(
    user: admin_dependency,
    db: db_dependency,
    active_update: ActiveUpdate,
    user_id: int = Path(ge=1),
):
    if user_id == user["id"] and not active_update.is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    target = db.query(Users).filter(Users.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = active_update.is_active
    db.commit()
    db.refresh(target)
    return target
