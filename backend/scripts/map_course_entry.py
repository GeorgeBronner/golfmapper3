"""
Map-Based Golf Course Entry Application
Allows adding new courses to the database by clicking on a map
Uses OpenStreetMaps with Leaflet and reverse geocoding
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, model_validator
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Share the country/state code rules with the API (backend/app/geo.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.geo import COUNTRY_CODES, CountryCode, StateCode, check_state_for_country, nominatim_to_geo  # noqa: E402

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Database setup
SQLITE_DB_PATH = "../golf_mapper.db"
DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Model
class Courses(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    club_name = Column(String(250))
    course_name = Column(String(250))
    created_at = Column(String)
    address = Column(String(250))
    city = Column(String(100))
    state = Column(String(40))
    country = Column(String(40))
    latitude = Column(Float)
    longitude = Column(Float)


# Pydantic Models
class CourseCreate(BaseModel):
    club_name: str
    course_name: str
    address: Optional[str] = None
    city: str
    state: StateCode = ""
    country: CountryCode
    latitude: float
    longitude: float

    @model_validator(mode="after")
    def state_matches_country(self):
        check_state_for_country(self.state, self.country)
        return self


class ReverseGeocodeResponse(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


# FastAPI app
app = FastAPI(title="Golf Course Map Entry", version="1.0.0")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the map interface"""
    return HTML_TEMPLATE.replace("__COUNTRY_CODES__", json.dumps(sorted(COUNTRY_CODES)))


@app.get("/api/reverse-geocode")
async def reverse_geocode(lat: float, lon: float):
    """Reverse geocode coordinates using Nominatim"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
                headers={"User-Agent": "GolfMapper3/1.0"},
                timeout=10.0,
            )

            if response.status_code != 200:
                return {"address": None, "city": None, "state": None, "country": None}

            data = response.json()
            address_data = data.get("address", {})

            # Try to get full address
            full_address = data.get("display_name", "").split(",")[0] if data.get("display_name") else None

            # City, ISO 3166-2 state code and ISO alpha-3 country, same rules as the main app
            geo = nominatim_to_geo(address_data)
            city = geo["city"] or address_data.get("municipality") or None
            state = geo["state"] or None
            country = geo["country"] or None

            return {"address": full_address, "city": city, "state": state, "country": country}

    except Exception as e:
        print(f"Reverse geocoding error: {e}")
        return {"address": None, "city": None, "state": None, "country": None}


@app.post("/api/courses")
async def create_course(course: CourseCreate):
    """Create a new course in the database"""
    db = SessionLocal()
    try:
        # Create timestamp in ISO format
        created_at = datetime.now(timezone.utc).isoformat()

        # Create new course record
        new_course = Courses(
            club_name=course.club_name,
            course_name=course.course_name,
            created_at=created_at,
            address=course.address,
            city=course.city,
            state=course.state,
            country=course.country,
            latitude=course.latitude,
            longitude=course.longitude,
        )

        db.add(new_course)
        db.commit()
        db.refresh(new_course)

        return {"success": True, "id": new_course.id, "message": "Course added successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e
    finally:
        db.close()


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Add Golf Course - Map Entry</title>

    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .map-container {
            position: relative;
            height: 600px;
        }

        #map {
            width: 100%;
            height: 100%;
        }

        .instructions {
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }

        .instructions h2 {
            color: #495057;
            font-size: 1.2em;
            margin-bottom: 10px;
        }

        .instructions ol {
            margin-left: 20px;
            color: #6c757d;
        }

        .instructions li {
            margin-bottom: 5px;
        }

        /* Custom Leaflet Popup Styles */
        .leaflet-popup-content-wrapper {
            border-radius: 8px;
            padding: 0;
        }

        .leaflet-popup-content {
            margin: 0;
            min-width: 320px;
        }

        .popup-form {
            padding: 20px;
        }

        .popup-form h3 {
            margin-bottom: 15px;
            color: #495057;
            font-size: 1.2em;
        }

        .form-group {
            margin-bottom: 12px;
        }

        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #495057;
            font-size: 0.9em;
        }

        .form-group label .required {
            color: #dc3545;
            margin-left: 3px;
        }

        .form-group input {
            width: 100%;
            padding: 8px 12px;
            border: 2px solid #dee2e6;
            border-radius: 6px;
            font-size: 0.95em;
            transition: border-color 0.3s;
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .form-group input:disabled {
            background: #f8f9fa;
            cursor: not-allowed;
        }

        .form-group small {
            display: block;
            margin-top: 3px;
            color: #6c757d;
            font-size: 0.85em;
        }

        .error-message {
            color: #dc3545;
            font-size: 0.9em;
            margin-top: 10px;
            display: none;
        }

        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .btn {
            flex: 1;
            padding: 10px 20px;
            font-size: 1em;
            font-weight: 600;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #6c757d;
            color: white;
        }

        .btn-secondary:hover {
            background: #5a6268;
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 10px;
            color: #667eea;
        }

        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }

        /* Confirmation dialog styles */
        .confirmation-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            justify-content: center;
            align-items: center;
        }

        .confirmation-dialog {
            background: white;
            border-radius: 12px;
            padding: 30px;
            max-width: 500px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .confirmation-dialog h3 {
            color: #495057;
            margin-bottom: 15px;
        }

        .confirmation-details {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        .confirmation-details p {
            margin-bottom: 8px;
            color: #495057;
        }

        .confirmation-details strong {
            color: #212529;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏌️ Add Golf Course</h1>
            <p>Click on the map to add a new course to the database</p>
        </div>

        <div class="instructions">
            <h2>Instructions:</h2>
            <ol>
                <li>Click anywhere on the map to select a course location</li>
                <li>Enter either Club Name or Course Name (at least one is required)</li>
                <li>Location details will be auto-filled via reverse geocoding</li>
                <li>Verify and edit City, State, and Country if needed (these are required)</li>
                <li>Review and confirm to add the course to the database</li>
            </ol>
        </div>

        <div class="map-container">
            <div id="map"></div>
        </div>

        <div class="footer">
            GolfMapper3 Course Entry • Database: golf_mapper_sqlite.db
        </div>
    </div>

    <!-- Confirmation overlay -->
    <div class="confirmation-overlay" id="confirmationOverlay">
        <div class="confirmation-dialog">
            <h3>Confirm New Course</h3>
            <div class="confirmation-details" id="confirmationDetails"></div>
            <div class="button-group">
                <button class="btn btn-primary" onclick="submitCourse()">Yes, Add Course</button>
                <button class="btn btn-secondary" onclick="cancelConfirmation()">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <script>
        const COUNTRY_CODES = new Set(__COUNTRY_CODES__);
        let map;
        let currentMarker = null;
        let currentPopup = null;
        let pendingCourseData = null;

        // Initialize map
        function initMap() {
            // Center on US (you can change this default location)
            map = L.map('map').setView([39.8283, -98.5795], 4);

            // Add OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 19
            }).addTo(map);

            // Add click handler
            map.on('click', onMapClick);
        }

        async function onMapClick(e) {
            const { lat, lng } = e.latlng;

            // Remove previous marker if exists
            if (currentMarker) {
                map.removeLayer(currentMarker);
            }

            // Add new marker
            currentMarker = L.marker([lat, lng]).addTo(map);

            // Create popup content
            const popupContent = createPopupForm(lat, lng);
            currentPopup = L.popup({
                closeButton: true,
                autoClose: false,
                closeOnClick: false
            })
                .setLatLng([lat, lng])
                .setContent(popupContent)
                .openOn(map);

            // Fetch reverse geocode data
            await fetchReverseGeocode(lat, lng);
        }

        function createPopupForm(lat, lng) {
            return `
                <div class="popup-form">
                    <h3>Add New Course</h3>
                    <div class="form-group">
                        <label>Club Name</label>
                        <input type="text" id="clubName" placeholder="Enter club name">
                        <small>At least one of Club or Course name required</small>
                    </div>
                    <div class="form-group">
                        <label>Course Name</label>
                        <input type="text" id="courseName" placeholder="Enter course name">
                    </div>
                    <div class="form-group">
                        <label>Address <span style="color: #6c757d;">(optional)</span></label>
                        <input type="text" id="address" placeholder="Loading...">
                    </div>
                    <div class="form-group">
                        <label>City <span class="required">*</span></label>
                        <input type="text" id="city" placeholder="Loading...">
                    </div>
                    <div class="form-group">
                        <label>State/Province <span style="color: #6c757d;">(ISO code, blank if none)</span></label>
                        <input type="text" id="state" placeholder="Loading...">
                    </div>
                    <div class="form-group">
                        <label>Country <span class="required">*</span> <span style="color: #6c757d;">(ISO alpha-3, e.g. USA)</span></label>
                        <input type="text" id="country" placeholder="Loading..." maxlength="3">
                    </div>
                    <div class="form-group">
                        <label>Coordinates</label>
                        <input type="text" id="coordinates" value="${lat.toFixed(6)}, ${lng.toFixed(6)}" disabled>
                    </div>
                    <div class="loading" id="geocodeLoading">Loading location data...</div>
                    <div class="error-message" id="errorMessage"></div>
                    <div class="button-group">
                        <button class="btn btn-primary" onclick="validateAndConfirm(${lat}, ${lng})">Next</button>
                        <button class="btn btn-secondary" onclick="map.closePopup()">Cancel</button>
                    </div>
                </div>
            `;
        }

        async function fetchReverseGeocode(lat, lng) {
            const loadingEl = document.getElementById('geocodeLoading');
            if (loadingEl) loadingEl.style.display = 'block';

            try {
                const response = await fetch(`/api/reverse-geocode?lat=${lat}&lon=${lng}`);
                const data = await response.json();

                // Update form fields
                if (data.address) {
                    document.getElementById('address').value = data.address;
                    document.getElementById('address').placeholder = 'Address';
                } else {
                    document.getElementById('address').value = '';
                    document.getElementById('address').placeholder = 'Address not found';
                }

                if (data.city) {
                    document.getElementById('city').value = data.city;
                } else {
                    document.getElementById('city').value = '';
                    document.getElementById('city').placeholder = 'Please enter city';
                }

                if (data.state) {
                    document.getElementById('state').value = data.state;
                } else {
                    document.getElementById('state').value = '';
                    document.getElementById('state').placeholder = 'State code (blank if none)';
                }

                if (data.country) {
                    document.getElementById('country').value = data.country;
                } else {
                    document.getElementById('country').value = '';
                    document.getElementById('country').placeholder = 'Please enter country';
                }

            } catch (error) {
                console.error('Reverse geocoding failed:', error);
                document.getElementById('address').placeholder = 'Could not load address';
                document.getElementById('city').placeholder = 'Please enter city';
                document.getElementById('state').placeholder = 'Please enter state';
                document.getElementById('country').placeholder = 'Please enter country';
            } finally {
                if (loadingEl) loadingEl.style.display = 'none';
            }
        }

        function validateAndConfirm(lat, lng) {
            const clubName = document.getElementById('clubName').value.trim();
            const courseName = document.getElementById('courseName').value.trim();
            const address = document.getElementById('address').value.trim();
            const city = document.getElementById('city').value.trim();
            const state = document.getElementById('state').value.trim().toUpperCase();
            const country = document.getElementById('country').value.trim().toUpperCase();
            const errorEl = document.getElementById('errorMessage');

            // Validation
            if (!clubName && !courseName) {
                errorEl.textContent = 'Please enter at least Club Name or Course Name';
                errorEl.style.display = 'block';
                return;
            }

            if (!city || !country) {
                errorEl.textContent = 'City and Country are required';
                errorEl.style.display = 'block';
                return;
            }

            if (!COUNTRY_CODES.has(country)) {
                errorEl.textContent = `Country must be an ISO alpha-3 code such as USA, GBR or CAN (got "${country}")`;
                errorEl.style.display = 'block';
                return;
            }

            if (state && !/^[A-Z0-9]{1,3}$/.test(state)) {
                errorEl.textContent = 'State must be an ISO subdivision code (1-3 letters/digits, e.g. FL), or blank';
                errorEl.style.display = 'block';
                return;
            }

            // If only one name is provided, use it for both
            const finalClubName = clubName || courseName;
            const finalCourseName = courseName || clubName;

            // Store pending data
            pendingCourseData = {
                club_name: finalClubName,
                course_name: finalCourseName,
                address: address || null,
                city: city,
                state: state,
                country: country,
                latitude: lat,
                longitude: lng
            };

            // Show confirmation dialog
            showConfirmation();
        }

        function escapeHtml(value) {
            const div = document.createElement('div');
            div.textContent = value;
            return div.innerHTML;
        }

        function showConfirmation() {
            const details = `
                <p><strong>Club Name:</strong> ${escapeHtml(pendingCourseData.club_name)}</p>
                <p><strong>Course Name:</strong> ${escapeHtml(pendingCourseData.course_name)}</p>
                ${pendingCourseData.address ? `<p><strong>Address:</strong> ${escapeHtml(pendingCourseData.address)}</p>` : ''}
                <p><strong>City:</strong> ${escapeHtml(pendingCourseData.city)}</p>
                <p><strong>State:</strong> ${escapeHtml(pendingCourseData.state)}</p>
                <p><strong>Country:</strong> ${escapeHtml(pendingCourseData.country)}</p>
                <p><strong>Coordinates:</strong> ${pendingCourseData.latitude.toFixed(6)}, ${pendingCourseData.longitude.toFixed(6)}</p>
            `;

            document.getElementById('confirmationDetails').innerHTML = details;
            document.getElementById('confirmationOverlay').style.display = 'flex';
        }

        function cancelConfirmation() {
            document.getElementById('confirmationOverlay').style.display = 'none';
            pendingCourseData = null;
        }

        async function submitCourse() {
            if (!pendingCourseData) return;

            try {
                const response = await fetch('/api/courses', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(pendingCourseData)
                });

                if (!response.ok) {
                    const error = await response.json();
                    const detail = Array.isArray(error.detail) ? error.detail.map(d => d.msg).join('; ') : error.detail;
                    throw new Error(detail || 'Failed to add course');
                }

                const result = await response.json();

                // Close confirmation dialog
                document.getElementById('confirmationOverlay').style.display = 'none';

                // Close popup
                map.closePopup();

                // Show success message
                alert(`✅ Course added successfully! (ID: ${result.id})`);

                // Reset
                pendingCourseData = null;
                if (currentMarker) {
                    map.removeLayer(currentMarker);
                    currentMarker = null;
                }

            } catch (error) {
                console.error('Error adding course:', error);
                alert(`❌ Error: ${error.message}`);
            }
        }

        // Initialize map on page load
        window.addEventListener('DOMContentLoaded', initMap);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("🏌️ Starting Golf Course Map Entry Application...")
    print(f"📁 Database: {SQLITE_DB_PATH}")
    print("🌐 Open your browser to: http://localhost:8889")
    print("⌨️  Press CTRL+C to stop the server\n")

    # Local admin tool with no auth — must not be reachable from the network.
    uvicorn.run(app, host="127.0.0.1", port=8889)
