"""
KorPIX Policy Engine — Decision Engine
========================================
Version:  0.1.0
Spec:     KorPIX Architecture Whitepaper §7, §8

Decision Engine은 Risk Evaluator가 계산한 Risk Score를
받아서 실제 '결정'을 실행하는 오케스트레이터입니다.

역할:
    1. Risk Score → Decision 변환
    2. UC-003 승인 체인 자동 빌드 (조직도 기반)
    3. 타임아웃 에스컬레이션 관리
    4. 긴급 Fast-Track 처리
    5. 서킷 브레이커 전역 발동/해제
    6. 결정 이벤트 Audit Network 전달

흐름:
    ActionRequest
        → RiskEvaluator.evaluate()      risk-evaluator.py
        → DecisionEngine.decide()       ← 이 파일
            → ApprovalChainBuilder      (UC-003 전용)
            → CircuitBreaker            (UC-002 전용)
            → EscalationManager         (타임아웃 처리)
        → DecisionResult                반환
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Callable

# risk-evaluator 임포트
from risk_evaluator import (
    ActionRequest, ActionType, Decision,
    PolicyResult, UserPolicy,
    PolicyEngine, build_action_record,
)


# ══════════════════════════════════════════════════════════════
#  상수 & 설정
# ══════════════════════════════════════════════════════════════

DECISION_ENGINE_VERSION = "0.1.0"

# 타임아웃 (초) — 결재자가 응답하지 않으면 에스컬레이션
TIMEOUT_NORMAL_SEC  = 86_400   # 24시간 (일반 결재)
TIMEOUT_URGENT_SEC  = 7_200    # 2시간  (긴급 Fast-Track)
TIMEOUT_CFO_SEC     = 172_800  # 48시간 (CFO 결재)

# UC-003 승인 티어별 금액 기준 (KRW)
TIER_THRESHOLDS = [
    (1_000_000,   1),   # 100만 미만    → Tier 1 자동
    (5_000_000,   2),   # 500만 미만    → Tier 2 팀장
    (20_000_000,  3),   # 2,000만 미만  → Tier 3 팀장+재무
    (100_000_000, 4),   # 1억 미만      → Tier 4 CFO
]


# ══════════════════════════════════════════════════════════════
#  데이터 클래스
# ══════════════════════════════════════════════════════════════

class ApprovalStatus(str, Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT  = "TIMEOUT"
    ESCALATED= "ESCALATED"


@dataclass
class ApprovalStep:
    """결재 체인의 단일 단계"""
    step_id:      str
    tier:         int
    approver_id:  str
    role:         str                     # '팀장' | '재무팀' | 'CFO' | '이사회'
    status:       ApprovalStatus = ApprovalStatus.PENDING
    parallel:     bool           = False  # True이면 다른 단계와 동시 진행
    timeout_sec:  int            = TIMEOUT_NORMAL_SEC
    created_at:   str            = field(default_factory=lambda: _now())
    responded_at: Optional[str]  = None
    signature:    Optional[str]  = None
    comment:      Optional[str]  = None

    def is_expired(self) -> bool:
        """타임아웃 여부 확인"""
        if self.status != ApprovalStatus.PENDING:
            return False
        created = datetime.fromisoformat(self.created_at)
        return (datetime.now(timezone.utc) - created).total_seconds() > self.timeout_sec

    def approve(self, approver_id: str, comment: str = "") -> None:
        self.status       = ApprovalStatus.APPROVED
        self.responded_at = _now()
        self.signature    = _soft_sign(f"{self.step_id}:{approver_id}:APPROVED")
        self.comment      = comment

    def reject(self, approver_id: str, comment: str = "") -> None:
        self.status       = ApprovalStatus.REJECTED
        self.responded_at = _now()
        self.comment      = comment


@dataclass
class ApprovalChain:
    """UC-003 구매 승인 전체 체인"""
    chain_id:     str
    request_id:   str
    tier:         int
    steps:        list[ApprovalStep] = field(default_factory=list)
    is_fast_track:bool               = False
    created_at:   str                = field(default_factory=lambda: _now())

    def is_complete(self) -> bool:
        """모든 필수 단계가 승인됐는지 확인"""
        required = [s for s in self.steps if not s.parallel or
                    all(other.parallel for other in self.steps)]
        return all(s.status == ApprovalStatus.APPROVED for s in required)

    def is_rejected(self) -> bool:
        return any(s.status == ApprovalStatus.REJECTED for s in self.steps)

    def pending_steps(self) -> list[ApprovalStep]:
        return [s for s in self.steps if s.status == ApprovalStatus.PENDING]

    def expired_steps(self) -> list[ApprovalStep]:
        return [s for s in self.steps if s.is_expired()]


@dataclass
class DecisionResult:
    """Decision Engine 최종 출력"""
    result_id:         str
    request_id:        str
    decision:          Decision
    risk_score:        int
    reasons:           list[str]

    # 추가 조치 필요 시
    approval_chain:    Optional[ApprovalChain] = None  # UC-003
    requires_notify:   bool                    = False  # 사용자 알림 필요
    notify_message:    Optional[str]           = None

    # 메타
    engine_version:    str = DECISION_ENGINE_VERSION
    decided_at:        str = field(default_factory=lambda: _now())

    def to_dict(self) -> dict:
        d = {
            "result_id":      self.result_id,
            "request_id":     self.request_id,
            "decision":       self.decision.value,
            "risk_score":     self.risk_score,
            "reasons":        self.reasons,
            "requires_notify":self.requires_notify,
            "notify_message": self.notify_message,
            "engine_version": self.engine_version,
            "decided_at":     self.decided_at,
        }
        if self.approval_chain:
            d["approval_chain"] = {
                "chain_id":    self.approval_chain.chain_id,
                "tier":        self.approval_chain.tier,
                "is_fast_track":self.approval_chain.is_fast_track,
                "steps": [
                    {
                        "step_id":    s.step_id,
                        "tier":       s.tier,
                        "approver_id":s.approver_id,
                        "role":       s.role,
                        "status":     s.status.value,
                        "parallel":   s.parallel,
                        "timeout_sec":s.timeout_sec,
                    }
                    for s in self.approval_chain.steps
                ],
            }
        return d


# ══════════════════════════════════════════════════════════════
#  조직도 어댑터 (실제 환경에서는 ERP/HR 시스템으로 교체)
# ══════════════════════════════════════════════════════════════

@dataclass
class OrgMember:
    employee_id: str
    name:        str
    role:        str
    dept_id:     str
    deputy_id:   Optional[str] = None   # 부재 시 대리자


class OrgChartAdapter:
    """
    조직도 어댑터.
    실제 환경에서는 ERP / HR 시스템 API로 교체하세요.
    """

    # 테스트용 더미 조직도
    _members: dict[str, OrgMember] = {
        "EMP-001": OrgMember("EMP-001", "김요청",  "구매담당자",  "DEPT-IT",  None),
        "EMP-010": OrgMember("EMP-010", "이팀장",  "팀장",        "DEPT-IT",  "EMP-011"),
        "EMP-011": OrgMember("EMP-011", "박대리팀","팀장대리",    "DEPT-IT",  None),
        "EMP-020": OrgMember("EMP-020", "최재무",  "재무팀장",    "DEPT-FIN", "EMP-021"),
        "EMP-021": OrgMember("EMP-021", "한재무대","재무팀대리",  "DEPT-FIN", None),
        "EMP-099": OrgMember("EMP-099", "강CFO",   "CFO",         "DEPT-EXEC",None),
    }

    # 부서 → 팀장 매핑
    _dept_manager: dict[str, str] = {
        "DEPT-IT":  "EMP-010",
        "DEPT-MKT": "EMP-010",
        "DEPT-OPS": "EMP-010",
    }

    def get_manager(self, employee_id: str) -> OrgMember:
        emp    = self._members.get(employee_id)
        dept   = emp.dept_id if emp else "DEPT-IT"
        mgr_id = self._dept_manager.get(dept, "EMP-010")
        return self._members[mgr_id]

    def get_finance_approver(self, dept_id: str) -> OrgMember:
        return self._members["EMP-020"]

    def get_cfo(self) -> OrgMember:
        return self._members["EMP-099"]

    def get_deputy(self, employee_id: str) -> Optional[OrgMember]:
        emp = self._members.get(employee_id)
        if emp and emp.deputy_id:
            return self._members.get(emp.deputy_id)
        return None


# ══════════════════════════════════════════════════════════════
#  서킷 브레이커 (UC-002 투자 전용)
# ══════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    시장 급락 시 모든 AI 투자 행동을 전역 차단합니다.
    VIX ≥ 35 또는 코스피 일간 -5% 이상 하락 시 발동.
    해제는 반드시 사용자 수동 확인이 필요합니다.
    """

    def __init__(self) -> None:
        self._triggered:   bool          = False
        self._triggered_at:Optional[str] = None
        self._reason:      Optional[str] = None
        # 발동된 사용자 목록 (실제 환경에서는 DB로 관리)
        self._affected_users: set[str]   = set()

    def check_and_trigger(self, vix: float, kospi_change: float) -> bool:
        """
        시장 상태를 확인하고 필요 시 서킷 브레이커를 발동합니다.

        Returns:
            True이면 서킷 브레이커가 발동(또는 이미 발동) 상태
        """
        if self._triggered:
            return True

        should_trigger = (vix >= 35.0 or kospi_change <= -0.05)
        if should_trigger:
            self._triggered    = True
            self._triggered_at = _now()
            self._reason       = (
                f"서킷 브레이커 발동 — VIX={vix:.1f}, "
                f"코스피={kospi_change:.1%}"
            )
            print(f"[CircuitBreaker] ⚡ {self._reason}")
        return self._triggered

    def deactivate(self, user_id: str, manual_confirm: bool) -> bool:
        """
        서킷 브레이커를 해제합니다.
        반드시 manual_confirm=True여야 합니다.

        Returns:
            True이면 해제 성공
        """
        if not manual_confirm:
            print("[CircuitBreaker] ❌ 수동 확인 없이 해제 불가")
            return False
        self._triggered      = False
        self._triggered_at   = None
        self._reason         = None
        self._affected_users.discard(user_id)
        print(f"[CircuitBreaker] ✅ {user_id} 에 의해 수동 해제됨")
        return True

    def add_affected_user(self, user_id: str) -> None:
        self._affected_users.add(user_id)

    @property
    def is_triggered(self) -> bool:
        return self._triggered

    @property
    def status(self) -> dict:
        return {
            "triggered":       self._triggered,
            "triggered_at":    self._triggered_at,
            "reason":          self._reason,
            "affected_users":  len(self._affected_users),
        }


# ══════════════════════════════════════════════════════════════
#  승인 체인 빌더 (UC-003 기업 구매 전용)
# ══════════════════════════════════════════════════════════════

class ApprovalChainBuilder:
    """
    Policy Engine의 결정(Tier)에 따라
    실제 결재자 목록과 순서를 자동으로 구성합니다.

    Tier 1  → 자동 승인 (체인 없음)
    Tier 2  → 팀장만
    Tier 3  → 팀장 → 재무팀  (긴급 시 병렬)
    Tier 4  → 팀장 → 재무팀 → CFO
    Tier 5  → DENY (이사회 수동 이관)
    """

    def __init__(self, org: OrgChartAdapter) -> None:
        self._org = org

    @staticmethod
    def _amount_to_tier(amount: int) -> int:
        for threshold, tier in TIER_THRESHOLDS:
            if amount < threshold:
                return tier
        return 5   # 1억 이상 → Tier 5 DENY

    def build(
        self,
        request:    ActionRequest,
        risk_score: int,
        is_urgent:  bool = False,
    ) -> ApprovalChain:
        """
        ActionRequest를 분석하여 ApprovalChain을 생성합니다.

        Args:
            request:    평가된 ActionRequest
            risk_score: Risk Evaluator의 Risk Score
            is_urgent:  긴급 구매 여부 (Fast-Track 활성화)

        Returns:
            ApprovalChain — 결재 단계 목록 포함
        """
        payload    = request.payload
        amount     = int(payload.get("total_amount", 0))
        requester  = str(payload.get("requester_id", request.user_id))
        tier       = self._amount_to_tier(amount)
        timeout    = TIMEOUT_URGENT_SEC if is_urgent else TIMEOUT_NORMAL_SEC

        chain = ApprovalChain(
            chain_id=str(uuid.uuid4()),
            request_id=request.request_id,
            tier=tier,
            is_fast_track=is_urgent,
        )

        if tier == 1:
            # 자동 승인 — 체인 불필요
            pass

        elif tier == 2:
            # 팀장 단독
            manager = self._org.get_manager(requester)
            chain.steps.append(self._make_step(2, manager, "팀장", timeout))

        elif tier == 3:
            # 팀장 → 재무팀 (긴급 시 병렬)
            manager = self._org.get_manager(requester)
            finance = self._org.get_finance_approver(
                str(payload.get("department_id", ""))
            )
            if is_urgent:
                # 병렬 결재 — 두 결재자에게 동시에 알림
                chain.steps.append(
                    self._make_step(3, manager, "팀장", timeout, parallel=True)
                )
                chain.steps.append(
                    self._make_step(3, finance, "재무팀", timeout, parallel=True)
                )
            else:
                # 직렬 결재 — 팀장 승인 후 재무팀
                chain.steps.append(self._make_step(3, manager, "팀장", timeout))
                chain.steps.append(self._make_step(3, finance, "재무팀", timeout))

        elif tier == 4:
            # 팀장 → 재무팀 → CFO (직렬)
            manager = self._org.get_manager(requester)
            finance = self._org.get_finance_approver(
                str(payload.get("department_id", ""))
            )
            cfo = self._org.get_cfo()
            chain.steps.append(self._make_step(4, manager, "팀장",   timeout))
            chain.steps.append(self._make_step(4, finance, "재무팀", timeout))
            chain.steps.append(self._make_step(4, cfo,     "CFO",    TIMEOUT_CFO_SEC))

        # Tier 5는 DENY — 체인을 만들지 않음

        return chain

    @staticmethod
    def _make_step(
        tier:      int,
        member:    OrgMember,
        role:      str,
        timeout:   int,
        parallel:  bool = False,
    ) -> ApprovalStep:
        return ApprovalStep(
            step_id=str(uuid.uuid4()),
            tier=tier,
            approver_id=member.employee_id,
            role=role,
            timeout_sec=timeout,
            parallel=parallel,
        )


# ══════════════════════════════════════════════════════════════
#  에스컬레이션 매니저
# ══════════════════════════════════════════════════════════════

class EscalationManager:
    """
    결재 타임아웃 발생 시 대리 결재자에게 자동 에스컬레이션합니다.

    처리 흐름:
        check_timeouts() 호출
        → 만료된 step 탐지
        → OrgChart에서 대리자 조회
        → 새로운 ApprovalStep 추가 (에스컬레이션 표시)
        → Audit Network에 TIMEOUT 이벤트 기록
    """

    def __init__(
        self,
        org:          OrgChartAdapter,
        audit_fn:     Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self._org      = org
        self._audit_fn = audit_fn or (lambda event, data: None)

    def check_timeouts(self, chain: ApprovalChain) -> list[ApprovalStep]:
        """
        체인 내 타임아웃된 단계를 처리합니다.

        Returns:
            새로 추가된 에스컬레이션 ApprovalStep 목록
        """
        escalated: list[ApprovalStep] = []

        for step in chain.expired_steps():
            step.status = ApprovalStatus.TIMEOUT
            deputy = self._org.get_deputy(step.approver_id)

            if deputy:
                new_step = ApprovalStep(
                    step_id=str(uuid.uuid4()),
                    tier=step.tier,
                    approver_id=deputy.employee_id,
                    role=f"{step.role}(에스컬레이션)",
                    timeout_sec=step.timeout_sec,
                    parallel=step.parallel,
                )
                chain.steps.append(new_step)
                escalated.append(new_step)

                print(
                    f"[Escalation] ⏰ {step.role}({step.approver_id}) 타임아웃 "
                    f"→ {deputy.name}({deputy.employee_id}) 에스컬레이션"
                )

                # 감사 기록
                self._audit_fn("APPROVAL_TIMEOUT_ESCALATION", {
                    "chain_id":        chain.chain_id,
                    "original_step":   step.step_id,
                    "original_approver": step.approver_id,
                    "escalated_to":    deputy.employee_id,
                    "occurred_at":     _now(),
                })
            else:
                print(
                    f"[Escalation] ⚠️  {step.role}({step.approver_id}) 타임아웃 "
                    f"— 대리자 없음, 관리자 수동 처리 필요"
                )

        return escalated


# ══════════════════════════════════════════════════════════════
#  메인 Decision Engine
# ══════════════════════════════════════════════════════════════

class DecisionEngine:
    """
    KorPIX Policy Engine Decision Engine.

    Risk Evaluator의 PolicyResult를 받아서
    실제 실행 결정(DecisionResult)을 만들어 반환합니다.

    UC별 추가 처리:
        UC-002 투자   → 서킷 브레이커 확인
        UC-003 구매   → 승인 체인 빌드
        공통          → 타임아웃 에스컬레이션 관리
    """

    def __init__(
        self,
        org:         Optional[OrgChartAdapter]   = None,
        circuit_breaker: Optional[CircuitBreaker]= None,
        audit_fn:    Optional[Callable]          = None,
    ) -> None:
        self._org             = org or OrgChartAdapter()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._chain_builder   = ApprovalChainBuilder(self._org)
        self._escalation_mgr  = EscalationManager(self._org, audit_fn)
        self._audit_fn        = audit_fn or (lambda e, d: None)

        # 진행 중인 승인 체인 저장소
        # 실제 환경에서는 DB / Redis로 교체
        self._active_chains: dict[str, ApprovalChain] = {}

    # ─── 메인 진입점 ────────────────────────────────────────
    def decide(
        self,
        request: ActionRequest,
        policy_result: PolicyResult,
    ) -> DecisionResult:
        """
        PolicyResult를 받아 최종 DecisionResult를 반환합니다.

        Args:
            request:       원본 ActionRequest
            policy_result: RiskEvaluator의 평가 결과

        Returns:
            DecisionResult — 결정, 승인 체인(필요 시), 알림 정보 포함
        """

        # UC-002: 서킷 브레이커 우선 확인
        if request.action_type == ActionType.INVESTMENT:
            if self._circuit_breaker.is_triggered:
                self._circuit_breaker.add_affected_user(request.user_id)
                return self._make_result(
                    request, policy_result,
                    override_decision=Decision.DENY,
                    notify_msg="서킷 브레이커 발동 중 — 투자 행동이 일시 차단됩니다.",
                )

        decision = policy_result.decision

        # ── AUTO_APPROVE: 즉시 실행 ──────────────────────────
        if decision == Decision.AUTO_APPROVE:
            return self._make_result(request, policy_result)

        # ── DENY: 즉시 차단 ──────────────────────────────────
        if decision == Decision.DENY:
            return self._make_result(
                request, policy_result,
                notify_msg=f"행동이 차단됐습니다. 사유: {', '.join(policy_result.reasons)}",
            )

        # ── USER_CONFIRM / ADMIN_APPROVE ─────────────────────
        if request.action_type == ActionType.PURCHASE_REQUEST:
            # UC-003: 승인 체인 자동 빌드
            is_urgent = (request.payload.get("urgency") == "URGENT")
            chain = self._chain_builder.build(
                request, policy_result.risk_score, is_urgent
            )
            self._active_chains[chain.chain_id] = chain

            # Tier 5 → DENY (이사회 수동 이관)
            if chain.tier == 5:
                return self._make_result(
                    request, policy_result,
                    override_decision=Decision.DENY,
                    notify_msg="1억원 초과 구매 — 이사회 수동 결의가 필요합니다.",
                    chain=chain,
                )

            msg = self._build_approval_message(chain, decision)
            return self._make_result(
                request, policy_result,
                chain=chain,
                notify_msg=msg,
            )

        else:
            # UC-001/002/004: 단순 사용자 확인
            msg = self._build_confirm_message(request, policy_result)
            return self._make_result(
                request, policy_result,
                notify_msg=msg,
            )

    # ─── 승인 처리 (UC-003) ─────────────────────────────────
    def process_approval(
        self,
        chain_id:    str,
        step_id:     str,
        approver_id: str,
        approved:    bool,
        comment:     str = "",
    ) -> dict:
        """
        결재자의 승인/반려를 처리합니다.

        Returns:
            {"chain_complete": bool, "chain_rejected": bool,
             "next_approver": Optional[str]}
        """
        chain = self._active_chains.get(chain_id)
        if not chain:
            raise ValueError(f"체인을 찾을 수 없음: {chain_id}")

        step = next((s for s in chain.steps if s.step_id == step_id), None)
        if not step:
            raise ValueError(f"결재 단계를 찾을 수 없음: {step_id}")

        if approved:
            step.approve(approver_id, comment)
            self._audit_fn("APPROVAL_GRANTED", {
                "chain_id":    chain_id,
                "step_id":     step_id,
                "approver_id": approver_id,
                "comment":     comment,
                "approved_at": step.responded_at,
            })
        else:
            step.reject(approver_id, comment)
            self._audit_fn("APPROVAL_REJECTED", {
                "chain_id":    chain_id,
                "step_id":     step_id,
                "approver_id": approver_id,
                "comment":     comment,
                "rejected_at": step.responded_at,
            })

        # 다음 결재자 탐색
        next_approver = self._next_approver(chain)

        return {
            "chain_complete": chain.is_complete(),
            "chain_rejected": chain.is_rejected(),
            "next_approver":  next_approver,
        }

    def check_timeouts(self, chain_id: str) -> list[ApprovalStep]:
        """특정 체인의 타임아웃을 확인하고 에스컬레이션합니다."""
        chain = self._active_chains.get(chain_id)
        if not chain:
            return []
        return self._escalation_mgr.check_timeouts(chain)

    # ─── 내부 유틸 ──────────────────────────────────────────
    def _make_result(
        self,
        request:           ActionRequest,
        policy_result:     PolicyResult,
        override_decision: Optional[Decision] = None,
        notify_msg:        Optional[str]       = None,
        chain:             Optional[ApprovalChain] = None,
    ) -> DecisionResult:
        decision = override_decision or policy_result.decision
        return DecisionResult(
            result_id=str(uuid.uuid4()),
            request_id=request.request_id,
            decision=decision,
            risk_score=policy_result.risk_score,
            reasons=policy_result.reasons,
            approval_chain=chain,
            requires_notify=(notify_msg is not None),
            notify_message=notify_msg,
        )

    @staticmethod
    def _next_approver(chain: ApprovalChain) -> Optional[str]:
        """승인을 기다리는 다음 결재자 ID를 반환합니다."""
        for step in chain.steps:
            if step.status == ApprovalStatus.PENDING:
                return step.approver_id
        return None

    @staticmethod
    def _build_approval_message(chain: ApprovalChain, decision: Decision) -> str:
        roles = [s.role for s in chain.steps]
        suffix = " (병렬 결재)" if chain.is_fast_track else ""
        return (
            f"Tier {chain.tier} 승인 필요{suffix} — "
            f"결재 경로: {' → '.join(roles)}"
        )

    @staticmethod
    def _build_confirm_message(
        request: ActionRequest, result: PolicyResult
    ) -> str:
        action_names = {
            ActionType.PAYMENT:    "결제",
            ActionType.INVESTMENT: "투자",
            ActionType.CIVIC_SERVICE: "행정 서비스",
        }
        name = action_names.get(request.action_type, "행동")
        return (
            f"위험 점수 {result.risk_score}점 — "
            f"{name} 실행을 확인해 주세요. "
            f"사유: {', '.join(result.reasons)}"
        )


# ══════════════════════════════════════════════════════════════
#  유틸리티
# ══════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _soft_sign(value: str) -> str:
    """개발용 소프트웨어 서명 (UC-005에서 TPM 서명으로 교체)"""
    import hashlib
    return hashlib.sha256(f"SOFT_SIG:{value}".encode()).hexdigest()


# ══════════════════════════════════════════════════════════════
#  빠른 동작 확인
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 62)
    print("KorPIX Decision Engine v0.1.0  —  동작 확인")
    print("=" * 62)

    risk_engine     = PolicyEngine()
    decision_engine = DecisionEngine()
    policy          = UserPolicy()

    # ── 케이스 1: 소액 결제 → AUTO_APPROVE ──────────────────
    req1 = ActionRequest(
        request_id="req-001", action_type=ActionType.PAYMENT,
        agent_id="agent-A", user_id="user-001", terminal_id="term-001",
        payload={"service": "netflix", "amount": 17_000,
                 "currency": "KRW", "merchant": "Netflix Korea",
                 "is_recurring": True},
        user_policy=policy,
    )
    r1  = risk_engine.evaluate(req1)
    dr1 = decision_engine.decide(req1, r1)
    print(f"\n[케이스 1] 넷플릭스 17,000원 결제")
    print(f"  Risk Score : {dr1.risk_score}")
    print(f"  결정       : {dr1.decision.value}")
    print(f"  알림 필요  : {dr1.requires_notify}")

    # ── 케이스 2: 한도 초과 결제 → DENY ─────────────────────
    req2 = ActionRequest(
        request_id="req-002", action_type=ActionType.PAYMENT,
        agent_id="agent-A", user_id="user-001", terminal_id="term-001",
        payload={"service": "annual_sub", "amount": 600_000,
                 "currency": "KRW", "merchant": "Cloud Service",
                 "is_recurring": False},
        user_policy=policy,
    )
    r2  = risk_engine.evaluate(req2)
    dr2 = decision_engine.decide(req2, r2)
    print(f"\n[케이스 2] 연간 구독 600,000원 (한도 초과)")
    print(f"  Risk Score : {dr2.risk_score}")
    print(f"  결정       : {dr2.decision.value}")
    print(f"  알림 메시지: {dr2.notify_message}")

    # ── 케이스 3: IT 장비 구매 → Tier 2 팀장 승인 ──────────
    req3 = ActionRequest(
        request_id="req-003", action_type=ActionType.PURCHASE_REQUEST,
        agent_id="agent-B", user_id="user-002", terminal_id="term-002",
        payload={
            "total_amount": 4_000_000, "category": "IT_EQUIPMENT",
            "item_code": "NB-DELL-001", "item_name": "Dell 노트북 2대",
            "quantity": 2, "unit_price": 2_000_000, "urgency": "NORMAL",
            "requester_id": "EMP-001",
            "department_id": "DEPT-IT", "budget_code": "BC-2025-IT",
            "justification": "신규 입사자 장비 지급",
        },
        user_policy=policy,
    )
    r3  = risk_engine.evaluate(req3)
    dr3 = decision_engine.decide(req3, r3)
    print(f"\n[케이스 3] 노트북 4,000,000원 구매")
    print(f"  Risk Score : {dr3.risk_score}")
    print(f"  결정       : {dr3.decision.value}")
    if dr3.approval_chain:
        chain = dr3.approval_chain
        print(f"  승인 Tier  : {chain.tier}")
        print(f"  Fast-Track : {chain.is_fast_track}")
        for step in chain.steps:
            print(f"  결재자     : [{step.role}] "
                  f"{step.approver_id}  "
                  f"(타임아웃 {step.timeout_sec//3600}시간)")

    # ── 케이스 4: 서버 구매 긴급 Fast-Track → Tier 3 병렬 ─
    req4 = ActionRequest(
        request_id="req-004", action_type=ActionType.PURCHASE_REQUEST,
        agent_id="agent-B", user_id="user-002", terminal_id="term-002",
        payload={
            "total_amount": 12_000_000, "category": "IT_EQUIPMENT",
            "item_code": "SRV-HPE-001", "item_name": "HPE 서버 장비",
            "quantity": 1, "unit_price": 12_000_000, "urgency": "URGENT",
            "requester_id": "EMP-001",
            "department_id": "DEPT-IT", "budget_code": "BC-2025-IT",
            "justification": "운영 서버 고장 — 긴급 교체",
        },
        user_policy=policy,
    )
    r4  = risk_engine.evaluate(req4)
    dr4 = decision_engine.decide(req4, r4)
    print(f"\n[케이스 4] 서버 12,000,000원 긴급 구매")
    print(f"  Risk Score : {dr4.risk_score}")
    print(f"  결정       : {dr4.decision.value}")
    if dr4.approval_chain:
        chain = dr4.approval_chain
        print(f"  승인 Tier  : {chain.tier}")
        print(f"  Fast-Track : {chain.is_fast_track} ← 병렬 결재 활성화")
        for step in chain.steps:
            print(f"  결재자     : [{step.role}] "
                  f"{step.approver_id}  "
                  f"{'(병렬)' if step.parallel else '(직렬)'}  "
                  f"타임아웃 {step.timeout_sec//3600}시간")

    # ── 케이스 5: 팀장 승인 처리 시뮬레이션 ────────────────
    print(f"\n[케이스 5] 케이스 3 팀장 승인 시뮬레이션")
    chain3  = dr3.approval_chain
    step3   = chain3.steps[0]
    result5 = decision_engine.process_approval(
        chain_id=chain3.chain_id,
        step_id=step3.step_id,
        approver_id="EMP-010",
        approved=True,
        comment="장비 구매 승인합니다.",
    )
    print(f"  체인 완료  : {result5['chain_complete']}")
    print(f"  체인 반려  : {result5['chain_rejected']}")
    print(f"  다음 결재자: {result5['next_approver']} (없으면 완료)")

    # ── 케이스 6: 서킷 브레이커 시뮬레이션 ─────────────────
    print(f"\n[케이스 6] 서킷 브레이커 시뮬레이션")
    cb = CircuitBreaker()
    cb.check_and_trigger(vix=37.5, kospi_change=-0.062)
    print(f"  발동 상태  : {cb.is_triggered}")
    print(f"  발동 상태  : {cb.status['reason']}")

    # 서킷 브레이커 발동 상태에서 투자 요청
    engine_with_cb = DecisionEngine(circuit_breaker=cb)
    req6 = ActionRequest(
        request_id="req-006", action_type=ActionType.INVESTMENT,
        agent_id="agent-C", user_id="user-003", terminal_id="term-003",
        payload={"ticker": "KODEX200", "quantity": 10,
                 "total_amount": 300_000, "order_type": "MARKET",
                 "sector": "diversified"},
        user_policy=policy,
    )
    r6  = risk_engine.evaluate(req6)
    dr6 = engine_with_cb.decide(req6, r6)
    print(f"  투자 결정  : {dr6.decision.value}  ← 서킷 브레이커로 차단")
    print(f"  알림       : {dr6.notify_message}")

    # 수동 해제
    cb.deactivate(user_id="user-003", manual_confirm=True)
    print(f"  해제 후 상태: triggered={cb.is_triggered}")

    print("\n" + "=" * 62)
    print("Decision Engine 정상 동작 확인 완료")
    print("=" * 62)
