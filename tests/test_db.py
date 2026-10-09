import sqlite3
import pytest
from server.db import create_connection, run_migrations, tx


@pytest.fixture
def memory_db():
    conn = create_connection(None)
    # Use in-memory for fast testing
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    run_migrations(conn)
    yield conn
    conn.close()


def test_migrations_create_tables(memory_db):
    tables = [
        row[0]
        for row in memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    assert "users" in tables
    assert "sessions" in tables
    assert "movement_events" in tables
    assert "item_definitions" in tables
    assert "spawned_items" in tables
    assert "collections" in tables
    assert "point_transactions" in tables
    assert "rewards" in tables
    assert "redemptions" in tables
    assert "missions" in tables


def test_transaction_rollback_on_error(memory_db):
    memory_db.execute("INSERT INTO users (id, display_name) VALUES ('u1', 'User 1');")
    memory_db.commit()

    with pytest.raises(RuntimeError):
        with tx(memory_db):
            memory_db.execute("INSERT INTO users (id, display_name) VALUES ('u2', 'User 2');")
            raise RuntimeError("Forced abort")

    row = memory_db.execute("SELECT * FROM users WHERE id = 'u2';").fetchone()
    assert row is None


def test_foreign_key_enforcement(memory_db):
    with pytest.raises(sqlite3.IntegrityError):
        with tx(memory_db):
            # Invalid user_id reference
            memory_db.execute("INSERT INTO installations (id, user_id, token_hash) VALUES ('i1', 'nonexistent', 'hash');")
