from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
 
 
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
    request_id:  str
    action_type: ActionType
    agent_id:    str
    user_id:     str
    terminal_id: str
    payload:     dict[str, Any]
    user_policy: UserPolicy
    timestamp:   str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
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
    approval_chain:    Any = None
    requires_notify:   bool = False
    notify_message:    Optional[str] = None
 
    def to_dict(self) -> dict:
        return {
            "decision":        self.decision.value,
            "riskScore":       self.risk_score,
            "riskDetails":     [
                {"factor": d.factor_name, "score": d.score_added, "reason": d.reason}
                for d in self.risk_details
            ],
            "reasons":         self.reasons,
            "requiresNotify":  self.requires_notify,
            "notifyMessage":   self.notify_message,
            "policyEngineVer": self.policy_engine_ver,
            "evaluatedAt":     self.evaluated_at,
        }
