"""
KorPIX Execution Gateway — FastAPI 서버

보안 적용:
  - API Key 인증 (X-KorPIX-API-Key 헤더)
  - Rate Limiting (slowapi, 30req/min — 실제 실행은 빈도 낮음)
  - CORS (허용 도메인 명시)
  - 운영 환경 Swagger UI 비활성화
  - 운영 환경 기본 API 키 사용 차단

실행:
  uvicorn services.execution_gateway.src.main:app --port 8003
"""
from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .gateway import ExecutionGateway, ExecutionRequest

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

_SUPPORTED_TYPES = {"PAYMENT", "INVESTMENT", "PURCHASE_REQUEST", "CIVIC_SERVICE"}


# ── FastAPI 앱 ───────────────────────────────────────────────────

app = FastAPI(
    title       = "KorPIX Execution Gateway",
    version     = "0.1.1",
    description = "Policy Engine 승인 완료 행동을 외부 시스템에 실행하는 게이트웨이",
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

_gateway = ExecutionGateway()


# ── 요청/응답 스키마 ─────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    action_id:   str           = Field(..., max_length=64)
    action_type: str           = Field(..., max_length=32)
    payload:     dict[str, Any]


# ── 엔드포인트 ───────────────────────────────────────────────────

@app.get("/health", summary="헬스 체크 (인증 불필요)")
def health():
    return {
        "status":          "ok",
        "version":         "0.1.1",
        "env":             _ENV,
        "supported_types": sorted(_SUPPORTED_TYPES),
    }


@app.post(
    "/execute",
    dependencies = [Depends(verify_api_key)],
    summary      = "승인된 행동 실행",
)
def execute(request: Request, req: ExecuteRequest):
    """
    Policy Engine이 승인한 행동을 외부 시스템에 실제 실행합니다.

    주의: Policy Engine에서 AUTO_APPROVE 또는 승인 완료된 행동만 전달하세요.
          이 엔드포인트는 Policy Engine의 결정을 재검증하지 않습니다.

    Rate Limit : 30회/분 (IP 기준)
    인증       : X-KorPIX-API-Key 헤더 필수
    """
    if _HAS_SLOWAPI:
        limiter.limit("30/minute")(lambda: None)()

    if req.action_type.upper() not in _SUPPORTED_TYPES:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = f"지원하지 않는 ActionType: {req.action_type}. "
                          f"허용 값: {sorted(_SUPPORTED_TYPES)}",
        )

    result = _gateway.execute(ExecutionRequest(
        action_id   = req.action_id,
        action_type = req.action_type,
        payload     = req.payload,
    ))
    return result.to_dict()
