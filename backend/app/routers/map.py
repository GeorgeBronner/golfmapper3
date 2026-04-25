import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from starlette import status
from fastapi.responses import FileResponse
import folium

from app.routers.user_courses import readall
from app.dependencies import db_dependency, user_dependency

MAP_DIR = Path(os.getenv("MAP_FILES_DIR", "./static/user_maps"))

router = APIRouter(prefix="/map", tags=["map"])


async def generate_user_map(user: dict, db) -> Path:
    user_courses = await readall(user, db)
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    map_path = MAP_DIR / f"user_map_{user['id']}.html"

    user_map = folium.Map(location=[40, -90], zoom_start=4, control_scale=True)
    if user_courses:
        fg = folium.FeatureGroup(name=user['username'])
        for course in user_courses:
            description = course.display_name + ' ' + str(course.id)
            fg.add_child(
                folium.CircleMarker(
                    location=[course.latitude, course.longitude],
                    popup=description,
                    color='red',
                    opacity=0.7,
                    radius=7,
                )
            )
        user_map.add_child(fg)

    try:
        user_map.save(str(map_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Map generation failed") from e

    return map_path


@router.get("/usermap")
async def get_usermap(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    map_path = MAP_DIR / f"user_map_{user['id']}.html"
    if not map_path.exists():
        map_path = await generate_user_map(user, db)
    return FileResponse(str(map_path))


@router.get("/user_map_generate", status_code=status.HTTP_200_OK)
async def user_map_generate(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    await generate_user_map(user, db)
    return {"message": "Map generated"}
