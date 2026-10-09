from fastapi import APIRouter, Depends, HTTPException, Request, status
from server.db import get_db
from server.routers.auth import get_current_user_id
from server.schemas import SampleBatchReq, SampleBatchResp, SessionResponse, SessionStartReq
from server.services.movement import process_sample_batch
from server.services.session import (
    build_session_response,
    end_session,
    get_active_session_for_user,
    pause_session,
    resume_session,
    start_new_session,
)

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start", response_model=SessionResponse)
def start_session_endpoint(
    payload: SessionStartReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return start_new_session(
            conn=conn,
            user_id=user_id,
            start_lat=payload.start_lat,
            start_lon=payload.start_lon
        )


@router.get("/active", response_model=SessionResponse)
def get_active_session_endpoint(
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        row = get_active_session_for_user(conn, user_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "NO_ACTIVE_SESSION", "message": "No active session in progress"}
            )
        return build_session_response(conn, row, user_id)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_endpoint(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ? AND user_id = ?;",
            (session_id, user_id)
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "SESSION_NOT_FOUND", "message": "Session not found"}
            )
        return build_session_response(conn, row, user_id)


@router.post("/{session_id}/pause", response_model=SessionResponse)
def pause_session_endpoint(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return pause_session(conn, session_id, user_id)


@router.post("/{session_id}/resume", response_model=SessionResponse)
def resume_session_endpoint(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return resume_session(conn, session_id, user_id)


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session_endpoint(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return end_session(conn, session_id, user_id)


@router.post("/{session_id}/samples", response_model=SampleBatchResp)
def post_samples_endpoint(
    session_id: str,
    batch: SampleBatchReq,
    user_id: str = Depends(get_current_user_id)
):
    with get_db() as conn:
        return process_sample_batch(conn, session_id, user_id, batch)
