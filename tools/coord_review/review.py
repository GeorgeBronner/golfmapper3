"""
Shared-coordinate review tool (tasks/todo.md "Courses sharing one coordinate").

Shows each unresolved course on an OpenStreetMap and a satellite map with its current point and the
proposed point. Decisions are written to data/decisions.json after every click; the database is only read.

Setup: copy env.sample to .env in this folder and set COORD_REVIEW_DB to a local copy of the DB.
Run from the project root:
    uv run --project backend python tools/coord_review/review.py
then open http://127.0.0.1:8890
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPORT = DATA / "report_data.json"
DECISIONS = DATA / "decisions.json"
PAGE = HERE / "review.html"

load_dotenv(HERE / ".env")
if not os.environ.get("COORD_REVIEW_DB"):
    sys.exit("Set COORD_REVIEW_DB in tools/coord_review/.env (see env.sample)")
# Local copy of the prod DB, matching prod; read-only here.
DB = Path(os.environ["COORD_REVIEW_DB"])


def build_queue():
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    current = {r[0]: (r[1], r[2]) for r in con.execute("SELECT id, latitude, longitude FROM courses")}
    con.close()

    # Courses already moved off a shared point: show them as context on the maps.
    moved_from = {}
    for m in data["moves"]:
        moved_from.setdefault((round(m["old_lat"], 6), round(m["old_lon"], 6)), []).append(
            {"name": m["course_name"] or m["club_name"], "lat": m["new_lat"], "lon": m["new_lon"]}
        )

    groups = {}
    for r in data["remaining"]:
        groups.setdefault(r["group"], []).append(r)

    queue, missing = [], 0
    for r in data["remaining"]:
        if r["id"] not in current:
            missing += 1
            continue
        lat, lon = current[r["id"]]
        queue.append(
            {
                "id": r["id"],
                "club": r["club_name"],
                "course": r["course_name"],
                "country": r["country"],
                "category": r["category"],
                "played": r["played"],
                "status": r["status"],
                "confidence": r["confidence"],
                "note": r["note"],
                "lat": lat,
                "lon": lon,
                "guess": None
                if r["guess_lat"] is None
                else {
                    "source": r["guess_source"],
                    "name": r["guess_name"],
                    "lat": r["guess_lat"],
                    "lon": r["guess_lon"],
                    "dist": r["guess_dist"],
                },
                "group": [
                    {"id": g["id"], "name": g["course_name"] or g["club_name"], "club": g["club_name"]}
                    for g in groups[r["group"]]
                    if g["id"] != r["id"]
                ],
                "moved": moved_from.get((round(r["lat"], 6), round(r["lon"], 6)), []),
            }
        )
    # Played courses first, then by confidence; ties keep a club's rows together.
    queue.sort(key=lambda q: (not q["played"], -q["confidence"], q["club"], q["id"]))
    return queue, missing


def load_decisions():
    if DECISIONS.exists():
        return json.loads(DECISIONS.read_text(encoding="utf-8"))
    return {}


def save_decisions(decisions):
    tmp = DECISIONS.with_suffix(".tmp")
    tmp.write_text(json.dumps(decisions, indent=1), encoding="utf-8")
    os.replace(tmp, DECISIONS)


QUEUE, MISSING = build_queue()
QUEUE_IDS = {q["id"] for q in QUEUE}
decisions = load_decisions()

app = FastAPI()


class Decision(BaseModel):
    decision: Literal["save", "no_edit", "undecided"]
    lat: Optional[float] = None
    lon: Optional[float] = None


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE.read_text(encoding="utf-8")


@app.get("/api/queue")
def get_queue():
    return {"queue": QUEUE, "decisions": decisions}


@app.put("/api/decision/{course_id}")
def put_decision(course_id: int, body: Decision):
    if course_id not in QUEUE_IDS:
        raise HTTPException(404, "Course is not in the review list")
    if body.decision == "save" and (
        body.lat is None or body.lon is None or not -90 <= body.lat <= 90 or not -180 <= body.lon <= 180
    ):
        raise HTTPException(422, "Save Change needs a valid point")
    entry = {"decision": body.decision, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if body.decision == "save":
        entry.update(lat=round(body.lat, 7), lon=round(body.lon, 7))
    decisions[str(course_id)] = entry
    save_decisions(decisions)
    return entry


@app.delete("/api/decision/{course_id}")
def delete_decision(course_id: int):
    decisions.pop(str(course_id), None)
    save_decisions(decisions)
    return {"ok": True}


if __name__ == "__main__":
    print(f"{len(QUEUE)} courses to review ({MISSING} no longer in the DB), {len(decisions)} already decided")
    print("Open http://127.0.0.1:8890  (CTRL+C to stop; decisions are saved as you go)")
    # Local tool with no auth: bind to loopback only.
    uvicorn.run(app, host="127.0.0.1", port=8890, log_level="warning")
