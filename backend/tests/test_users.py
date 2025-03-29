from routers.users import get_db, get_current_user
from fastapi import status
from .utils import *

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

# id = Column(Integer, primary_key=True, index=True)
# email = Column(String, unique=True)
# username = Column(String, unique=True)
# first_name = Column(String)
# last_name = Column(String)
# hashed_password = Column(String)
# is_active = Column(Boolean, default=True)
# role = Column(String)


def test_return_user(test_user):
    response = client.get("/user")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "georgetest"
    assert response.json()["email"] == "georgetest@mail.com"
    assert response.json()["first_name"] == "firsttest"
    assert response.json()["last_name"] == "lasttest"
    assert response.json()["role"] == "admin"
    assert response.json()["is_active"] == True


def test_password_change_success(test_user):
    request_body = {"password": "password", "new_password": "newpassword"}
    response = client.put("/user/password", json=request_body)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    db = TestingSessionLocal()
    user = db.query(Users).filter(Users.username == "georgetest").first()
    assert bcrypt_context.verify("newpassword", user.hashed_password)


def test_password_change_invalid_current_password(test_user):
    request_body = {"password": "wrong_password", "new_password": "newpassword"}
    response = client.put("/user/password", json=request_body)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Error on password verification"}

