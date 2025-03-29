from enum import Enum
import httpx
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .cities import us_cities, CityName

app = FastAPI()

# Add CORS middleware to allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8083", "http://127.0.0.1:8083"],  # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.get("/api/items")
async def get_items():
    return {"items": ["Item 1", "Item 2", "Item 3"]}

@app.get("/api/fake_weather")
async def get_fake_weather():
    return {
  "latitude": 33.50626,
  "longitude": -86.8124,
  "generationtime_ms": 0.020503997802734375,
  "utc_offset_seconds": 0,
  "timezone": "GMT",
  "timezone_abbreviation": "GMT",
  "elevation": 187,
  "current_units": {
    "time": "iso8601",
    "interval": "seconds",
    "temperature_2m": "°C",
    "wind_speed_10m": "km/h"
  },
  "current": {
    "time": "2025-03-22T17:00",
    "interval": 900,
    "temperature_2m": 19,
    "wind_speed_10m": 12.4
  },
  "city": "Birmingham"
}

@app.get("/api/weather")
async def get_weather(
        city: Optional[CityName] = Query(None, description="Select a city from the dropdown")
):
    # Get coordinates for the selected city (or default to Birmingham)
    if city:
        city_name = city.value
    else:
        city_name = "Birmingham"

    # Get coordinates from the cities dictionary
    lat, long = us_cities[city_name]

    # Construct URL with coordinates
    url = f"https://api.open-meteo.com/v1/forecast?units=imperial&latitude={lat}&longitude={long}&current=temperature_2m,wind_speed_10m"

    # Make API request
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        # Add city name to response
        data["city"] = city_name

        return data

@app.get("/api/cities")
async def get_cities():
    return {city.name: city.value for city in CityName}