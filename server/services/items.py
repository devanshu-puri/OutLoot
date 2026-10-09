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
            lat=float(existing["lat"]) if existing["status"] == "AVAILABLE" else None,
            lon=float(existing["lon"]) if existing["status"] == "AVAILABLE" else None,
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
        lat=None,
        lon=None,
        distance_m=dist_m,
        bearing_deg=bearing_val
    )


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
