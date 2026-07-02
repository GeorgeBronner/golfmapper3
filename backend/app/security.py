from typing import Annotated

import bcrypt
from pydantic import AfterValidator, Field

# bcrypt only uses the first 72 bytes of a password; bcrypt 5.x raises
# ValueError instead of silently truncating, so every hash/verify path
# must enforce the limit up front.
BCRYPT_MAX_PASSWORD_BYTES = 72


def _check_password_bytes(v: str) -> str:
    if len(v.encode()) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes")
    return v


# Pydantic field type for endpoints that accept a new password.
NewPassword = Annotated[str, Field(min_length=8), AfterValidator(_check_password_bytes)]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode()
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode())
