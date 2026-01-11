 Refactor App to Use New Database

 Overview

 Refactor the GolfMapper3 application to use the new database (dbs/golf_mapper_sqlite.db) instead of the old database (backend/app/garmin.db). This requires updating column names, table names, and database paths throughout the application.

 Current State Analysis

 Database Schema Differences

 Old Database (garmin.db):
 - Table: courses
   - id, g_course, g_address, g_city, g_state, g_country, g_latitude, g_longitude
 - Table: new_user_courses

 New Database (golf_mapper_sqlite.db):
 - Table: courses
   - id, club_name, course_name, created_at, address, city, state, country, latitude, longitude
 - Table: user_courses (renamed from new_user_courses)
 - Table: users

 Column Name Mapping
 ┌─────────────┬─────────────────────────────┐
 │ Old Column  │         New Column          │
 ├─────────────┼─────────────────────────────┤
 │ g_course    │ course_name (or club_name?) │
 ├─────────────┼─────────────────────────────┤
 │ g_address   │ address                     │
 ├─────────────┼─────────────────────────────┤
 │ g_city      │ city                        │
 ├─────────────┼─────────────────────────────┤
 │ g_state     │ state                       │
 ├─────────────┼─────────────────────────────┤
 │ g_country   │ country                     │
 ├─────────────┼─────────────────────────────┤
 │ g_latitude  │ latitude                    │
 ├─────────────┼─────────────────────────────┤
 │ g_longitude │ longitude                   │
 └─────────────┴─────────────────────────────┘
 Note: The new DB has both club_name and course_name. Need to determine which to use for display.

 Files That Need Changes

 1. Database Configuration

 - File: backend/app/database.py:27
   - Change default SQLite path from /garmin.db to new database location

 2. Models

 - File: backend/app/models.py
   - Update Courses model column names to match new database
   - Update UserCourses.__tablename__ from "new_user_courses" to "user_courses"

 3. Routers

 - File: backend/app/routers/garmin_courses.py
   - Update all references to old column names (g_course, g_city, g_state, g_latitude, g_longitude)
   - Update CourseBase Pydantic model
 - File: backend/app/routers/garmin_courses_no_auth.py
   - Update all references to old column names
 - File: backend/app/routers/map.py:55-58
   - Update map generation to use new column names

 4. Utility Scripts

 - File: backend/app/manual_GPS_edit.py
   - Update column references (if still needed)

 User Decisions

 ✓ Database Path: backend/app/golf_mapper.db (user has already copied it)
 ✓ Course Name Display: Use "{club_name} - {course_name}" if different, otherwise just course_name

 Implementation Plan

 Phase 1: Update Database Configuration

 1. Update backend/app/database.py
   - Change default SQLite path from /garmin.db to /golf_mapper.db

 Phase 2: Update Models

 1. Update backend/app/models.py:
   - Rename all g_* columns to new names:
       - g_course → Keep as property/computed field (logic: club_name - course_name if different)
     - g_address → address
     - g_city → city
     - g_state → state
     - g_country → country
     - g_latitude → latitude
     - g_longitude → longitude
   - Add club_name, course_name, and created_at columns
   - Add property g_course that returns formatted name
   - Change UserCourses.__tablename__ to "user_courses"

 Phase 3: Update Routers

 1. garmin_courses.py:
   - Update CourseBase Pydantic model to include club_name, course_name, and add computed g_course
   - Replace Courses.g_state → Courses.state
   - Replace Courses.g_latitude → Courses.latitude
   - Replace Courses.g_longitude → Courses.longitude
   - Update all references in queries
   - The g_course property will handle formatting automatically
 2. garmin_courses_no_auth.py:
   - Same column updates as above
 3. map.py:
   - Update to use i.g_course property (which will use the formatted name logic)
   - Update i.g_latitude → i.latitude
   - Update i.g_longitude → i.longitude
 4. user_courses.py:
   - Verify it works with renamed table (should be automatic via model)

 Phase 4: Update Utility Scripts

 1. Update backend/app/manual_GPS_edit.py if still needed

 Phase 5: Testing

 1. Test each endpoint:
   - /garmin_courses/readall
   - /garmin_courses/readall_alabama
   - /garmin_courses/course/{id}
   - /garmin_courses/closest_courses/
   - /user_courses/readall
   - /user_courses/readall_ids_w_year
   - /map/user_map_generate
 2. Verify:
   - Courses are displayed correctly
   - Queries work with new column names
   - Maps generate properly
   - User courses link correctly

 Implementation Details

 Courses Model Changes

 Before:
 class Courses(Base):
     __tablename__ = "courses"
     id = Column(Integer, primary_key=True)
     g_course = Column(String(250))
     g_address = Column(String(250))
     g_city = Column(String(100))
     g_state = Column(String(40))
     g_country = Column(String(40))
     g_latitude = Column(Float)
     g_longitude = Column(Float)

 After:
 class Courses(Base):
     __tablename__ = "courses"
     id = Column(Integer, primary_key=True)
     club_name = Column(String)
     course_name = Column(String)
     created_at = Column(String)  # TIMESTAMP in DB
     address = Column(String)
     city = Column(String)
     state = Column(String)
     country = Column(String)
     latitude = Column(Float)
     longitude = Column(Float)

     @property
     def g_course(self):
         """Computed property for backwards compatibility"""
         if self.club_name and self.course_name and self.club_name != self.course_name:
             return f"{self.club_name} - {self.course_name}"
         return self.course_name or self.club_name or ""

 Database Path Change

 backend/app/database.py line 27:
 - Change: SQLALCHEMY_DATABASE_URL = "sqlite:////garmin.db"
 - To: SQLALCHEMY_DATABASE_URL = "sqlite:////golf_mapper.db"

 Summary of Changes

 Files to Modify:
 1. backend/app/database.py - Update default database path
 2. backend/app/models.py - Update Courses and UserCourses models
 3. backend/app/routers/garmin_courses.py - Update column references and Pydantic model
 4. backend/app/routers/garmin_courses_no_auth.py - Update column references
 5. backend/app/routers/map.py - Update column references
 6. backend/app/manual_GPS_edit.py - Update if still needed

 Key Strategy:
 - Add g_course as a computed property for backwards compatibility
 - This minimizes changes needed in routers/map code
 - Direct column references (g_latitude, g_state, etc.) must still be updated

 Risks & Considerations

 1. Frontend Impact: Frontend code may expect old field names in API responses
 2. Testing Required: All endpoints must be tested after changes
 3. Backwards Compatibility: The g_course property helps but field names in JSON responses will change

 Verification Checklist

 - Database connection works with new path
 - All models use correct column names
 - All routers query correctly
 - Course data displays properly
 - Maps generate with correct coordinates
 - User courses link properly
 - No references to old column names remain
 - Frontend still works (may need separate updates)