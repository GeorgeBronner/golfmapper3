import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import Users

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
SECRET_KEY = settings.SECRET_KEY_AUTH
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY_AUTH environment variable is not set")

ALGORITHM = "HS256"

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

db_dependency = Annotated[Session, Depends(get_db)]


def authenticate_user(username: str, password: str, db: Session) -> Users | bool:
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        return False
    if not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        return False
    return user


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {"sub": username, "id": user_id, "role": role}
    encode.update({"exp": datetime.now(timezone.utc) + expires_delta})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return {"username": username, "id": user_id, "role": user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from None


class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    existing_user = db.query(Users).filter(
        (Users.username == create_user_request.username) |
        (Users.email == create_user_request.email)
    ).first()

    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="User with the same username or email already exists")

    create_user_model = Users(
        username=create_user_request.username,
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=bcrypt.hashpw(create_user_request.password.encode(), bcrypt.gensalt()).decode(),
        role='user',
        is_active=True,
    )
    db.add(create_user_model)
    db.commit()


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        logger.warning("Failed login attempt for username=%s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    logger.info("Successful login for username=%s", user.username)
    token = create_access_token(
        user.username, user.id, user.role,
        timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: Annotated[dict, Depends(get_current_user)]):
    """Issue a fresh token for an already-authenticated user."""
    token = create_access_token(
        current_user["username"], current_user["id"], current_user["role"],
        timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}
