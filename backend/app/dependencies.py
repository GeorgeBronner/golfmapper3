import ssl
from typing import Annotated

import certifi
import geopy.geocoders
from fastapi import Depends
from sqlalchemy.orm import Session

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
