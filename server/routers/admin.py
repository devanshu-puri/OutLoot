import json
import secrets
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status
from server.db import get_db, tx
from server.schemas import AdjustPointsReq, BalanceResponse
from server.services.items import seed_item_definitions_if_empty
from server.services.market import seed_rewards_if_empty
from server.services.points import add_point_transaction, get_points_balance
from server.settings import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


def verify_admin_token(x_admin_token: Optional[str] = Header(None)) -> bool:
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "FORBIDDEN", "message": "Invalid or missing X-Admin-Token header"}
        )
    return True


@router.post("/adjust", response_model=BalanceResponse)
def admin_adjust_points(
    payload: AdjustPointsReq,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
):
    settings = get_settings()
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "FORBIDDEN", "message": "Invalid or missing X-Admin-Token header"}
        )

    with get_db() as conn:
        with tx(conn):
            # Check user exists
            user_row = conn.execute("SELECT id FROM users WHERE id = ?;", (payload.user_id,)).fetchone()
            if not user_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error_code": "USER_NOT_FOUND", "message": "User not found"}
                )

            add_point_transaction(
                conn=conn,
                user_id=payload.user_id,
                delta=payload.delta,
                kind="ADMIN_ADJUSTMENT",
                ref_type="admin",
                ref_id="admin_cli",
                note=payload.note
            )

            # Audit event
            audit_id = f"aud_{secrets.token_hex(8)}"
            conn.execute(
                """
                INSERT INTO audit_events (id, actor, action, detail_json, created_at)
                VALUES (?, 'admin', 'ADJUST_POINTS', ?, CURRENT_TIMESTAMP);
                """,
                (audit_id, json.dumps({"user_id": payload.user_id, "delta": payload.delta, "note": payload.note}))
            )

            new_bal = get_points_balance(conn, payload.user_id)
            return BalanceResponse(balance=new_bal, recent_transactions=[])


@router.post("/seed")
def admin_seed_database(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
):
    settings = get_settings()
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "FORBIDDEN", "message": "Invalid or missing X-Admin-Token header"}
        )

    with get_db() as conn:
        with tx(conn):
            seed_item_definitions_if_empty(conn)
            seed_rewards_if_empty(conn)
    return {"status": "success", "message": "Item definitions and sample rewards seeded successfully"}
