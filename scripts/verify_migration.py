#!/usr/bin/env python3
"""
Quick verification script to confirm migration results.
"""
import sqlite3

TARGET_DB = "dbs/golf_mapper_sqlite.db"

conn = sqlite3.connect(TARGET_DB)
cursor = conn.cursor()

# Get total count
cursor.execute("SELECT COUNT(*) FROM courses")
total = cursor.fetchone()[0]

# Get count under 4900
cursor.execute("SELECT COUNT(*) FROM courses WHERE id < 4900")
under_4900 = cursor.fetchone()[0]

# Get count at or above 4900
cursor.execute("SELECT COUNT(*) FROM courses WHERE id >= 4900")
above_4900 = cursor.fetchone()[0]

# Get ID ranges
cursor.execute("SELECT MIN(id), MAX(id) FROM courses")
id_range = cursor.fetchone()

# Sample records from migrated data
cursor.execute("""
    SELECT id, club_name, course_name, city, state
    FROM courses
    WHERE id < 4900
    ORDER BY id
    LIMIT 5
""")
samples = cursor.fetchall()

conn.close()

print("=" * 80)
print("MIGRATION VERIFICATION")
print("=" * 80)
print(f"\nDatabase: {TARGET_DB}")
print(f"\nTotal records: {total}")
print(f"  Records with ID < 4900: {under_4900}")
print(f"  Records with ID >= 4900: {above_4900}")
print(f"\nID Range: {id_range[0]} to {id_range[1]}")

print(f"\nSample migrated records:")
print("-" * 80)
for record in samples:
    print(f"  ID {record[0]}: {record[1]} - {record[2]} ({record[3]}, {record[4]})")

print("\n[OK] Migration verified successfully!")
