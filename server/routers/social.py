from typing import List
from fastapi import APIRouter, Depends
from server.db import get_db
from server.routers.auth import get_current_user_id
from server.schemas import (
    AddFriendReq,
    FriendItem,
    FriendNudgeItem,
    FriendNudgeReq,
    LeaderboardResp,
    ScreenTimeHeartbeatReq,
    ScreenTimeHeartbeatResp,
    ScreenTimeImportReq,
    ScreenTimeImportResp,
    UpdateThresholdReq,
)
from server.services.social import (
    add_friend,
    get_live_leaderboard,
    get_pending_nudges,
    get_screentime_summary,
    import_digital_wellbeing,
    list_friends,
    record_screentime_heartbeat,
    send_nudge,
    update_threshold,
)

router = APIRouter(tags=["social_and_screentime"])


@router.get("/api/screentime/summary")
def screentime_summary_endpoint(user_id: str = Depends(get_current_user_id)):
    with get_db() as conn:
        return get_screentime_summary(conn, user_id)


@router.post("/api/screentime/heartbeat", response_model=ScreenTimeHeartbeatResp)
def screentime_heartbeat_endpoint(
    payload: ScreenTimeHeartbeatReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return record_screentime_heartbeat(
            conn=conn,
            user_id=user_id,
            active_s=payload.active_s,
            idle_s=payload.idle_s
        )


@router.post("/api/screentime/import", response_model=ScreenTimeImportResp)
def screentime_import_endpoint(
    payload: ScreenTimeImportReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return import_digital_wellbeing(
            conn=conn,
            user_id=user_id,
            daily_screen_hours=payload.daily_screen_hours,
            device_label=payload.device_label
        )


@router.post("/api/screentime/threshold")
def update_threshold_endpoint(
    payload: UpdateThresholdReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        new_s = update_threshold(conn, user_id, payload.threshold_minutes)
        return {"status": "success", "threshold_seconds": new_s, "threshold_minutes": payload.threshold_minutes}


@router.get("/api/leaderboard", response_model=LeaderboardResp)
def get_leaderboard_endpoint(user_id: str = Depends(get_current_user_id)):
    with get_db() as conn:
        return get_live_leaderboard(conn, user_id)


@router.get("/api/friends", response_model=List[FriendItem])
def get_friends_endpoint(user_id: str = Depends(get_current_user_id)):
    with get_db() as conn:
        return list_friends(conn, user_id)


@router.post("/api/friends/add", response_model=FriendItem)
def add_friend_endpoint(
    payload: AddFriendReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return add_friend(conn, user_id, payload.friend_code_or_name)


@router.post("/api/friends/nudge")
def send_friend_nudge_endpoint(
    payload: FriendNudgeReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        nudge_id = send_nudge(conn, user_id, payload.friend_id, payload.message or "🌱 Time to Touch Grass!")
        return {"status": "sent", "nudge_id": nudge_id}


@router.get("/api/friends/nudges", response_model=List[FriendNudgeItem])
def get_friend_nudges_endpoint(user_id: str = Depends(get_current_user_id)):
    with get_db() as conn:
        return get_pending_nudges(conn, user_id)
