from typing import List
from fastapi import APIRouter, Depends
from server.db import get_db
from server.routers.auth import get_current_user_id
from server.schemas import RedeemReq, RedemptionResp, RewardItem
from server.services.market import get_user_redemptions, list_active_rewards, redeem_reward

router = APIRouter(tags=["marketplace"])


@router.get("/api/rewards", response_model=List[RewardItem])
def get_rewards_endpoint():
    with get_db() as conn:
        return list_active_rewards(conn)


@router.post("/api/rewards/{reward_id}/redeem", response_model=RedemptionResp)
def redeem_reward_endpoint(
    reward_id: str,
    payload: RedeemReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return redeem_reward(
            conn=conn,
            user_id=user_id,
            reward_id=reward_id,
            idempotency_key=payload.idempotency_key
        )


@router.get("/api/redemptions", response_model=List[RedemptionResp])
def get_redemptions_endpoint(user_id: str = Depends(get_current_user_id)):
    with get_db() as conn:
        return get_user_redemptions(conn, user_id)
