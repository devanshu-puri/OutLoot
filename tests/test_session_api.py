import time
import pytest
from server.domain.geo import destination_point


def test_session_lifecycle_flow(test_client):
    auth = test_client.post("/api/auth/anon").json()
    headers = {"Authorization": f"Bearer {auth['token']}"}

    # 1. Start Session
    start_resp = test_client.post(
        "/api/session/start",
        json={"display_name": "Test Runner", "start_lat": 13.0827, "start_lon": 80.2707},
        headers=headers
    )
    assert start_resp.status_code == 200
    ses = start_resp.json()
    session_id = ses["id"]
    assert ses["state"] == "ACTIVE"
    assert ses["cycle_progress_s"] == 0.0
    assert ses["distance_m"] == 0.0
    assert ses["next_item"] is not None
    assert ses["next_item"]["status"] == "LOCKED"

    # 2. Starting again returns the same active session (1 active session per user)
    dup_start = test_client.post(
        "/api/session/start",
        json={"display_name": "Test Runner"},
        headers=headers
    )
    assert dup_start.status_code == 200
    assert dup_start.json()["id"] == session_id

    # 3. Post movement samples
    now = time.time()
    lat0, lon0 = 13.0827, 80.2707
    samples = []
    for i in range(5):
        lat_i, lon_i = destination_point(lat0, lon0, 90.0, i * 7.0)
        samples.append({
            "t": now - (4 - i) * 5.0,
            "lat": lat_i,
            "lon": lon_i,
            "accuracy_m": 4.0
        })

    sample_resp = test_client.post(
        f"/api/session/{session_id}/samples",
        json={"samples": samples},
        headers=headers
    )
    assert sample_resp.status_code == 200
    batch_data = sample_resp.json()
    assert batch_data["accepted_count"] == 5
    assert batch_data["cycle_progress_s"] == 20.0
    assert batch_data["distance_m"] > 25.0

    # 4. Pause Session
    pause_resp = test_client.post(f"/api/session/{session_id}/pause", headers=headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["state"] == "PAUSED"

    # Samples while paused are rejected
    paused_sample_resp = test_client.post(
        f"/api/session/{session_id}/samples",
        json={"samples": [{"t": now, "lat": 13.0827, "lon": 80.2707, "accuracy_m": 4.0}]},
        headers=headers
    )
    assert paused_sample_resp.status_code == 200
    assert paused_sample_resp.json()["accepted_count"] == 0

    # 5. Resume Session
    resume_resp = test_client.post(f"/api/session/{session_id}/resume", headers=headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["state"] == "ACTIVE"

    # 6. End Session
    end_resp = test_client.post(f"/api/session/{session_id}/end", headers=headers)
    assert end_resp.status_code == 200
    assert end_resp.json()["state"] == "COMPLETED"
    assert end_resp.json()["ended_at"] is not None
