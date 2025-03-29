from .utils import *
from routers.auth import get_db, authenticate_user, create_access_token, SECRET_KEY, ALGORITHM, get_current_user
from fastapi import status
from jose import jwt
from datetime import timedelta
import pytest
from fastapi import HTTPException

app.dependency_overrides[get_db] = override_get_db


def test_authenticate_user(test_user):
    db = TestingSessionLocal()

    authenticated_user = authenticate_user(test_user.username, "password", db)

    assert authenticated_user is not None
    assert authenticated_user.username == test_user.username

    none_user = authenticate_user("wrong_username", "password", db)
    assert none_user is False

    wrong_password = authenticate_user(test_user.username, "wrong_password", db)
    assert wrong_password is False


def test_create_access_token(test_user):
    access_token = create_access_token(test_user.username, test_user.id, test_user.role, timedelta(minutes=15))

    payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    print(payload)
    assert payload.get("sub") == test_user.username
    assert payload.get("id") == test_user.id
    assert payload.get("role") == test_user.role


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    encode = {"sub": "georgetest", "id": 1, "role": "admin"}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    user = await get_current_user(token)
    assert user["username"] == "georgetest"


@pytest.mark.asyncio
async def test_get_current_user_bad_token():
    encode = {"role": "admin"}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as e:
        await get_current_user(token)

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.detail == "Invalid credentials"
