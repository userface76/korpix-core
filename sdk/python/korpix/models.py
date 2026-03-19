"""KorPIX Python SDK — 공개 데이터 모델"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class ActionType(str, Enum):
    PAYMENT          = "PAYMENT"
    INVESTMENT       = "INVESTMENT"
    PURCHASE_REQUEST = "PURCHASE_REQUEST"
    CIVIC_SERVICE    = "CIVIC_SERVICE"
    SYSTEM           = "SYSTEM"


class PolicyDecision(str, Enum):
    AUTO_APPROVE  = "AUTO_APPROVE"
    USER_CONFIRM  = "USER_CONFIRM"
    ADMIN_APPROVE = "ADMIN_APPROVE"
    DENY          = "DENY"


@dataclass
class UserPolicy:
    monthly_payment_limit: int   = 1_000_000
    single_payment_limit:  int   = 500_000
    monthly_invest_limit:  int   = 5_000_000
    max_loss_rate:         float = 0.10
    civic_payment_limit:   int   = 500_000
    policy_version:        str   = "0.1.0"


@dataclass
class ActionRequest:
    action_type: ActionType
    payload:     dict[str, Any]
    user_policy: Optional[UserPolicy] = None
    request_id:  str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:   str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "request_id":  self.request_id,
            "action_type": self.action_type.value,
            "payload":     self.payload,
            "timestamp":   self.timestamp,
        }


@dataclass
class PolicyResponse:
    decision:       PolicyDecision
    risk_score:     int
    reasons:        list[str]
    result_id:      str
    decided_at:     str
    approval_chain: Optional[dict] = None
    notify_message: Optional[str]  = None

    @classmethod
    def from_dict(cls, d: dict) -> "PolicyResponse":
        return cls(
            decision       = PolicyDecision(d["decision"]),
            risk_score     = d["risk_score"],
            reasons        = d.get("reasons", []),
            result_id      = d.get("result_id", ""),
            decided_at     = d.get("decided_at", ""),
            approval_chain = d.get("approval_chain"),
            notify_message = d.get("notify_message"),
        )
