from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.database import SessionLocal
from sqlalchemy.orm import Session
from typing import Annotated
from app.models import Users
from .auth import get_current_user
import bcrypt


router = APIRouter(prefix="/user", tags=["user"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
class UserVerification(BaseModel):
    password: str
    new_password: str = Field(min_length=6)


@router.get("/", status_code=status.HTTP_200_OK)
async def user_info(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()

    return user_model


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(user: user_dependency, db: db_dependency, user_verification: UserVerification):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()
    if not bcrypt.checkpw(user_verification.password.encode(), user_model.hashed_password.encode()):
        raise HTTPException(status_code=401, detail="Error on password verification")
    user_model.hashed_password = bcrypt.hashpw(user_verification.new_password.encode(), bcrypt.gensalt()).decode()
    db.commit()
