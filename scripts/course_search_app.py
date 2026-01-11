"""
Standalone Golf Course Search Application
Connects to golf_mapper_sqlite.db and provides a web interface to search courses
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel, ConfigDict
from typing import Optional
import uvicorn
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Database setup
SQLITE_DB_PATH = "../dbs/golf_mapper_sqlite.db"
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

# Pydantic Model
class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    club_name: Optional[str] = None
    course_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# FastAPI app
app = FastAPI(title="Golf Course Search", version="1.0.0")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the search interface"""
    return HTML_TEMPLATE

@app.get("/api/courses")
async def search_courses(
    search: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 100
):
    """Search courses with optional filters"""
    from sqlalchemy import or_
    db = SessionLocal()
    try:
        query = db.query(Courses)

        # Apply filters
        if search:
            search_pattern = f"%{search}%"
            # Search in both club_name and course_name
            query = query.filter(
                or_(
                    Courses.club_name.like(search_pattern),
                    Courses.course_name.like(search_pattern)
                )
            )

        if city:
            city_pattern = f"%{city}%"
            query = query.filter(Courses.city.like(city_pattern))

        if state:
            state_pattern = f"%{state}%"
            query = query.filter(Courses.state.like(state_pattern))

        if country:
            country_pattern = f"%{country}%"
            query = query.filter(Courses.country.like(country_pattern))

        # Get results with limit
        courses = query.limit(limit).all()

        return {
            "count": len(courses),
            "courses": [CourseResponse.model_validate(course).model_dump() for course in courses]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    db = SessionLocal()
    try:
        total_courses = db.query(Courses).count()
        countries = db.query(Courses.country).distinct().count()
        return {
            "total_courses": total_courses,
            "total_countries": countries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Golf Course Search</title>
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
            max-width: 1200px;
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

        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 15px;
            font-size: 0.9em;
            opacity: 0.9;
        }

        .search-section {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }

        .search-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .input-group {
            display: flex;
            flex-direction: column;
        }

        .input-group label {
            font-weight: 600;
            margin-bottom: 5px;
            color: #495057;
            font-size: 0.9em;
        }

        .input-group input {
            padding: 10px 15px;
            border: 2px solid #dee2e6;
            border-radius: 6px;
            font-size: 1em;
            transition: border-color 0.3s;
        }

        .input-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .button-group {
            display: flex;
            gap: 10px;
            justify-content: center;
        }

        button {
            padding: 12px 30px;
            font-size: 1em;
            font-weight: 600;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-search {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-search:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-clear {
            background: #6c757d;
            color: white;
        }

        .btn-clear:hover {
            background: #5a6268;
        }

        .results-section {
            padding: 30px;
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .results-count {
            font-size: 1.1em;
            color: #495057;
            font-weight: 600;
        }

        .table-container {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }

        thead {
            background: #f8f9fa;
            position: sticky;
            top: 0;
        }

        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
            cursor: pointer;
            user-select: none;
        }

        th:hover {
            background: #e9ecef;
        }

        td {
            padding: 12px 15px;
            border-bottom: 1px solid #dee2e6;
        }

        tbody tr:hover {
            background: #f8f9fa;
        }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }

        .no-results-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }

        .loading {
            text-align: center;
            padding: 60px 20px;
            color: #667eea;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .sort-indicator {
            margin-left: 5px;
            opacity: 0.5;
        }

        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏌️ Golf Course Search</h1>
            <div class="stats" id="stats">
                <span>Loading statistics...</span>
            </div>
        </div>

        <div class="search-section">
            <div class="search-grid">
                <div class="input-group">
                    <label for="searchInput">Course Name</label>
                    <input type="text" id="searchInput" placeholder="Search by name...">
                </div>
                <div class="input-group">
                    <label for="cityInput">City</label>
                    <input type="text" id="cityInput" placeholder="Filter by city...">
                </div>
                <div class="input-group">
                    <label for="stateInput">State</label>
                    <input type="text" id="stateInput" placeholder="Filter by state...">
                </div>
                <div class="input-group">
                    <label for="countryInput">Country</label>
                    <input type="text" id="countryInput" placeholder="Filter by country...">
                </div>
            </div>
            <div class="button-group">
                <button class="btn-search" onclick="searchCourses()">Search</button>
                <button class="btn-clear" onclick="clearSearch()">Clear</button>
            </div>
        </div>

        <div class="results-section">
            <div class="results-header">
                <div class="results-count" id="resultsCount">Enter search criteria</div>
            </div>
            <div class="table-container" id="tableContainer">
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <p>Enter search criteria and click "Search" to find golf courses</p>
                </div>
            </div>
        </div>

        <div class="footer">
            GolfMapper3 Course Search • Database: golf_mapper_sqlite.db
        </div>
    </div>

    <script>
        let currentData = [];
        let sortColumn = null;
        let sortAscending = true;

        // Load stats on page load
        window.addEventListener('DOMContentLoaded', loadStats);

        // Allow Enter key to trigger search
        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') searchCourses();
            });
        });

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if (data && data.total_courses !== undefined) {
                    document.getElementById('stats').innerHTML = `
                        <span>📊 Total Courses: ${data.total_courses.toLocaleString()}</span>
                        <span>🌍 Countries: ${data.total_countries}</span>
                    `;
                } else {
                    throw new Error('Invalid data structure received');
                }
            } catch (error) {
                console.error('Error loading stats:', error);
                document.getElementById('stats').innerHTML = `
                    <span>⚠️ Unable to load statistics</span>
                `;
            }
        }

        async function searchCourses() {
            const search = document.getElementById('searchInput').value;
            const city = document.getElementById('cityInput').value;
            const state = document.getElementById('stateInput').value;
            const country = document.getElementById('countryInput').value;

            // Build query parameters
            const params = new URLSearchParams();
            if (search) params.append('search', search);
            if (city) params.append('city', city);
            if (state) params.append('state', state);
            if (country) params.append('country', country);
            params.append('limit', '1000');

            // Show loading
            document.getElementById('tableContainer').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Searching courses...</p>
                </div>
            `;

            try {
                const response = await fetch(`/api/courses?${params.toString()}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if (data && Array.isArray(data.courses)) {
                    currentData = data.courses;
                    displayResults(currentData);
                    document.getElementById('resultsCount').textContent =
                        `Found ${data.count} course${data.count !== 1 ? 's' : ''}`;
                } else {
                    throw new Error('Invalid data structure received');
                }
            } catch (error) {
                console.error('Error searching courses:', error);
                document.getElementById('tableContainer').innerHTML = `
                    <div class="no-results">
                        <div class="no-results-icon">⚠️</div>
                        <p>Error searching courses: ${error.message}</p>
                        <p style="font-size: 0.9em; margin-top: 10px;">Check the console for details.</p>
                    </div>
                `;
            }
        }

        function displayResults(courses) {
            if (!courses || !Array.isArray(courses) || courses.length === 0) {
                document.getElementById('tableContainer').innerHTML = `
                    <div class="no-results">
                        <div class="no-results-icon">🔍</div>
                        <p>No courses found matching your criteria</p>
                    </div>
                `;
                return;
            }

            const tableHTML = `
                <table>
                    <thead>
                        <tr>
                            <th onclick="sortTable('id')">ID <span class="sort-indicator">↕</span></th>
                            <th onclick="sortTable('club_name')">Club <span class="sort-indicator">↕</span></th>
                            <th onclick="sortTable('course_name')">Course <span class="sort-indicator">↕</span></th>
                            <th onclick="sortTable('city')">City <span class="sort-indicator">↕</span></th>
                            <th onclick="sortTable('state')">State <span class="sort-indicator">↕</span></th>
                            <th onclick="sortTable('country')">Country <span class="sort-indicator">↕</span></th>
                            <th>Coordinates</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${courses.map(course => `
                            <tr>
                                <td>${course.id}</td>
                                <td>${course.club_name || 'N/A'}</td>
                                <td><strong>${course.course_name || 'N/A'}</strong></td>
                                <td>${course.city || 'N/A'}</td>
                                <td>${course.state || 'N/A'}</td>
                                <td>${course.country || 'N/A'}</td>
                                <td>${course.latitude && course.longitude
                                    ? `${course.latitude.toFixed(4)}, ${course.longitude.toFixed(4)}`
                                    : 'N/A'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;

            document.getElementById('tableContainer').innerHTML = tableHTML;
        }

        function sortTable(column) {
            if (sortColumn === column) {
                sortAscending = !sortAscending;
            } else {
                sortColumn = column;
                sortAscending = true;
            }

            const sorted = [...currentData].sort((a, b) => {
                const aVal = a[column] || '';
                const bVal = b[column] || '';

                if (typeof aVal === 'number' && typeof bVal === 'number') {
                    return sortAscending ? aVal - bVal : bVal - aVal;
                }

                return sortAscending
                    ? String(aVal).localeCompare(String(bVal))
                    : String(bVal).localeCompare(String(aVal));
            });

            displayResults(sorted);
        }

        function clearSearch() {
            document.getElementById('searchInput').value = '';
            document.getElementById('cityInput').value = '';
            document.getElementById('stateInput').value = '';
            document.getElementById('countryInput').value = '';
            document.getElementById('resultsCount').textContent = 'Enter search criteria';
            document.getElementById('tableContainer').innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <p>Enter search criteria and click "Search" to find golf courses</p>
                </div>
            `;
            currentData = [];
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("🏌️ Starting Golf Course Search Application...")
    print(f"📁 Database: {SQLITE_DB_PATH}")
    print("🌐 Open your browser to: http://localhost:8888")
    print("⌨️  Press CTRL+C to stop the server\n")

    uvicorn.run(app, host="0.0.0.0", port=8888)