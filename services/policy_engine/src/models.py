"""KorPIX Policy Engine — 공유 데이터 모델"""
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


class Decision(str, Enum):
    AUTO_APPROVE  = "AUTO_APPROVE"
    USER_CONFIRM  = "USER_CONFIRM"
    ADMIN_APPROVE = "ADMIN_APPROVE"
    DENY          = "DENY"


@dataclass
class UserPolicy:
    monthly_payment_limit:    int   = 1_000_000
    single_payment_limit:     int   = 500_000
    monthly_invest_limit:     int   = 5_000_000
    max_loss_rate:            float = 0.10
    max_sector_concentration: float = 0.35
    investor_risk_grade:      int   = 3
    auto_approve_threshold:   int   = 1_000_000
    civic_payment_limit:      int   = 500_000
    two_factor_required:      bool  = False
    policy_version:           str   = "0.1.0"


@dataclass
class ActionRequest:
    request_id:   str
    action_type:  ActionType
    agent_id:     str
    user_id:      str
    terminal_id:  str
    payload:      dict[str, Any]
    user_policy:  UserPolicy
    timestamp:    str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def new(
        cls,
        action_type:  ActionType,
        agent_id:     str,
        user_id:      str,
        terminal_id:  str,
        payload:      dict[str, Any],
        user_policy:  Optional[UserPolicy] = None,
    ) -> "ActionRequest":
        return cls(
            request_id  = str(uuid.uuid4()),
            action_type = action_type,
            agent_id    = agent_id,
            user_id     = user_id,
            terminal_id = terminal_id,
            payload     = payload,
            user_policy = user_policy or UserPolicy(),
        )


@dataclass
class RiskDetail:
    factor_name: str
    score_added: int
    reason:      str


@dataclass
class PolicyResult:
    decision:          Decision
    risk_score:        int
    risk_details:      list[RiskDetail]
    reasons:           list[str]
    policy_engine_ver: str = "0.1.0"
    evaluated_at:      str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "decision":          self.decision.value,
            "risk_score":        self.risk_score,
            "risk_details":      [
                {"factor": d.factor_name, "score": d.score_added, "reason": d.reason}
                for d in self.risk_details
            ],
            "reasons":           self.reasons,
            "policy_engine_ver": self.policy_engine_ver,
            "evaluated_at":      self.evaluated_at,
        }
