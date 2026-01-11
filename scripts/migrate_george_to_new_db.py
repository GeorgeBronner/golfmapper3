#!/usr/bin/env python3
"""
Migration script to copy george user and courses from old DB to new DB.

This script:
1. Creates users and new_user_courses tables in the new database
2. Copies the george user from the old database
3. Populates user_courses with courses from george_matches.json

Usage:
    python scripts/migrate_george_to_new_db.py           # Dry run (default)
    python scripts/migrate_george_to_new_db.py --execute # Execute migration
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# Add backend to path for SQLAlchemy imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import Users


# File paths
OLD_DB_PATH = PROJECT_ROOT / "backend" / "app" / "garmin.db"
NEW_DB_PATH = PROJECT_ROOT / "dbs" / "golf_mapper_sqlite.db"
JSON_PATH = PROJECT_ROOT / "dbs" / "george_matches.json"


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f" {text}")
    print('=' * 60)


def print_step(step_num, total, text):
    """Print a step indicator"""
    print(f"\n[{step_num}/{total}] {text}...", end=" ", flush=True)


def print_success():
    """Print success indicator"""
    print("[OK]")


def print_error(text):
    """Print error message"""
    print(f"[X]\nERROR: {text}")


def safety_checks():
    """Perform pre-flight safety checks"""
    print_header("Safety Checks")

    errors = []

    # Check old DB exists
    if not OLD_DB_PATH.exists():
        errors.append(f"Old database not found: {OLD_DB_PATH}")
    else:
        print(f"[OK] Old DB exists: {OLD_DB_PATH}")

    # Check new DB exists
    if not NEW_DB_PATH.exists():
        errors.append(f"New database not found: {NEW_DB_PATH}")
    else:
        print(f"[OK] New DB exists: {NEW_DB_PATH}")

    # Check JSON file exists
    if not JSON_PATH.exists():
        errors.append(f"JSON file not found: {JSON_PATH}")
    else:
        print(f"[OK] JSON file exists: {JSON_PATH}")

    if errors:
        for error in errors:
            print_error(error)
        return False

    # Check george user exists in old DB
    try:
        db = SessionLocal()
        george = db.query(Users).filter(Users.username == "george").first()
        if not george:
            errors.append("User 'george' not found in old database")
        else:
            print(f"[OK] George user found in old DB (ID: {george.id})")
        db.close()
    except Exception as e:
        errors.append(f"Error reading old database: {e}")

    # Check new DB has courses table
    try:
        conn = sqlite3.connect(NEW_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM courses")
        course_count = cursor.fetchone()[0]
        print(f"[OK] New DB has {course_count:,} courses")
        conn.close()
    except Exception as e:
        errors.append(f"Error reading new database courses: {e}")

    # Check JSON is valid
    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)
        mapping_count = len(data.get('mappings', []))
        print(f"[OK] JSON file loaded with {mapping_count} mappings")
    except Exception as e:
        errors.append(f"Error reading JSON file: {e}")

    if errors:
        for error in errors:
            print_error(error)
        return False

    return True


def get_george_user():
    """Fetch george user from old database"""
    db = SessionLocal()
    try:
        george = db.query(Users).filter(Users.username == "george").first()
        return {
            'username': george.username,
            'email': george.email,
            'first_name': george.first_name,
            'last_name': george.last_name,
            'hashed_password': george.hashed_password,
            'is_active': george.is_active,
            'role': george.role
        }
    finally:
        db.close()


def load_course_mappings():
    """Load course mappings from JSON file"""
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)
    return data['mappings']


def validate_course_ids(mappings, new_db_conn):
    """Validate that golf_courses.id exists in new database"""
    cursor = new_db_conn.cursor()

    valid_mappings = []
    skipped = []
    missing_courses = []

    for mapping in mappings:
        # Skip if no golf_courses match
        if 'golf_courses' not in mapping or not mapping['golf_courses']:
            skipped.append({
                'garmin_id': mapping['garmin'].get('id', 'Unknown'),
                'name': mapping['garmin'].get('course_name', 'Unknown'),
                'reason': 'No match found'
            })
            continue

        golf_course_id = mapping['golf_courses']['id']

        # Check if course exists in new DB
        cursor.execute("SELECT COUNT(*) FROM courses WHERE id = ?", (golf_course_id,))
        exists = cursor.fetchone()[0] > 0

        if not exists:
            missing_courses.append({
                'garmin_id': mapping['garmin'].get('id', 'Unknown'),
                'golf_course_id': golf_course_id,
                'name': mapping['garmin'].get('course_name', 'Unknown')
            })
            continue

        # Extract year (first year played, or None)
        years_played = mapping['garmin'].get('years_played', [])
        year = years_played[0] if years_played else None

        valid_mappings.append({
            'course_id': golf_course_id,
            'year': year,
            'garmin_name': mapping['garmin'].get('course_name', 'Unknown'),
            'golf_course_name': mapping['golf_courses'].get('course_name', 'Unknown')
        })

    return valid_mappings, skipped, missing_courses


def dry_run():
    """Show what would happen without executing"""
    print_header("Migration Dry Run")

    print(f"\nOld DB: {OLD_DB_PATH}")
    print(f"New DB: {NEW_DB_PATH}")
    print(f"JSON: {JSON_PATH}")

    # Get george user
    george = get_george_user()
    print(f"\n{'User to migrate:'}")
    print(f"  Username: {george['username']}")
    print(f"  Email: {george['email']}")
    print(f"  Name: {george['first_name']} {george['last_name']}")
    print(f"  Role: {george['role']}")
    print(f"  Active: {george['is_active']}")

    # Load and validate course mappings
    mappings = load_course_mappings()
    conn = sqlite3.connect(NEW_DB_PATH)

    valid_mappings, skipped, missing_courses = validate_course_ids(mappings, conn)
    conn.close()

    print(f"\n{'Courses to migrate:'} {len(valid_mappings)}")
    if skipped:
        print(f"  Skipped (no match): {len(skipped)}")
    if missing_courses:
        print(f"  Skipped (course not in new DB): {len(missing_courses)}")

    # Show sample mappings
    print(f"\n{'Sample mappings (first 5):'}")
    for i, mapping in enumerate(valid_mappings[:5], 1):
        year_str = str(mapping['year']) if mapping['year'] else 'N/A'
        print(f"  {i}. {mapping['garmin_name'][:50]}")
        print(f"     -> Course ID {mapping['course_id']} (year: {year_str})")

    # Show warnings
    warnings = []
    if skipped:
        warnings.append(f"{len(skipped)} course(s) have no golf_courses.id (will be skipped)")
    if missing_courses:
        warnings.append(f"{len(missing_courses)} course(s) not found in new database (will be skipped)")

    courses_without_year = sum(1 for m in valid_mappings if m['year'] is None)
    if courses_without_year:
        warnings.append(f"{courses_without_year} course(s) have no years_played data")

    if warnings:
        print(f"\n{'[!] Warnings:'}")
        for warning in warnings:
            print(f"  - {warning}")

    # Show skipped courses details
    if skipped:
        print(f"\n{'Skipped courses (no match):'}")
        for course in skipped:
            print(f"  - {course['name']} (Garmin ID: {course['garmin_id']})")

    if missing_courses:
        print(f"\n{'Skipped courses (not in new DB):'}")
        for course in missing_courses:
            print(f"  - {course['name']} (Golf course ID: {course['golf_course_id']})")

    print(f"\n{'-' * 60}")
    print("Use --execute flag to perform migration.")
    print('-' * 60)


def execute_migration():
    """Execute the actual migration"""
    print_header("Executing Migration")

    new_conn = None

    try:
        # Connect to new database
        new_conn = sqlite3.connect(NEW_DB_PATH)
        new_conn.execute("BEGIN TRANSACTION")
        cursor = new_conn.cursor()

        # Step 1: Create users table
        print_step(1, 5, "Creating users table")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR UNIQUE,
                username VARCHAR UNIQUE,
                first_name VARCHAR,
                last_name VARCHAR,
                hashed_password VARCHAR,
                is_active BOOLEAN DEFAULT 1,
                role VARCHAR
            )
        """)
        print_success()

        # Step 2: Create user_courses table
        print_step(2, 5, "Creating new_user_courses table")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS new_user_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                user_id INTEGER,
                year INTEGER,
                FOREIGN KEY (course_id) REFERENCES courses(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        print_success()

        # Step 3: Copy george user
        print_step(3, 5, "Copying george user")
        george = get_george_user()

        # Check if george already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (george['username'],))
        existing = cursor.fetchone()

        if existing:
            george_id = existing[0]
            print(f"[OK] (already exists, ID: {george_id})")
        else:
            cursor.execute("""
                INSERT INTO users (email, username, first_name, last_name, hashed_password, is_active, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                george['email'],
                george['username'],
                george['first_name'],
                george['last_name'],
                george['hashed_password'],
                george['is_active'],
                george['role']
            ))
            george_id = cursor.lastrowid
            print(f"[OK] (ID: {george_id})")

        # Step 4: Insert user_courses
        print_step(4, 5, f"Inserting user_courses records")

        mappings = load_course_mappings()
        valid_mappings, skipped, missing_courses = validate_course_ids(mappings, new_conn)

        # Check for existing courses for this user
        cursor.execute("SELECT COUNT(*) FROM new_user_courses WHERE user_id = ?", (george_id,))
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            print(f"\n  [!] Warning: {existing_count} course(s) already exist for user. Skipping duplicates...")

        inserted = 0
        duplicates = 0

        for mapping in valid_mappings:
            # Check if course already exists for this user
            cursor.execute("""
                SELECT COUNT(*) FROM new_user_courses
                WHERE user_id = ? AND course_id = ?
            """, (george_id, mapping['course_id']))

            if cursor.fetchone()[0] > 0:
                duplicates += 1
                continue

            cursor.execute("""
                INSERT INTO new_user_courses (course_id, user_id, year)
                VALUES (?, ?, ?)
            """, (mapping['course_id'], george_id, mapping['year']))
            inserted += 1

        print(f"[OK] ({inserted} inserted")
        if duplicates > 0:
            print(f"  {duplicates} duplicate(s) skipped")
        if skipped:
            print(f"  {len(skipped)} no-match course(s) skipped")
        if missing_courses:
            print(f"  {len(missing_courses)} missing course(s) skipped")
        print(")")

        # Step 5: Verify migration
        print_step(5, 5, "Verifying migration")

        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (george['username'],))
        user_exists = cursor.fetchone()[0] > 0

        cursor.execute("SELECT COUNT(*) FROM new_user_courses WHERE user_id = ?", (george_id,))
        course_count = cursor.fetchone()[0]

        if user_exists and course_count > 0:
            print_success()
        else:
            raise Exception("Verification failed")

        # Commit transaction
        new_conn.commit()

        # Show results
        print_header("Migration Complete")
        print(f"\n{'Results:'}")
        print(f"  - Users table created")
        print(f"  - UserCourses table created")
        print(f"  - George user migrated (ID: {george_id})")
        print(f"  - {inserted} courses migrated")
        if duplicates > 0:
            print(f"  - {duplicates} duplicate(s) skipped")
        if skipped:
            print(f"  - {len(skipped)} course(s) skipped (no match)")
        if missing_courses:
            print(f"  - {len(missing_courses)} course(s) skipped (missing in new DB)")

        # Show sample records
        cursor.execute("""
            SELECT c.course_id, c.year
            FROM new_user_courses c
            WHERE c.user_id = ?
            LIMIT 5
        """, (george_id,))

        sample_records = cursor.fetchall()
        if sample_records:
            print(f"\n{'Sample records:'}")
            for course_id, year in sample_records:
                year_str = str(year) if year else 'N/A'
                print(f"  Course {course_id}: {year_str}")

    except Exception as e:
        if new_conn:
            new_conn.rollback()
        print_error(f"Migration failed: {e}")
        raise

    finally:
        if new_conn:
            new_conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate george user and courses to new database"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the migration (default is dry run)'
    )

    args = parser.parse_args()

    # Safety checks
    if not safety_checks():
        print("\nSafety checks failed. Aborting.")
        sys.exit(1)

    # Execute or dry run
    if args.execute:
        try:
            execute_migration()
        except Exception as e:
            print(f"\nMigration failed: {e}")
            sys.exit(1)
    else:
        dry_run()


if __name__ == "__main__":
    main()
