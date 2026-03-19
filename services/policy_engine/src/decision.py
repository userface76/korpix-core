"""
KorPIX Policy Engine — Decision Engine
승인 체인 빌더 · 서킷 브레이커 · 에스컬레이션
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Callable
from .models import ActionRequest, ActionType, Decision, PolicyResult

TIMEOUT_NORMAL = 86_400
TIMEOUT_URGENT = 7_200
TIMEOUT_CFO    = 172_800

AMOUNT_TIERS = [
    (1_000_000,   1),
    (5_000_000,   2),
    (20_000_000,  3),
    (100_000_000, 4),
]

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApprovalStatus(str, Enum):
    PENDING   = "PENDING"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    TIMEOUT   = "TIMEOUT"
    ESCALATED = "ESCALATED"


@dataclass
class ApprovalStep:
    step_id:      str
    tier:         int
    approver_id:  str
    role:         str
    status:       ApprovalStatus = ApprovalStatus.PENDING
    parallel:     bool           = False
    timeout_sec:  int            = TIMEOUT_NORMAL
    created_at:   str = field(default_factory=_now)
    responded_at: Optional[str] = None
    comment:      Optional[str] = None

    def approve(self, approver_id: str, comment: str = "") -> None:
        self.status = ApprovalStatus.APPROVED
        self.responded_at = _now()
        self.comment = comment

    def reject(self, approver_id: str, comment: str = "") -> None:
        self.status = ApprovalStatus.REJECTED
        self.responded_at = _now()
        self.comment = comment


@dataclass
class ApprovalChain:
    chain_id:      str
    request_id:    str
    tier:          int
    steps:         list[ApprovalStep] = field(default_factory=list)
    is_fast_track: bool = False
    created_at:    str  = field(default_factory=_now)

    def is_complete(self) -> bool:
        return bool(self.steps) and all(
            s.status == ApprovalStatus.APPROVED for s in self.steps
        )

    def is_rejected(self) -> bool:
        return any(s.status == ApprovalStatus.REJECTED for s in self.steps)


@dataclass
class DecisionResult:
    result_id:       str
    request_id:      str
    decision:        Decision
    risk_score:      int
    reasons:         list[str]
    approval_chain:  Optional[ApprovalChain] = None
    requires_notify: bool = False
    notify_message:  Optional[str] = None
    engine_version:  str = "0.1.0"
    decided_at:      str = field(default_factory=_now)

    def to_dict(self) -> dict:
        d: dict = {
            "result_id":       self.result_id,
            "request_id":      self.request_id,
            "decision":        self.decision.value,
            "risk_score":      self.risk_score,
            "reasons":         self.reasons,
            "requires_notify": self.requires_notify,
            "notify_message":  self.notify_message,
            "engine_version":  self.engine_version,
            "decided_at":      self.decided_at,
        }
        if self.approval_chain:
            d["approval_chain"] = {
                "chain_id":      self.approval_chain.chain_id,
                "tier":          self.approval_chain.tier,
                "is_fast_track": self.approval_chain.is_fast_track,
                "steps": [
                    {"step_id": s.step_id, "tier": s.tier,
                     "approver_id": s.approver_id, "role": s.role,
                     "status": s.status.value, "parallel": s.parallel,
                     "timeout_sec": s.timeout_sec}
                    for s in self.approval_chain.steps
                ],
            }
        return d


@dataclass
class OrgMember:
    employee_id: str
    name:        str
    role:        str
    dept_id:     str
    deputy_id:   Optional[str] = None


class OrgChartAdapter:
    _members = {
        "EMP-001": OrgMember("EMP-001","김요청","구매담당자","DEPT-IT"),
        "EMP-010": OrgMember("EMP-010","이팀장","팀장","DEPT-IT","EMP-011"),
        "EMP-011": OrgMember("EMP-011","박대리","팀장대리","DEPT-IT"),
        "EMP-020": OrgMember("EMP-020","최재무","재무팀장","DEPT-FIN","EMP-021"),
        "EMP-021": OrgMember("EMP-021","한재무대","재무팀대리","DEPT-FIN"),
        "EMP-099": OrgMember("EMP-099","강CFO","CFO","DEPT-EXEC"),
    }
    _dept_mgr = {"DEPT-IT":"EMP-010","DEPT-MKT":"EMP-010","DEPT-OPS":"EMP-010"}

    def get_manager(self, emp_id: str) -> OrgMember:
        emp    = self._members.get(emp_id)
        dept   = emp.dept_id if emp else "DEPT-IT"
        mgr_id = self._dept_mgr.get(dept, "EMP-010")
        return self._members[mgr_id]

    def get_finance_approver(self, dept_id: str) -> OrgMember:
        return self._members["EMP-020"]

    def get_cfo(self) -> OrgMember:
        return self._members["EMP-099"]

    def get_deputy(self, emp_id: str) -> Optional[OrgMember]:
        emp = self._members.get(emp_id)
        if emp and emp.deputy_id:
            return self._members.get(emp.deputy_id)
        return None


class ApprovalChainBuilder:
    def __init__(self, org: OrgChartAdapter) -> None:
        self._org = org

    @staticmethod
    def _tier(amount: int) -> int:
        for threshold, t in AMOUNT_TIERS:
            if amount < threshold:
                return t
        return 5

    def build(self, req: ActionRequest, risk_score: int,
              is_urgent: bool = False) -> ApprovalChain:
        amount    = int(req.payload.get("total_amount", 0))
        requester = str(req.payload.get("requester_id", req.user_id))
        tier      = self._tier(amount)
        timeout   = TIMEOUT_URGENT if is_urgent else TIMEOUT_NORMAL
        chain     = ApprovalChain(chain_id=str(uuid.uuid4()),
                                  request_id=req.request_id,
                                  tier=tier, is_fast_track=is_urgent)

        if tier == 1:
            pass
        elif tier == 2:
            m = self._org.get_manager(requester)
            chain.steps.append(ApprovalStep(str(uuid.uuid4()),2,m.employee_id,"팀장",timeout_sec=timeout))
        elif tier == 3:
            m = self._org.get_manager(requester)
            f = self._org.get_finance_approver(str(req.payload.get("department_id","")))
            p = is_urgent
            chain.steps.append(ApprovalStep(str(uuid.uuid4()),3,m.employee_id,"팀장",timeout_sec=timeout,parallel=p))
            chain.steps.append(ApprovalStep(str(uuid.uuid4()),3,f.employee_id,"재무팀",timeout_sec=timeout,parallel=p))
        elif tier == 4:
            m   = self._org.get_manager(requester)
            f   = self._org.get_finance_approver(str(req.payload.get("department_id","")))
            cfo = self._org.get_cfo()
            for role, member, to in [("팀장",m,timeout),("재무팀",f,timeout),("CFO",cfo,TIMEOUT_CFO)]:
                chain.steps.append(ApprovalStep(str(uuid.uuid4()),4,member.employee_id,role,timeout_sec=to))
        return chain


class CircuitBreaker:
    def __init__(self) -> None:
        self._triggered = False
        self._reason: Optional[str] = None
        self._affected: set[str] = set()

    def check_and_trigger(self, vix: float, kospi_change: float) -> bool:
        if self._triggered:
            return True
        if vix >= 35.0 or kospi_change <= -0.05:
            self._triggered = True
            self._reason    = f"VIX={vix:.1f}, 코스피={kospi_change:.1%}"
        return self._triggered

    def deactivate(self, user_id: str, manual_confirm: bool) -> bool:
        if not manual_confirm:
            return False
        self._triggered = False
        self._reason    = None
        self._affected.discard(user_id)
        return True

    @property
    def is_triggered(self) -> bool:
        return self._triggered

    @property
    def status(self) -> dict:
        return {"triggered": self._triggered, "reason": self._reason,
                "affected_users": len(self._affected)}


class DecisionEngine:
    def __init__(
        self,
        org:             Optional[OrgChartAdapter] = None,
        circuit_breaker: Optional[CircuitBreaker]  = None,
        audit_fn:        Optional[Callable]        = None,
    ) -> None:
        self._org      = org or OrgChartAdapter()
        self._cb       = circuit_breaker or CircuitBreaker()
        self._builder  = ApprovalChainBuilder(self._org)
        self._audit_fn = audit_fn or (lambda e, d: None)
        self._chains:  dict[str, ApprovalChain] = {}

    def decide(self, req: ActionRequest, pr: PolicyResult) -> DecisionResult:
        # UC-002 서킷 브레이커 우선 확인
        if req.action_type == ActionType.INVESTMENT and self._cb.is_triggered:
            self._cb._affected.add(req.user_id)
            return self._mk(req, pr, override=Decision.DENY,
                            notify="서킷 브레이커 발동 중 — 투자 행동이 일시 차단됩니다.")

        d = pr.decision

        if d == Decision.AUTO_APPROVE:
            return self._mk(req, pr)

        if d == Decision.DENY:
            return self._mk(req, pr,
                            notify=f"행동이 차단됐습니다. 사유: {', '.join(pr.reasons)}")

        if req.action_type == ActionType.PURCHASE_REQUEST:
            is_urgent = req.payload.get("urgency") == "URGENT"
            chain     = self._builder.build(req, pr.risk_score, is_urgent)
            self._chains[chain.chain_id] = chain
            if chain.tier == 5:
                return self._mk(req, pr, override=Decision.DENY,
                                notify="1억원 초과 — 이사회 수동 결의 필요.", chain=chain)
            roles = [s.role for s in chain.steps]
            ft    = " (병렬 Fast-Track)" if chain.is_fast_track else ""
            return self._mk(req, pr, chain=chain,
                            notify=f"Tier {chain.tier} 승인 필요{ft} — {' → '.join(roles)}")

        return self._mk(req, pr,
                        notify=f"위험 점수 {pr.risk_score}점 — 확인이 필요합니다.")

    def process_approval(self, chain_id: str, step_id: str,
                         approver_id: str, approved: bool,
                         comment: str = "") -> dict:
        chain = self._chains.get(chain_id)
        if not chain:
            raise ValueError(f"체인을 찾을 수 없음: {chain_id}")
        step = next((s for s in chain.steps if s.step_id == step_id), None)
        if not step:
            raise ValueError(f"결재 단계를 찾을 수 없음: {step_id}")

        if approved:
            step.approve(approver_id, comment)
        else:
            step.reject(approver_id, comment)

        next_approver = next(
            (s.approver_id for s in chain.steps
             if s.status == ApprovalStatus.PENDING), None
        )
        return {"chain_complete": chain.is_complete(),
                "chain_rejected": chain.is_rejected(),
                "next_approver":  next_approver}

    def _mk(self, req, pr, override=None, notify=None, chain=None) -> DecisionResult:
        return DecisionResult(
            result_id       = str(uuid.uuid4()),
            request_id      = req.request_id,
            decision        = override or pr.decision,
            risk_score      = pr.risk_score,
            reasons         = pr.reasons,
            approval_chain  = chain,
            requires_notify = notify is not None,
            notify_message  = notify,
        )
