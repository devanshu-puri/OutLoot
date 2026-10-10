import pytest


def test_screentime_heartbeat_and_touch_grass_alert(test_client):
    auth = test_client.post("/api/auth/anon").json()
    headers = {"Authorization": f"Bearer {auth['token']}"}

    # Set a 1-minute threshold for easy testing
    test_client.post("/api/screentime/threshold", json={"threshold_minutes": 1}, headers=headers)

    # 1. First heartbeat with 30s active -> No alert yet
    r1 = test_client.post("/api/screentime/heartbeat", json={"active_s": 30.0, "idle_s": 0.0}, headers=headers)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["screen_time_total_s"] == 30.0
    assert d1["current_screen_streak_s"] == 30.0
    assert d1["touch_grass_alert"] is False

    # 2. Second heartbeat with 40s active -> total streak 70s > 60s threshold -> ALERT!
    r2 = test_client.post("/api/screentime/heartbeat", json={"active_s": 40.0, "idle_s": 0.0}, headers=headers)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["screen_time_total_s"] == 70.0
    assert d2["current_screen_streak_s"] == 70.0
    assert d2["touch_grass_alert"] is True
    assert d2["grass_debt_minutes"] > 0
    assert "Touch Grass Alert" in d2["message"]


def test_digital_wellbeing_import(test_client):
    auth = test_client.post("/api/auth/anon").json()
    headers = {"Authorization": f"Bearer {auth['token']}"}

    # Import 4.5 hours of daily screen time
    r = test_client.post(
        "/api/screentime/import",
        json={"daily_screen_hours": 4.5, "device_label": "Pixel 8 Digital Wellbeing"},
        headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported_hours"] == 4.5
    assert data["grass_debt_minutes"] > 30.0
    assert "Pixel 8" in data["message"]


def test_friends_and_live_leaderboard(test_client):
    auth = test_client.post("/api/auth/anon").json()
    headers = {"Authorization": f"Bearer {auth['token']}"}
    user_id = auth["user_id"]

    # 1. Fetch live leaderboard
    lb_resp = test_client.get("/api/leaderboard", headers=headers)
    assert lb_resp.status_code == 200
    lb = lb_resp.json()
    assert len(lb["leaderboard"]) >= 2
    assert lb["user_rank"] >= 1

    # 2. Add friend "Maya Stride" by display name
    add_resp = test_client.post("/api/friends/add", json={"friend_code_or_name": "Maya Stride"}, headers=headers)
    assert add_resp.status_code == 200
    f_data = add_resp.json()
    assert f_data["display_name"] == "Maya Stride"

    # 3. List friends
    friends_resp = test_client.get("/api/friends", headers=headers)
    assert friends_resp.status_code == 200
    friends_list = friends_resp.json()
    assert any(f["display_name"] == "Maya Stride" for f in friends_list)

    # 4. Send friend nudge
    nudge_resp = test_client.post(
        "/api/friends/nudge",
        json={"friend_id": f_data["user_id"], "message": "Come join me on the park trail!"},
        headers=headers
    )
    assert nudge_resp.status_code == 200
    assert nudge_resp.json()["status"] == "sent"

    # 5. Follow another player
    follow_resp = test_client.post(f"/api/friends/follow/{f_data['user_id']}", headers=headers)
    assert follow_resp.status_code == 200
    assert follow_resp.json()["is_following"] is True

    # 6. Unfollow player
    unfollow_resp = test_client.post(f"/api/friends/unfollow/{f_data['user_id']}", headers=headers)
    assert unfollow_resp.status_code == 200
    assert unfollow_resp.json()["is_following"] is False

    # 7. Inspect player's track
    track_resp = test_client.get(f"/api/social/track/{f_data['user_id']}", headers=headers)
    assert track_resp.status_code == 200
    track_data = track_resp.json()
    assert track_data["user_id"] == f_data["user_id"]
    assert len(track_data["points"]) >= 2
    assert "distance_m" in track_data
