from fastapi import APIRouter, HTTPException, Path
from starlette import status
from app.models import Courses
from app.dependencies import db_dependency, user_dependency

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/")
async def root(user: user_dependency):
    if user is None or user.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"message": "Hello Admin"}


@router.get("/courses", status_code=status.HTTP_200_OK)
async def readall(user: user_dependency, db: db_dependency):
    if user is None or user.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return db.query(Courses).all()


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(user: user_dependency, db: db_dependency, course_id: int = Path(ge=1)):
    if user is None or user.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")
    course_model = db.query(Courses).filter(Courses.id == course_id).first()
    if course_model is None:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course_model)
    db.commit()
