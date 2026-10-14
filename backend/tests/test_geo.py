import pytest
from fastapi import status
from sqlalchemy import text

from app.dependencies import get_current_user, get_db
from app.geo import nominatim_to_geo, normalize_country, normalize_state

from .utils import app, client, engine, override_get_current_user, override_get_db

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


# ── Nominatim address → DB codes ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "address,expected",
    [
        (
            {"country_code": "us", "state": "Florida", "city": "Lakeland", "ISO3166-2-lvl4": "US-FL"},
            {"city": "Lakeland", "state": "FL", "country": "USA"},
        ),
        (
            {"country_code": "ca", "state": "Nova Scotia", "city": "Halifax", "ISO3166-2-lvl4": "CA-NS"},
            {"city": "Halifax", "state": "NS", "country": "CAN"},
        ),
        (
            {"country_code": "mx", "state": "Quintana Roo", "town": "Cancún", "ISO3166-2-lvl4": "MX-ROO"},
            {"city": "Cancún", "state": "ROO", "country": "MEX"},
        ),
        # GB and IE are stored by county (lvl6), not by nation/province
        (
            {"country_code": "gb", "village": "Wisley", "ISO3166-2-lvl4": "GB-ENG", "ISO3166-2-lvl6": "GB-SRY"},
            {"city": "Wisley", "state": "SRY", "country": "GBR"},
        ),
        (
            {"country_code": "gb", "city": "Belfast", "ISO3166-2-lvl4": "GB-NIR"},
            {"city": "Belfast", "state": "NIR", "country": "GBR"},
        ),
        (
            {"country_code": "ie", "city": "Dublin", "ISO3166-2-lvl5": "IE-L", "ISO3166-2-lvl6": "IE-D"},
            {"city": "Dublin", "state": "D", "country": "IRL"},
        ),
        # Everywhere else uses the first-level subdivision
        (
            {"country_code": "it", "city": "Roma", "ISO3166-2-lvl4": "IT-62", "ISO3166-2-lvl6": "IT-RM"},
            {"city": "Roma", "state": "62", "country": "ITA"},
        ),
        # No ISO subdivisions → empty state
        ({"country_code": "je", "town": "St Helier"}, {"city": "St Helier", "state": "", "country": "JEY"}),
        (
            {"country_code": "nl", "town": "Philipsburg", "ISO3166-2-lvl3": "NL-SX"},
            {"city": "Philipsburg", "state": "", "country": "SXM"},
        ),
        # US territories are stored as USA + territory code
        ({"country_code": "pr", "city": "San Juan"}, {"city": "San Juan", "state": "PR", "country": "USA"}),
        # Never fall back to a full state name
        ({"country_code": "us", "state": "Florida", "city": "Tampa"}, {"city": "Tampa", "state": "", "country": "USA"}),
        ({}, {"city": "", "state": "", "country": ""}),
    ],
)
def test_nominatim_to_geo(address, expected):
    assert nominatim_to_geo(address) == expected


def test_normalize_country():
    assert normalize_country(" usa ") == "USA"
    assert normalize_country(None) is None
    for bad in ["US", "United States", "", "XXX"]:
        with pytest.raises(ValueError):
            normalize_country(bad)


def test_normalize_state():
    assert normalize_state(" fl ") == "FL"
    assert normalize_state("") == ""
    assert normalize_state("D") == "D"
    for bad in ["Florida", "Nova Scotia", "US-FL", "ABCD"]:
        with pytest.raises(ValueError):
            normalize_state(bad)


# ── API rejects non-standard values ──────────────────────────────────────────


@pytest.fixture
def cleanup_courses():
    yield
    with engine.connect() as con:
        con.execute(text("DELETE FROM courses;"))
        con.commit()


def _new_course(**geo):
    return {"club_name": "Geo Club", "latitude": 27.8, "longitude": -81.9, **geo}


def test_admin_create_course_normalizes_codes(cleanup_courses):
    response = client.post("/api/v1/admin/courses", json=_new_course(state="fl", country="usa"))
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["state"] == "FL"
    assert response.json()["country"] == "USA"


def test_admin_create_course_allows_empty_state(cleanup_courses):
    response = client.post("/api/v1/admin/courses", json=_new_course(state="", country="JEY"))
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["state"] == ""


@pytest.mark.parametrize(
    "geo",
    [
        {"state": "FL", "country": "United States"},
        {"state": "FL", "country": "US"},
        {"state": "Nova Scotia", "country": "CAN"},
        {"state": "JY", "country": "JEY"},
    ],
)
def test_admin_create_course_rejects_bad_codes(geo, cleanup_courses):
    response = client.post("/api/v1/admin/courses", json=_new_course(**geo))
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_admin_update_course_info_rejects_bad_country(test_user_courses):
    response = client.put("/api/v1/admin/courses/200/info", json={"country": "United States"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_new_course_request_rejects_bad_country():
    response = client.post("/api/v1/course-requests/new-course", json=_new_course(state="QR", country="Mexico"))
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
