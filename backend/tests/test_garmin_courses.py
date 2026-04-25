from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app

client = TestClient(app)


def _mock_location(lat=40.7128, lon=-74.0060):
    loc = MagicMock()
    loc.latitude = lat
    loc.longitude = lon
    return loc


def test_zipcode_coordinates_found():
    with patch("app.routers.garmin_courses.geolocator.geocode", return_value=_mock_location()):
        response = client.get("/zipcode_coordinates/", params={"zipcode": "10005", "country": "US"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["latitude"] == 40.7128
    assert data["longitude"] == -74.0060


def test_zipcode_coordinates_not_found():
    with patch("app.routers.garmin_courses.geolocator.geocode", return_value=None):
        response = client.get("/zipcode_coordinates/", params={"zipcode": "notarealplace99999"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Location not found"


def test_zipcode_coordinates_missing_param():
    response = client.get("/zipcode_coordinates/", params={"country": "US"})
    assert response.status_code == 422


def test_city_coordinates_found():
    with patch("app.routers.garmin_courses.geolocator.geocode", return_value=_mock_location(33.4484, -112.0740)):
        response = client.get("/city_coordinates/", params={"city": "Phoenix", "state": "AZ"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["latitude"] == 33.4484
    assert data["longitude"] == -112.0740


def test_city_coordinates_not_found():
    with patch("app.routers.garmin_courses.geolocator.geocode", return_value=None):
        response = client.get("/city_coordinates/", params={"city": "NotARealCityXYZ"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Location not found"
