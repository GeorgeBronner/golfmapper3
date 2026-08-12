import logging
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

if settings.USE_SQLITE_DB:
    if settings.SQLITE_DB_URL:
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.SQLITE_DB_URL}"
    else:
        db_path = Path(__file__).parent / "golf_mapper.db"
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/golfmapper3?options=-csearch_path%3Dmain"
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns(table_name: str, columns: dict[str, str]) -> None:
    """Add columns missing from an already-existing table.

    There's no migration tool in this project — `Base.metadata.create_all`
    creates missing tables but never alters existing ones, so newly added
    model columns need this to reach databases that predate them.
    """
    existing = {col["name"] for col in inspect(engine).get_columns(table_name)}
    for name, ddl_type in columns.items():
        if name in existing:
            continue
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl_type}"))
        except DBAPIError:
            # Another worker/replica racing the same startup migration
            # already added it — the column existing is the only outcome
            # we're trying to guarantee here, so that's fine.
            pass


def ensure_index(name: str, create_ddl: str) -> None:
    """Run a `CREATE UNIQUE INDEX IF NOT EXISTS ...` against an already-existing
    table — same rationale as ensure_columns, for indexes instead of columns.

    Unlike a missing column, a missing *unique* index can fail to create on a
    database that already has rows violating it (duplicates that predate the
    constraint). That's logged and left as-is rather than crashing startup —
    resolving those duplicates is a data decision, not something to do silently.
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(create_ddl))
    except DBAPIError as e:
        logger.warning("Could not create index %s — likely pre-existing duplicate rows violating it: %s", name, e)
