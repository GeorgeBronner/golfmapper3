"""
Test authentication and password verification
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/app/.env
env_path = Path(__file__).parent.parent / "backend" / "app" / ".env"
load_dotenv(dotenv_path=env_path)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.models import Users

# Set up bcrypt (same as auth.py)
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database path
DB_PATH = Path(__file__).parent.parent / "backend" / "app" / "golf_mapper.db"

def main():
    print("Testing authentication...")
    print()

    # Connect to database
    engine = create_engine(f'sqlite:///{DB_PATH}')
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get the george user
        user = session.query(Users).filter(Users.username == "george").first()

        if not user:
            print("[ERROR] User 'george' not found")
            return

        print(f"User found: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Hashed password (first 60 chars): {user.hashed_password[:60]}")
        print()

        # Test password
        test_password = input("Enter password to test: ").strip()

        print(f"\nTesting password: '{test_password}'")
        print(f"Against hash: {user.hashed_password[:60]}...")

        # Verify password
        is_valid = bcrypt_context.verify(test_password, user.hashed_password)

        print()
        if is_valid:
            print("[SUCCESS] Password is VALID - authentication should work!")
        else:
            print("[FAIL] Password is INVALID - authentication will fail")
            print()
            print("Let's reset it now...")
            new_password = "newpassword123"
            new_hash = bcrypt_context.hash(new_password)
            print(f"New hash: {new_hash[:60]}...")

            user.hashed_password = new_hash
            session.commit()

            # Verify the new password
            is_valid_new = bcrypt_context.verify(new_password, user.hashed_password)
            print()
            if is_valid_new:
                print(f"[SUCCESS] Password reset to: {new_password}")
                print("   Authentication should now work!")
            else:
                print("[FAIL] Something went wrong with the reset")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()
