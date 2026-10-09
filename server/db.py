import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from server.settings import get_settings


def get_db_path() -> Path:
    settings = get_settings()
    db_path = Path(settings.db_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parent.parent / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def create_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    
    conn = sqlite3.connect(
        str(db_path),
        timeout=30.0,
        check_same_thread=False,
        autocommit=True
    )
    conn.row_factory = sqlite3.Row
    # Configure SQLite for robust concurrent reads & writes
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def get_db(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    conn = create_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def tx(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for atomic database transactions using BEGIN IMMEDIATE.
    Acquires write lock immediately to prevent deadlocks and races.
    Handles nested transactions safely.
    """
    is_outer = not conn.in_transaction
    if is_outer:
        conn.execute("BEGIN IMMEDIATE;")
    try:
        yield conn
        if is_outer:
            conn.execute("COMMIT;")
    except Exception:
        if is_outer:
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
        raise


def run_migrations(conn: sqlite3.Connection, migrations_dir: Optional[Path] = None) -> None:
    if migrations_dir is None:
        migrations_dir = Path(__file__).resolve().parent / "migrations"

    if not migrations_dir.exists():
        return

    sql_files = sorted(migrations_dir.glob("*.sql"))
    for sql_file in sql_files:
        with open(sql_file, "r", encoding="utf-8") as f:
            script = f.read()
            conn.executescript(script)


def init_db(db_path: Optional[Path] = None) -> None:
    with get_db(db_path) as conn:
        run_migrations(conn)
