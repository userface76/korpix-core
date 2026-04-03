"""
KorPIX Policy Engine — FastAPI 서버

보안 적용:
  - API Key 인증 (X-KorPIX-API-Key 헤더)
  - Rate Limiting (slowapi, 60req/min)
  - CORS (허용 도메인 명시)
  - 운영 환경 Swagger UI 비활성화
  - 입력값 크기 제한 (Pydantic Field)
  - 운영 환경 기본 API 키 사용 차단

실행:
  uvicorn services.policy_engine.src.main:app --port 8001
"""
from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .models import ActionRequest, ActionType, UserPolicy
from .engine import PolicyEngine
from .decision import DecisionEngine, CircuitBreaker

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

# 운영 환경에서 기본 키 사용 차단
if _ENV == "production" and _RAW_KEYS == "dev-key-001":
    raise RuntimeError(
        "운영 환경에서 기본 API 키(dev-key-001)는 사용할 수 없습니다.\n"
        "API_KEYS 환경변수에 최소 32자 랜덤 키를 설정하세요."
    )

_VALID_KEYS: set[str] = set(k.strip() for k in _RAW_KEYS.split(",") if k.strip())


# ── FastAPI 앱 ───────────────────────────────────────────────────

app = FastAPI(
    title       = "KorPIX Policy Engine",
    version     = "0.1.1",
    description = "AI 행동 위험도 평가 및 승인 결정 API",
    docs_url    = "/docs"         if _ENV != "production" else None,
    redoc_url   = "/redoc"        if _ENV != "production" else None,
    openapi_url = "/openapi.json" if _ENV != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins     = _ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["GET", "POST"],
    allow_headers     = ["Authorization", "Content-Type", "X-KorPIX-API-Key"],
)

# Rate Limiting
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

_engine          = PolicyEngine()
_cb              = CircuitBreaker()
_decision_engine = DecisionEngine(circuit_breaker=_cb)


# ── 요청/응답 스키마 ─────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    request_id:  Optional[str] = Field(None,  max_length=64)
    action_type: str           = Field(...,   max_length=32)
    agent_id:    str           = Field(...,   max_length=64)
    user_id:     str           = Field(...,   max_length=128)
    terminal_id: str           = Field(...,   max_length=64)
    payload:     dict[str, Any]


class CircuitBreakerUpdate(BaseModel):
    vix:          float = Field(..., ge=0,    le=100)
    kospi_change: float = Field(..., ge=-1.0, le=1.0)


# ── 엔드포인트 ───────────────────────────────────────────────────

@app.get("/health", summary="헬스 체크 (인증 불필요)")
def health():
    return {
        "status":          "ok",
        "version":         "0.1.1",
        "env":             _ENV,
        "circuit_breaker": _cb.status,
    }


@app.post(
    "/evaluate",
    dependencies = [Depends(verify_api_key)],
    summary      = "AI 행동 요청 평가",
)
def evaluate(request: Request, req: EvaluateRequest):
    """
    AI 에이전트의 행동 요청을 평가하여 결정(decision)과 위험도(risk_score)를 반환합니다.

    Rate Limit : 60회/분 (IP 기준)
    인증       : X-KorPIX-API-Key 헤더 필수
    """
    if _HAS_SLOWAPI:
        limiter.limit("60/minute")(lambda: None)()

    try:
        action_type = ActionType(req.action_type)
    except ValueError:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = f"지원하지 않는 ActionType: {req.action_type}. "
                          f"허용 값: {[e.value for e in ActionType]}",
        )

    action = ActionRequest.new(
        action_type = action_type,
        agent_id    = req.agent_id,
        user_id     = req.user_id,
        terminal_id = req.terminal_id,
        payload     = req.payload,
    )
    if req.request_id:
        action.request_id = req.request_id

    policy_result   = _engine.evaluate(action)
    decision_result = _decision_engine.decide(action, policy_result)
    return decision_result.to_dict()


@app.post(
    "/circuit-breaker/check",
    dependencies = [Depends(verify_api_key)],
    summary      = "서킷 브레이커 확인 및 발동 (UC-002)",
)
def circuit_breaker_check(req: CircuitBreakerUpdate):
    triggered = _cb.check_and_trigger(req.vix, req.kospi_change)
    return {"triggered": triggered, "status": _cb.status}


@app.post(
    "/circuit-breaker/deactivate",
    dependencies = [Depends(verify_api_key)],
    summary      = "서킷 브레이커 수동 해제 (관리자 전용)",
)
def circuit_breaker_deactivate(user_id: str):
    success = _cb.deactivate(user_id=user_id, manual_confirm=True)
    return {"success": success, "status": _cb.status}
