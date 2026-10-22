"""
Apply the "save" decisions from data/decisions.json to a copy of the DB.

    uv run --project backend python tools/coord_review/apply.py <db copy>
    uv run --project backend python tools/coord_review/apply.py --mark <live db copy>   # after the swap

Guarded: a row is updated only if it is still at the point it had when the review list was built.
State/country are re-derived with Nominatim reverse and changed only on a real difference (same rule as the
first pass). --mark gives saves that are live an "applied" date so later runs skip them.
"""

import json
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.geo import nominatim_to_geo  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).resolve().parent / "data"
DECISIONS = DATA / "decisions.json"
STATE_COUNTRIES = {"GBR", "USA", "CAN", "AUS", "IRL"}
VAGUE_STATES = {"ENG", "SCT", "WLS", "NIR", ""}


def reverse(client, lat, lon):
    r = client.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1, "zoom": 10},
    )
    r.raise_for_status()
    time.sleep(1.1)
    return nominatim_to_geo(r.json().get("address", {}))


def main(db_path):
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
    original = {
        r["id"]: (r["lat"], r["lon"])
        for r in json.loads((DATA / "report_data.json").read_text(encoding="utf-8"))["remaining"]
    }
    todo = {int(k): v for k, v in decisions.items() if v["decision"] == "save" and not v.get("applied")}

    con = sqlite3.connect(db_path)
    client = httpx.Client(headers={"User-Agent": "GolfMapper3-maintenance/1.0"}, timeout=30)
    moved, skipped, geo = 0, [], []
    for cid, d in todo.items():
        row = con.execute(
            "SELECT club_name, course_name, latitude, longitude, state, country FROM courses WHERE id=?", (cid,)
        ).fetchone()
        old_lat, old_lon = original[cid]
        if not row or abs(row[2] - old_lat) > 1e-7 or abs(row[3] - old_lon) > 1e-7:
            skipped.append(cid)
            continue
        state, country = row[4] or "", row[5] or ""
        g = reverse(client, d["lat"], d["lon"])
        new_state, new_country = state, country
        if g["country"] and g["country"] != country:
            new_state, new_country = g["state"], g["country"]
        elif country in STATE_COUNTRIES and g["state"] not in VAGUE_STATES and g["state"] != state:
            new_state = g["state"]
        if (new_state, new_country) != (state, country):
            geo.append(f"{cid} {row[0]} | {row[1]}: {country}/{state} -> {new_country}/{new_state}")
        cur = con.execute(
            "UPDATE courses SET latitude=?, longitude=?, state=?, country=? WHERE id=? AND latitude=? AND longitude=?",
            (d["lat"], d["lon"], new_state, new_country, cid, row[2], row[3]),
        )
        moved += cur.rowcount
    con.commit()
    print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
    print(
        "courses:",
        con.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        "user_courses:",
        con.execute("SELECT COUNT(*) FROM user_courses").fetchone()[0],
    )
    con.close()

    print(f"moved {moved} of {len(todo)}; skipped (row changed since review): {skipped}")
    print("geo changes:", *geo, sep="\n  ") if geo else print("geo changes: none")
    return [cid for cid in todo if cid not in skipped]


def mark(db_path):
    """Mark saves as applied where the given DB (the live one, after the swap) has the course at the saved point."""
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    marked = 0
    for k, d in decisions.items():
        if d["decision"] != "save" or d.get("applied"):
            continue
        row = con.execute("SELECT latitude, longitude FROM courses WHERE id=?", (int(k),)).fetchone()
        if row and abs(row[0] - d["lat"]) <= 1e-7 and abs(row[1] - d["lon"]) <= 1e-7:
            d["applied"] = date.today().isoformat()
            marked += 1
    con.close()
    DECISIONS.write_text(json.dumps(decisions, indent=1), encoding="utf-8")
    print(f"marked {marked} decisions as applied")


if __name__ == "__main__":
    if sys.argv[1] == "--mark":
        mark(sys.argv[2])
    else:
        main(sys.argv[1])
