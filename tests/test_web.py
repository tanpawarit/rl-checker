from fastapi.testclient import TestClient

from app import main
from app.web import routes
from tests.factories import finding, make_result

client = TestClient(main.app)

JPEG = ("ad.jpg", b"\xff\xd8\xff", "image/jpeg")


def test_index_serves_form():
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'hx-post="/check-ui"' in resp.text
    assert 'name="file"' in resp.text and 'name="text"' in resp.text


def test_static_served():
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/htmx.min.js").status_code == 200


def test_check_ui_renders_report(monkeypatch):
    # mock the brain at the single seam (run_check) — no real Gemini calls in tests
    result = make_result(
        findings=[
            finding("RL-2.1", "fail", "critical", issue="ไม่มีคำเตือน", fix_note="เพิ่มข้อความบังคับ"),
            finding("RL-3.1", "fail", "high", issue="วลีต้องห้าม", fix_note="ตัดวลี"),
            finding("RL-1.1", "review", "medium", issue="ภาพก้ำกึ่ง", fix_note="ปรับภาพ"),
            finding("RL-4.1", "pass", "low", fix_note="-"),
        ],
        manual=["วัดขนาดตัวอักษรบนสื่อจริง"],
    )
    monkeypatch.setattr(
        routes, "run_check", lambda data, mime="image/jpeg", text=None: (result, ["ธง-required-text"])
    )
    resp = client.post("/check-ui", files={"file": JPEG}, data={"text": "แคปชันทดสอบ"})
    assert resp.status_code == 200
    html = resp.text
    # every schema group must be rendered: fail/review/pass + manual + flags + saw
    assert "RL-2.1" in html and "RL-3.1" in html and "RL-1.1" in html and "RL-4.1" in html
    assert "ธง-required-text" in html
    assert "วัดขนาดตัวอักษรบนสื่อจริง" in html
    assert "กู้เท่าที่จำเป็นและชำระคืนไหว" in html  # text_verbatim from saw
    assert "data:image/jpeg;base64," in html  # the checked image embedded back into the report


def test_check_ui_sorts_fails_by_severity(monkeypatch):
    result = make_result(
        findings=[
            finding("RL-9.2", "fail", "low"),
            finding("RL-9.1", "fail", "critical"),
        ]
    )
    monkeypatch.setattr(routes, "run_check", lambda data, mime="image/jpeg", text=None: (result, []))
    html = client.post("/check-ui", files={"file": JPEG}).text
    assert html.index("RL-9.1") < html.index("RL-9.2")  # critical comes before low


def test_check_ui_renders_hotspots_for_boxed_findings(monkeypatch):
    result = make_result(
        findings=[
            finding("RL-2.1", "fail", "critical", box_2d=[880, 40, 990, 960]),
            finding("RL-1.1", "review", "medium"),  # no box → the card must not be interactive
        ]
    )
    monkeypatch.setattr(routes, "run_check", lambda data, mime="image/jpeg", text=None: (result, []))
    html = client.post("/check-ui", files={"file": JPEG}).text
    assert 'data-for="RL-2.1"' in html  # hotspot drawn on the image
    assert "top:88.0%" in html and "left:4.0%" in html  # box_2d 0-1000 → percent of the image
    assert 'data-fid="RL-2.1"' in html  # finding card ↔ hotspot linked
    assert 'data-fid="RL-1.1"' not in html


def test_check_ui_error_renders_error_partial(monkeypatch):
    def boom(data, mime="image/jpeg", text=None):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(routes, "run_check", boom)
    resp = client.post("/check-ui", files={"file": JPEG})
    assert resp.status_code == 200  # return 200 so HTMX swaps the error partial into the page
    assert "ตรวจไม่สำเร็จ" in resp.text
