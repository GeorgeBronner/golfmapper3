"""Seed ranking lists, editions and entries from plans/top100-lists.

Reads the us-public files in the folder itself, each list subfolder named in
LIST_DIRS (us-all, world), and best-in-state as one list per state.

Safe to re-run: lists match on slug and editions on (list, label) and are
updated in place; an edition's entries are replaced wholesale, so a corrected
CSV (moved or swapped courses, dropped ranks) never leaves stale rows behind.

    uv run python scripts/seed_rankings.py PATH_TO_DB --data-dir DIR [--dry-run]

The data CSVs are not in the repo (plans/ is gitignored), so --data-dir is
required unless they sit in plans/top100-lists. --dry-run works on a temporary
copy of the database and leaves PATH_TO_DB untouched.
"""

import argparse
import csv
import shutil
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
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
    "golf-digest-us-all": {
        "name": "America's 100 Greatest Golf Courses",
        "publisher": "Golf Digest",
        "scope": "us-all",
        "size": 100,
    },
    "golf-digest-world": {
        "name": "World's 100 Greatest Golf Courses",
        "publisher": "Golf Digest",
        "scope": "world",
        "size": 100,
    },
}

# Folders under the data dir that hold their own editions.csv and course-matches.csv.
LIST_DIRS = ("us-all", "world")

# best-in-state is one ranking list per state (a unique rank per edition would
# collide across states otherwise): slug golf-digest-best-in-state-<code>.
STATE_DIR = "best-in-state"
STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(value: str) -> float | None:
    return float(value) if value.strip() else None


def _rank(printed: str, position: int) -> tuple[int, str | None]:
    """(rank, rank_label) for a printed rank. Ties print as "T53" and the ranks they
    skip are not printed, so a tied entry takes its 1-based position in the file."""
    printed = printed.strip()
    if printed.isdigit():
        return int(printed), None
    return position, printed


def _state_ranks(rows: list[dict]) -> list[tuple[dict, int, str | None]]:
    """(row, rank, rank_label) for one state's rows. The state pages print a tie as
    the same number twice (FL 40, 40, then 42), so the extra entries take the next
    rank numbers and every entry in the group keeps the label "T40"."""
    by_rank: dict[int, list[dict]] = {}
    for row in rows:
        by_rank.setdefault(int(row["rank"]), []).append(row)
    out = []
    for printed, group in sorted(by_rank.items()):
        for i, row in enumerate(group):
            out.append((row, printed + i, f"T{printed}" if len(group) > 1 else None))
    return out


def _upsert_list(db, slug: str, meta: dict, counts: dict) -> RankingLists:
    lst = db.query(RankingLists).filter_by(slug=slug).one_or_none()
    if lst is None:
        lst = RankingLists(slug=slug, **meta)
        db.add(lst)
        db.flush()
        counts["lists"] += 1
    return lst


def _upsert_edition(db, lst: RankingLists, label: str, ed: dict, counts: dict) -> RankingEditions:
    edition = db.query(RankingEditions).filter_by(list_id=lst.id, label=label).one_or_none()
    if edition is None:
        edition = RankingEditions(list_id=lst.id, label=label)
        db.add(edition)
        counts["editions"] += 1
    edition.start_year = int(ed["start_year"])
    edition.published_on = ed["published_on"] or None
    edition.source_url = ed["source_url"] or None
    edition.notes = ed["notes"] or None
    db.flush()
    return edition


def _replace_entries(db, edition: RankingEditions, entries: list[dict], counts: dict) -> None:
    """Replace an edition's entries wholesale. Each dict holds the RankingEntries fields."""
    db.query(RankingEntries).filter_by(edition_id=edition.id).delete()
    seen_ranks: set[int] = set()
    for entry in entries:
        if entry["rank"] in seen_ranks:
            raise SystemExit(
                f"{edition.label}: rank {entry['rank']} used twice ({entry['published_name']}); check the ties"
            )
        seen_ranks.add(entry["rank"])
        db.add(RankingEntries(edition_id=edition.id, **entry))
        counts["entries"] += 1
    db.flush()


def _seed_dir(db, data_dir: Path, counts: dict) -> None:
    for name in ("course-matches.csv", "editions.csv"):
        if not (data_dir / name).is_file():
            raise SystemExit(f"{data_dir / name} not found; pass --data-dir")
    # Tied entries share a printed rank, so the course name is part of the key.
    matches = {
        (m["edition"], m["rank"].strip(), m["published_course"].strip()): int(m["course_id"])
        for m in _read(data_dir / "course-matches.csv")
    }

    for ed in _read(data_dir / "editions.csv"):
        meta = LISTS.get(ed["list"])
        if meta is None:
            raise SystemExit(f"editions.csv: unknown list slug {ed['list']!r}; add it to LISTS")
        lst = _upsert_list(db, ed["list"], meta, counts)
        edition = _upsert_edition(db, lst, ed["edition"], ed, counts)

        entries = []
        for position, row in enumerate(_read(data_dir / ed["file"]), start=1):
            course = row["course"].strip()
            if not course:
                counts["skipped"] += 1  # 2021-22 rank 54 was pulled by Golf Digest (private)
                continue
            printed = row["rank"].strip()
            course_id = matches.get((ed["edition"], printed, course))
            if course_id is None:
                raise SystemExit(f"course-matches.csv has no match for {ed['edition']} rank {printed} ({course})")
            rank, rank_label = _rank(printed, position)
            entries.append(
                {
                    "rank": rank,
                    "rank_label": rank_label,
                    "course_id": course_id,
                    "prior_rank": row["prior_rank"].strip() or None,
                    "published_name": course,
                    "points": _float(row.get("points") or ""),
                    "access": (row.get("access") or "").strip() or None,
                }
            )
        _replace_entries(db, edition, entries, counts)


def _seed_states(db, data_dir: Path, counts: dict) -> None:
    """Golf Digest Best in State: one file per edition holding every state, one list per state."""
    matches = {
        (m["edition"], m["group"], m["rank"].strip(), m["published_course"].strip()): int(m["course_id"])
        for m in _read(data_dir / "course-matches.csv")
    }
    for editions_csv in sorted(data_dir.glob("editions-*.csv")):
        for ed in _read(editions_csv):
            label = ed["edition"].split(" ")[0]  # "2025-26 (25th)" -> "2025-26"
            by_state: dict[str, list[dict]] = {}
            for row in _read(data_dir / ed["file"]):
                by_state.setdefault(row["state"], []).append(row)
            for code in sorted(by_state):
                if code not in STATE_NAMES:
                    raise SystemExit(f"{ed['file']}: unknown state {code!r}")
                meta = {
                    "name": f"Best Courses in {STATE_NAMES[code]}",
                    "publisher": "Golf Digest",
                    "scope": f"us-state-{code}",
                    "size": None,
                }
                lst = _upsert_list(db, f"golf-digest-best-in-state-{code.lower()}", meta, counts)
                edition = _upsert_edition(db, lst, label, ed, counts)
                entries = []
                for row, rank, rank_label in _state_ranks(by_state[code]):
                    course = row["course"].strip()
                    course_id = matches.get((label, code, row["rank"].strip(), course))
                    if course_id is None:
                        raise SystemExit(
                            f"course-matches.csv has no match for {label} {code} rank {row['rank']} ({course})"
                        )
                    entries.append(
                        {
                            "rank": rank,
                            "rank_label": rank_label,
                            "course_id": course_id,
                            "prior_rank": row["prior_rank"].strip() or None,
                            "published_name": course,
                            "points": None,
                            "access": row["access"].strip() or None,
                        }
                    )
                _replace_entries(db, edition, entries, counts)


def seed(db, data_dir: Path) -> dict:
    counts = {"lists": 0, "editions": 0, "entries": 0, "skipped": 0}
    _seed_dir(db, data_dir, counts)
    for sub in LIST_DIRS:
        if (data_dir / sub).is_dir():
            _seed_dir(db, data_dir / sub, counts)
    if (data_dir / STATE_DIR).is_dir():
        _seed_states(db, data_dir / STATE_DIR, counts)

    missing = (
        db.query(RankingEntries.course_id)
        .outerjoin(Courses, Courses.id == RankingEntries.course_id)
        .filter(Courses.id.is_(None))
        .count()
    )
    if missing:
        raise SystemExit(f"{missing} entries point at courses that do not exist")
    return counts


def _add_missing_columns(engine) -> None:
    """create_all never alters existing tables; the app does this at startup, but the
    seed may run on a database file that has not been started with the new code."""
    existing = {c["name"] for c in inspect(engine).get_columns("ranking_entries")}
    for name in ("rank_label", "access"):
        if name not in existing:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE ranking_entries ADD COLUMN {name} VARCHAR"))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("db_path")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--dry-run", action="store_true", help="roll back instead of committing")
    args = parser.parse_args()

    if not Path(args.db_path).is_file():
        raise SystemExit(f"No such database: {args.db_path}")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = args.db_path
        if args.dry_run:
            db_path = str(Path(tmp) / "dry-run.db")
            shutil.copyfile(args.db_path, db_path)
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        _add_missing_columns(engine)
        with sessionmaker(bind=engine)() as db:
            counts = seed(db, args.data_dir)
            if args.dry_run:
                db.rollback()
            else:
                db.commit()
        engine.dispose()
    print(
        ("DRY RUN, nothing written: " if args.dry_run else "Committed: ")
        + ", ".join(f"{v} {k}" for k, v in counts.items())
    )


if __name__ == "__main__":
    main()
