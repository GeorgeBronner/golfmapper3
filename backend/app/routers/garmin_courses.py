from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette import status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Optional
from app.models import Courses
from app.dependencies import db_dependency, user_dependency, get_db
from geopy.distance import geodesic
import geopy.geocoders
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel

router = APIRouter()

geolocator = geopy.geocoders.Nominatim(user_agent="golfmapper2")


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

    class Config:
        from_attributes = True


@router.get("/readall", status_code=status.HTTP_200_OK, response_model=list[CourseBase])
async def readall(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return db.query(Courses).all()


@router.get("/readall_page", status_code=status.HTTP_200_OK, response_model=Page[CourseBase])
async def readall_page(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return paginate(db, select(Courses))


@router.get("/course/{course_id}", status_code=status.HTTP_200_OK, response_model=CourseBase)
async def read_course(user: user_dependency, db: db_dependency, course_id: int = Path(ge=1)):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    course_model = db.query(Courses).filter(Courses.id == course_id).first()
    if course_model is not None:
        return course_model
    raise HTTPException(status_code=404, detail="Course not found")


@router.get("/closest_courses/")
async def get_closest_courses(
    lat: float = Query(...),
    long: float = Query(...),
    limit: int = Query(5, ge=1),
    db: Session = Depends(get_db),
):
    closest_courses = (
        db.query(Courses)
        .order_by(func.abs(Courses.latitude - lat) + func.abs(Courses.longitude - long))
        .limit(limit)
        .all()
    )
    courses_with_distances = []
    for course in closest_courses:
        distance = geodesic((lat, long), (course.latitude, course.longitude)).kilometers
        courses_with_distances.append((course, distance))
    return courses_with_distances


@router.get("/city_coordinates/")
async def get_city_coordinates(city: str = Query(...), state: str = None, country: str = None):
    location_str = city
    if state:
        location_str += f", {state}"
    if country:
        location_str += f", {country}"
    try:
        location = geolocator.geocode(location_str)
        if location:
            return {"latitude": location.latitude, "longitude": location.longitude}
        else:
            raise HTTPException(status_code=404, detail="Location not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Geocoding service error")


def courses_from_location(
    location: geopy.location.Location, db: Session, courses_returned: int = 5
):
    lat, long = location.latitude, location.longitude
    closest_courses = (
        db.query(Courses)
        .order_by(func.abs(Courses.latitude - lat) + func.abs(Courses.longitude - long))
        .limit(courses_returned)
        .all()
    )
    courses_with_distances = []
    for course in closest_courses:
        distance = geodesic((lat, long), (course.latitude, course.longitude)).kilometers
        courses_with_distances.append((course, {"distance": distance}))
    return courses_with_distances


@router.get("/zipcode_coordinates/")
async def get_zipcode_coordinates(zipcode: str = Query(...), country: Optional[str] = "US"):
    try:
        location = geolocator.geocode(zipcode, country_codes=country)
        if location:
            return {"latitude": location.latitude, "longitude": location.longitude}
        else:
            raise HTTPException(status_code=404, detail="Location not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Geocoding service error")


@router.get("/zipcode_closest_courses/")
async def zipcode_closest_courses(
    zipcode: str = Query(...),
    country: Optional[str] = "US",
    courses_returned: Optional[int] = 5,
    db: Session = Depends(get_db),
):
    try:
        location = geolocator.geocode(zipcode, country_codes=country)
        if location:
            return courses_from_location(location, db, courses_returned)
        else:
            raise HTTPException(status_code=404, detail="Location not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Geocoding service error")


@router.get("/city_closest_courses/")
async def city_closest_courses(
    city: str = Query(...),
    state: Optional[str] = None,
    country: Optional[str] = None,
    courses_returned: Optional[int] = 5,
    db: Session = Depends(get_db),
):
    location_str = city
    if state:
        location_str += f", {state}"
    if country:
        location_str += f", {country}"
    try:
        location = geolocator.geocode(location_str)
        if location:
            return courses_from_location(location, db, courses_returned)
        else:
            raise HTTPException(status_code=404, detail="Location not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Geocoding service error")
