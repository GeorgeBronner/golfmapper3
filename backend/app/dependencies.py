from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def require_admin(user: user_dependency) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


admin_dependency = Annotated[dict, Depends(require_admin)]
