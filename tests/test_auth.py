import pytest
from server.routers.auth import _rate_limit_records


def test_health_endpoint(test_client):
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["db_ok"] is True
    assert "version" in data
    assert "status" in data


def test_anonymous_auth_flow(test_client):
    _rate_limit_records.clear()
    resp = test_client.post("/api/auth/anon")
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "token" in data
    assert data["token"].startswith("tgt_")
    assert data["user_id"].startswith("usr_")


def test_unauthenticated_protected_route_rejection(test_client):
    _rate_limit_records.clear()

    # Missing token
    r1 = test_client.get("/api/auth/verify")
    assert r1.status_code == 401
    assert r1.json()["error_code"] == "AUTH_REQUIRED"

    # Bad token
    r2 = test_client.get("/api/auth/verify", headers={"Authorization": "Bearer fake_token"})
    assert r2.status_code == 401
    assert r2.json()["error_code"] == "INVALID_TOKEN"

    # Valid token
    auth_resp = test_client.post("/api/auth/anon").json()
    r3 = test_client.get("/api/auth/verify", headers={"Authorization": f"Bearer {auth_resp['token']}"})
    assert r3.status_code == 200
    assert r3.json()["user_id"] == auth_resp["user_id"]
