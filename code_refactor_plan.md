# GolfMapper3 — Comprehensive Code Refactor Plan

**Reviewed**: 2026-04-24  
**Branch**: `apr26-refactor`  
**Scope**: Full-stack audit of backend (FastAPI/Python) and frontend (React/Vite)

---

## Tier 1 — Must Do ✅ ALL COMPLETE (2026-04-25)

These are things that are broken or dangerous right now and should be fixed before any new feature work.

---

### [B-1] Unprotected division-by-zero endpoint in production
**File**: `backend/app/routers/admin.py:49–51`  
No auth check, deliberately crashes the process. Any unauthenticated user can trigger it.
```python
@router.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
```
**Fix**: Delete it. Sentry integration testing doesn't belong in a production route.

---

### [B-2] Debug print statements leak authentication data
**File**: `backend/app/routers/auth.py:42–53`  
Six `print()` calls log the attempted username and password check results to stdout on every login attempt. This is in production code.
```python
print(f"[DEBUG] authenticate_user: username={username}")
print(f"[DEBUG] Password valid: {password_valid}")
```
**Fix**: Remove all six debug prints immediately.

---

### [B-3] Map file path traversal vulnerability
**File**: `backend/app/routers/map.py:37, 61`  
Username is concatenated directly into a file path without sanitization. A user with a username containing `../` characters could escape the maps directory.
```python
user_map.save(f"app/static/user_maps/user_map_{user['username']}_{user['id']}.html")
```
**Fix**: Use only `user['id']` (integer, safe) in the filename — username is unnecessary:
```python
map_path = map_dir / f"user_map_{user['id']}.html"
```

---

### [B-4] Map directory not created — crashes with FileNotFoundError
**File**: `backend/app/routers/map.py:37, 61`  
The directory `app/static/user_maps/` is hardcoded and assumed to exist. On a fresh deploy or Docker container it doesn't, causing an unhandled exception. The GET endpoint at `:37` also has no existence check — it will crash if the map was never generated.
```python
# No directory creation, no try/except, no 404 fallback
return FileResponse(f"app/static/user_maps/user_map_{user['username']}_{user['id']}.html")
```
**Fix**:
```python
from pathlib import Path

MAP_DIR = Path(os.getenv("MAP_FILES_DIR", "./static/user_maps"))

@router.get("/user_map_generate")
async def user_map_generate(user: user_dependency, db: db_dependency):
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    map_path = MAP_DIR / f"user_map_{user['id']}.html"
    try:
        user_map.save(str(map_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Map generation failed")
    return {"message": "Map generated"}

@router.get("/usermap")
async def get_usermap(user: user_dependency):
    map_path = MAP_DIR / f"user_map_{user['id']}.html"
    if not map_path.exists():
        raise HTTPException(status_code=404, detail="Map not yet generated")
    return FileResponse(str(map_path))
```

---

### [B-5] ProtectedRoute redirects to wrong destination
**File**: `frontend/src/routes/ProtectedRoute.jsx:9`  
Unauthenticated users are redirected to `/course_list` — itself a protected route — creating an infinite redirect loop instead of landing on the login page.
```javascript
return <Navigate to="/course_list" />;  // Wrong
```
**Fix**: `return <Navigate to="/" />;`

---

### [B-6] SSL verification is disabled for geopy
**Files**: `user_courses.py:15–16`, `garmin_courses.py:18–19`, `map.py:16–17`  
```python
ctx = ssl._create_unverified_context(cafile=certifi.where())
```
`_create_unverified_context` bypasses certificate validation entirely, making all geopy calls vulnerable to MITM attacks. This is a Python-private API not meant for application use.  
**Fix**: Use the verified context:
```python
import ssl, certifi
ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx
```

---

### [B-7] isAuthenticated() evaluated once at router creation — not reactive
**File**: `frontend/src/router.js:52`  
```javascript
element: <ProtectedRoute isAuthenticated={isAuthenticated()} />
```
`isAuthenticated()` is called once when the module loads. If the token expires or the user logs out without a full page reload, the router keeps the old `true` value and users can access protected routes with an invalid token. API calls will 401, but the UI won't redirect.  
**Fix**: Move auth check inside `ProtectedRoute` so it's evaluated on each render:
```javascript
// ProtectedRoute.jsx
const ProtectedRoute = () => {
    const token = localStorage.getItem('token');
    if (!token) return <Navigate to="/" />;
    return <div><Header /><Outlet /><Footer /></div>;
};
// router.js — no isAuthenticated prop needed
element: <ProtectedRoute />
```

---

### [B-8] Login silently fires map generation with no error handling
**File**: `frontend/src/components/LoginPage.jsx:24`  
```javascript
.then(response => {
    localStorage.setItem('token', response.data.access_token);
    generateUserMap();   // Fire-and-forget, no await, no error handling
    navigate('/course_list');
})
```
`generateUserMap()` is called before navigating but its result is neither awaited nor handled. If it fails (e.g., user has no courses), the error is silently swallowed. Also generates a map on every login — wasteful.  
**Fix**: Remove `generateUserMap()` from the login flow. The map should be generated on-demand from the Map page.

---

## Tier 2 — Needed (Code correctness, data integrity, notable UX gaps)

---

### [N-1] GarminCourses and CourseSearch both skip the first course
**Files**: `GarminCourses.jsx:54`, `CourseSearch.jsx:73`  
```javascript
// GarminCourses.jsx
{this.state.courses.slice(1).map(course => ...)}
// CourseSearch.jsx
response.data.shift();
```
Both components silently discard the first item in the course list with no comment explaining why. This hides a real course from users.  
**Fix**: Remove both `.slice(1)` and `.shift()` calls. If this was working around a specific data issue (e.g., a header row), document it explicitly or fix the upstream data.

---

### [N-2] Duplicate `get_db()` across 8 router files
**Files**: `auth.py:29`, `admin.py:12`, `users.py:14`, `garmin_courses.py:24`, `user_courses.py:20`, `map.py:21`, `garmin_courses_no_auth.py:24`, `user_courses_no_auth.py:20`  
Identical 5-line function copied 8 times. Same with `db_dependency = Annotated[Session, Depends(get_db)]`.  
**Fix**: Create `backend/app/dependencies.py`:
```python
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
```
Then import in all routers. Also centralise the SSL context and `bcrypt_context` here.

---

### [N-3] N+1 query in readall_ids_w_year
**File**: `backend/app/routers/user_courses.py:67–96`  
Two sequential queries plus an O(n²) nested loop to attach years to courses.
```python
user_courses = db.query(UserCourses.course_id, UserCourses.year).filter(...)
courses = db.query(Courses).filter(Courses.id.in_([...]))
for course in courses:
    for course_id, year in course_ids_years:  # O(n²)
        if course.id == course_id: ...
```
**Fix**: Single join query:
```python
results = (
    db.query(Courses, UserCourses.year)
    .join(UserCourses, Courses.id == UserCourses.course_id)
    .filter(UserCourses.user_id == user.get("id"))
    .all()
)
```

---

### [N-4] Missing SQLAlchemy relationships on models
**File**: `backend/app/models.py`  
ForeignKeys are defined but no `relationship()` is configured. This prevents lazy loading, backref queries, and cascade deletes.  
**Fix**: Add relationships:
```python
class Users(Base):
    courses = relationship("UserCourses", back_populates="user", cascade="all, delete-orphan")

class Courses(Base):
    user_courses = relationship("UserCourses", back_populates="course")

class UserCourses(Base):
    user = relationship("Users", back_populates="courses")
    course = relationship("Courses", back_populates="user_courses")
```

---

### [N-5] Missing database constraints — duplicate course entries allowed
**File**: `backend/app/models.py:52–62`  
`UserCourses` has no unique constraint, so a user can add the same course for the same year multiple times. Foreign key columns also have no `nullable=False` or indexes.  
**Fix**:
```python
from sqlalchemy import UniqueConstraint

class UserCourses(Base):
    __tablename__ = "user_courses"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    year = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', 'year', name='uq_user_course_year'),
    )
```
Note: this requires an Alembic migration (see N-8).

---

### [N-6] Wrong variable and function names in admin.py (copy-paste leftovers)
**File**: `backend/app/routers/admin.py:39–46`  
```python
async def delete_todo(...)         # Should be delete_course
    todo_model = db.query(Courses) # Should be course_model
    raise HTTPException(404, detail="Todo not found")  # Should be "Course not found"
```
**Fix**: Rename function, variable, and error message to match what the code actually does.

---

### [N-7] garmin_courses router has no prefix
**File**: `backend/app/routers/garmin_courses.py:21`  
```python
router = APIRouter()  # No prefix
```
All routes in this file are registered at the root level (`/readall`, `/course/{id}`, etc.) without any namespace, colliding risk with other routers and making the API hard to consume.  
**Fix**: `router = APIRouter(prefix="/garmin_courses", tags=["garmin_courses"])`  
Note: this is a breaking change for frontend code that calls `/readall` — `CourseSearch.jsx:68` and `GarminCourses.jsx:16` both need updating.

---

### [N-8] No database migrations
**File**: `backend/app/main.py:42`  
`Base.metadata.create_all(bind=engine)` creates tables on startup but cannot modify existing schemas. Any column addition, constraint, or type change requires manual intervention in production.  
**Fix**: Implement Alembic:
```bash
cd backend && uv add alembic
alembic init alembic
# Point to app/database.py in alembic.ini
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

---

### [N-9] `created_at` field is String instead of DateTime
**File**: `backend/app/models.py:13`  
```python
created_at = Column(String, nullable=True)  # Wrong type
```
**Fix**: `created_at = Column(DateTime, nullable=True)`

---

### [N-10] Three class components in a functional-component codebase
**Files**: `CourseList.jsx`, `GarminCourses.jsx`, `PageAfterAuth.jsx`  
The rest of the frontend uses functional components with hooks. These three outliers use class components, making the codebase inconsistent and harder to extend with hooks-based patterns.  
**Fix**: Convert to functional components. `CourseList` is the highest priority as it's the main user view.

---

### [N-11] No user feedback on form submission (CourseForm, LoginPage)
**File**: `frontend/src/components/CourseForm.jsx`, `LoginPage.jsx`  
- `CourseForm.jsx`: After submitting, the form clears silently. No success message, no error display if the API returns 409 (duplicate course) or 422 (validation error).
- `LoginPage.jsx`: Wrong credentials silently logs to console. User sees nothing.

**Fix**: Add state for success/error messages and display them inline:
```javascript
const [error, setError] = useState('');
const [success, setSuccess] = useState('');
// In catch: setError('Invalid username or password')
// In then: setSuccess('Course added successfully')
// In render: {error && <div className="alert alert-danger">{error}</div>}
```

---

### [N-12] Delete course has no confirmation dialog
**File**: `frontend/src/components/CourseCard.jsx` (via `CourseList.jsx`)  
Clicking delete immediately fires the DELETE API call with no "Are you sure?" prompt.  
**Fix**: Either use `window.confirm()` as a quick fix, or add a Bootstrap modal for a better UX.

---

### [N-13] Map page makes no attempt to generate map — just fails silently
**File**: `frontend/src/components/Map.jsx`  
The map page fetches `/map/usermap` directly. If the map file doesn't exist (first visit, or after a server restart), the iframe shows nothing and no error is shown to the user.  
**Fix**: On 404 response from `/map/usermap`, automatically call `/map/user_map_generate`, show a loading state, then re-fetch. Or combine into a single endpoint that generates-then-returns.

---

### [N-14] CourseSearch table shows raw debug JSON and a "Force Rerender" button
**File**: `frontend/src/components/CourseSearch.jsx:92, 110, 236`  
```javascript
<button onClick={() => rerender()}>Force Rerender</button>  // Debug button
debugTable: true,                                            // Debug mode on
<pre>{JSON.stringify(table.getState().pagination, null, 2)}</pre>  // Raw JSON visible
```
Three separate debug artifacts are visible to users in production.  
**Fix**: Remove all three.

---

### [N-15] ID column appears twice in CourseSearch table
**File**: `frontend/src/components/CourseSearch.jsx:43–59`  
Both column definitions use `accessorKey: 'id'`, giving the table two ID-keyed columns. This causes TanStack Table to use duplicate column IDs, which will trigger warnings and potentially broken filtering.  
**Fix**: Give the "Link to Add" column a unique id:
```javascript
{
    id: 'add_link',
    accessorKey: 'id',
    header: () => <span>Add</span>,
    ...
}
```

---

## Tier 3 — To Review (Architecture / maintainability improvements)

---

### [R-1] CORS is overly permissive and hardcoded
**File**: `backend/app/main.py:44–73`  
- `allow_methods=["*"]` — permits TRACE, OPTIONS, CONNECT, and other methods that should be blocked
- `allow_headers=["*"]` — no header restrictions
- 20 hardcoded origins including private IPs (10.9.8.221, 132.145.156.224) — maintenance burden
- Mix of http and https for same domains

**Recommendation**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # From env/config
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### [R-2] No configuration management (Pydantic Settings)
**Files**: `backend/app/main.py`, `auth.py`, `database.py`  
Settings are scattered across files using raw `os.getenv()` with no validation, no type checking, and no documentation of required vs optional keys.  
**Recommendation**: Create `backend/app/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY_AUTH: str
    USE_SQLITE_DB: bool = True
    SQLITE_DB_URL: str = ""
    SENTRY_DSN: str = ""
    STATIC_FILES_DIR: str = "./dist"
    MAP_FILES_DIR: str = "./static/user_maps"
    ALLOWED_ORIGINS: list[str] = ["https://golf.bronnerapp.com"]
    LOG_LEVEL: str = "INFO"
    TRACES_SAMPLE_RATE: float = 0.1  # Not 1.0 in production

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### [R-3] Token lifetime is hardcoded with no refresh support
**File**: `backend/app/routers/auth.py:125`  
```python
token = create_access_token(..., timedelta(minutes=90))
```
90 minutes is hardcoded. No refresh token mechanism exists, so users are abruptly logged out with no recovery path.  
**Recommendation**: Make duration configurable via settings. Add a refresh token endpoint at a minimum.

---

### [R-4] Sentry sample rates set to 100%
**File**: `backend/app/main.py:33, 37`  
```python
traces_sample_rate=1.0,    # 100% of all transactions
profiles_sample_rate=1.0,  # 100% of all profiler runs
```
In production this will generate enormous Sentry bills and slow the application. The code comment even says "We recommend adjusting this value in production" — it was never adjusted.  
**Recommendation**: Set to 0.1 (10%) for traces, 0.0 for profiles unless actively debugging performance.

---

### [R-5] `/readall` for Garmin courses loads entire database client-side
**File**: `backend/app/routers/garmin_courses.py:56–60` + `CourseSearch.jsx:68`, `GarminCourses.jsx:16`  
Both `CourseSearch` and `GarminCourses` call `/readall` which returns all courses in the DB. With 50k+ Garmin courses, this is a large payload on every page load.  
**Recommendation**: 
- `CourseSearch` already has a TanStack Table with pagination — wire it to the existing paginated endpoint (`/readall_page`) instead of fetching everything at once.
- For `GarminCourses`, use server-side search/filter instead of fetching all courses.

---

### [R-6] Direct localStorage access in every component instead of AuthProvider
**Files**: `CourseList.jsx:22`, `CourseForm.jsx:23`, `GarminCourses.jsx:18`, `CourseSearch.jsx:70`, `Map.jsx:7`, `mapUtils.js:7`, `LoginPage.jsx:23`  
`AuthProvider.jsx` exists but is barely used. Every component pulls the token from localStorage directly. If the token storage mechanism ever changes, every component needs updating.  
**Recommendation**: Extend `AuthProvider` to expose `token`, and update all components to use `useAuth()`.

---

### [R-7] No API service layer — duplicate axios boilerplate everywhere
All components manually construct axios requests with auth headers. Related to R-6.  
**Recommendation**: Create `frontend/src/services/api.js` with an interceptor:
```javascript
import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

api.interceptors.response.use(
    res => res,
    err => {
        if (err.response?.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/';
        }
        return Promise.reject(err);
    }
);

export default api;
```
This also handles the currently-missing 401 redirect when tokens expire.

---

### [R-8] No no-auth routers are registered but are still imported
**File**: `backend/app/main.py:12–13, 100, 104`  
```python
from app.routers import ..., garmin_courses_no_auth, ..., user_courses_no_auth, ...
# app.include_router(garmin_courses_no_auth.router)  # Commented out
# app.include_router(user_courses_no_auth.router)    # Commented out
```
Files are imported but routers are commented out. The files themselves remain in the codebase creating confusion.  
**Recommendation**: Either delete the no-auth files entirely, or document why they exist and add a clear comment at the import.

---

### [R-9] Docker EXPOSE mismatch and redundant install steps
**File**: `backend/Dockerfile`  
```dockerfile
EXPOSE 8000          # Wrong — app runs on 8005
RUN uv venv create   # Creates venv
RUN uv sync          # Installs deps into venv
RUN uv pip install --no-cache .  # Installs again — redundant
```
**Recommendation**:
```dockerfile
RUN uv sync --frozen  # Single install step
EXPOSE 8005
```

---

### [R-10] Map uses `document.write()` to inject HTML into iframe
**File**: `frontend/src/components/Map.jsx:18–21`  
```javascript
const doc = iframeRef.current.contentWindow.document;
doc.open();
doc.write(html);  // Deprecated, CSP-hostile
doc.close();
```
`document.write` is deprecated, blocked by some Content Security Policies, and slow. It also means the Folium map HTML is fetched twice (authenticated fetch) and then written into the DOM rather than using a proper URL.  
**Recommendation**: Serve the map file via a URL-based approach with the auth token in a query param or cookie, and use `iframe src=` instead.

---

### [R-11] `get_test_user()` and other unused functions
**Files**: `auth.py:76–78`, `garmin_courses.py:63–68` (`readall_alabama`), `garmin_courses.py:78–91` (`readall_page_manual`)  
- `get_test_user()` is never called anywhere
- `readall_alabama` is a hardcoded test filter
- `readall_page_manual` is a manual re-implementation of `readall_page` (which uses fastapi-pagination)

**Recommendation**: Delete all three. They add noise to the API schema and test surface.

---

### [R-12] config.js logs to console on every page load
**File**: `frontend/src/config.js:7–9`  
```javascript
console.log('import.meta.env.VITE_BACKEND_SERVER_IP value:', ...);
console.log('import.meta.env.VITE_BACKEND_PORT value:', ...);
console.log('API_BASE_URL value:', API_BASE_URL);
```
Three `console.log` statements fire on every page load, leaking configuration to browser devtools.  
**Recommendation**: Remove all three lines.

---

### [R-13] `auth.py` misidentifies function name for course endpoint
**File**: `backend/app/routers/garmin_courses.py:95`  
```python
async def read_todo(...)  # This is read_course
```
Misleading name — this endpoint returns a golf course.  
**Recommendation**: Rename to `read_course`.

---

## Tier 4 — Nice to Have (Improvements that add polish / robustness)

---

### [NH-1] Add structured logging
Currently there is zero logging in either the backend or frontend. Application errors, auth events, and API failures are invisible in production.  
**Recommendation**: Add Python `logging` module usage in backend (structured JSON logging for production). Add a lightweight logging service in frontend (or integrate Sentry properly).

---

### [NH-2] Add loading states to all data-fetching components
`CourseList`, `GarminCourses`, `CourseSearch` all show empty tables while data loads. There's no spinner or skeleton screen.  
**Recommendation**: Add `loading` state to each:
```javascript
const [loading, setLoading] = useState(true);
// In fetch: finally(() => setLoading(false))
// In render: {loading ? <Spinner /> : <table>...}
```

---

### [NH-3] Add React Error Boundaries
No error boundary wraps the component tree. A runtime error in any component crashes the entire app.  
**Recommendation**: Add an `ErrorBoundary` class component and wrap the route tree.

---

### [NH-4] Add rate limiting to auth endpoint
`/auth/token` has no brute force protection.  
**Recommendation**: Add `slowapi` with a limit of e.g. 10 attempts per minute per IP.
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/token")
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, ...):
```

---

### [NH-5] Add audit timestamps to all models
None of the models track `created_at` / `updated_at`. This makes debugging and data auditing impossible.  
**Recommendation**: Add to `Users` and `UserCourses` (requires Alembic migration from N-8):
```python
from datetime import datetime, timezone

created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                    onupdate=lambda: datetime.now(timezone.utc), nullable=False)
```

---

### [NH-6] Add API versioning prefix
All routes are registered without a version prefix. Adding one later is a breaking change.  
**Recommendation**: Mount all routers under `/api/v1/` in `main.py`.

---

### [NH-7] Add Pydantic response models to all endpoints
Some endpoints (admin, users) return raw SQLAlchemy ORM objects. This can leak sensitive fields (e.g., `hashed_password` from the Users model) if the model gains new columns.  
**Recommendation**: Define explicit Pydantic response schemas for every endpoint and set `response_model=` on each route decorator. Already partially done in `user_courses.py` — extend to all routers.

---

### [NH-8] Add no-courses empty state to Map page
If a user has no courses, the map endpoint returns 404. The current UI shows a blank iframe with no explanation.  
**Recommendation**: Detect the 404 and show "You haven't added any courses yet. Add one from Course Search."

---

### [NH-9] Dead code cleanup
The following files serve no purpose in the current codebase:
- `frontend/src/components/CourseSearch_old.jsx` — old duplicate component
- `frontend/src/components/PageTest.jsx` — 272-line test/prototype page
- `frontend/src/components/makeData.jsx` — sample data generator from TanStack Table docs
- `frontend/src/counter.js` — Vite template leftover
- `backend/app/manual_GPS_edit.py` — one-off data migration script with hardcoded path `/Users/george/`

**Recommendation**: Delete all five.

---

### [NH-10] Replace `map.py` feature group hardcoded name
**File**: `backend/app/routers/map.py:53`  
```python
fg = folium.FeatureGroup(name=f"FIX ME - USERNAME")
```
The feature group name is a placeholder that was never filled in.  
**Recommendation**: `fg = folium.FeatureGroup(name=user['username'])`

---

### [NH-11] `UserCourseRequest.check_year` validator silently returns None
**File**: `backend/app/routers/user_courses.py:35–39`  
```python
@field_validator('year')
def check_year(cls, v):
    if v < 1900 or v > 2070:
        return None  # Silent null instead of raising validation error
    return v
```
Returning `None` on invalid year silently stores a null year instead of rejecting the request. The frontend also uses `type="text"` for this field, so any string is accepted.  
**Fix**: Raise `ValueError` and use `type="number"` in the frontend input.

---

### [NH-12] GarminCourses search/filter capability
Currently, `GarminCourses` shows a flat list of all 50k+ courses with no search or filter. The table headers have no sort or filter controls.  
**Recommendation**: Replace `GarminCourses` with the `CourseSearch` component (after fixing [N-1], [R-5]), or add column-level filtering using the same TanStack Table pattern used in `CourseSearch`.

---

### [NH-13] Add test coverage
The backend has a `tests/` directory but minimal coverage. The frontend has `App.test.js` with likely placeholder content.  
**Recommendation**:
- Backend: pytest integration tests for all router endpoints using httpx + TestClient
- Frontend: React Testing Library tests for auth flows, course add/delete, and route protection

---

### [NH-14] Improve 404 handling and SPA routing fallback
**File**: `backend/app/main.py:114–131`  
The catch-all route checks `api_prefixes` to decide whether to serve index.html, but this list is hardcoded and will silently fail if a new router prefix is added without updating the list.  
**Recommendation**: Use a more robust check — return 404 JSON only if the path starts with known API patterns, otherwise always serve index.html.

---

## Summary Table

| ID   | Area     | Issue                                          | Priority    |
|------|----------|------------------------------------------------|-------------|
| B-1  | Backend  | ~~Exposed /sentry-debug crash endpoint~~       | ✅ Done     |
| B-2  | Backend  | ~~Debug prints leaking auth data to stdout~~   | ✅ Done     |
| B-3  | Backend  | ~~Path traversal via username in map filenames~~| ✅ Done    |
| B-4  | Backend  | ~~Map directory not created — FileNotFoundError~~| ✅ Done   |
| B-5  | Frontend | ~~ProtectedRoute redirects to wrong path~~     | ✅ Done     |
| B-6  | Backend  | ~~SSL verification disabled for geopy~~        | ✅ Done     |
| B-7  | Frontend | ~~isAuthenticated evaluated once, not reactive~~| ✅ Done    |
| B-8  | Frontend | ~~generateUserMap called fire-and-forget on login~~| ✅ Done |
| N-1  | Frontend | First course silently skipped in two components| Needed      |
| N-2  | Backend  | get_db() duplicated 8 times                    | Needed      |
| N-3  | Backend  | N+1 query in readall_ids_w_year                | Needed      |
| N-4  | Backend  | No SQLAlchemy relationships on models          | Needed      |
| N-5  | Backend  | No unique constraint on UserCourses            | Needed      |
| N-6  | Backend  | ~~Wrong names in admin.py (todo → course)~~    | ✅ Done     |
| N-7  | Backend  | garmin_courses router has no prefix            | Needed      |
| N-8  | Backend  | No database migrations (Alembic)               | Needed      |
| N-9  | Backend  | created_at is String not DateTime              | Needed      |
| N-10 | Frontend | Class components in functional codebase        | Needed      |
| N-11 | Frontend | No user feedback on form submission (LoginPage ✅, CourseForm pending) | Needed |
| N-12 | Frontend | Delete course has no confirmation              | Needed      |
| N-13 | Frontend | Map page silently fails if not yet generated   | Needed      |
| N-14 | Frontend | CourseSearch shows debug JSON + button         | Needed      |
| N-15 | Frontend | Duplicate column ID in CourseSearch            | Needed      |
| R-1  | Backend  | CORS overly permissive and hardcoded           | To Review   |
| R-2  | Backend  | No Pydantic Settings config management         | To Review   |
| R-3  | Backend  | Token hardcoded 90min, no refresh              | To Review   |
| R-4  | Backend  | Sentry sample rates at 100%                    | To Review   |
| R-5  | Backend  | /readall loads entire course DB client-side    | To Review   |
| R-6  | Frontend | Direct localStorage access vs AuthProvider     | To Review   |
| R-7  | Frontend | No API service layer — duplicate axios code    | To Review   |
| R-8  | Backend  | Disabled no-auth routers still imported        | To Review   |
| R-9  | Docker   | EXPOSE mismatch + redundant install steps      | To Review   |
| R-10 | Frontend | Map uses deprecated document.write() in iframe | To Review   |
| R-11 | Backend  | Unused functions (get_test_user, readall_alabama)| To Review  |
| R-12 | Frontend | config.js console.logs on every page load      | To Review   |
| R-13 | Backend  | read_todo function name for course endpoint    | To Review   |
| NH-1 | Backend  | Add structured logging                         | Nice to Have|
| NH-2 | Frontend | Add loading states                             | Nice to Have|
| NH-3 | Frontend | Add React Error Boundaries                     | Nice to Have|
| NH-4 | Backend  | Rate limiting on /auth/token                   | Nice to Have|
| NH-5 | Backend  | Audit timestamps on models                     | Nice to Have|
| NH-6 | Backend  | API versioning prefix (/api/v1/)               | Nice to Have|
| NH-7 | Backend  | Pydantic response models on all endpoints      | Nice to Have|
| NH-8 | Frontend | Empty state on Map page                        | Nice to Have|
| NH-9 | Both     | Dead code file deletion                        | Nice to Have|
| NH-10| Backend  | ~~Fix hardcoded "FIX ME - USERNAME" in map.py~~| ✅ Done     |
| NH-11| Both     | year validator returns None silently           | Nice to Have|
| NH-12| Frontend | GarminCourses needs search/filter              | Nice to Have|
| NH-13| Both     | Add test coverage (backend ✅ 20/20, frontend blocked by jsdom/vitest ESM conflict) | Nice to Have |
| NH-14| Backend  | Fragile SPA catch-all route (api_prefixes typo /users/→/user/ ✅ fixed) | Nice to Have |

**Must Do**: ~~8 items~~ ✅ 8/8 complete (2026-04-25)  
**Needed**: 13 remaining (N-6 ✅, N-11 partial) — estimated 1–2 days  
**To Review**: 13 items — estimated 2–4 days  
**Nice to Have**: 12 remaining (NH-10 ✅, NH-13 partial, NH-14 partial) — estimated 1–2 weeks  

### Additional fixes made during test overhaul (2026-04-25)
- `garmin_courses.py`: Fixed broad `except Exception` swallowing `HTTPException(404)` and re-raising as 500 — in all four geocoding endpoints
- `main.py`: Fixed `api_prefixes` typo (`/users/` → `/user/`) that caused `/user/` API routes to be served as frontend HTML
- `docker-compose.yml`: Synced to match production server's working config (`golf_mapper.db` at correct bind-mount path)
- Backend test suite: 20/20 passing — rewrote test infrastructure (in-memory SQLite, `app.xxx` imports, mocked geocoder, real admin tests)
- Frontend tests: vitest/jsdom v27 ESM conflict unresolved — deferred to Nice to Have
