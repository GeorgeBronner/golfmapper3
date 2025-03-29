from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.database import SessionLocal
from sqlalchemy.orm import Session
from typing import Annotated
from app.models import Users
from .auth import get_current_user
from passlib.context import CryptContext


router = APIRouter(prefix="/user", tags=["user"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    if not bcrypt_context.verify(user_verification.password, user_model.hashed_password):
        raise HTTPException(status_code=401, detail="Error on password verification")
    user_model.hashed_password = bcrypt_context.hash(user_verification.new_password)
    db.commit()


@router.put("/phone-number/{user_phone}", status_code=status.HTTP_204_NO_CONTENT)
async def update_phone(user: user_dependency, db: db_dependency, user_phone: str):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()
    user_model.phone_number = user_phone
    db.commit()
