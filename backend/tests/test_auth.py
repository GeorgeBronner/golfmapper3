from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException, status
from sqlalchemy import text

from app.routers.auth import (
    ALGORITHM,
    SECRET_KEY,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
)

from .utils import TestingSessionLocal, app, client, engine, override_get_db

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


def test_authenticate_user_over_72_bytes_returns_false(test_user):
    # bcrypt 5.x raises ValueError for >72-byte passwords; login must return
    # False (→ 401), not crash with a 500.
    db = TestingSessionLocal()
    result = authenticate_user(test_user.username, "x" * 100, db)
    assert result is False


def test_authenticate_inactive_user_returns_false(test_user):
    db = TestingSessionLocal()
    user = db.merge(test_user)
    user.is_active = False
    db.commit()

    result = authenticate_user(test_user.username, "password", db)
    assert result is False


def test_create_access_token(test_user):
    access_token = create_access_token(test_user.username, test_user.id, test_user.role, timedelta(minutes=15))

    payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload.get("sub") == test_user.username
    assert payload.get("id") == test_user.id
    assert payload.get("role") == test_user.role


@pytest.mark.asyncio
async def test_get_current_user_valid_token(test_user):
    encode = {"sub": "georgetest", "id": 1, "role": "admin"}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    user = await get_current_user(token, TestingSessionLocal())
    assert user["username"] == "georgetest"


@pytest.mark.asyncio
async def test_get_current_user_bad_token():
    encode = {"role": "admin"}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as e:
        await get_current_user(token, TestingSessionLocal())

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_get_current_user_role_comes_from_db(test_user):
    # A stale "admin" claim in the token must not grant admin after demotion.
    db = TestingSessionLocal()
    user = db.merge(test_user)
    user.role = "user"
    db.commit()

    encode = {"sub": "georgetest", "id": 1, "role": "admin"}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    current = await get_current_user(token, TestingSessionLocal())
    assert current["role"] == "user"


@pytest.mark.asyncio
async def test_get_current_user_inactive_user_rejected(test_user):
    db = TestingSessionLocal()
    user = db.merge(test_user)
    user.is_active = False
    db.commit()

    encode = {"sub": "georgetest", "id": 1, "role": "admin"}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as e:
        await get_current_user(token, TestingSessionLocal())
    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_user_rejects_invalid_email():
    response = client.post(
        "/api/v1/auth/",
        json={
            "username": "newuser",
            "email": "not-an-email",
            "first_name": "New",
            "last_name": "User",
            "password": "password123",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_user_accepts_valid_email():
    response = client.post(
        "/api/v1/auth/",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "password123",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    with engine.connect() as con:
        con.execute(text("DELETE FROM users;"))
        con.commit()


@pytest.mark.asyncio
async def test_get_current_user_deleted_user_rejected():
    # Token is signed and unexpired, but the user no longer exists.
    encode = {"sub": "ghost", "id": 424242, "role": "admin"}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as e:
        await get_current_user(token, TestingSessionLocal())
    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.fixture
def clean_users():
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM users;"))
        con.commit()


def _register(**overrides):
    body = {
        "username": "newuser",
        "email": "newuser@example.com",
        "first_name": "New",
        "last_name": "User",
        "password": "password123",
    }
    body.update(overrides)
    return client.post("/api/v1/auth/", json=body)


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "ab"},
        {"username": "x" * 31},
        {"username": "has space"},
        {"username": "<script>"},
        {"first_name": "x" * 51},
        {"last_name": "   "},
    ],
)
def test_create_user_rejects_bad_fields(overrides):
    assert _register(**overrides).status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_user_is_case_insensitive_for_username_and_email(clean_users):
    assert _register().status_code == status.HTTP_201_CREATED
    assert _register(username="NewUser", email="other@example.com").status_code == status.HTTP_409_CONFLICT
    assert _register(username="another", email="NewUser@Example.com").status_code == status.HTTP_409_CONFLICT


def test_email_is_stored_lowercase(clean_users):
    assert _register(email="MiXed@Example.com").status_code == status.HTTP_201_CREATED
    with engine.connect() as con:
        assert con.execute(text("SELECT email FROM users")).scalar() == "mixed@example.com"


def test_login_username_is_case_insensitive(test_user):
    db = TestingSessionLocal()
    assert authenticate_user(test_user.username.upper(), "password", db).id == test_user.id


def test_refresh_keeps_original_auth_time_and_caps_session(test_user):
    from datetime import datetime, timezone

    from app.routers.auth import MAX_SESSION_DAYS

    # Exercise the real token path rather than the suite-wide auth override.
    saved = app.dependency_overrides.pop(get_current_user, None)
    now = datetime.now(timezone.utc)

    def token_from(auth_time):
        return create_access_token(
            test_user.username, test_user.id, test_user.role, timedelta(minutes=15), test_user.token_version, auth_time
        )

    try:
        headers = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
        old = now - timedelta(days=MAX_SESSION_DAYS - 1)
        ok = client.post("/api/v1/auth/refresh", headers=headers(token_from(old)))
        assert ok.status_code == status.HTTP_200_OK
        new_claims = jwt.decode(ok.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        assert new_claims["auth_time"] == int(old.timestamp())

        expired = client.post(
            "/api/v1/auth/refresh", headers=headers(token_from(now - timedelta(days=MAX_SESSION_DAYS + 1)))
        )
        assert expired.status_code == status.HTTP_401_UNAUTHORIZED
    finally:
        if saved is not None:
            app.dependency_overrides[get_current_user] = saved
