# Golf Course Search - Standalone Application

A lightweight, standalone web application for searching golf courses in the GolfMapper database.

## Features

- 🔍 **Real-time search** by course name, city, state, and country
- 📊 **Database statistics** showing total courses and countries
- 🔄 **Sortable columns** - click any column header to sort
- 🎨 **Modern UI** with gradient design and responsive layout
- ⚡ **Fast & lightweight** - single file application
- 🗄️ **Direct SQLite access** - connects to `dbs/golf_mapper_sqlite.db`

## Quick Start

### 1. Install Dependencies

```bash
# From the scripts directory
pip install fastapi uvicorn sqlalchemy pydantic
```

Or use uv (faster):

```bash
uv pip install fastapi uvicorn sqlalchemy pydantic
```

### 2. Run the Application

```bash
# From the scripts directory
python course_search_app.py
```

Or with uv:

```bash
uv run python course_search_app.py
```

### 3. Open Your Browser

Navigate to: **http://localhost:8888**

## Usage

1. **Search by any criteria:**
   - Course Name: Find courses by name (partial match supported)
   - City: Filter by city name
   - State: Filter by state/province
   - Country: Filter by country

2. **Click "Search"** to query the database (up to 1,000 results)

3. **Sort results** by clicking column headers (ID, Name, City, State, Country)

4. **Clear filters** with the "Clear" button to start fresh

## API Endpoints

The application exposes two API endpoints:

### GET `/api/courses`

Search courses with optional filters:

**Query Parameters:**
- `search` - Course name search term (partial match)
- `city` - City filter (partial match)
- `state` - State filter (partial match)
- `country` - Country filter (partial match)
- `limit` - Max results to return (default: 100, max in UI: 1000)

**Example:**
```
http://localhost:8888/api/courses?search=pebble&country=US&limit=10
```

**Response:**
```json
{
  "count": 2,
  "courses": [
    {
      "id": 12345,
      "g_course": "Pebble Beach Golf Links",
      "g_address": "1700 17 Mile Dr",
      "g_city": "Pebble Beach",
      "g_state": "CA",
      "g_country": "US",
      "g_latitude": 36.5674,
      "g_longitude": -121.9490
    }
  ]
}
```

### GET `/api/stats`

Get database statistics:

**Response:**
```json
{
  "total_courses": 45821,
  "total_countries": 157
}
```

## Database Structure

Connects to: `../dbs/golf_mapper_sqlite.db`

**Courses Table:**
- `id` - Primary key
- `club_name` - Club name (e.g., "Augusta National Golf Club")
- `course_name` - Course name (e.g., "Augusta National")
- `address` - Street address
- `city` - City
- `state` - State/Province
- `country` - Country
- `latitude` - GPS latitude
- `longitude` - GPS longitude
- `created_at` - Timestamp

**Statistics:**
- Total courses: 25,402
- Total countries: 62

## Configuration

To modify the database path, edit the `SQLITE_DB_PATH` variable at the top of `course_search_app.py`:

```python
SQLITE_DB_PATH = "../dbs/golf_mapper_sqlite.db"
```

To change the port, modify the `uvicorn.run()` call at the bottom:

```python
uvicorn.run(app, host="0.0.0.0", port=8888)  # Change port here
```

## Technical Details

- **Backend**: FastAPI + SQLAlchemy
- **Database**: SQLite (direct connection)
- **Frontend**: Vanilla JavaScript (embedded HTML)
- **Styling**: CSS3 with gradients and animations
- **No authentication required** (standalone tool)

## Differences from Main Application

This standalone app differs from the main GolfMapper3 application:

- ❌ No authentication required
- ❌ No user-specific data (doesn't use `UserCourses` table)
- ✅ Simpler, single-file deployment
- ✅ Server-side filtering (more efficient than client-side)
- ✅ Direct database access (no backend routing complexity)

## Troubleshooting

### Database not found
If you get a database error, make sure:
1. You're running the script from the `scripts/` directory
2. The database file exists at `dbs/golf_mapper_sqlite.db`
3. The relative path `../dbs/golf_mapper_sqlite.db` is correct

### Port already in use
If port 8888 is already in use:
1. Edit the port in the script (bottom of file)
2. Or stop the process using port 8888

### Missing dependencies
Install required packages:
```bash
pip install fastapi uvicorn sqlalchemy pydantic
```

## License

Part of the GolfMapper3 project.
