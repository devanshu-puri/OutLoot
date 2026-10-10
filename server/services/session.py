import json
import secrets
import sqlite3
import time
from typing import Optional
from fastapi import HTTPException, status
from server.db import tx
from server.domain.geo import haversine_m, bearing_deg
from server.domain.states import SessionState, SessionEvent, transition_session
from server.schemas import SessionResponse, SpawnedItemHint
from server.services.items import spawn_next_item
from server.settings import get_settings


def get_active_session_for_user(conn: sqlite3.Connection, user_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM sessions
        WHERE user_id = ? AND state IN ('ACTIVE', 'PAUSED')
        ORDER BY started_at DESC LIMIT 1;
        """,
        (user_id,)
    ).fetchone()


def build_session_response(conn: sqlite3.Connection, session_row: sqlite3.Row, user_id: str) -> SessionResponse:
    session_id = str(session_row["id"])

    # Fetch next item status if available
    item_row = conn.execute(
        """
        SELECT si.*, idf.name, idf.rarity, idf.category, idf.base_points
        FROM spawned_items si
        JOIN item_definitions idf ON si.item_id = idf.id
        WHERE si.session_id = ? AND si.status IN ('LOCKED', 'AVAILABLE')
        ORDER BY si.spawned_at DESC LIMIT 1;
        """,
        (session_id,)
    ).fetchone()

    next_item: Optional[SpawnedItemHint] = None
    if item_row:
        lat = float(item_row["lat"])
        lon = float(item_row["lon"])
        dist = None
        brg = None
        if session_row["cycle_start_lat"] is not None and session_row["cycle_start_lon"] is not None:
            dist = haversine_m(session_row["cycle_start_lat"], session_row["cycle_start_lon"], item_row["lat"], item_row["lon"])
            brg = bearing_deg(session_row["cycle_start_lat"], session_row["cycle_start_lon"], item_row["lat"], item_row["lon"])

        next_item = SpawnedItemHint(
            id=str(item_row["id"]),
            rarity=str(item_row["rarity"]),
            base_points=int(item_row["base_points"]),
            name=str(item_row["name"]),
            category=str(item_row["category"]),
            status=item_row["status"],
            lat=lat,
            lon=lon,
            distance_m=dist,
            bearing_deg=brg
        )

    # Fetch nearby spawned items around player's session
    from server.services.items import get_nearby_items_for_session
    ref_lat = float(session_row["cycle_start_lat"] or (item_row["lat"] if item_row else 13.0827))
    ref_lon = float(session_row["cycle_start_lon"] or (item_row["lon"] if item_row else 80.2707))
    nearby_items = get_nearby_items_for_session(conn, session_id, ref_lat, ref_lon, desired_count=3)

    # Calculate points earned in this session
    points_row = conn.execute(
        """
        SELECT COALESCE(SUM(points), 0) AS total_pts, COUNT(*) AS count
        FROM collections
        WHERE session_id = ? AND result = 'SUCCESS';
        """,
        (session_id,)
    ).fetchone()
    points_earned = points_row["total_pts"] if points_row else 0
    collections_count = points_row["count"] if points_row else 0

    return SessionResponse(
        id=session_id,
        user_id=str(session_row["user_id"]),
        state=str(session_row["state"]),
        started_at=str(session_row["started_at"]),
        ended_at=str(session_row["ended_at"]) if session_row["ended_at"] else None,
        paused_reason=session_row["paused_reason"],
        session_elapsed_s=float(session_row["session_elapsed_s"] or 0.0),
        cycle_progress_s=float(session_row["cycle_progress_s"] or 0.0),
        cycle_required_s=float(session_row["cycle_required_s"]),
        distance_m=float(session_row["distance_m"] or 0.0),
        points_earned=points_earned,
        collections_count=collections_count,
        next_item=next_item,
        nearby_items=nearby_items,
        invalid_reason=session_row["invalid_reason"]
    )


def start_new_session(
    conn: sqlite3.Connection,
    user_id: str,
    start_lat: Optional[float] = None,
    start_lon: Optional[float] = None
) -> SessionResponse:
    settings = get_settings()
    cycle_req = float(settings.game_config.active_cycle_required_s)

    with tx(conn):
        # If active session exists, return existing
        active = get_active_session_for_user(conn, user_id)
        if active:
            return build_session_response(conn, active, user_id)

        session_id = f"ses_{secrets.token_hex(8)}"
        config_snapshot = json.dumps({
            "cycle_required_s": cycle_req,
            "demo_mode": settings.game_config.app.demo_mode,
            "min_displacement_m": settings.game_config.movement.min_displacement_m
        })

        conn.execute(
            """
            INSERT INTO sessions (
                id, user_id, state, started_at, session_elapsed_s,
                cycle_progress_s, cycle_required_s, distance_m,
                cycle_start_lat, cycle_start_lon, config_snapshot_json
            )
            VALUES (?, ?, 'ACTIVE', CURRENT_TIMESTAMP, 0.0, 0.0, ?, 0.0, ?, ?, ?);
            """,
            (session_id, user_id, cycle_req, start_lat, start_lon, config_snapshot)
        )

        # If initial location provided, pre-spawn the first locked item
        if start_lat is not None and start_lon is not None:
            spawn_next_item(conn, session_id, start_lat, start_lon)

        row = conn.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,)).fetchone()
        return build_session_response(conn, row, user_id)


def pause_session(conn: sqlite3.Connection, session_id: str, user_id: str, reason: str = "USER_PAUSED") -> SessionResponse:
    with tx(conn):
        row = conn.execute("SELECT * FROM sessions WHERE id = ? AND user_id = ?;", (session_id, user_id)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "SESSION_NOT_FOUND", "message": "Session not found"})

        current_state = SessionState(row["state"])
        next_state = transition_session(current_state, SessionEvent.PAUSE)

        conn.execute(
            "UPDATE sessions SET state = ?, paused_reason = ? WHERE id = ?;",
            (next_state.value, reason, session_id)
        )
        updated = conn.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,)).fetchone()
        return build_session_response(conn, updated, user_id)


def resume_session(conn: sqlite3.Connection, session_id: str, user_id: str) -> SessionResponse:
    with tx(conn):
        row = conn.execute("SELECT * FROM sessions WHERE id = ? AND user_id = ?;", (session_id, user_id)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "SESSION_NOT_FOUND", "message": "Session not found"})

        current_state = SessionState(row["state"])
        next_state = transition_session(current_state, SessionEvent.RESUME)

        conn.execute(
            "UPDATE sessions SET state = ?, paused_reason = NULL WHERE id = ?;",
            (next_state.value, session_id)
        )
        updated = conn.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,)).fetchone()
        return build_session_response(conn, updated, user_id)


def end_session(conn: sqlite3.Connection, session_id: str, user_id: str) -> SessionResponse:
    with tx(conn):
        row = conn.execute("SELECT * FROM sessions WHERE id = ? AND user_id = ?;", (session_id, user_id)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "SESSION_NOT_FOUND", "message": "Session not found"})

        current_state = SessionState(row["state"])
        if current_state not in (SessionState.COMPLETED, SessionState.INVALIDATED):
            next_state = transition_session(current_state, SessionEvent.COMPLETE)
            conn.execute(
                "UPDATE sessions SET state = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (next_state.value, session_id)
            )

        # Purge excess raw GPS samples past limit to preserve privacy
        conn.execute(
            """
            DELETE FROM movement_events
            WHERE session_id = ? AND id NOT IN (
                SELECT id FROM movement_events
                WHERE session_id = ?
                ORDER BY t DESC LIMIT 200
            );
            """,
            (session_id, session_id)
        )

        # Update user outdoor time & reset screen streak
        duration_s = float(row["session_elapsed_s"] or 0.0)
        if duration_s <= 0:
            duration_s = max(60.0, float(row["cycle_progress_s"] or 0.0))
        from server.services.social import reset_screen_streak_after_walk
        reset_screen_streak_after_walk(conn, user_id, duration_s)

        updated = conn.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,)).fetchone()
        return build_session_response(conn, updated, user_id)
