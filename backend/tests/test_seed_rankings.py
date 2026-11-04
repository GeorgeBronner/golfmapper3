import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Courses, RankingEntries, RankingLists

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from seed_rankings import _add_missing_columns, _rank, seed  # noqa: E402

EDITIONS_HEADER = "list,edition,start_year,published_on,source_url,file,notes\n"
MATCHES_HEADER = "edition,group,rank,published_course,city,state,country,course_id\n"


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with sessionmaker(bind=engine)() as session:
        session.add_all([Courses(id=i, club_name=f"Club {i}") for i in range(1, 5)])
        session.commit()
        yield session


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _data_dir(tmp_path: Path) -> Path:
    # Top-level us-public list with a blank (pulled) rank, plus a world subfolder with a tie.
    _write(
        tmp_path / "editions.csv",
        EDITIONS_HEADER + "golf-digest-us-public,2021-22,2021,,,pub.csv,\n",
    )
    _write(tmp_path / "pub.csv", "rank,prior_rank,course,city,state,yards,par,points\n1,1,A,x,y,,,70.5\n2,,,,,,,\n")
    _write(
        tmp_path / "course-matches.csv",
        "edition,rank,published_course,city,state,course_id\n2021-22,1,A,x,y,1\n",
    )
    world = tmp_path / "world"
    world.mkdir()
    _write(world / "editions.csv", EDITIONS_HEADER + "golf-digest-world,2026-27,2026,,,w.csv,\n")
    _write(
        world / "w.csv",
        "rank,prior_rank,course,city,region,country,architect,yards,par\n"
        "1,1,B,,,,,,\nT2,5,C,,,,,,\nT2,NEW,D,,,,,,\n4,3,E,,,,,,\n",
    )
    _write(
        world / "course-matches.csv",
        MATCHES_HEADER + "2026-27,,1,B,,,,2\n2026-27,,T2,C,,,,3\n2026-27,,T2,D,,,,4\n2026-27,,4,E,,,,1\n",
    )
    return tmp_path


def test_rank_numbers_ties_by_position():
    assert _rank("7", 7) == (7, None)
    assert _rank("T2", 3) == (3, "T2")


def test_seed_reads_subfolders_ties_and_blank_rows(db, tmp_path):
    counts = seed(db, _data_dir(tmp_path))
    assert counts == {"lists": 2, "editions": 2, "entries": 5, "skipped": 1}
    world = db.query(RankingLists).filter_by(slug="golf-digest-world").one()
    entries = db.query(RankingEntries).filter_by(edition_id=world.editions[0].id).order_by(RankingEntries.rank).all()
    assert [(e.rank, e.rank_label, e.course_id, e.prior_rank) for e in entries] == [
        (1, None, 2, "1"),
        (2, "T2", 3, "5"),
        (3, "T2", 4, "NEW"),
        (4, None, 1, "3"),
    ]
    assert db.query(RankingEntries).filter_by(rank=1, published_name="A").one().points == 70.5


def test_seed_is_idempotent(db, tmp_path):
    data_dir = _data_dir(tmp_path)
    seed(db, data_dir)
    counts = seed(db, data_dir)
    assert counts["lists"] == 0 and counts["editions"] == 0
    assert db.query(RankingEntries).count() == 5


def test_seed_fails_on_unmatched_row(db, tmp_path):
    data_dir = _data_dir(tmp_path)
    _write(data_dir / "world" / "course-matches.csv", MATCHES_HEADER + "2026-27,,1,B,,,,2\n")
    with pytest.raises(SystemExit, match="no match"):
        seed(db, data_dir)


def test_seed_fails_when_a_tie_collides_with_a_printed_rank(db, tmp_path):
    data_dir = _data_dir(tmp_path)
    # Position 2 is tied, but the next row prints 2 as well.
    rows = ["1,1,B", "T2,5,C", "2,3,E"]
    _write(
        data_dir / "world" / "w.csv",
        "rank,prior_rank,course,city,region,country,architect,yards,par\n" + "".join(f"{row},,,,,,\n" for row in rows),
    )
    matches = ["2026-27,,1,B,,,,2", "2026-27,,T2,C,,,,3", "2026-27,,2,E,,,,1"]
    _write(data_dir / "world" / "course-matches.csv", MATCHES_HEADER + "\n".join(matches) + "\n")
    with pytest.raises(SystemExit, match="used twice"):
        seed(db, data_dir)


def test_add_missing_columns_upgrades_a_legacy_table():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE ranking_entries (id INTEGER PRIMARY KEY, rank INTEGER)"))
        conn.execute(text("INSERT INTO ranking_entries (id, rank) VALUES (1, 5)"))
    _add_missing_columns(engine)
    _add_missing_columns(engine)  # idempotent
    assert {"rank_label", "access"} <= {c["name"] for c in inspect(engine).get_columns("ranking_entries")}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT rank, rank_label, access FROM ranking_entries")).one() == (5, None, None)


# ── best-in-state ─────────────────────────────────────────────────────────────

STATE_HEADER = "state,rank,prior_rank,course,city,city_state,access,panelists\n"


def _state_dir(tmp_path: Path) -> Path:
    state = tmp_path / "best-in-state"
    state.mkdir()
    _write(
        state / "editions-2025-26.csv",
        EDITIONS_HEADER + "golf-digest-best-in-state,2025-26 (25th),2025,2025-05-29,http://x,states.csv,\n",
    )
    # TX prints rank 2 twice (no 3) and is not in rank order; AL has one row with no access label.
    _write(
        state / "states.csv",
        STATE_HEADER
        + "TX,2,NR,Second,x,x,private,\n"
        + "TX,1,1,First,x,x,public,\n"
        + "TX,2,3,Also Second,x,x,private,\n"
        + "TX,4,4,Fourth,x,x,private,\n"
        + "AL,1,NEW,Alone,x,x,,\n",
    )
    names = {
        ("TX", "2", "Second"): 1,
        ("TX", "1", "First"): 2,
        ("TX", "2", "Also Second"): 3,
        ("TX", "4", "Fourth"): 4,
        ("AL", "1", "Alone"): 1,
    }
    _write(
        state / "course-matches.csv",
        "edition,group,rank,published_course,city,state,country,course_id\n"
        + "".join(f"2025-26,{g},{r},{c},,,,{cid}\n" for (g, r, c), cid in names.items()),
    )
    return state


def test_seed_states_creates_a_list_per_state_with_tie_labels_and_access(db, tmp_path):
    data_dir = _data_dir(tmp_path)
    _state_dir(tmp_path)
    counts = seed(db, data_dir)
    assert counts["lists"] == 4  # us-public, world, TX, AL

    tx = db.query(RankingLists).filter_by(slug="golf-digest-best-in-state-tx").one()
    assert (tx.name, tx.scope, tx.size) == ("Best Courses in Texas", "us-state-TX", None)
    [edition] = tx.editions
    assert (edition.label, edition.start_year) == ("2025-26", 2025)  # "(25th)" dropped
    entries = db.query(RankingEntries).filter_by(edition_id=edition.id).order_by(RankingEntries.rank).all()
    # The second printed "2" takes rank 3 and both keep the label; rank 4 is untouched.
    assert [(e.rank, e.rank_label, e.published_name, e.access) for e in entries] == [
        (1, None, "First", "public"),
        (2, "T2", "Second", "private"),
        (3, "T2", "Also Second", "private"),
        (4, None, "Fourth", "private"),
    ]
    al = db.query(RankingLists).filter_by(slug="golf-digest-best-in-state-al").one()
    [only] = db.query(RankingEntries).filter_by(edition_id=al.editions[0].id).all()
    assert only.access is None


def test_seed_states_is_idempotent(db, tmp_path):
    data_dir = _data_dir(tmp_path)
    _state_dir(tmp_path)
    seed(db, data_dir)
    counts = seed(db, data_dir)
    assert counts["lists"] == 0 and counts["editions"] == 0
    assert db.query(RankingEntries).count() == 5 + 5  # 5 from the main fixture, 5 state rows


def test_seed_states_fails_on_unmatched_row(db, tmp_path):
    data_dir = _data_dir(tmp_path)
    state = _state_dir(tmp_path)
    _write(state / "course-matches.csv", "edition,group,rank,published_course,city,state,country,course_id\n")
    with pytest.raises(SystemExit, match="no match"):
        seed(db, data_dir)
