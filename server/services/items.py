import json
import random
import secrets
import sqlite3
import time
from typing import Optional, Tuple
from fastapi import HTTPException, status
from server.db import tx
from server.domain.geo import haversine_m, destination_point, bearing_deg
from server.domain.states import ItemState, ItemEvent, transition_item
from server.schemas import CollectResp, SpawnedItemHint
from server.settings import get_settings


def seed_item_definitions_if_empty(conn: sqlite3.Connection) -> None:
    settings = get_settings()
    count = conn.execute("SELECT COUNT(*) FROM item_definitions;").fetchone()[0]
    if count == 0:
        for item in settings.game_config.items:
            conn.execute(
                """
                INSERT OR IGNORE INTO item_definitions (id, name, category, rarity, base_points, weight, active, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item.id, item.name, item.category, item.rarity, item.base_points, item.weight, 1 if item.active else 0, item.description)
            )


def pick_random_item_definition(conn: sqlite3.Connection) -> sqlite3.Row:
    seed_item_definitions_if_empty(conn)
    items = conn.execute("SELECT * FROM item_definitions WHERE active = 1 AND weight > 0;").fetchall()
    if not items:
        # Fallback to any active item
        items = conn.execute("SELECT * FROM item_definitions WHERE active = 1;").fetchall()
    
    weights = [it["weight"] for it in items]
    chosen = random.choices(items, weights=weights, k=1)[0]
    return chosen


def spawn_next_item(
    conn: sqlite3.Connection,
    session_id: str,
    origin_lat: float,
    origin_lon: float
) -> SpawnedItemHint:
    settings = get_settings()
    cfg = settings.game_config

    # Check if there is already an active locked or available item for this session
    existing = conn.execute(
        """
        SELECT si.*, idf.name, idf.rarity, idf.category, idf.base_points
        FROM spawned_items si
        JOIN item_definitions idf ON si.item_id = idf.id
        WHERE si.session_id = ? AND si.status IN ('LOCKED', 'AVAILABLE')
        ORDER BY si.spawned_at DESC LIMIT 1;
        """,
        (session_id,)
    ).fetchone()

    if existing:
        dist = haversine_m(origin_lat, origin_lon, existing["lat"], existing["lon"])
        brg = bearing_deg(origin_lat, origin_lon, existing["lat"], existing["lon"])
        return SpawnedItemHint(
            id=str(existing["id"]),
            rarity=str(existing["rarity"]),
            base_points=int(existing["base_points"]),
            name=str(existing["name"]),
            category=str(existing["category"]),
            status=existing["status"],
            lat=float(existing["lat"]),
            lon=float(existing["lon"]),
            distance_m=dist,
            bearing_deg=brg
        )

    # Pick item definition by weighted rarity
    item_def = pick_random_item_definition(conn)

    # Generate random distance and bearing within configured bounds
    dist_m = random.uniform(cfg.spawn.spawn_min_m, cfg.spawn.spawn_max_m)
    bearing_val = random.uniform(0.0, 360.0)
    target_lat, target_lon = destination_point(origin_lat, origin_lon, bearing_val, dist_m)

    spawn_id = f"spw_{secrets.token_hex(8)}"
    conn.execute(
        """
        INSERT INTO spawned_items (id, item_id, session_id, lat, lon, status, spawned_at)
        VALUES (?, ?, ?, ?, ?, 'LOCKED', CURRENT_TIMESTAMP);
        """,
        (spawn_id, item_def["id"], session_id, target_lat, target_lon)
    )

    return SpawnedItemHint(
        id=spawn_id,
        rarity=str(item_def["rarity"]),
        base_points=int(item_def["base_points"]),
        name=str(item_def["name"]),
        category=str(item_def["category"]),
        status="LOCKED",
        lat=target_lat,
        lon=target_lon,
        distance_m=dist_m,
        bearing_deg=bearing_val
    )


def get_nearby_items_for_session(
    conn: sqlite3.Connection,
    session_id: str,
    origin_lat: float,
    origin_lon: float,
    desired_count: int = 3
) -> list[SpawnedItemHint]:
    """
    Ensure multiple discoverable items are spawned around the user's walk path.
    """
    settings = get_settings()
    cfg = settings.game_config

    rows = conn.execute(
        """
        SELECT si.*, idf.name, idf.rarity, idf.category, idf.base_points
        FROM spawned_items si
        JOIN item_definitions idf ON si.item_id = idf.id
        WHERE si.session_id = ? AND si.status IN ('LOCKED', 'AVAILABLE')
        ORDER BY si.spawned_at ASC;
        """,
        (session_id,)
    ).fetchall()

    items = list(rows)
    # If fewer than desired_count, spawn extra drops at different bearings & distances
    while len(items) < desired_count:
        item_def = pick_random_item_definition(conn)
        dist_m = random.uniform(cfg.spawn.spawn_min_m * 0.9, cfg.spawn.spawn_max_m * 1.2)
        bearing_val = random.uniform(0.0, 360.0)
        target_lat, target_lon = destination_point(origin_lat, origin_lon, bearing_val, dist_m)
        spawn_id = f"spw_{secrets.token_hex(8)}"
        conn.execute(
            """
            INSERT INTO spawned_items (id, item_id, session_id, lat, lon, status, spawned_at)
            VALUES (?, ?, ?, ?, ?, 'LOCKED', CURRENT_TIMESTAMP);
            """,
            (spawn_id, item_def["id"], session_id, target_lat, target_lon)
        )
        new_row = conn.execute(
            """
            SELECT si.*, idf.name, idf.rarity, idf.category, idf.base_points
            FROM spawned_items si
            JOIN item_definitions idf ON si.item_id = idf.id
            WHERE si.id = ?;
            """,
            (spawn_id,)
        ).fetchone()
        items.append(new_row)

    hints = []
    for r in items:
        dist = haversine_m(origin_lat, origin_lon, r["lat"], r["lon"])
        brg = bearing_deg(origin_lat, origin_lon, r["lat"], r["lon"])
        hints.append(SpawnedItemHint(
            id=str(r["id"]),
            rarity=str(r["rarity"]),
            base_points=int(r["base_points"]),
            name=str(r["name"]),
            category=str(r["category"]),
            status=r["status"],
            lat=float(r["lat"]),
            lon=float(r["lon"]),
            distance_m=dist,
            bearing_deg=brg
        ))
    return hints



def check_and_unlock_items(
    conn: sqlite3.Connection,
    session_id: str,
    cycle_progress_s: float,
    cycle_required_s: float,
    displacement_m: float
) -> Optional[SpawnedItemHint]:
    settings = get_settings()
    min_disp = settings.game_config.movement.min_displacement_m

    # Item unlocks when accumulated qualifying seconds >= required AND net displacement from cycle start >= min threshold
    if cycle_progress_s >= cycle_required_s and displacement_m >= min_disp:
        # Find locked item for this session
        row = conn.execute(
            """
            SELECT si.*, idf.name, idf.rarity, idf.category, idf.base_points
            FROM spawned_items si
            JOIN item_definitions idf ON si.item_id = idf.id
            WHERE si.session_id = ? AND si.status = 'LOCKED'
            ORDER BY si.spawned_at DESC LIMIT 1;
            """,
            (session_id,)
        ).fetchone()

        if row:
            conn.execute(
                "UPDATE spawned_items SET status = 'AVAILABLE', available_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (row["id"],)
            )
            return SpawnedItemHint(
                id=str(row["id"]),
                rarity=str(row["rarity"]),
                base_points=int(row["base_points"]),
                name=str(row["name"]),
                category=str(row["category"]),
                status="AVAILABLE",
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                distance_m=None,
                bearing_deg=None
            )

    return None


def collect_item(
    conn: sqlite3.Connection,
    session_id: str,
    user_id: str,
    spawn_id: str,
    user_lat: float,
    user_lon: float,
    accuracy_m: float,
    idempotency_key: str
) -> CollectResp:
    from server.services.points import add_point_transaction, get_points_balance
    settings = get_settings()
    cfg = settings.game_config

    with tx(conn):
        # 1. Check idempotency replay
        existing_col = conn.execute(
            "SELECT * FROM collections WHERE idempotency_key = ?;",
            (idempotency_key,)
        ).fetchone()

        if existing_col:
            current_balance = get_points_balance(conn, user_id)
            return CollectResp(
                result="REPLAY",
                reason_code="REPLAY",
                points_awarded=int(existing_col["points"]),
                new_balance=current_balance,
                cycle_progress_s=0.0,
                message="Collection replayed from previous submission"
            )

        # 2. Check session state
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE id = ? AND user_id = ?;",
            (session_id, user_id)
        ).fetchone()

        if not session_row or session_row["state"] != "ACTIVE":
            curr_bal = get_points_balance(conn, user_id)
            return CollectResp(
                result="REJECTED",
                reason_code="NOT_ACTIVE",
                points_awarded=0,
                new_balance=curr_bal,
                cycle_progress_s=float(session_row["cycle_progress_s"] if session_row else 0.0),
                message="Session is not currently active"
            )

        # 3. Check session limits
        counts = conn.execute(
            """
            SELECT COUNT(*) AS total_cols, COALESCE(SUM(points), 0) AS total_pts
            FROM collections
            WHERE session_id = ? AND result = 'SUCCESS';
            """,
            (session_id,)
        ).fetchone()
        if counts["total_cols"] >= cfg.limits.max_collections_per_session or counts["total_pts"] >= cfg.limits.max_points_per_session:
            curr_bal = get_points_balance(conn, user_id)
            return CollectResp(
                result="REJECTED",
                reason_code="SESSION_LIMIT",
                points_awarded=0,
                new_balance=curr_bal,
                cycle_progress_s=float(session_row["cycle_progress_s"]),
                message="Session collection limit reached"
            )

        # 4. Check accuracy
        if accuracy_m > cfg.movement.max_accuracy_m:
            curr_bal = get_points_balance(conn, user_id)
            return CollectResp(
                result="REJECTED",
                reason_code="LOW_ACCURACY",
                points_awarded=0,
                new_balance=curr_bal,
                cycle_progress_s=float(session_row["cycle_progress_s"]),
                message=f"GPS accuracy ({accuracy_m:.1f}m) too low to verify collection proximity"
            )

        # 5. Check item existence & availability
        item_row = conn.execute(
            """
            SELECT si.*, idf.name, idf.rarity, idf.category, idf.base_points
            FROM spawned_items si
            JOIN item_definitions idf ON si.item_id = idf.id
            WHERE si.id = ? AND si.session_id = ?;
            """,
            (spawn_id, session_id)
        ).fetchone()

        if not item_row:
            curr_bal = get_points_balance(conn, user_id)
            return CollectResp(
                result="REJECTED",
                reason_code="ITEM_NOT_AVAILABLE",
                points_awarded=0,
                new_balance=curr_bal,
                cycle_progress_s=float(session_row["cycle_progress_s"]),
                message="Spawned item not found for this session"
            )

        if item_row["status"] == "COLLECTED":
            curr_bal = get_points_balance(conn, user_id)
            return CollectResp(
                result="REJECTED",
                reason_code="ALREADY_COLLECTED",
                points_awarded=0,
                new_balance=curr_bal,
                cycle_progress_s=float(session_row["cycle_progress_s"]),
                message="Item has already been collected"
            )

        if item_row["status"] != "AVAILABLE":
            curr_bal = get_points_balance(conn, user_id)
            return CollectResp(
                result="REJECTED",
                reason_code="ITEM_NOT_AVAILABLE",
                points_awarded=0,
                new_balance=curr_bal,
                cycle_progress_s=float(session_row["cycle_progress_s"]),
                message="Item is still locked. Walk further to unlock it!"
            )

        # 6. Check Proximity
        dist_m = haversine_m(user_lat, user_lon, item_row["lat"], item_row["lon"])
        allowed_radius = cfg.spawn.collect_radius_m + min(accuracy_m, 15.0)

        if dist_m > allowed_radius:
            curr_bal = get_points_balance(conn, user_id)
            return CollectResp(
                result="REJECTED",
                reason_code="OUT_OF_RANGE",
                points_awarded=0,
                new_balance=curr_bal,
                cycle_progress_s=float(session_row["cycle_progress_s"]),
                message=f"Item is {int(dist_m)}m away (must be within {int(allowed_radius)}m)"
            )

        # 7. Collect Success: Update item, insert collection record, add ledger points
        points_to_award = int(item_row["base_points"])
        conn.execute(
            "UPDATE spawned_items SET status = 'COLLECTED', collected_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (spawn_id,)
        )

        col_id = f"col_{secrets.token_hex(8)}"
        conn.execute(
            """
            INSERT INTO collections (id, session_id, spawn_id, user_id, idempotency_key, result, reason_code, points)
            VALUES (?, ?, ?, ?, ?, 'SUCCESS', 'OK', ?);
            """,
            (col_id, session_id, spawn_id, user_id, idempotency_key, points_to_award)
        )

        add_point_transaction(
            conn=conn,
            user_id=user_id,
            delta=points_to_award,
            kind="COLLECT_ITEM",
            ref_type="spawn",
            ref_id=spawn_id,
            note=f"Collected {item_row['name']} ({item_row['rarity']})"
        )

        from server.services.profile import record_daily_stats
        record_daily_stats(conn, user_id, delta_points=points_to_award, delta_items=1)

        # Reset session cycle progress and update origin to collection location
        conn.execute(
            """
            UPDATE sessions
            SET cycle_progress_s = 0.0,
                cycle_start_lat = ?,
                cycle_start_lon = ?
            WHERE id = ?;
            """,
            (user_lat, user_lon, session_id)
        )

        # Pre-spawn next locked item from this location
        spawn_next_item(conn, session_id, user_lat, user_lon)

        new_balance = get_points_balance(conn, user_id)

        return CollectResp(
            result="SUCCESS",
            reason_code="OK",
            points_awarded=points_to_award,
            new_balance=new_balance,
            cycle_progress_s=0.0,
            message=f"Successfully collected {item_row['name']}! (+{points_to_award} points)",
            item_name=str(item_row["name"]),
            rarity=str(item_row["rarity"])
        )
