"""
KorPIX Execution Gateway
Policy Engine 승인 완료 행동을 외부 시스템에 실제 실행합니다.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExecutionRequest:
    exec_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    action_id:  str = ""
    action_type:str = ""
    payload:    dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)


@dataclass
class ExecutionResult:
    exec_id:       str
    action_id:     str
    status:        str        # SUCCESS | FAILED | PENDING
    response:      dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str]  = None
    executed_at:   str            = field(default_factory=_now)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class BaseConnector:
    """외부 시스템 연결 기반 클래스 — 실제 API로 교체"""
    name = "base"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class PaymentConnector(BaseConnector):
    """결제 API 연동 — Mock 구현"""
    name = "payment"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "receipt_id":   str(uuid.uuid4()),
            "service":      payload.get("service"),
            "amount":       payload.get("amount"),
            "status":       "PAID",
            "paid_at":      _now(),
        }


class InvestmentConnector(BaseConnector):
    """투자 API 연동 — Mock 구현 (가상 Sandbox)"""
    name = "investment"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "order_id":    str(uuid.uuid4()),
            "ticker":      payload.get("ticker"),
            "quantity":    payload.get("quantity"),
            "unit_price":  payload.get("unit_price"),
            "status":      "FILLED",
            "filled_at":   _now(),
        }


class ERPConnector(BaseConnector):
    """ERP API 연동 — Mock 구현"""
    name = "erp"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        po_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        return {
            "po_id":       po_id,
            "item_code":   payload.get("item_code"),
            "quantity":    payload.get("quantity"),
            "total":       payload.get("total_amount"),
            "status":      "CREATED",
            "created_at":  _now(),
        }


class GovAPIConnector(BaseConnector):
    """공공 API 연동 — Mock 구현 (정부24 Sandbox)"""
    name = "gov"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "receipt_number": f"GOV-{str(uuid.uuid4())[:8].upper()}",
            "service_code":   payload.get("service_code"),
            "agency_code":    payload.get("agency_code"),
            "status":         "SUCCESS",
            "processed_at":   _now(),
        }


# 커넥터 레지스트리
_CONNECTORS: dict[str, BaseConnector] = {
    "PAYMENT":          PaymentConnector(),
    "INVESTMENT":       InvestmentConnector(),
    "PURCHASE_REQUEST": ERPConnector(),
    "CIVIC_SERVICE":    GovAPIConnector(),
}


class ExecutionGateway:
    """
    KorPIX Execution Gateway.
    Policy Engine 승인 완료 후 적합한 외부 커넥터로 라우팅합니다.
    """

    def execute(self, req: ExecutionRequest) -> ExecutionResult:
        connector = _CONNECTORS.get(req.action_type.upper())
        if not connector:
            return ExecutionResult(
                exec_id=req.exec_id, action_id=req.action_id,
                status="FAILED",
                error_message=f"지원하지 않는 ActionType: {req.action_type}",
            )
        try:
            response = connector.execute(req.payload)
            return ExecutionResult(
                exec_id=req.exec_id, action_id=req.action_id,
                status="SUCCESS", response=response,
            )
        except Exception as e:
            return ExecutionResult(
                exec_id=req.exec_id, action_id=req.action_id,
                status="FAILED", error_message=str(e),
            )
