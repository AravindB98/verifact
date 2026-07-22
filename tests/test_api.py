import pytest
from fastapi.testclient import TestClient

from verifact.api.server import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "llm_configured" in body


def test_analyze_requires_exactly_one_input():
    assert client.post("/api/v1/analyze", json={}).status_code == 422
    assert (
        client.post("/api/v1/analyze", json={"url": "https://x.com", "text": "hi"}).status_code
        == 422
    )


def test_analyze_text_returns_report():
    text = (
        "The health ministry announced on Monday that cases rose 42 percent in 2025, "
        "according to official data. A spokesperson said vaccination coverage fell below "
        "80 percent in twelve districts. Officials confirmed the trend in a statement."
    )
    resp = client.post("/api/v1/analyze", json={"text": text})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] in {
        "high_credibility",
        "moderate_credibility",
        "low_credibility",
        "very_low_credibility",
        "insufficient_evidence",
    }
    assert isinstance(body["signals"], list) and body["signals"]
    assert body["disclaimer"]


def test_index_serves_web_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "VeriFact" in resp.text


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_api_docs_exposed(path):
    assert client.get(path).status_code == 200
