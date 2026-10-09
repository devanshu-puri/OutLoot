import time
import pytest
from server.db import get_db, tx
from server.domain.geo import destination_point


def test_item_collect_lifecycle(test_client):
    auth = test_client.post("/api/auth/anon").json()
    headers = {"Authorization": f"Bearer {auth['token']}"}
    user_id = auth["user_id"]

    # 1. Start Session
    start_resp = test_client.post(
        "/api/session/start",
        json={"display_name": "Collector", "start_lat": 13.0827, "start_lon": 80.2707},
        headers=headers
    ).json()
    session_id = start_resp["id"]
    spawn_id = start_resp["next_item"]["id"]
    assert start_resp["next_item"]["status"] == "LOCKED"

    # Attempting to collect locked item -> REJECTED
    col_early = test_client.post(
        f"/api/session/{session_id}/collect",
        json={
            "spawn_id": spawn_id,
            "lat": 13.0827,
            "lon": 80.2707,
            "accuracy_m": 4.0,
            "idempotency_key": "early_key_1"
        },
        headers=headers
    ).json()
    assert col_early["result"] == "REJECTED"
    assert col_early["reason_code"] == "ITEM_NOT_AVAILABLE"

    # 2. Unlock item by setting status to AVAILABLE or walking
    with get_db() as conn:
        with tx(conn):
            # Fetch item coordinates
            row = conn.execute("SELECT lat, lon FROM spawned_items WHERE id = ?;", (spawn_id,)).fetchone()
            item_lat = float(row["lat"])
            item_lon = float(row["lon"])
            conn.execute("UPDATE spawned_items SET status = 'AVAILABLE' WHERE id = ?;", (spawn_id,))

    # 3. Out of Range Collection attempt (1 km away)
    col_far = test_client.post(
        f"/api/session/{session_id}/collect",
        json={
            "spawn_id": spawn_id,
            "lat": item_lat + 0.05,
            "lon": item_lon + 0.05,
            "accuracy_m": 5.0,
            "idempotency_key": "far_key_1"
        },
        headers=headers
    ).json()
    assert col_far["result"] == "REJECTED"
    assert col_far["reason_code"] == "OUT_OF_RANGE"
    assert "away" in col_far["message"]

    # 4. In Range Collection Success
    col_success = test_client.post(
        f"/api/session/{session_id}/collect",
        json={
            "spawn_id": spawn_id,
            "lat": item_lat,
            "lon": item_lon,
            "accuracy_m": 5.0,
            "idempotency_key": "success_key_1"
        },
        headers=headers
    ).json()
    assert col_success["result"] == "SUCCESS"
    assert col_success["reason_code"] == "OK"
    assert col_success["points_awarded"] > 0
    assert col_success["new_balance"] == col_success["points_awarded"]

    # 5. Idempotency Replay with same key -> Returns REPLAY
    col_replay = test_client.post(
        f"/api/session/{session_id}/collect",
        json={
            "spawn_id": spawn_id,
            "lat": item_lat,
            "lon": item_lon,
            "accuracy_m": 5.0,
            "idempotency_key": "success_key_1"
        },
        headers=headers
    ).json()
    assert col_replay["result"] == "REPLAY"
    assert col_replay["points_awarded"] == col_success["points_awarded"]

    # 6. Double collect with a different key -> REJECTED (ALREADY_COLLECTED)
    col_double = test_client.post(
        f"/api/session/{session_id}/collect",
        json={
            "spawn_id": spawn_id,
            "lat": item_lat,
            "lon": item_lon,
            "accuracy_m": 5.0,
            "idempotency_key": "different_key_2"
        },
        headers=headers
    ).json()
    assert col_double["result"] == "REJECTED"
    assert col_double["reason_code"] == "ALREADY_COLLECTED"

    # 7. Balance check via /api/points
    pts_resp = test_client.get("/api/points", headers=headers).json()
    assert pts_resp["balance"] == col_success["points_awarded"]
