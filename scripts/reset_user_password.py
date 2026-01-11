"""
Utility script to reset user passwords in the GolfMapper3 database.

This script:
1. Connects to the golf_mapper.db database
2. Lists all users
3. Allows you to select a user
4. Resets their password to one you choose
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/app/.env
env_path = Path(__file__).parent.parent / "backend" / "app" / ".env"
load_dotenv(dotenv_path=env_path)

# Add parent directory to path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Import the Users model
from app.models import Users

# Set up bcrypt for password hashing (same as used in auth.py)
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database path
DB_PATH = Path(__file__).parent.parent / "backend" / "app" / "golf_mapper.db"

def main():
    print("=" * 60)
    print("GolfMapper3 - User Password Reset Utility")
    print("=" * 60)
    print()

    # Check if database exists
    if not DB_PATH.exists():
        print(f"❌ Error: Database not found at {DB_PATH}")
        print("Please ensure the database file exists.")
        return

    # Connect to database
    engine = create_engine(f'sqlite:///{DB_PATH}')
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Fetch all users
        users = session.query(Users).all()

        if not users:
            print("❌ No users found in the database.")
            print("Please create a user account first through the application.")
            return

        # Display users
        print(f"Found {len(users)} user(s) in the database:\n")
        print(f"{'#':<4} {'Username':<20} {'Email':<30} {'Name':<25} {'Role':<10}")
        print("-" * 95)

        for idx, user in enumerate(users, 1):
            full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else "N/A"
            print(f"{idx:<4} {user.username:<20} {user.email:<30} {full_name:<25} {user.role:<10}")

        print()

        # Get user selection
        while True:
            try:
                selection = input(f"Select user number (1-{len(users)}) or 'q' to quit: ").strip()

                if selection.lower() == 'q':
                    print("\n👋 Exiting without changes.")
                    return

                user_idx = int(selection) - 1

                if 0 <= user_idx < len(users):
                    selected_user = users[user_idx]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(users)}")
            except ValueError:
                print("❌ Invalid input. Please enter a number or 'q' to quit.")

        # Confirm selection
        print()
        print(f"Selected user: {selected_user.username} ({selected_user.email})")
        confirm = input("Continue with password reset? (yes/no): ").strip().lower()

        if confirm not in ['yes', 'y']:
            print("\n👋 Password reset cancelled.")
            return

        # Get new password
        print()
        while True:
            new_password = input("Enter new password (min 4 characters): ").strip()

            if len(new_password) < 4:
                print("❌ Password must be at least 4 characters long.")
                continue

            confirm_password = input("Confirm new password: ").strip()

            if new_password != confirm_password:
                print("❌ Passwords do not match. Please try again.")
                continue

            break

        # Hash the password and update
        hashed_password = bcrypt_context.hash(new_password)
        selected_user.hashed_password = hashed_password
        session.commit()

        print()
        print("✅ Password successfully reset!")
        print(f"   User: {selected_user.username}")
        print(f"   You can now log in with the new password.")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    main()
