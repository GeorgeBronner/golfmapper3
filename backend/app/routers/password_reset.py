import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import mailtrap as mt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import PasswordResetToken, Users

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

TOKEN_EXPIRY_MINUTES = 15

db_dependency = Annotated[Session, Depends(get_db)]


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _send_reset_email(to_email: str, to_name: str, reset_url: str) -> None:
    if not settings.MAILTRAP_API_KEY:
        logger.warning("MAILTRAP_API_KEY not set — skipping email send for %s", to_email)
        return

    client = mt.MailtrapClient(token=settings.MAILTRAP_API_KEY)
    mail = mt.Mail(
        sender=mt.Address(email=settings.FROM_EMAIL, name=settings.FROM_NAME),
        to=[mt.Address(email=to_email, name=to_name)],
        subject="Reset your GolfMapper password",
        text=(
            f"Hi {to_name},\n\n"
            "We received a request to reset your GolfMapper password.\n\n"
            f"Click the link below to set a new password (valid for {TOKEN_EXPIRY_MINUTES} minutes):\n\n"
            f"{reset_url}\n\n"
            "If you didn't request this, you can safely ignore this email.\n\n"
            "— The GolfMapper Team"
        ),
        html=(
            f"<p>Hi {to_name},</p>"
            "<p>We received a request to reset your GolfMapper password.</p>"
            f"<p><a href=\"{reset_url}\">Reset my password</a></p>"
            f"<p>This link is valid for {TOKEN_EXPIRY_MINUTES} minutes. "
            "If you didn't request this, ignore this email.</p>"
            "<p>— The GolfMapper Team</p>"
        ),
        category="Password Reset",
    )
    client.send(mail)
    logger.info("Password reset email sent to %s", to_email)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: db_dependency,
):
    # Always return success to avoid user enumeration
    user = db.query(Users).filter(Users.email == body.email).first()
    if user:
        # Invalidate any existing unused tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,  # noqa: E712
        ).delete()

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES)

        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))

        reset_url = f"{settings.APP_BASE_URL}/reset-password?token={raw_token}"
        try:
            _send_reset_email(
                to_email=user.email,
                to_name=user.first_name or user.username,
                reset_url=reset_url,
            )
            db.commit()
            logger.info("Password reset requested for user_id=%s", user.id)
        except (mt.AuthorizationError, mt.APIError) as e:
            logger.error("Password reset email failed for user_id=%s: %s", user.id, e)
            db.rollback()

    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def reset_password(request: Request, body: ResetPasswordRequest, db: db_dependency):
    token_hash = _hash_token(body.token)
    now = datetime.now(timezone.utc)

    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,  # noqa: E712
            PasswordResetToken.expires_at > now,
        )
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters.",
        )

    user = db.query(Users).filter(Users.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    user.hashed_password = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    reset_token.used = True
    db.commit()

    logger.info("Password reset completed for user_id=%s", user.id)
    return {"message": "Password updated successfully."}
