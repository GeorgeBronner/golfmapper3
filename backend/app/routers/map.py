from pathlib import Path

import folium
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from starlette import status

from app.config import settings
from app.dependencies import db_dependency, user_dependency
from app.models import Courses, UserCourses, Users
from app.routers.user_courses import readall

MAP_DIR = Path(settings.MAP_FILES_DIR)

router = APIRouter(prefix="/map", tags=["map"])

_USER_COLORS = [
    '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
    '#1abc9c', '#e67e22', '#e91e8c', '#00bcd4', '#8d6e63',
]


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


def generate_all_users_map(db) -> str:
    users = db.query(Users).filter(Users.is_active.is_(True)).all()
    all_map = folium.Map(location=[40, -90], zoom_start=4, control_scale=True)

    for i, user in enumerate(users):
        results = (
            db.query(Courses, UserCourses.year)
            .join(UserCourses, Courses.id == UserCourses.course_id)
            .filter(UserCourses.user_id == user.id)
            .filter(Courses.latitude.isnot(None), Courses.longitude.isnot(None))
            .all()
        )
        if not results:
            continue

        color = _USER_COLORS[i % len(_USER_COLORS)]
        dot = f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:6px;vertical-align:middle;"></span>'
        fg = folium.FeatureGroup(name=dot + user.username)
        for course, year in results:
            label = course.display_name
            if year:
                label += f' ({year})'
            fg.add_child(
                folium.CircleMarker(
                    location=[course.latitude, course.longitude],
                    popup=label,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    opacity=0.9,
                    radius=7,
                )
            )
        all_map.add_child(fg)

    folium.LayerControl(collapsed=False).add_to(all_map)
    return all_map.get_root().render()


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


@router.get("/allmap")
async def get_allmap(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    html = generate_all_users_map(db)
    return HTMLResponse(content=html)
