import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Courses, RankingEntries, RankingLists

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from seed_rankings import _rank, seed  # noqa: E402

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
