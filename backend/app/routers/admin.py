from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, literal_column
from starlette import status

from app.dependencies import admin_dependency, db_dependency
from app.geo import CountryCode, StateCode, check_state_for_country
from app.limiter import limiter
from app.models import CourseRequests, Courses, UserCourses, Users, course_display_name
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
    state: StateCode = None
    country: CountryCode = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

    @model_validator(mode="after")
    def state_matches_country(self):
        check_state_for_country(self.state, self.country)
        return self


class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class CourseInfoUpdate(BaseModel):
    club_name: str | None = None
    course_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: StateCode = None
    country: CountryCode = None

    @model_validator(mode="after")
    def state_matches_country(self):
        check_state_for_country(self.state, self.country)
        return self


@router.get("/")
async def root(user: admin_dependency):
    return {"message": "Hello Admin"}


@router.get("/courses", status_code=status.HTTP_200_OK, response_model=list[CourseBase])
async def readall(user: admin_dependency, db: db_dependency):
    return db.query(Courses).all()


# `state`/`country` are free text (imported data, admin edits, user course
# requests), so compare on a trimmed, upper-cased form. main.py backfills an
# expression index on exactly this expression for courses.state.
def _normalized(column):
    return func.upper(func.trim(column))


@router.get("/courses/points", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def course_points(
    request: Request,
    user: admin_dependency,
    db: db_dependency,
    state: str | None = Query(default=None, max_length=100),
    country: str | None = Query(default=None, max_length=100),
):
    """Every course with coordinates, optionally filtered by state/country.
    An empty `country` matches courses with no country (as /courses/states
    reports them, country null).

    Compact on purpose — a whole-dataset response is ~15k rows:

        {"fields": ["id", "lat", "lon", "name"],
         "points": [[123, 27.95, -82.46, "Some Club - North"], ...]}

    Names are returned unescaped; the client must render them as text.
    """
    query = db.query(Courses.id, Courses.latitude, Courses.longitude, Courses.club_name, Courses.course_name).filter(
        Courses.latitude.isnot(None), Courses.longitude.isnot(None)
    )
    if state and state.strip():
        query = query.filter(_normalized(Courses.state) == state.strip().upper())
    if country is not None:
        if country.strip():
            query = query.filter(_normalized(Courses.country) == country.strip().upper())
        else:
            query = query.filter(func.coalesce(func.trim(Courses.country), "") == "")
    points = [
        [course_id, round(lat, 5), round(lon, 5), course_display_name(club, name)]
        for course_id, lat, lon, club, name in query.order_by(Courses.id)
    ]
    return {"fields": ["id", "lat", "lon", "name"], "points": points}


@router.get("/courses/states", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def course_states(request: Request, user: admin_dependency, db: db_dependency):
    """Distinct (normalized) state/country pairs with mappable-course counts,
    for the admin course map's state picker."""
    state_col = _normalized(Courses.state).label("state")
    # Blank and NULL countries both report as null. A literal rather than a
    # bind param, so SELECT and GROUP BY are the identical expression for
    # Postgres even under a server-side-binding driver.
    country_col = func.nullif(_normalized(Courses.country), literal_column("''")).label("country")
    rows = (
        db.query(state_col, country_col, func.count(Courses.id))
        .filter(Courses.latitude.isnot(None), Courses.longitude.isnot(None))
        .filter(Courses.state.isnot(None), func.trim(Courses.state) != "")
        .group_by(state_col, country_col)
        # Explicit NULLs-last: SQLite and Postgres default to opposite ends.
        .order_by(country_col.is_(None), country_col, state_col)
        .all()
    )
    return [{"state": s, "country": c, "count": n} for s, c, n in rows]


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
    target.token_version += 1
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
