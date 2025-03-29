from routers.user_courses import get_db, get_current_user
from fastapi import status
from .utils import *

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


def test_readall_authenticated(test_user_courses):
    response = client.get("/user_courses/readall")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": 200,
            "g_course": "RTJ Golf Trail at Magnolia Grove - Falls",
            "g_address": "  7001 MAGNOLIA GROVE PKY",
            "g_country": "US",
            "g_longitude": -88.20578,
            "g_city": "Mobile",
            "g_state": "Alabama",
            "g_latitude": 30.740501
        }
    ]


def test_read_one_authenticated(test_user_courses):
    response = client.get("/user_courses/readall_ids")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {'course_id': 200, 'user_id': 1, 'year': 2021, 'id': 1}
    ]
