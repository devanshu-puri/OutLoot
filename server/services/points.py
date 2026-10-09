import secrets
import sqlite3
from typing import List, Optional
from server.schemas import PointTxItem


def add_point_transaction(
    conn: sqlite3.Connection,
    user_id: str,
    delta: int,
    kind: str,
    ref_type: Optional[str] = None,
    ref_id: Optional[str] = None,
    note: Optional[str] = None
) -> str:
    """
    Append a new point transaction to the ledger.
    Must be called inside an active transaction.
    """
    tx_id = f"ptx_{secrets.token_hex(8)}"
    conn.execute(
        """
        INSERT INTO point_transactions (id, user_id, delta, kind, ref_type, ref_id, created_at, note)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?);
        """,
        (tx_id, user_id, delta, kind, ref_type, ref_id, note)
    )
    return tx_id


def get_points_balance(conn: sqlite3.Connection, user_id: str) -> int:
    """
    Calculate user's authoritative point balance by summing all ledger transactions.
    """
    row = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) AS balance FROM point_transactions WHERE user_id = ?;",
        (user_id,)
    ).fetchone()
    return int(row["balance"]) if row else 0


def get_recent_point_transactions(conn: sqlite3.Connection, user_id: str, limit: int = 20) -> List[PointTxItem]:
    rows = conn.execute(
        """
        SELECT id, delta, kind, created_at, note
        FROM point_transactions
        WHERE user_id = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT ?;
        """,
        (user_id, limit)
    ).fetchall()

    return [
        PointTxItem(
            id=str(r["id"]),
            delta=int(r["delta"]),
            kind=str(r["kind"]),
            created_at=str(r["created_at"]),
            note=r["note"]
        )
        for r in rows
    ]
