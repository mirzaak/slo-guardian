from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").status_code == 200


def test_eligibility():
    response = client.get("/api/v1/members/M123456/eligibility")
    assert response.status_code == 200
    assert response.json()["plan"] in ["PPO-GOLD", "HMO-SILVER", "HDHP-BRONZE"]


def test_unknown_member():
    assert client.get("/api/v1/members/abc/eligibility").status_code == 404


def test_metrics_do_not_contain_member_ids():
    client.get("/api/v1/members/M000001/eligibility")
    metrics = client.get("/metrics").text
    assert 'route="/api/v1/members/{member_id}/eligibility"' in metrics
    assert "M000001" not in metrics


def test_chaos(monkeypatch):
    monkeypatch.setenv("CHAOS_ENABLED", "true")
    client.put("/chaos", json={"error_rate": 1})
    assert client.get("/api/v1/plans").status_code == 503
    client.put("/chaos", json={"error_rate": 0})
    assert client.get("/api/v1/plans").status_code == 200


def test_chaos_disabled_by_default():
    assert client.put("/chaos", json={"error_rate": 1}).status_code == 404
