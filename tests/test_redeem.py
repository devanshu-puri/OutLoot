import pytest
from server.db import get_db, tx
from server.services.points import add_point_transaction


def test_marketplace_rewards_and_redemption_flow(test_client):
    auth = test_client.post("/api/auth/anon").json()
    headers = {"Authorization": f"Bearer {auth['token']}"}
    user_id = auth["user_id"]

    # 1. Fetch rewards list
    rewards_resp = test_client.get("/api/rewards")
    assert rewards_resp.status_code == 200
    rewards = rewards_resp.json()
    assert len(rewards) >= 3
    cheapest = rewards[0]
    reward_id = cheapest["id"]
    cost = cheapest["cost_points"]

    # 2. Attempt redemption with 0 balance -> 400 INSUFFICIENT_POINTS
    r_fail = test_client.post(
        f"/api/rewards/{reward_id}/redeem",
        json={"idempotency_key": "rdm_key_1"},
        headers=headers
    )
    assert r_fail.status_code == 400
    assert r_fail.json()["error_code"] == "INSUFFICIENT_POINTS"

    # 3. Grant points via admin adjustment
    admin_headers = {"X-Admin-Token": "dev_admin_secret_token_change_me"}
    adjust_resp = test_client.post(
        "/api/admin/adjust",
        json={"user_id": user_id, "delta": 500, "note": "Starter credit"},
        headers=admin_headers
    )
    assert adjust_resp.status_code == 200
    assert adjust_resp.json()["balance"] == 500

    # 4. Successful Redemption
    r_success = test_client.post(
        f"/api/rewards/{reward_id}/redeem",
        json={"idempotency_key": "rdm_key_1"},
        headers=headers
    )
    assert r_success.status_code == 200
    red_data = r_success.json()
    assert red_data["status"] == "CONFIRMED"
    assert red_data["cost_points"] == cost
    assert red_data["new_balance"] == 500 - cost
    assert red_data["code"].startswith("TG-")
    assert red_data["replayed"] is False

    # 5. Idempotency Replay with same key -> Returns existing redemption
    r_replay = test_client.post(
        f"/api/rewards/{reward_id}/redeem",
        json={"idempotency_key": "rdm_key_1"},
        headers=headers
    )
    assert r_replay.status_code == 200
    assert r_replay.json()["replayed"] is True
    assert r_replay.json()["code"] == red_data["code"]

    # 6. Verify Redemptions list endpoint
    list_resp = test_client.get("/api/redemptions", headers=headers)
    assert list_resp.status_code == 200
    user_reds = list_resp.json()
    assert len(user_reds) == 1
    assert user_reds[0]["code"] == red_data["code"]


def test_reward_out_of_stock_enforcement(test_client):
    auth = test_client.post("/api/auth/anon").json()
    headers = {"Authorization": f"Bearer {auth['token']}"}
    user_id = auth["user_id"]

    # Seed rewards first
    test_client.get("/api/rewards")

    # Give enough points
    admin_headers = {"X-Admin-Token": "dev_admin_secret_token_change_me"}
    test_client.post(
        "/api/admin/adjust",
        json={"user_id": user_id, "delta": 5000, "note": "Rich tester"},
        headers=admin_headers
    )

    # Set sticker pack stock to 1
    with get_db() as conn:
        with tx(conn):
            conn.execute("UPDATE rewards SET stock = 1 WHERE id = 'rew_sticker_pack';")

    # Redeem 1st time -> OK
    r1 = test_client.post(
        "/api/rewards/rew_sticker_pack/redeem",
        json={"idempotency_key": "stock_key_1"},
        headers=headers
    )
    assert r1.status_code == 200

    # Redeem 2nd time with different key -> 400 OUT_OF_STOCK
    r2 = test_client.post(
        "/api/rewards/rew_sticker_pack/redeem",
        json={"idempotency_key": "stock_key_2"},
        headers=headers
    )
    assert r2.status_code == 400
    assert r2.json()["error_code"] == "OUT_OF_STOCK"
