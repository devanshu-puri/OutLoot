import sqlite3
import pytest
from server.db import create_connection, run_migrations, tx
from server.services.points import add_point_transaction, get_points_balance, get_recent_point_transactions


@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    run_migrations(conn)
    conn.execute("INSERT INTO users (id, display_name) VALUES ('usr_test', 'Tester');")
    conn.commit()
    yield conn
    conn.close()


def test_ledger_balance_equals_sum_property(memory_db):
    deltas = [10, 25, 60, -35, 120, -50, 10]
    expected_sum = sum(deltas)

    with tx(memory_db):
        for d in deltas:
            add_point_transaction(
                conn=memory_db,
                user_id="usr_test",
                delta=d,
                kind="TEST_TX",
                note="property test"
            )

    actual_balance = get_points_balance(memory_db, "usr_test")
    assert actual_balance == expected_sum

    history = get_recent_point_transactions(memory_db, "usr_test", limit=50)
    assert len(history) == len(deltas)
    assert sum(h.delta for h in history) == expected_sum
