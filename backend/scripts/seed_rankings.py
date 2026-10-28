"""Seed ranking lists, editions and entries from plans/top100-lists/*.csv.

Idempotent: lists match on slug, editions on (list, label) and entries on
(edition, rank), so re-running updates rows in place and adds only what is new.

    uv run python scripts/seed_rankings.py PATH_TO_DB [--data-dir DIR] [--dry-run]

Run it on a copy of the database first.
"""

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models import Base, Courses, RankingEditions, RankingEntries, RankingLists  # noqa: E402

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "plans" / "top100-lists"

# One row per list slug in editions.csv; the CSVs carry no list metadata.
LISTS = {
    "golf-digest-us-public": {
        "name": "America's 100 Greatest Public Courses",
        "publisher": "Golf Digest",
        "scope": "us-public",
        "size": 100,
    },
}


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(value: str) -> float | None:
    return float(value) if value.strip() else None


def seed(db, data_dir: Path) -> dict:
    matches = {(m["edition"], int(m["rank"])): int(m["course_id"]) for m in _read(data_dir / "course-matches.csv")}
    counts = {"lists": 0, "editions": 0, "entries": 0, "skipped": 0}

    for ed in _read(data_dir / "editions.csv"):
        meta = LISTS[ed["list"]]
        lst = db.query(RankingLists).filter_by(slug=ed["list"]).one_or_none()
        if lst is None:
            lst = RankingLists(slug=ed["list"], **meta)
            db.add(lst)
            db.flush()
            counts["lists"] += 1

        edition = db.query(RankingEditions).filter_by(list_id=lst.id, label=ed["edition"]).one_or_none()
        if edition is None:
            edition = RankingEditions(list_id=lst.id, label=ed["edition"])
            db.add(edition)
            counts["editions"] += 1
        edition.start_year = int(ed["start_year"])
        edition.published_on = ed["published_on"] or None
        edition.source_url = ed["source_url"] or None
        edition.notes = ed["notes"] or None
        db.flush()

        existing = {e.rank: e for e in db.query(RankingEntries).filter_by(edition_id=edition.id)}
        for row in _read(data_dir / ed["file"]):
            rank = int(row["rank"])
            if not row["course"].strip():
                counts["skipped"] += 1  # 2021-22 rank 54 is unknown
                continue
            course_id = matches[(ed["edition"], rank)]
            entry = existing.get(rank)
            if entry is None:
                entry = RankingEntries(edition_id=edition.id, rank=rank)
                db.add(entry)
                counts["entries"] += 1
            entry.course_id = course_id
            entry.prior_rank = row["prior_rank"].strip() or None
            entry.published_name = row["course"].strip()
            entry.points = _float(row["points"])
        db.flush()

    missing = (
        db.query(RankingEntries.course_id)
        .outerjoin(Courses, Courses.id == RankingEntries.course_id)
        .filter(Courses.id.is_(None))
        .count()
    )
    if missing:
        raise SystemExit(f"{missing} entries point at courses that do not exist")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("db_path")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--dry-run", action="store_true", help="roll back instead of committing")
    args = parser.parse_args()

    if not Path(args.db_path).is_file():
        raise SystemExit(f"No such database: {args.db_path}")
    engine = create_engine(f"sqlite:///{args.db_path}")
    Base.metadata.create_all(bind=engine)
    with sessionmaker(bind=engine)() as db:
        counts = seed(db, args.data_dir)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    print(
        ("DRY RUN, rolled back: " if args.dry_run else "Committed: ") + ", ".join(f"{v} {k}" for k, v in counts.items())
    )


if __name__ == "__main__":
    main()
