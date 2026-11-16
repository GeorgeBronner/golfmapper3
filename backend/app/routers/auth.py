import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette import status

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import Users
from app.security import NewPassword, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
SECRET_KEY = settings.SECRET_KEY_AUTH
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY_AUTH environment variable is not set")
# HS256 signatures are only as strong as the key; 32 bytes matches the hash size.
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY_AUTH must be at least 32 characters")

ALGORITHM = "HS256"
MAX_SESSION_DAYS = 30

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

db_dependency = Annotated[Session, Depends(get_db)]


def authenticate_user(username: str, password: str, db: Session) -> Users | bool:
    # Usernames are unique case-insensitively (see create_user), so match that way.
    user = db.query(Users).filter(func.lower(Users.username) == username.lower()).first()
    if user is None:
        return False
    if not user.is_active:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(
    username: str,
    user_id: int,
    role: str,
    expires_delta: timedelta,
    token_version: int = 0,
    auth_time: datetime | None = None,
):
    # auth_time is when the password was actually entered. Refreshes carry it
    # forward so a session cannot be extended past MAX_SESSION_DAYS.
    auth_time = auth_time or datetime.now(timezone.utc)
    encode = {
        "sub": username,
        "id": user_id,
        "role": role,
        "tv": token_version,
        "auth_time": int(auth_time.timestamp()),
    }
    encode.update({"exp": datetime.now(timezone.utc) + expires_delta})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_bearer)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from None
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # Identity, role, and account status come from the DB rather than token
    # claims, so demotions, deactivations, and deletions take effect
    # immediately instead of only when the token expires.
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # Tokens issued before a password change carry the old token_version, so
    # a leaked/stolen token stops working as soon as the password is reset
    # instead of remaining valid until it naturally expires.
    if payload.get("tv", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {
        "username": user.username,
        "id": user.id,
        "role": user.role,
        "token_version": user.token_version,
        "auth_time": payload.get("auth_time"),
    }


NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class CreateUserRequest(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.-]+$")]
    email: EmailStr
    first_name: NameStr
    last_name: NameStr
    password: NewPassword

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()


class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_user(request: Request, db: db_dependency, create_user_request: CreateUserRequest):
    existing_user = (
        db.query(Users)
        .filter(
            (func.lower(Users.username) == create_user_request.username.lower())
            | (func.lower(Users.email) == create_user_request.email)
        )
        .first()
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User with the same username or email already exists"
        )

    create_user_model = Users(
        username=create_user_request.username,
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=hash_password(create_user_request.password),
        role="user",
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
        user.username,
        user.id,
        user.role,
        timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
        user.token_version,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_token(request: Request, current_user: Annotated[dict, Depends(get_current_user)]):
    """Issue a fresh token for an already-authenticated user, up to MAX_SESSION_DAYS after login."""
    now = datetime.now(timezone.utc)
    # Tokens issued before auth_time existed have no claim; they restart the clock once.
    auth_time = datetime.fromtimestamp(current_user.get("auth_time") or now.timestamp(), tz=timezone.utc)
    if now - auth_time > timedelta(days=MAX_SESSION_DAYS):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    token = create_access_token(
        current_user["username"],
        current_user["id"],
        current_user["role"],
        timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
        current_user["token_version"],
        auth_time,
    )
    return {"access_token": token, "token_type": "bearer"}
