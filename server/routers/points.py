from fastapi import APIRouter, Depends
from server.db import get_db
from server.routers.auth import get_current_user_id
from server.schemas import BalanceResponse
from server.services.points import get_points_balance, get_recent_point_transactions

router = APIRouter(prefix="/api/points", tags=["points"])


@router.get("", response_model=BalanceResponse)
def get_points_endpoint(user_id: str = Depends(get_current_user_id)):
    with get_db() as conn:
        bal = get_points_balance(conn, user_id)
        recent = get_recent_point_transactions(conn, user_id, limit=20)
        return BalanceResponse(balance=bal, recent_transactions=recent)
