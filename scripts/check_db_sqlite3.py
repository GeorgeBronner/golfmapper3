"""
Check what data is in the courses table using sqlite3
"""
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "backend" / "app" / "golf_mapper.db"

def main():
    print(f"Checking database at: {DB_PATH}")
    print()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get first 5 courses
        cursor.execute("SELECT COUNT(*) FROM courses")
        total = cursor.fetchone()[0]
        print(f"Found {total} total courses")
        print()

        cursor.execute("SELECT id, club_name, course_name, city, state FROM courses LIMIT 5")
        courses = cursor.fetchall()

        print("First 5 courses:")
        print()

        for i, course in enumerate(courses):
            id, club_name, course_name, city, state = course
            print(f"Course {i+1}:")
            print(f"  ID: {id}")
            print(f"  club_name: '{club_name}'")
            print(f"  course_name: '{course_name}'")

            # Calculate display_name
            if club_name and course_name and club_name != course_name:
                display_name = f"{club_name} - {course_name}"
            elif course_name:
                display_name = course_name
            elif club_name:
                display_name = club_name
            else:
                display_name = ""

            print(f"  display_name: '{display_name}'")
            print(f"  city: '{city}'")
            print(f"  state: '{state}'")
            print()

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
