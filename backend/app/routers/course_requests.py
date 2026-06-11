from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from starlette import status as http_status

from app.dependencies import db_dependency, user_dependency
from app.models import CourseRequests, Courses, UserCourses

router = APIRouter(prefix="/course-requests", tags=["course-requests"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class NewCourseRequest(BaseModel):
    club_name: str | None = None
    course_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

    @model_validator(mode='after')
    def require_at_least_one_name(self):
        if not (self.club_name and self.club_name.strip()) and not (self.course_name and self.course_name.strip()):
            raise ValueError('Either club_name or course_name is required')
        return self


class LocationChangeRequest(BaseModel):
    course_id: int = Field(..., ge=1)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class RejectBody(BaseModel):
    message: str = Field(..., min_length=1)


class CourseRequestOut(BaseModel):
    id: int
    request_type: str
    status: str
    course_id: int | None
    club_name: str | None
    course_name: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    latitude: float
    longitude: float
    original_latitude: float | None
    original_longitude: float | None
    review_message: str | None
    reviewed_at: datetime | None
    approved_course_id: int | None = None
    created_at: datetime | None
    # Resolved display name for location_change requests
    course_display_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


def _to_out(req: CourseRequests) -> CourseRequestOut:
    data = CourseRequestOut.model_validate(req)
    if req.course:
        data.course_display_name = req.course.display_name
    return data


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------

@router.post("/new-course", status_code=http_status.HTTP_201_CREATED, response_model=CourseRequestOut)
async def submit_new_course(user: user_dependency, db: db_dependency, body: NewCourseRequest):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    req = CourseRequests(
        request_type="new_course",
        submitted_by_user_id=user["id"],
        club_name=body.club_name,
        course_name=body.course_name,
        address=body.address,
        city=body.city,
        state=body.state,
        country=body.country,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.post("/location-change", status_code=http_status.HTTP_201_CREATED, response_model=CourseRequestOut)
async def submit_location_change(user: user_dependency, db: db_dependency, body: LocationChangeRequest):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    course = db.query(Courses).filter(Courses.id == body.course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = (
        db.query(CourseRequests)
        .filter(
            CourseRequests.submitted_by_user_id == user["id"],
            CourseRequests.request_type == "location_change",
            CourseRequests.course_id == body.course_id,
            CourseRequests.status == "pending",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending location change request for this course.",
        )

    req = CourseRequests(
        request_type="location_change",
        submitted_by_user_id=user["id"],
        course_id=body.course_id,
        original_latitude=course.latitude,
        original_longitude=course.longitude,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    try:
        db.add(req)
        db.commit()
        db.refresh(req)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="You already have a pending location change request for this course.",
        ) from None
    return _to_out(req)


@router.get("/my-requests", status_code=http_status.HTTP_200_OK, response_model=list[CourseRequestOut])
async def my_requests(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rows = (
        db.query(CourseRequests)
        .filter(CourseRequests.submitted_by_user_id == user["id"])
        .order_by(CourseRequests.created_at.desc())
        .all()
    )
    return [_to_out(r) for r in rows]


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

def _require_admin(user):
    if user is None or user.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/admin/all", status_code=http_status.HTTP_200_OK, response_model=list[CourseRequestOut])
async def admin_list_requests(user: user_dependency, db: db_dependency, pending_only: bool = True):
    _require_admin(user)
    q = db.query(CourseRequests)
    if pending_only:
        q = q.filter(CourseRequests.status == "pending")
    rows = q.order_by(CourseRequests.created_at.asc()).all()
    return [_to_out(r) for r in rows]


@router.post("/admin/{request_id}/approve", status_code=http_status.HTTP_200_OK, response_model=CourseRequestOut)
async def admin_approve(user: user_dependency, db: db_dependency, request_id: int = Path(ge=1)):
    _require_admin(user)
    req = db.query(CourseRequests).filter(CourseRequests.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Request is no longer pending")

    if req.request_type == "new_course":
        course = Courses(
            club_name=req.club_name,
            course_name=req.course_name,
            address=req.address,
            city=req.city,
            state=req.state,
            country=req.country,
            latitude=req.latitude,
            longitude=req.longitude,
            created_at=datetime.now(timezone.utc),
        )
        db.add(course)
        db.flush()  # get course.id before committing
        user_course = UserCourses(
            course_id=course.id,
            user_id=req.submitted_by_user_id,
            year=None,
        )
        db.add(user_course)
        req.approved_course_id = course.id

    elif req.request_type == "location_change":
        course = db.query(Courses).filter(Courses.id == req.course_id).first()
        if course is None:
            raise HTTPException(status_code=404, detail="Target course no longer exists")
        course.latitude = req.latitude
        course.longitude = req.longitude

    req.status = "approved"
    req.reviewed_by_user_id = user["id"]
    req.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.post("/admin/{request_id}/reject", status_code=http_status.HTTP_200_OK, response_model=CourseRequestOut)
async def admin_reject(
    user: user_dependency,
    db: db_dependency,
    body: RejectBody,
    request_id: int = Path(ge=1),
):
    _require_admin(user)
    req = db.query(CourseRequests).filter(CourseRequests.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Request is no longer pending")

    req.status = "rejected"
    req.review_message = body.message
    req.reviewed_by_user_id = user["id"]
    req.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return _to_out(req)
