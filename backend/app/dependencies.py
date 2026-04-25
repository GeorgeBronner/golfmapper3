import ssl
import certifi
import geopy.geocoders
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import SessionLocal
from app.routers.auth import get_current_user

_ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = _ctx


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
