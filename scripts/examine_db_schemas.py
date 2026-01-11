#!/usr/bin/env python3
"""
Script to examine and compare the schemas of courses tables in both databases.
"""
import sqlite3
from pathlib import Path

def get_table_schema(db_path: str, table_name: str = "courses"):
    """Get the schema of a table from a SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get table info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    # Get table creation SQL
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    create_sql = cursor.fetchone()

    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]

    # Get ID range
    cursor.execute(f"SELECT MIN(id), MAX(id) FROM {table_name}")
    id_range = cursor.fetchone()

    # Get count of IDs < 4900
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE id < 4900")
    count_under_4900 = cursor.fetchone()[0]

    conn.close()

    return {
        'columns': columns,
        'create_sql': create_sql[0] if create_sql else None,
        'total_count': count,
        'id_range': id_range,
        'count_under_4900': count_under_4900
    }

def main():
    # Database paths
    db1 = "dbs/golf_courses-new.db"
    db2 = "dbs/golf_mapper_sqlite.db"

    print("=" * 80)
    print("DATABASE SCHEMA COMPARISON")
    print("=" * 80)

    # Check if files exist
    if not Path(db1).exists():
        print(f"ERROR: {db1} does not exist!")
        return
    if not Path(db2).exists():
        print(f"ERROR: {db2} does not exist!")
        return

    # Get schemas
    print(f"\nExamining: {db1}")
    print("-" * 80)
    schema1 = get_table_schema(db1)

    print(f"\nTable Creation SQL:")
    print(schema1['create_sql'])

    print(f"\nColumns:")
    for col in schema1['columns']:
        print(f"  {col[0]:3} | {col[1]:20} | {col[2]:15} | NotNull: {col[3]} | Default: {col[4]} | PK: {col[5]}")

    print(f"\nStatistics:")
    print(f"  Total rows: {schema1['total_count']}")
    print(f"  ID range: {schema1['id_range'][0]} to {schema1['id_range'][1]}")
    print(f"  Rows with ID < 4900: {schema1['count_under_4900']}")

    print(f"\n{'=' * 80}")
    print(f"\nExamining: {db2}")
    print("-" * 80)
    schema2 = get_table_schema(db2)

    print(f"\nTable Creation SQL:")
    print(schema2['create_sql'])

    print(f"\nColumns:")
    for col in schema2['columns']:
        print(f"  {col[0]:3} | {col[1]:20} | {col[2]:15} | NotNull: {col[3]} | Default: {col[4]} | PK: {col[5]}")

    print(f"\nStatistics:")
    print(f"  Total rows: {schema2['total_count']}")
    print(f"  ID range: {schema2['id_range'][0]} to {schema2['id_range'][1]}")
    print(f"  Rows with ID < 4900: {schema2['count_under_4900']}")

    # Compare schemas
    print(f"\n{'=' * 80}")
    print("SCHEMA COMPARISON")
    print("=" * 80)

    cols1 = {col[1]: col for col in schema1['columns']}
    cols2 = {col[1]: col for col in schema2['columns']}

    all_cols = set(cols1.keys()) | set(cols2.keys())

    print(f"\nColumn Comparison:")
    for col_name in sorted(all_cols):
        if col_name in cols1 and col_name in cols2:
            c1 = cols1[col_name]
            c2 = cols2[col_name]
            if c1[2:] == c2[2:]:  # Compare type, notnull, default, pk
                print(f"  [OK] {col_name:20} - MATCH")
            else:
                print(f"  [WARN] {col_name:20} - DIFFERENT")
                print(f"      {db1}: {c1[2:]}")
                print(f"      {db2}: {c2[2:]}")
        elif col_name in cols1:
            print(f"  [+] {col_name:20} - Only in {db1}")
        else:
            print(f"  [-] {col_name:20} - Only in {db2}")

    schemas_match = cols1.keys() == cols2.keys() and all(
        cols1[k][2:] == cols2[k][2:] for k in cols1.keys()
    )

    print(f"\n{'[OK] Schemas MATCH' if schemas_match else '[ERROR] Schemas DIFFER'}")

if __name__ == "__main__":
    main()
