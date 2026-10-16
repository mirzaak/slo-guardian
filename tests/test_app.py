import pytest
from fastapi.testclient import TestClient

from app.main import app, member_ref


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CHAOS_ENABLED", "true")
    with TestClient(app) as c:
        yield c
        c.delete("/admin/chaos")


def test_probes(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200


def test_eligibility_pseudonymises_member_id(client):
    resp = client.get("/api/v1/members/M123456/eligibility")
    assert resp.status_code == 200
    body = resp.json()
    assert body["member_ref"] == member_ref("M123456")
    assert "M123456" not in resp.text


def test_unknown_member_is_404(client):
    assert client.get("/api/v1/members/bogus/eligibility").status_code == 404


def test_metrics_use_route_template_not_raw_path(client):
    client.get("/api/v1/members/M000001/eligibility")
    metrics = client.get("/metrics").text
    assert 'route="/api/v1/members/{member_id}/eligibility"' in metrics
    assert "M000001" not in metrics
    assert 'le="0.3"' in metrics  # latency SLO threshold must be a bucket boundary


def test_probe_traffic_excluded_from_sli(client):
    client.get("/healthz")
    assert 'route="/healthz"' not in client.get("/metrics").text


def test_chaos_injects_errors(client):
    assert client.put("/admin/chaos", json={"error_rate": 1.0}).status_code == 200
    assert client.get("/api/v1/plans").status_code == 503
    client.delete("/admin/chaos")
    assert client.get("/api/v1/plans").status_code == 200


def test_chaos_rejects_invalid_config(client):
    assert client.put("/admin/chaos", json={"error_rate": 2}).status_code == 422


def test_chaos_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CHAOS_ENABLED", raising=False)
    with TestClient(app) as c:
        assert c.put("/admin/chaos", json={"error_rate": 1.0}).status_code == 404
