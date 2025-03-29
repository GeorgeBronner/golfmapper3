import pytest
from fastapi.testclient import TestClient
from main import app  # Assuming your FastAPI app is in a file named main.py

client = TestClient(app)

def test_get_zipcode_coordinates():
    response = client.get("/zipcode_coordinates/", params={"zipcode": "10005", "country": "US"})
    assert response.status_code == 200
    data = response.json()
    assert "latitude" in data
    assert "longitude" in data
    assert isinstance(data["latitude"], float)
    assert isinstance(data["longitude"], float)

def test_get_zipcode_coordinates_not_found():
    response = client.get("/zipcode_coordinates/", params={"zipcode": "Jason Bourne", "country": "US"})
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "404: Location not found"

def test_get_zipcode_coordinates_invalid():
    response = client.get("/zipcode_coordinates/", params={"zipcode": "", "country": "US"})
    assert response.status_code == 500