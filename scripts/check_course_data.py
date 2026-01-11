"""
Check what data is in the courses table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Courses

# Database path
DB_PATH = Path(__file__).parent.parent / "backend" / "app" / "golf_mapper.db"

def main():
    print(f"Checking database at: {DB_PATH}")
    print()

    # Connect to database
    engine = create_engine(f'sqlite:///{DB_PATH}')
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get first 5 courses
        courses = session.query(Courses).limit(5).all()

        print(f"Found {session.query(Courses).count()} total courses")
        print()
        print("First 5 courses:")
        print()

        for i, course in enumerate(courses):
            print(f"Course {i+1}:")
            print(f"  ID: {course.id}")
            print(f"  club_name: '{course.club_name}'")
            print(f"  course_name: '{course.course_name}'")
            print(f"  display_name: '{course.display_name}'")
            print(f"  city: '{course.city}'")
            print(f"  state: '{course.state}'")
            print()

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()
