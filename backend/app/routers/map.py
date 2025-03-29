from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from app.database import SessionLocal
from sqlalchemy.orm import Session
from typing import Annotated
from app.routers.auth import get_current_user
from fastapi.responses import FileResponse
import folium
import geopy.geocoders
import certifi
import ssl

from app.routers.user_courses import readall
from app.routers.users import user_info

ctx = ssl._create_unverified_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx

router = APIRouter(prefix="/map", tags=["map"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/usermap")
async def root(user: user_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return FileResponse(f"static/user_maps/user_map_{user['username']}_{user['id']}.html")


# @router.get("/usermap1")
# async def root():
#     return FileResponse("static/user_map_test1.html")


@router.get("/user_map_generate", status_code=status.HTTP_200_OK)
async def user_map_generate(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_courses = await readall(user, db)
    if not user_courses:
        raise HTTPException(status_code=404, detail="No courses found")
    user_map = folium.Map(location=[40, -90], zoom_start=4, control_scale=True)
    fg = folium.FeatureGroup(name=f"FIX ME - USERNAME")
    for i in user_courses:
        new_description = i.g_course + ' ' + str(i.id)
        fg.add_child(
            folium.CircleMarker(location=[i.g_latitude, i.g_longitude], popup=new_description, color='red', opacity=0.7,
                                radius=7))
    user_map.add_child(fg)

    user_map.save(f"static/user_maps/user_map_{user['username']}_{user['id']}.html")

    return {"message": "Map generated"}
