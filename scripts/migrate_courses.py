#!/usr/bin/env python3
"""
Script to migrate course records from golf_courses-new.db to golf_mapper_sqlite.db.
Only migrates records with ID < 4900 that don't already exist in the target database.
"""
import sqlite3
from pathlib import Path
import sys

# Database paths
SOURCE_DB = "dbs/golf_courses-new.db"
TARGET_DB = "dbs/golf_mapper_sqlite.db"
MAX_ID = 4900


def get_source_records(source_path: str, max_id: int):
    """Get all records with ID < max_id from source database."""
    conn = sqlite3.connect(source_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, club_name, course_name, address, city, state, country,
               latitude, longitude, created_at
        FROM courses
        WHERE id < ?
        ORDER BY id
    """, (max_id,))

    records = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return records


def get_existing_ids(target_path: str, max_id: int):
    """Get all existing IDs < max_id from target database."""
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM courses WHERE id < ?", (max_id,))
    existing_ids = {row[0] for row in cursor.fetchall()}

    conn.close()
    return existing_ids


def preview_migration(source_records, existing_ids):
    """Show what will be migrated."""
    source_ids = {record['id'] for record in source_records}
    missing_ids = source_ids - existing_ids

    print("=" * 80)
    print("MIGRATION PREVIEW")
    print("=" * 80)

    print(f"\nSource database: {SOURCE_DB}")
    print(f"Target database: {TARGET_DB}")
    print(f"ID threshold: < {MAX_ID}")

    print(f"\nStatistics:")
    print(f"  Records in source (ID < {MAX_ID}): {len(source_records)}")
    print(f"  Records already in target (ID < {MAX_ID}): {len(existing_ids)}")
    print(f"  Records to be inserted: {len(missing_ids)}")

    if missing_ids:
        print(f"\nID Range to be inserted:")
        sorted_missing = sorted(missing_ids)
        print(f"  Min ID: {min(sorted_missing)}")
        print(f"  Max ID: {max(sorted_missing)}")

        print(f"\nFirst 10 records to be inserted:")
        print("-" * 80)

        # Get records to insert
        records_to_insert = [r for r in source_records if r['id'] in missing_ids]
        records_to_insert.sort(key=lambda x: x['id'])

        for i, record in enumerate(records_to_insert[:10], 1):
            print(f"\n{i}. ID: {record['id']}")
            print(f"   Club: {record['club_name']}")
            print(f"   Course: {record['course_name']}")
            print(f"   Location: {record['city']}, {record['state']}, {record['country']}")
            print(f"   Coordinates: ({record['latitude']}, {record['longitude']})")
            print(f"   Created: {record['created_at']}")

        if len(records_to_insert) > 10:
            print(f"\n... and {len(records_to_insert) - 10} more records")

    else:
        print("\n[OK] No records need to be inserted. All source records already exist in target.")

    return missing_ids


def insert_records(target_path: str, source_records, missing_ids):
    """Insert missing records into target database."""
    records_to_insert = [r for r in source_records if r['id'] in missing_ids]

    if not records_to_insert:
        print("\nNo records to insert.")
        return 0

    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()

    inserted_count = 0

    try:
        for record in records_to_insert:
            cursor.execute("""
                INSERT INTO courses (id, club_name, course_name, address, city, state,
                                   country, latitude, longitude, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['id'],
                record['club_name'],
                record['course_name'],
                record['address'],
                record['city'],
                record['state'],
                record['country'],
                record['latitude'],
                record['longitude'],
                record['created_at']
            ))
            inserted_count += 1

        conn.commit()
        print(f"\n[OK] Successfully inserted {inserted_count} records into {target_path}")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[ERROR] Database error occurred: {e}")
        print("No records were inserted (transaction rolled back).")
        inserted_count = 0

    finally:
        conn.close()

    return inserted_count


def main():
    # Check if files exist
    if not Path(SOURCE_DB).exists():
        print(f"[ERROR] Source database not found: {SOURCE_DB}")
        sys.exit(1)

    if not Path(TARGET_DB).exists():
        print(f"[ERROR] Target database not found: {TARGET_DB}")
        sys.exit(1)

    # Get source records
    print(f"Reading records from {SOURCE_DB}...")
    source_records = get_source_records(SOURCE_DB, MAX_ID)

    # Get existing IDs in target
    print(f"Checking existing records in {TARGET_DB}...")
    existing_ids = get_existing_ids(TARGET_DB, MAX_ID)

    # Show preview
    missing_ids = preview_migration(source_records, existing_ids)

    if not missing_ids:
        return

    # Ask for confirmation
    print("\n" + "=" * 80)
    response = input("\nDo you want to proceed with the migration? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        print("\nProceeding with migration...")
        inserted = insert_records(TARGET_DB, source_records, missing_ids)

        if inserted > 0:
            # Verify insertion
            print(f"\nVerifying insertion...")
            new_existing_ids = get_existing_ids(TARGET_DB, MAX_ID)
            print(f"Records in target (ID < {MAX_ID}) after migration: {len(new_existing_ids)}")
    else:
        print("\n[CANCELLED] Migration cancelled by user.")


if __name__ == "__main__":
    main()
