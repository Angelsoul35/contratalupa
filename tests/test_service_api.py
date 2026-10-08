from __future__ import annotations

from fastapi.testclient import TestClient

from contratalupa.config import Settings
from contratalupa.llm.fake import FakeLLM
from contratalupa.samples import SAMPLE_CONTRACT
from contratalupa.service import ContractService


def _service() -> ContractService:
    # Heuristic-only service (no network): pass a failing-free fake that never
    # returns JSON, so every clause falls back to deterministic heuristics.
    return ContractService(settings=Settings(), llm=FakeLLM("no json here"))


def test_service_analyze_as_dict():
    result = _service().analyze_as_dict(SAMPLE_CONTRACT)
    assert result["overall_risk"] == "high"
    assert "data_protection" in result["missing_clauses"]
    assert all("clause_type" in c for c in result["clauses"])
    assert all(c["source"] == "heuristic" for c in result["clauses"])


def test_api_health_and_analyze():
    import contratalupa.main as main

    main._service = _service()
    client = TestClient(main.app)

    assert client.get("/health").json() == {"status": "ok"}

    resp = client.post("/analyze", json={"text": SAMPLE_CONTRACT})
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_risk"] == "high"
    assert len(body["clauses"]) >= 8


def test_api_rejects_empty_text():
    import contratalupa.main as main

    main._service = _service()
    client = TestClient(main.app)
    assert client.post("/analyze", json={"text": ""}).status_code == 422
