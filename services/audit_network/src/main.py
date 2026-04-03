"""
KorPIX Audit Network — FastAPI 서버

보안 적용:
  - API Key 인증 (X-KorPIX-API-Key 헤더)
  - Rate Limiting (slowapi, 120req/min — 감사 제출은 빈도 높음)
  - CORS (허용 도메인 명시)
  - 운영 환경 Swagger UI 비활성화
  - 운영 환경 기본 API 키 사용 차단

실행:
  uvicorn services.audit_network.src.main:app --port 8002
"""
from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .gateway import AuditGateway, make_terminal_log

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _HAS_SLOWAPI = True
except ImportError:
    _HAS_SLOWAPI = False


# ── 환경 변수 ────────────────────────────────────────────────────

_ENV             = os.getenv("TERMINAL_ENV",    "development")
_ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
).split(",")

_RAW_KEYS = os.getenv("API_KEYS", "dev-key-001")

if _ENV == "production" and _RAW_KEYS == "dev-key-001":
    raise RuntimeError(
        "운영 환경에서 기본 API 키(dev-key-001)는 사용할 수 없습니다.\n"
        "API_KEYS 환경변수에 최소 32자 랜덤 키를 설정하세요."
    )

_VALID_KEYS: set[str] = set(k.strip() for k in _RAW_KEYS.split(",") if k.strip())


# ── FastAPI 앱 ───────────────────────────────────────────────────

app = FastAPI(
    title       = "KorPIX Audit Network",
    version     = "0.3.1",
    description = "AI 행동 감사 기록 수집 · 검증 · 조회 API",
    docs_url    = "/docs"         if _ENV != "production" else None,
    redoc_url   = "/redoc"        if _ENV != "production" else None,
    openapi_url = "/openapi.json" if _ENV != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = _ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["GET", "POST"],
    allow_headers     = ["Authorization", "Content-Type", "X-KorPIX-API-Key"],
)

if _HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── 인증 ─────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-KorPIX-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    if not api_key or api_key not in _VALID_KEYS:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "유효하지 않은 API 키입니다. X-KorPIX-API-Key 헤더를 확인하세요.",
            headers     = {"WWW-Authenticate": "ApiKey"},
        )
    return api_key


# ── 서비스 인스턴스 ──────────────────────────────────────────────

_gateway = AuditGateway(gateway_id="gateway-001")


# ── 요청/응답 스키마 ─────────────────────────────────────────────

class SubmitLogRequest(BaseModel):
    action_record: dict[str, Any]


class QueryRequest(BaseModel):
    user_id_hash:    Optional[str] = Field(None, max_length=128)
    action_type:     Optional[str] = Field(None, max_length=32)
    policy_decision: Optional[str] = Field(None, max_length=32)
    page:            int           = Field(1,    ge=1)
    page_size:       int           = Field(50,   ge=1, le=200)


# ── 엔드포인트 ───────────────────────────────────────────────────

@app.get("/health", summary="헬스 체크 (인증 불필요)")
def health():
    return {
        "status":       "ok",
        "version":      "0.3.1",
        "env":          _ENV,
        "ledger_count": _gateway.ledger_count,
        "stats":        _gateway.stats,
    }


@app.post(
    "/submit",
    dependencies = [Depends(verify_api_key)],
    summary      = "감사 기록 제출",
)
def submit_log(request: Request, req: SubmitLogRequest):
    """
    Trust Terminal이 생성한 ActionRecord를 수신하여 검증 후 원장에 저장합니다.

    Rate Limit : 120회/분 (IP 기준)
    인증       : X-KorPIX-API-Key 헤더 필수
    """
    if _HAS_SLOWAPI:
        limiter.limit("120/minute")(lambda: None)()

    entry  = make_terminal_log(req.action_record)
    result = _gateway.process(entry)
    return {
        "log_id":     result.log_id,
        "status":     result.verification_status.value,
        "success":    result.success,
        "error":      result.error_detail,
        "normalized": result.normalized_record.to_dict()
                      if result.normalized_record else None,
    }


@app.post(
    "/query",
    dependencies = [Depends(verify_api_key)],
    summary      = "감사 기록 조회",
)
def query(req: QueryRequest):
    return _gateway.query(
        user_id_hash    = req.user_id_hash,
        action_type     = req.action_type,
        policy_decision = req.policy_decision,
        page            = req.page,
        page_size       = req.page_size,
    )


@app.get(
    "/integrity",
    dependencies = [Depends(verify_api_key)],
    summary      = "해시 체인 무결성 검증",
)
def verify_integrity():
    is_valid, broken = _gateway.verify_integrity()
    return {
        "is_valid":     is_valid,
        "broken_at":    broken,
        "ledger_count": _gateway.ledger_count,
    }


@app.get(
    "/anomalies",
    dependencies = [Depends(verify_api_key)],
    summary      = "이상 탐지 이벤트 조회",
)
def get_anomalies(severity: Optional[str] = None):
    events = _gateway.get_anomalies(severity=severity)
    return {"events": [e.to_dict() for e in events], "total": len(events)}


@app.post(
    "/anomalies/{event_id}/resolve",
    dependencies = [Depends(verify_api_key)],
    summary      = "이상 이벤트 해제",
)
def resolve_anomaly(event_id: str):
    ok = _gateway._detector.resolve(event_id)
    if not ok:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"이벤트를 찾을 수 없음: {event_id}",
        )
    return {"resolved": True}
