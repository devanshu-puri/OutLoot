import secrets
import sqlite3
from typing import List
from fastapi import HTTPException, status
from server.db import tx
from server.schemas import RedemptionResp, RewardItem
from server.services.points import add_point_transaction, get_points_balance
from server.settings import get_settings


def seed_rewards_if_empty(conn: sqlite3.Connection) -> None:
    settings = get_settings()
    count = conn.execute("SELECT COUNT(*) FROM rewards;").fetchone()[0]
    if count == 0:
        for r in settings.game_config.rewards:
            conn.execute(
                """
                INSERT OR IGNORE INTO rewards (id, title, description, cost_points, stock, state, terms)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (r.id, r.title, r.description, r.cost_points, r.stock, r.state, r.terms)
            )


def list_active_rewards(conn: sqlite3.Connection) -> List[RewardItem]:
    seed_rewards_if_empty(conn)
    rows = conn.execute(
        """
        SELECT id, title, description, cost_points, stock, state, terms
        FROM rewards
        WHERE state = 'ACTIVE'
        ORDER BY cost_points ASC;
        """
    ).fetchall()

    return [
        RewardItem(
            id=str(r["id"]),
            title=str(r["title"]),
            description=str(r["description"] or ""),
            cost_points=int(r["cost_points"]),
            stock=int(r["stock"]),
            state=str(r["state"]),
            terms=str(r["terms"] or "")
        )
        for r in rows
    ]


def generate_voucher_code() -> str:
    # Format: TG-XXXX-XXXX (crypto uppercase)
    p1 = secrets.token_hex(2).upper()
    p2 = secrets.token_hex(2).upper()
    return f"TG-{p1}-{p2}"


def redeem_reward(
    conn: sqlite3.Connection,
    user_id: str,
    reward_id: str,
    idempotency_key: str
) -> RedemptionResp:
    seed_rewards_if_empty(conn)

    with tx(conn):
        # 1. Idempotency replay check
        existing = conn.execute(
            """
            SELECT red.*, rew.title, rew.cost_points
            FROM redemptions red
            JOIN rewards rew ON red.reward_id = rew.id
            WHERE red.idempotency_key = ?;
            """,
            (idempotency_key,)
        ).fetchone()

        if existing:
            current_bal = get_points_balance(conn, user_id)
            return RedemptionResp(
                id=str(existing["id"]),
                reward_id=str(existing["reward_id"]),
                reward_title=str(existing["title"]),
                code=str(existing["code"]),
                status=str(existing["status"]),
                cost_points=int(existing["cost_points"]),
                new_balance=current_bal,
                created_at=str(existing["created_at"]),
                replayed=True
            )

        # 2. Check reward eligibility and stock
        reward = conn.execute(
            "SELECT * FROM rewards WHERE id = ?;",
            (reward_id,)
        ).fetchone()

        if not reward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "REWARD_NOT_FOUND", "message": "Reward not found"}
            )

        if reward["state"] != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "REWARD_NOT_ACTIVE", "message": "This reward is no longer available"}
            )

        if int(reward["stock"]) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "OUT_OF_STOCK", "message": "Sorry, this reward is out of stock"}
            )

        cost = int(reward["cost_points"])
        balance = get_points_balance(conn, user_id)
        if balance < cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "INSUFFICIENT_POINTS", "message": f"Insufficient points (you have {balance} pts, need {cost} pts)"}
            )

        # 3. Decrement stock atomically
        cursor = conn.execute(
            "UPDATE rewards SET stock = stock - 1 WHERE id = ? AND stock > 0;",
            (reward_id,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "OUT_OF_STOCK", "message": "Sorry, this reward was just claimed by another explorer"}
            )

        # 4. Generate unique redemption code & record
        code = generate_voucher_code()
        redemption_id = f"rdm_{secrets.token_hex(8)}"

        conn.execute(
            """
            INSERT INTO redemptions (id, user_id, reward_id, code, status, idempotency_key, created_at, fulfilled_at)
            VALUES (?, ?, ?, ?, 'CONFIRMED', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """,
            (redemption_id, user_id, reward_id, code, idempotency_key)
        )

        # 5. Append negative point transaction to ledger
        add_point_transaction(
            conn=conn,
            user_id=user_id,
            delta=-cost,
            kind="REDEEM_REWARD",
            ref_type="redemption",
            ref_id=redemption_id,
            note=f"Redeemed {reward['title']}"
        )

        new_bal = get_points_balance(conn, user_id)
        created_row = conn.execute("SELECT created_at FROM redemptions WHERE id = ?;", (redemption_id,)).fetchone()

        return RedemptionResp(
            id=redemption_id,
            reward_id=reward_id,
            reward_title=str(reward["title"]),
            code=code,
            status="CONFIRMED",
            cost_points=cost,
            new_balance=new_bal,
            created_at=str(created_row["created_at"]),
            replayed=False
        )


def get_user_redemptions(conn: sqlite3.Connection, user_id: str) -> List[RedemptionResp]:
    rows = conn.execute(
        """
        SELECT red.*, rew.title, rew.cost_points
        FROM redemptions red
        JOIN rewards rew ON red.reward_id = rew.id
        WHERE red.user_id = ?
        ORDER BY red.created_at DESC;
        """,
        (user_id,)
    ).fetchall()

    return [
        RedemptionResp(
            id=str(r["id"]),
            reward_id=str(r["reward_id"]),
            reward_title=str(r["title"]),
            code=str(r["code"]),
            status=str(r["status"]),
            cost_points=int(r["cost_points"]),
            new_balance=0,
            created_at=str(r["created_at"]),
            replayed=False
        )
        for r in rows
    ]
