#!/usr/bin/env python3
"""
Simulates a walk by posting batches of GPS samples from sample_walk.json
to the running TG Trails server API.
"""
import json
import os
import sys
import time
from pathlib import Path
import httpx


def run_simulation(base_url: str = "http://127.0.0.1:8000", sample_file: str = "scripts/sample_walk.json"):
    print(f"Connecting to TG Trails at {base_url}...")
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Health check
    h_resp = client.get("/api/health")
    if h_resp.status_code != 200:
        print(f"Server health check failed: {h_resp.text}")
        sys.exit(1)
    print(f"Server healthy: {h_resp.json()}")

    # 2. Authenticate
    auth_resp = client.post("/api/auth/anon")
    auth_data = auth_resp.json()
    token = auth_data["token"]
    user_id = auth_data["user_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Authenticated as {user_id} ({auth_data['display_name']})")

    # 3. Read sample file
    sample_path = Path(sample_file)
    if not sample_path.is_absolute():
        sample_path = Path(__file__).resolve().parent.parent / sample_path

    with open(sample_path, "r", encoding="utf-8") as f:
        raw_samples = json.load(f)

    # 4. Start session
    first_pt = raw_samples[0]
    ses_resp = client.post(
        "/api/session/start",
        json={"display_name": "Simulated Explorer", "start_lat": first_pt["lat"], "start_lon": first_pt["lon"]},
        headers=headers
    )
    session_data = ses_resp.json()
    session_id = session_data["id"]
    print(f"Started session {session_id} (cycle required: {session_data['cycle_required_s']}s)")

    # 5. Stream samples in small batches aligned to real-time clock
    start_sim_time = time.time()
    t_offset = start_sim_time - raw_samples[0]["t"]

    batch_size = 2
    for i in range(0, len(raw_samples), batch_size):
        chunk = raw_samples[i:i + batch_size]
        payload = []
        for s in chunk:
            payload.append({
                "t": s["t"] + t_offset,
                "lat": s["lat"],
                "lon": s["lon"],
                "accuracy_m": s["accuracy_m"]
            })

        post_resp = client.post(
            f"/api/session/{session_id}/samples",
            json={"samples": payload},
            headers=headers
        )
        if post_resp.status_code == 200:
            res = post_resp.json()
            print(f"Batch {i//batch_size + 1}: accepted={res['accepted_count']}, rejected={len(res['rejected'])}, "
                  f"cycle_progress={res['cycle_progress_s']:.1f}s, dist={res['distance_m']:.1f}m, "
                  f"item_available={res['item_available']}")
        else:
            print(f"Batch {i//batch_size + 1} error: {post_resp.text}")

    print("Simulation stream complete.")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    run_simulation(url)
