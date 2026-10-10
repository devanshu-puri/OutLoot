import pytest


def test_register_login_and_profile_flow(test_client):
    # 1. Register a new user
    uname = "explorer_dev"
    reg_resp = test_client.post(
        "/api/auth/register",
        json={"username": uname, "password": "supersecretpassword", "display_name": "Dev Explorer"}
    )
    assert reg_resp.status_code == 200, reg_resp.text
    reg_data = reg_resp.json()
    assert reg_data["username"] == uname
    assert reg_data["display_name"] == "Dev Explorer"
    assert reg_data["token"].startswith("tgt_")
    token = reg_data["token"]
    user_id = reg_data["user_id"]

    # 2. Cannot register with duplicate username
    dup_resp = test_client.post(
        "/api/auth/register",
        json={"username": uname, "password": "anotherpassword"}
    )
    assert dup_resp.status_code == 400
    assert dup_resp.json()["error_code"] == "USERNAME_TAKEN"

    # 3. Login with correct password
    login_resp = test_client.post(
        "/api/auth/login",
        json={"username": uname, "password": "supersecretpassword"}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["user_id"] == user_id
    new_token = login_data["token"]

    # 4. Login with bad password fails
    bad_login = test_client.post(
        "/api/auth/login",
        json={"username": uname, "password": "wrongpassword"}
    )
    assert bad_login.status_code == 401

    # 5. Fetch profile & verify daily stats structure
    headers = {"Authorization": f"Bearer {new_token}"}
    prof_resp = test_client.get("/api/auth/profile", headers=headers)
    assert prof_resp.status_code == 200
    prof = prof_resp.json()
    assert prof["username"] == uname
    assert prof["display_name"] == "Dev Explorer"
    assert "today_stats" in prof
    assert prof["today_stats"]["points_collected"] == 0

    # 6. Update profile
    upd_resp = test_client.post(
        "/api/auth/profile/update",
        json={"display_name": "Master Walker", "avatar_emoji": "🦊", "bio": "Hunting rare relics"},
        headers=headers
    )
    assert upd_resp.status_code == 200
    updated_prof = upd_resp.json()
    assert updated_prof["display_name"] == "Master Walker"
    assert updated_prof["avatar_emoji"] == "🦊"
    assert updated_prof["bio"] == "Hunting rare relics"
