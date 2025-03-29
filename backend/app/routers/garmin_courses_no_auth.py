from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette import status
from app.database import SessionLocal
from sqlalchemy.orm import Session
from typing import Annotated
from app.models import Courses
from app.routers.auth import get_test_user
from sqlalchemy import func
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import geopy.geocoders
import certifi
import ssl
from typing import Optional


ctx = ssl._create_unverified_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx  #reenable

router = APIRouter(prefix="/no_auth", tags=["no_auth"])


@router.get("/")
async def root():
    return {"message": "Hello World"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_test_user)]


@router.get("/readall", status_code=status.HTTP_200_OK)
async def readall(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return db.query(Courses).all()

@router.get("/readall_alabama", status_code=status.HTTP_200_OK)
async def readall_alabama(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return db.query(Courses).filter(Courses.g_state == 'Alabama').all()

@router.get("/course/{course_id}", status_code=status.HTTP_200_OK)
async def read_todo(user: user_dependency, db: db_dependency, course_id: int = Path(ge=1)):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    course_model = db.query(Courses).filter(Courses.id == course_id).first()
    if course_model is not None:
        return course_model
    raise HTTPException(status_code=404, detail="Course not found")

@router.get("/closest_courses/")
async def get_closest_courses(lat: float = Query(...),
                              long: float = Query(...),
                              limit: int = Query(5, ge=1),
                              db: Session = Depends(get_db)):

    closest_courses = db.query(Courses).order_by(
        func.abs(Courses.g_latitude - lat) + func.abs(Courses.g_longitude - long)
    ).limit(limit).all()

    # Calculate distances for the fetched courses
    courses_with_distances = []
    for course in closest_courses:
        distance = geodesic((lat, long), (course.g_latitude, course.g_longitude)).kilometers
        courses_with_distances.append((course, distance))

    return courses_with_distances


geolocator = Nominatim(user_agent="geoapi")

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/city_closest_courses/")
async def city_closest_courses(
        city: str = Query(...),
        state: Optional[str] = None,
        country: Optional[str] = None,
        db: Session = Depends(get_db)
):
    location_str = city
    if state:
        location_str += f", {state}"
    if country:
        location_str += f", {country}"

    try:
        location = geolocator.geocode(location_str)
        if location:
            lat, long = location.latitude, location.longitude
            closest_courses = db.query(Courses).order_by(
                func.abs(Courses.g_latitude - lat) + func.abs(Courses.g_longitude - long)
            ).limit(5).all()

# Calculate distances for the fetched courses
            courses_with_distances = []
            for course in closest_courses:
                distance = geodesic((lat, long), (course.g_latitude, course.g_longitude)).kilometers
                courses_with_distances.append((course, distance))

            return courses_with_distances
        else:
            raise HTTPException(status_code=404, detail="Location not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


