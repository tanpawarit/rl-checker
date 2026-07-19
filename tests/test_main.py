from fastapi.testclient import TestClient

from app import main
from tests.factories import make_result

client = TestClient(main.app)


def test_healthz():
    assert client.get("/healthz").json() == {"ok": True}


def test_check_returns_contract(monkeypatch):
    # mock the brain at the single seam (run_check) — no real Gemini calls in tests
    monkeypatch.setattr(
        main, "run_check", lambda data, mime="image/jpeg", text=None: (make_result(), ["flag-x"])
    )
    resp = client.post("/check", files={"file": ("ad.jpg", b"\xff\xd8\xff", "image/jpeg")})
    assert resp.status_code == 200
    body = resp.json()
    # /check returns the neutral contract (§1.7) — rendering is the front-end's job
    assert body["flags"] == ["flag-x"]
    assert body["result"]["saw"]["products_mentioned"]
    assert body["result"]["findings"][0]["rule_id"] == "RL-2.1"
