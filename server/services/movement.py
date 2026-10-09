import secrets
import sqlite3
import time
from typing import List
from fastapi import HTTPException, status
from server.db import tx
from server.domain.movement import MovementState, evaluate_samples
from server.domain.states import SessionState
from server.schemas import RejectedSampleDetail, SampleBatchReq, SampleBatchResp, SampleItem
from server.services.items import check_and_unlock_items, spawn_next_item
from server.services.session import build_session_response
from server.settings import get_settings


def process_sample_batch(
    conn: sqlite3.Connection,
    session_id: str,
    user_id: str,
    batch: SampleBatchReq
) -> SampleBatchResp:
    settings = get_settings()
    cfg = settings.game_config

    with tx(conn):
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE id = ? AND user_id = ?;",
            (session_id, user_id)
        ).fetchone()

        if not session_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "SESSION_NOT_FOUND", "message": "Session not found"}
            )

        if session_row["state"] != "ACTIVE":
            # If paused or completed, reject samples gracefully
            return SampleBatchResp(
                accepted_count=0,
                rejected=[
                    RejectedSampleDetail(index=i, reason_code="SESSION_NOT_ACTIVE", detail=f"Session is {session_row['state']}")
                    for i in range(len(batch.samples))
                ],
                session_state=session_row["state"],
                cycle_progress_s=float(session_row["cycle_progress_s"] or 0.0),
                cycle_required_s=float(session_row["cycle_required_s"]),
                distance_m=float(session_row["distance_m"] or 0.0),
                item_available=False
            )

        # Retrieve the latest movement event to reconstruct previous state
        last_event = conn.execute(
            """
            SELECT t, lat, lon, accuracy_m FROM movement_events
            WHERE session_id = ? AND verdict = 'QUALIFYING'
            ORDER BY t DESC LIMIT 1;
            """,
            (session_id,)
        ).fetchone()

        prev_state = MovementState(
            last_lat=float(last_event["lat"]) if last_event else session_row["cycle_start_lat"],
            last_lon=float(last_event["lon"]) if last_event else session_row["cycle_start_lon"],
            last_t=float(last_event["t"]) if last_event else None,
            last_accuracy_m=float(last_event["accuracy_m"]) if last_event else None,
            cycle_start_lat=session_row["cycle_start_lat"],
            cycle_start_lon=session_row["cycle_start_lon"],
            cycle_progress_s=float(session_row["cycle_progress_s"] or 0.0),
            distance_m=float(session_row["distance_m"] or 0.0),
            implausible_count=0
        )

        now = time.time()
        eval_result = evaluate_samples(prev_state, batch.samples, cfg.movement, server_now=now)

        # Save movement events into database (with TTL management)
        for seg in eval_result.segments:
            event_id = f"mve_{secrets.token_hex(8)}"
            conn.execute(
                """
                INSERT INTO movement_events (id, session_id, t, lat, lon, accuracy_m, verdict, reason_code, seg_speed_mps)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_id,
                    session_id,
                    seg.sample.t,
                    seg.sample.lat,
                    seg.sample.lon,
                    seg.sample.accuracy_m,
                    seg.verdict,
                    seg.reason_code,
                    seg.speed_mps
                )
            )

        # Update session cycle progress, distance, and cycle start lat/lon if not set
        new_cycle_start_lat = session_row["cycle_start_lat"] or eval_result.new_state.last_lat
        new_cycle_start_lon = session_row["cycle_start_lon"] or eval_result.new_state.last_lon

        # Auto-spawn item if none exists
        if new_cycle_start_lat is not None and new_cycle_start_lon is not None:
            spawn_next_item(conn, session_id, new_cycle_start_lat, new_cycle_start_lon)

        # Check if cycle unlocks the spawned item
        cycle_req = float(session_row["cycle_required_s"])
        unlocked_hint = check_and_unlock_items(
            conn,
            session_id,
            eval_result.new_state.cycle_progress_s,
            cycle_req,
            eval_result.displacement_from_cycle_start_m
        )

        conn.execute(
            """
            UPDATE sessions
            SET cycle_progress_s = ?,
                distance_m = ?,
                cycle_start_lat = ?,
                cycle_start_lon = ?
            WHERE id = ?;
            """,
            (
                eval_result.new_state.cycle_progress_s,
                eval_result.new_state.distance_m,
                new_cycle_start_lat,
                new_cycle_start_lon,
                session_id
            )
        )

        # Build response with hint
        updated_session = conn.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,)).fetchone()
        session_resp = build_session_response(conn, updated_session, user_id)

        is_item_avail = bool(session_resp.next_item and session_resp.next_item.status == "AVAILABLE")

        return SampleBatchResp(
            accepted_count=len(eval_result.accepted),
            rejected=[RejectedSampleDetail(index=r.index, reason_code=r.reason_code, detail=r.message) for r in eval_result.rejected],
            session_state=session_row["state"],
            cycle_progress_s=eval_result.new_state.cycle_progress_s,
            cycle_required_s=cycle_req,
            distance_m=eval_result.new_state.distance_m,
            item_available=is_item_avail,
            next_item=session_resp.next_item
        )
