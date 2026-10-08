"""Contratalupa HTTP API."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .service import ContractService

app = FastAPI(
    title="Contratalupa",
    version="1.0.0",
    summary="LLM-assisted contract-clause analysis and risk flagging.",
)

_service: ContractService | None = None


def get_service() -> ContractService:
    global _service
    if _service is None:
        _service = ContractService()
    return _service


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", tags=["analysis"])
def analyze(request: AnalyzeRequest) -> dict:
    return get_service().analyze_as_dict(request.text)
