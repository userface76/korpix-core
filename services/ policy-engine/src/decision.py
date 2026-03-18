from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Optional
from .models import ActionRequest, ActionType, Decision, PolicyResult, RiskDetail
from .risk import PaymentEvaluator, InvestmentEvaluator, PurchaseEvaluator, CivicEvaluator, score_to_decision
 
_EVALUATORS = {
    ActionType.PAYMENT:          PaymentEvaluator(),
    ActionType.INVESTMENT:       InvestmentEvaluator(),
    ActionType.PURCHASE_REQUEST: PurchaseEvaluator(),
    ActionType.CIVIC_SERVICE:    CivicEvaluator(),
}
 
_AMOUNT_TIERS = [(1_000_000,1),(5_000_000,2),(20_000_000,3),(100_000_000,4)]
 
 
@dataclass
class ApprovalStep:
    step_id:     str  = field(default_factory=lambda: str(uuid.uuid4()))
    tier:        int  = 1
    approver_id: str  = ""
    role:        str  = ""
    status:      str  = "PENDING"
    parallel:    bool = False
    timeout_sec: int  = 86_400
 
 
@dataclass
class ApprovalChain:
    chain_id:     str  = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:   str  = ""
    tier:         int  = 1
    steps:        list = field(default_factory=list)
    is_fast_track:bool = False
 
    def is_complete(self) -> bool:
        return all(s.status == "APPROVED" for s in self.steps)
 
 
class CircuitBreaker:
    def __init__(self) -> None:
        self._triggered = False
 
    def check(self, vix: float, kospi_change: float) -> bool:
        if not self._triggered and (vix >= 35.0 or kospi_change <= -0.05):
            self._triggered = True
        return self._triggered
 
    def deactivate(self, manual_confirm: bool) -> bool:
        if not manual_confirm:
            return False
        self._triggered = False
        return True
 
    @property
    def is_triggered(self) -> bool:
        return self._triggered
 
 
class PolicyEngine:
    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None) -> None:
        self._cb = circuit_breaker or CircuitBreaker()
 
    def evaluate(self, req: ActionRequest) -> PolicyResult:
        ev = _EVALUATORS.get(req.action_type)
        if ev is None:
            raise ValueError(f"지원하지 않는 ActionType: {req.action_type}")
 
        if req.action_type == ActionType.INVESTMENT and self._cb.is_triggered:
            return PolicyResult(
                decision=Decision.DENY, risk_score=100, risk_details=[],
                reasons=["서킷 브레이커 발동 중"],
                requires_notify=True, notify_message="서킷 브레이커 발동 — 투자 차단"
            )
 
        score, details = ev.calculate(req)
        decision = score_to_decision(score)
        reasons  = [d.reason for d in details if d.score_added > 0]
        chain    = None
 
        if req.action_type == ActionType.PURCHASE_REQUEST:
            chain = self._build_chain(req, score)
            if chain.tier == 5:
                decision = Decision.DENY
                reasons.append("1억 초과 — 이사회 수동 이관")
 
        return PolicyResult(
            decision=decision, risk_score=score, risk_details=details,
            reasons=reasons, approval_chain=chain,
            requires_notify=(decision != Decision.AUTO_APPROVE),
        )
 
    @staticmethod
    def _build_chain(req: ActionRequest, score: int) -> ApprovalChain:
        amount    = int(req.payload.get("total_amount", 0))
        is_urgent = req.payload.get("urgency") == "URGENT"
        tier = 5
        for threshold, t in _AMOUNT_TIERS:
            if amount < threshold:
                tier = t
                break
        timeout = 7_200 if is_urgent else 86_400
        chain   = ApprovalChain(request_id=req.request_id, tier=tier, is_fast_track=is_urgent)
        if tier == 2:
            chain.steps.append(ApprovalStep(tier=2,approver_id="EMP-MGR",role="팀장",timeout_sec=timeout))
        elif tier == 3:
            chain.steps.append(ApprovalStep(tier=3,approver_id="EMP-MGR",role="팀장",  timeout_sec=timeout,parallel=is_urgent))
            chain.steps.append(ApprovalStep(tier=3,approver_id="EMP-FIN",role="재무팀",timeout_sec=timeout,parallel=is_urgent))
        elif tier == 4:
            chain.steps.append(ApprovalStep(tier=4,approver_id="EMP-MGR",role="팀장",  timeout_sec=timeout))
            chain.steps.append(ApprovalStep(tier=4,approver_id="EMP-FIN",role="재무팀",timeout_sec=timeout))
            chain.steps.append(ApprovalStep(tier=4,approver_id="EMP-CFO",role="CFO",   timeout_sec=172_800))
        return chain
 
