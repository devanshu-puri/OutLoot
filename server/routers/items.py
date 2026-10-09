from fastapi import APIRouter, Depends, HTTPException, Request, status
from server.db import get_db
from server.routers.auth import get_current_user_id
from server.schemas import CollectReq, CollectResp
from server.services.items import collect_item

router = APIRouter(prefix="/api/session", tags=["items"])


@router.post("/{session_id}/collect", response_model=CollectResp)
def collect_item_endpoint(
    session_id: str,
    payload: CollectReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return collect_item(
            conn=conn,
            session_id=session_id,
            user_id=user_id,
            spawn_id=payload.spawn_id,
            user_lat=payload.lat,
            user_lon=payload.lon,
            accuracy_m=payload.accuracy_m,
            idempotency_key=payload.idempotency_key
        )
