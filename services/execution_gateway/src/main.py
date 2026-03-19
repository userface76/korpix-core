"""
KorPIX Execution Gateway — FastAPI 서버
실행: uvicorn services.execution_gateway.src.main:app --port 8003
"""
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Optional

from .gateway import ExecutionGateway, ExecutionRequest

app     = FastAPI(title="KorPIX Execution Gateway", version="0.1.0")
gateway = ExecutionGateway()


class ExecuteRequest(BaseModel):
    action_id:   str
    action_type: str
    payload:     dict[str, Any]


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0",
            "supported_types": ["PAYMENT","INVESTMENT","PURCHASE_REQUEST","CIVIC_SERVICE"]}


@app.post("/execute")
def execute(req: ExecuteRequest):
    result = gateway.execute(ExecutionRequest(
        action_id   = req.action_id,
        action_type = req.action_type,
        payload     = req.payload,
    ))
    return result.to_dict()
