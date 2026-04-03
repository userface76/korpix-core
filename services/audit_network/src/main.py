"""
KorPIX Audit Network — FastAPI 서버
실행: uvicorn services.audit_network.src.main:app --port 8002
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from .gateway import AuditGateway, make_terminal_log

import os
ENV = os.getenv("TERMINAL_ENV", "development")

app = FastAPI(
    title="KorPIX Policy Engine",
    version="0.1.0",
    # 운영 환경에서 Swagger/ReDoc 비활성화
    docs_url   = "/docs"   if ENV != "production" else None,
    redoc_url  = "/redoc"  if ENV != "production" else None,
    openapi_url= "/openapi.json" if ENV != "production" else None,
)
gateway = AuditGateway(gateway_id="gateway-001")


class SubmitLogRequest(BaseModel):
    action_record: dict[str, Any]


class QueryRequest(BaseModel):
    user_id_hash:    Optional[str] = None
    action_type:     Optional[str] = None
    policy_decision: Optional[str] = None
    page:            int = 1
    page_size:       int = 50


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.0",
            "ledger_count": gateway.ledger_count, "stats": gateway.stats}


@app.post("/submit")
def submit_log(req: SubmitLogRequest):
    entry  = make_terminal_log(req.action_record)
    result = gateway.process(entry)
    return {
        "log_id":     result.log_id,
        "status":     result.verification_status.value,
        "success":    result.success,
        "error":      result.error_detail,
        "normalized": result.normalized_record.to_dict()
                      if result.normalized_record else None,
    }


@app.post("/query")
def query(req: QueryRequest):
    return gateway.query(
        user_id_hash    = req.user_id_hash,
        action_type     = req.action_type,
        policy_decision = req.policy_decision,
        page            = req.page,
        page_size       = req.page_size,
    )


@app.get("/integrity")
def verify_integrity():
    is_valid, broken = gateway.verify_integrity()
    return {"is_valid": is_valid, "broken_at": broken,
            "ledger_count": gateway.ledger_count}


@app.get("/anomalies")
def get_anomalies(severity: Optional[str] = None):
    events = gateway.get_anomalies(severity=severity)
    return {"events": [e.to_dict() for e in events], "total": len(events)}


@app.post("/anomalies/{event_id}/resolve")
def resolve_anomaly(event_id: str):
    ok = gateway._detector.resolve(event_id)
    if not ok:
        raise HTTPException(404, f"이벤트를 찾을 수 없음: {event_id}")
    return {"resolved": True}


from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,   # 운영: ["https://korpix.dev"]
    allow_credentials = True,
    allow_methods     = ["GET", "POST"],
    allow_headers     = ["Authorization", "Content-Type", "X-Terminal-ID"],
)
