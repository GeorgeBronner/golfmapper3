from datetime import datetime

import bcrypt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import db_dependency, user_dependency
from app.models import Users

router = APIRouter(prefix="/user", tags=["user"])


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: str
    last_name: str
    is_active: bool
    role: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserVerification(BaseModel):
    password: str
    new_password: str = Field(min_length=8)


@router.get("/", status_code=status.HTTP_200_OK, response_model=UserResponse)
async def user_info(user: user_dependency, db: db_dependency):
    return db.query(Users).filter(Users.id == user.get("id")).first()


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(user: user_dependency, db: db_dependency, user_verification: UserVerification):
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()
    if user_model is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not bcrypt.checkpw(user_verification.password.encode(), user_model.hashed_password.encode()):
        raise HTTPException(status_code=401, detail="Error on password verification")
    user_model.hashed_password = bcrypt.hashpw(user_verification.new_password.encode(), bcrypt.gensalt()).decode()
    db.commit()
