#!/usr/bin/env python3
"""
Merge Courses and Locations Script
Creates a new golf_courses_loc_merged.db with courses and locations in a single table.

Author: Generated for GolfMapper3
Date: 2026-01-10
"""

import sqlite3
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_DB = PROJECT_ROOT / "dbs/golf_courses.db"
TARGET_DB = PROJECT_ROOT / "dbs/golf_courses_loc_merged.db"


def merge_courses_and_locations():
    """
    Merge courses and locations tables into a single table.
    """
    print("=" * 70)
    print("Merging Courses and Locations Tables")
    print("=" * 70)

    # Validate source database exists
    if not SOURCE_DB.exists():
        print(f"ERROR: Source database not found: {SOURCE_DB}")
        return False

    print(f"\nSource database: {SOURCE_DB}")
    print(f"Target database: {TARGET_DB}")

    # Connect to source database
    print("\nConnecting to source database...")
    source_conn = sqlite3.connect(SOURCE_DB)
    source_cursor = source_conn.cursor()

    # Get schema information
    print("\nAnalyzing source schema...")

    # Get courses table columns
    source_cursor.execute("PRAGMA table_info(courses)")
    courses_columns = source_cursor.fetchall()
    print(f"  Courses table has {len(courses_columns)} columns")

    # Get locations table columns
    source_cursor.execute("PRAGMA table_info(locations)")
    locations_columns = source_cursor.fetchall()
    print(f"  Locations table has {len(locations_columns)} columns")

    # Count records
    source_cursor.execute("SELECT COUNT(*) FROM courses")
    total_courses = source_cursor.fetchone()[0]
    print(f"  Total courses: {total_courses}")

    source_cursor.execute("""
        SELECT COUNT(*)
        FROM courses c
        LEFT JOIN locations l ON c.id = l.course_id
        WHERE l.id IS NOT NULL
    """)
    courses_with_locations = source_cursor.fetchone()[0]
    print(f"  Courses with locations: {courses_with_locations}")

    # Create new database
    print(f"\nCreating new database: {TARGET_DB}")
    if TARGET_DB.exists():
        print("  WARNING: Target database already exists. It will be overwritten.")
        TARGET_DB.unlink()

    target_conn = sqlite3.connect(TARGET_DB)
    target_cursor = target_conn.cursor()

    # Get actual columns from courses table
    # Format: (cid, name, type, notnull, dflt_value, pk)
    courses_col_info = {col[1]: col[2] for col in courses_columns}  # name -> type
    courses_col_names = [col[1] for col in courses_columns]
    print(f"  Courses columns: {', '.join(courses_col_names)}")

    # Get actual columns from locations table (excluding id and course_id)
    locations_col_info = {col[1]: col[2] for col in locations_columns}
    locations_col_names = [col[1] for col in locations_columns if col[1] not in ['id', 'course_id']]
    print(f"  Locations columns: {', '.join(locations_col_names)}")

    # Build SELECT clause dynamically based on actual columns
    courses_select = ', '.join([f'c.{col}' for col in courses_col_names])
    locations_select = ', '.join([f'l.{col}' for col in locations_col_names])

    # Create merged courses table with actual source columns + location columns
    print("\nCreating merged courses table...")

    # Build column definitions from source courses table
    col_defs = []
    for col_name in courses_col_names:
        col_type = courses_col_info[col_name]
        if col_name == 'id':
            col_defs.append(f"{col_name} {col_type} PRIMARY KEY")
        else:
            col_defs.append(f"{col_name} {col_type}")

    # Add location columns from actual locations table
    for col_name in locations_col_names:
        col_type = locations_col_info[col_name]
        col_defs.append(f"{col_name} {col_type}")

    create_table_sql = f"""
    CREATE TABLE courses (
        {',\n        '.join(col_defs)}
    )
    """
    target_cursor.execute(create_table_sql)
    print("  Table created successfully")

    # Copy and merge data
    print("\nMerging and copying data...")
    merge_sql = f"""
    SELECT
        {courses_select},
        {locations_select}
    FROM courses c
    LEFT JOIN locations l ON c.id = l.course_id
    """

    source_cursor.execute(merge_sql)
    rows = source_cursor.fetchall()

    # Build INSERT dynamically to match SELECT
    target_columns = courses_col_names + locations_col_names
    placeholders = ', '.join(['?'] * len(target_columns))
    insert_sql = f"""
    INSERT INTO courses ({', '.join(target_columns)})
    VALUES ({placeholders})
    """

    target_cursor.executemany(insert_sql, rows)
    target_conn.commit()

    print(f"  Copied {len(rows)} courses")

    # Create indices for common lookups (only if columns exist)
    print("\nCreating indices...")
    all_columns = set(target_columns)
    indices = []

    if 'club_name' in all_columns:
        indices.append("CREATE INDEX idx_courses_club_name ON courses(club_name)")
    if 'course_name' in all_columns:
        indices.append("CREATE INDEX idx_courses_course_name ON courses(course_name)")
    if 'state' in all_columns:
        indices.append("CREATE INDEX idx_courses_state ON courses(state)")
    if 'country' in all_columns:
        indices.append("CREATE INDEX idx_courses_country ON courses(country)")
    if 'latitude' in all_columns and 'longitude' in all_columns:
        indices.append("CREATE INDEX idx_courses_location ON courses(latitude, longitude)")

    for idx_sql in indices:
        target_cursor.execute(idx_sql)
    target_conn.commit()
    print(f"  Created {len(indices)} indices")

    # Verify data
    print("\nVerifying merged database...")
    target_cursor.execute("SELECT COUNT(*) FROM courses")
    merged_count = target_cursor.fetchone()[0]

    target_cursor.execute("SELECT COUNT(*) FROM courses WHERE latitude IS NOT NULL")
    with_coords = target_cursor.fetchone()[0]

    target_cursor.execute("SELECT COUNT(*) FROM courses WHERE latitude IS NULL")
    without_coords = target_cursor.fetchone()[0]

    print(f"  Total courses in merged DB: {merged_count}")
    print(f"  Courses with coordinates: {with_coords}")
    print(f"  Courses without coordinates: {without_coords}")

    # Close connections
    source_conn.close()
    target_conn.close()

    # Print summary
    print("\n" + "=" * 70)
    print("MERGE COMPLETE")
    print("=" * 70)
    print(f"\nNew database created: {TARGET_DB}")
    print(f"Total courses: {merged_count}")
    print(f"  With location data: {with_coords} ({with_coords/merged_count*100:.1f}%)")
    print(f"  Without location data: {without_coords} ({without_coords/merged_count*100:.1f}%)")
    print("\nThe merged database has a single 'courses' table with location")
    print("data included directly in each course record.")
    print("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = merge_courses_and_locations()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
