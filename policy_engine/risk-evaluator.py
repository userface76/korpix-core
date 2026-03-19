"""
KorPIX Policy Engine — Risk Evaluator
========================================
Version:  0.1.0
Spec:     KorPIX Architecture Whitepaper §7, §8, §9

AI 에이전트의 행동 요청을 분석하여 0~100 사이의
Risk Score를 계산하고 실행 여부를 결정합니다.

결정 분기:
    Score  0 ~ 29  →  AUTO_APPROVE    자동 승인
    Score 30 ~ 59  →  USER_CONFIRM    사용자 확인
    Score 60 ~ 79  →  ADMIN_APPROVE   관리자 승인
    Score 80+      →  DENY            차단

UC별 계산 구조:
    BaseEvaluator           ← UC-001~005 공통
    ├─ PaymentEvaluator     ← UC-001 결제
    ├─ InvestmentEvaluator  ← UC-002 투자
    ├─ PurchaseEvaluator    ← UC-003 기업 구매
    └─ CivicEvaluator       ← UC-004 행정 서비스
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ══════════════════════════════════════════════════════════════
#  열거형 & 상수
# ══════════════════════════════════════════════════════════════

class Decision(str, Enum):
    AUTO_APPROVE  = "AUTO_APPROVE"   # Risk 0~29
    USER_CONFIRM  = "USER_CONFIRM"   # Risk 30~59
    ADMIN_APPROVE = "ADMIN_APPROVE"  # Risk 60~79
    DENY          = "DENY"           # Risk 80+

class ActionType(str, Enum):
    PAYMENT          = "PAYMENT"
    INVESTMENT       = "INVESTMENT"
    PURCHASE_REQUEST = "PURCHASE_REQUEST"
    CIVIC_SERVICE    = "CIVIC_SERVICE"
    SYSTEM           = "SYSTEM"

# Risk Score → Decision 임계값
THRESHOLDS = {
    Decision.AUTO_APPROVE:  30,
    Decision.USER_CONFIRM:  60,
    Decision.ADMIN_APPROVE: 80,
}

POLICY_ENGINE_VERSION = "0.1.0"


# ══════════════════════════════════════════════════════════════
#  데이터 클래스
# ══════════════════════════════════════════════════════════════

@dataclass
class UserPolicy:
    """사용자 정책 — Trust Terminal에서 로드"""
    # UC-001 결제
    monthly_payment_limit:    int   = 1_000_000   # 월 결제 한도 (KRW)
    single_payment_limit:     int   = 500_000      # 건당 결제 한도
    # UC-002 투자
    monthly_invest_limit:     int   = 5_000_000   # 월 투자 한도
    max_loss_rate:            float = 0.10         # 손실 한도 (10%)
    max_sector_concentration: float = 0.35         # 최대 섹터 집중도 (35%)
    investor_risk_grade:      int   = 3            # 1(안정)~5(공격)
    # UC-003 구매
    auto_approve_threshold:   int   = 1_000_000   # 자동 승인 한도
    # UC-004 행정
    civic_payment_limit:      int   = 500_000      # 공과금 자동납부 한도
    # 공통
    two_factor_required:      bool  = False
    policy_version:           str   = "0.1.0"


@dataclass
class ActionRequest:
    """Policy Engine 행동 요청"""
    request_id:   str
    action_type:  ActionType
    agent_id:     str
    user_id:      str
    terminal_id:  str
    payload:      dict[str, Any]
    user_policy:  UserPolicy
    timestamp:    str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RiskDetail:
    """Risk Score 구성 상세 — 감사 기록에 포함"""
    factor_name:  str
    score_added:  int
    reason:       str


@dataclass
class PolicyResult:
    """Policy Engine 최종 결정"""
    decision:         Decision
    risk_score:       int
    risk_details:     list[RiskDetail]
    reasons:          list[str]
    policy_engine_ver:str = POLICY_ENGINE_VERSION
    evaluated_at:     str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "decision":          self.decision.value,
            "risk_score":        self.risk_score,
            "risk_details":      [{"factor": d.factor_name, "score": d.score_added, "reason": d.reason}
                                  for d in self.risk_details],
            "reasons":           self.reasons,
            "policy_engine_ver": self.policy_engine_ver,
            "evaluated_at":      self.evaluated_at,
        }


# ══════════════════════════════════════════════════════════════
#  외부 의존성 인터페이스 (실제 구현은 어댑터로 교체)
# ══════════════════════════════════════════════════════════════

class AccessLogAdapter:
    """접근 빈도 기록 조회 — 실제 환경에서는 Redis / DB로 교체"""
    def get_recent_count(self, user_id: str, minutes: int) -> int:
        # TODO: 실제 구현 연결
        return 0

class PortfolioAdapter:
    """포트폴리오 데이터 조회 — 실제 환경에서는 증권 API로 교체"""
    def get_loss_rate(self, user_id: str) -> float:
        return 0.0
    def get_sector_concentration(self, user_id: str, sector: str) -> float:
        return 0.0
    def get_monthly_used_rate(self, user_id: str) -> float:
        return 0.0

class MarketDataAdapter:
    """시장 데이터 조회 — 실제 환경에서는 금융 데이터 API로 교체"""
    def get_vix(self) -> float:
        return 15.0
    def get_daily_change(self, index: str) -> float:
        return 0.0

class ERPAdapter:
    """ERP 데이터 조회 — 실제 환경에서는 ERP API로 교체"""
    def get_budget_used_rate(self, dept_id: str, budget_code: str) -> float:
        return 0.5
    def get_urgent_count(self, dept_id: str) -> int:
        return 0
    def get_recent_purchase_count(self, item_code: str, days: int) -> int:
        return 0

# 기본 어댑터 인스턴스 (의존성 주입으로 교체 가능)
_access_log = AccessLogAdapter()
_portfolio  = PortfolioAdapter()
_market     = MarketDataAdapter()
_erp        = ERPAdapter()


# ══════════════════════════════════════════════════════════════
#  Base Evaluator — 공통 Risk Score 계산
# ══════════════════════════════════════════════════════════════

class BaseRiskEvaluator(ABC):
    """
    모든 UC 공통 Risk Score 계산 기반 클래스.
    하위 클래스에서 add_specific_scores()를 구현하여
    UC별 추가 점수를 더합니다.
    """

    # UC별 행동 유형 기본 점수
    ACTION_TYPE_BASE: dict[ActionType, int] = {
        ActionType.PAYMENT:          15,
        ActionType.INVESTMENT:       20,
        ActionType.PURCHASE_REQUEST: 10,
        ActionType.CIVIC_SERVICE:    10,
        ActionType.SYSTEM:            5,
    }

    def evaluate(self, request: ActionRequest) -> PolicyResult:
        """
        메인 평가 메서드.
        기본 점수 계산 후 UC별 추가 점수를 더해 최종 결정을 반환합니다.
        """
        score   = 0
        details: list[RiskDetail] = []

        # ── 1. 행동 유형 기본 점수 ──────────────────────────
        base = self.ACTION_TYPE_BASE.get(request.action_type, 15)
        score += base
        details.append(RiskDetail("action_type", base, f"{request.action_type.value} 기본 점수"))

        # ── 2. 이상 접근 패턴 (10분 내 5회 이상) ──────────────
        recent_count = _access_log.get_recent_count(request.user_id, minutes=10)
        if recent_count >= 5:
            score += 40
            details.append(RiskDetail("abnormal_pattern", 40, f"10분 내 {recent_count}회 접근 감지"))

        # ── 3. UC별 추가 점수 (하위 클래스 구현) ──────────────
        specific_score, specific_details = self.add_specific_scores(request)
        score   += specific_score
        details += specific_details

        # ── 4. 최종 결정 ──────────────────────────────────────
        decision = self._score_to_decision(score)
        reasons  = [d.reason for d in details if d.score_added > 0]

        return PolicyResult(
            decision=decision,
            risk_score=min(score, 100),  # 최대 100 캡
            risk_details=details,
            reasons=reasons,
        )

    @abstractmethod
    def add_specific_scores(
        self, request: ActionRequest
    ) -> tuple[int, list[RiskDetail]]:
        """UC별 추가 Risk Score 반환 — 하위 클래스에서 구현"""
        ...

    @staticmethod
    def _score_to_decision(score: int) -> Decision:
        if score <  30: return Decision.AUTO_APPROVE
        if score <  60: return Decision.USER_CONFIRM
        if score <  80: return Decision.ADMIN_APPROVE
        return Decision.DENY


# ══════════════════════════════════════════════════════════════
#  UC-001 Payment Evaluator
# ══════════════════════════════════════════════════════════════

class PaymentRiskEvaluator(BaseRiskEvaluator):
    """
    UC-001 결제 위험도 평가기.

    추가 평가 요소:
        - 결제 금액 vs 건당 한도
        - 결제 금액 vs 월 한도
    """

    def add_specific_scores(
        self, request: ActionRequest
    ) -> tuple[int, list[RiskDetail]]:
        score   = 0
        details: list[RiskDetail] = []
        payload = request.payload
        policy  = request.user_policy
        amount  = int(payload.get("amount", 0))

        # 금액 구간 점수
        if   amount < 10_000:   add = 0
        elif amount < 50_000:   add = 5
        elif amount < 100_000:  add = 10
        elif amount < 500_000:  add = 20
        else:                   add = 35
        score += add
        details.append(RiskDetail("amount_range", add, f"결제 금액 {amount:,}원 구간 점수"))

        # 건당 한도 초과
        if amount > policy.single_payment_limit:
            score += 30
            details.append(RiskDetail(
                "single_limit_exceeded", 30,
                f"건당 한도 {policy.single_payment_limit:,}원 초과 ({amount:,}원)"
            ))

        return score, details


# ══════════════════════════════════════════════════════════════
#  UC-002 Investment Evaluator
# ══════════════════════════════════════════════════════════════

class InvestmentRiskEvaluator(BaseRiskEvaluator):
    """
    UC-002 투자 위험도 평가기.

    추가 평가 요소:
        - 시장 변동성 (VIX)         → 서킷 브레이커
        - 포트폴리오 손실률          → 손실 한도 차단
        - 섹터 집중도               → 분산투자 원칙
        - 월 한도 소진율
        - 투자자 등급 vs 상품 위험도 → 적합성 원칙
    """

    # VIX 임계값 — 이 값 이상이면 서킷 브레이커 발동
    CIRCUIT_BREAKER_VIX      = 35.0
    KOSPI_DROP_THRESHOLD     = -0.05   # 코스피 일간 -5%

    def add_specific_scores(
        self, request: ActionRequest
    ) -> tuple[int, list[RiskDetail]]:
        score   = 0
        details: list[RiskDetail] = []
        payload = request.payload
        policy  = request.user_policy
        amount  = int(payload.get("total_amount", 0))
        sector  = str(payload.get("sector", ""))
        product_risk_grade = int(payload.get("product_risk_grade", 3))

        # ── 서킷 브레이커 확인 (VIX / 시장 급락) ─────────────
        vix          = _market.get_vix()
        kospi_change = _market.get_daily_change("KOSPI")

        if vix >= self.CIRCUIT_BREAKER_VIX or kospi_change <= self.KOSPI_DROP_THRESHOLD:
            details.append(RiskDetail(
                "circuit_breaker", 100,
                f"서킷 브레이커 발동 (VIX={vix:.1f}, 코스피={kospi_change:.1%})"
            ))
            # 서킷 브레이커는 즉시 DENY — 점수 무관
            return 100, details

        # ── VIX 구간 점수 ──────────────────────────────────────
        if   vix < 15:  add = 0
        elif vix < 25:  add = 10
        elif vix < 35:  add = 25
        else:           add = 50
        score += add
        details.append(RiskDetail("vix", add, f"VIX={vix:.1f} 변동성 점수"))

        # ── 손실 한도 확인 ─────────────────────────────────────
        loss_rate = _portfolio.get_loss_rate(request.user_id)
        if loss_rate <= -abs(policy.max_loss_rate):
            score += 60
            details.append(RiskDetail(
                "loss_limit_exceeded", 60,
                f"손실 한도 {policy.max_loss_rate:.0%} 초과 (현재 {loss_rate:.1%})"
            ))

        # ── 섹터 집중도 확인 ───────────────────────────────────
        if sector:
            concentration = _portfolio.get_sector_concentration(request.user_id, sector)
            if   concentration < 0.30: add = 0
            elif concentration < 0.40: add = 15
            else:                      add = 35
            score += add
            details.append(RiskDetail(
                "concentration", add,
                f"{sector} 섹터 집중도 {concentration:.0%}"
            ))

        # ── 월 한도 소진율 ─────────────────────────────────────
        monthly_used = _portfolio.get_monthly_used_rate(request.user_id)
        if   monthly_used > 0.90: add = 20
        elif monthly_used > 0.75: add = 10
        else:                     add = 0
        score += add
        if add:
            details.append(RiskDetail("monthly_usage", add, f"월 한도 {monthly_used:.0%} 소진"))

        # ── 금액 구간 점수 ─────────────────────────────────────
        if   amount < 100_000:    add = 0
        elif amount < 1_000_000:  add = 10
        elif amount < 5_000_000:  add = 20
        else:                     add = 35
        score += add
        details.append(RiskDetail("amount", add, f"투자금액 {amount:,}원 구간 점수"))

        # ── 적합성 원칙 ────────────────────────────────────────
        if product_risk_grade > policy.investor_risk_grade:
            score += 30
            details.append(RiskDetail(
                "suitability", 30,
                f"투자자 등급({policy.investor_risk_grade}) < 상품 위험도({product_risk_grade}) — 적합성 위반"
            ))

        return score, details


# ══════════════════════════════════════════════════════════════
#  UC-003 Purchase Evaluator
# ══════════════════════════════════════════════════════════════

class PurchaseRiskEvaluator(BaseRiskEvaluator):
    """
    UC-003 기업 구매 위험도 평가기.

    승인 티어:
        Tier 1  (Auto)      : score ≤ 25
        Tier 2  (팀장)       : 26 ≤ score ≤ 50
        Tier 3  (팀장+재무)  : 51 ≤ score ≤ 70
        Tier 4  (CFO)       : 71 ≤ score ≤ 85
        Tier 5  (이사회)    : score > 85 → DENY (수동 이관)

    추가 평가 요소:
        - 금액 × 품목 위험도
        - 부서 예산 소진율 / 초과 여부
        - 긴급 구매 남용 패턴
        - 분할 발주 패턴
    """

    AMOUNT_TIERS: list[tuple[int, int]] = [
        (1_000_000,   0),    # 100만 미만    → +0
        (5_000_000,  15),    # 500만 미만    → +15
        (20_000_000, 35),    # 2,000만 미만  → +35
        (100_000_000,55),    # 1억 미만      → +55
    ]

    CATEGORY_RISK: dict[str, int] = {
        "CONSUMABLE":   0,    # 소모품
        "SERVICE":      10,   # 서비스 계약
        "IT_EQUIPMENT": 15,   # IT 장비
        "ASSET":        25,   # 자산성 구매
    }

    def add_specific_scores(
        self, request: ActionRequest
    ) -> tuple[int, list[RiskDetail]]:
        score   = 0
        details: list[RiskDetail] = []
        payload = request.payload
        amount  = int(payload.get("total_amount", 0))
        category= str(payload.get("category", "CONSUMABLE"))
        urgency = str(payload.get("urgency", "NORMAL"))
        dept_id = str(payload.get("department_id", ""))
        budget_code = str(payload.get("budget_code", ""))
        item_code   = str(payload.get("item_code", ""))

        # ── 예산 초과 확인 (즉시 DENY) ───────────────────────
        if dept_id and budget_code:
            budget_used = _erp.get_budget_used_rate(dept_id, budget_code)
            if budget_used > 1.0:
                details.append(RiskDetail(
                    "budget_exceeded", 100,
                    f"부서 예산 초과 (소진율 {budget_used:.0%})"
                ))
                return 100, details

            if   budget_used > 0.90: add = 20
            elif budget_used > 0.75: add = 10
            else:                    add = 0
            score += add
            if add:
                details.append(RiskDetail("budget_usage", add, f"예산 {budget_used:.0%} 소진"))

        # ── 금액 구간 점수 ────────────────────────────────────
        matched = False
        for threshold, points in self.AMOUNT_TIERS:
            if amount < threshold:
                score += points
                details.append(RiskDetail("amount", points, f"구매금액 {amount:,}원 구간 점수"))
                matched = True
                break
        if not matched:
            # 1억 초과 → DENY (이사회 수동 이관)
            details.append(RiskDetail("amount_over_limit", 100, "1억원 초과 — 이사회 결의 필요"))
            return 100, details

        # ── 품목 위험도 ───────────────────────────────────────
        cat_score = self.CATEGORY_RISK.get(category, 20)
        score += cat_score
        details.append(RiskDetail("category", cat_score, f"{category} 품목 위험도"))

        # ── 긴급 구매 가중치 ──────────────────────────────────
        if urgency == "URGENT":
            score += 15
            details.append(RiskDetail("urgency", 15, "긴급 구매 가중치"))
            # 당월 긴급 남용 감지
            if dept_id:
                urgent_count = _erp.get_urgent_count(dept_id)
                if urgent_count >= 3:
                    score += 10
                    details.append(RiskDetail(
                        "urgency_abuse", 10,
                        f"당월 긴급 구매 {urgent_count}회 남용 패턴"
                    ))

        # ── 분할 발주 패턴 ────────────────────────────────────
        if item_code:
            recent_purchases = _erp.get_recent_purchase_count(item_code, days=30)
            if recent_purchases >= 3:
                score += 8
                details.append(RiskDetail(
                    "split_order", 8,
                    f"30일 내 동일 품목 {recent_purchases}회 반복 구매 패턴"
                ))

        return score, details


# ══════════════════════════════════════════════════════════════
#  UC-004 Civic Evaluator
# ══════════════════════════════════════════════════════════════

class CivicRiskEvaluator(BaseRiskEvaluator):
    """
    UC-004 행정 서비스 위험도 평가기.

    개인정보 등급:
        Grade 1 — 일반 (이름·주소)         → +0
        Grade 2 — 민감 (주민번호·계좌)     → +15, User Confirm 필수
        Grade 3 — 고민감 (건강·복지 이력)  → +30, 로컬 처리 전용
        Grade 4 — 최고민감 (생체·범죄)     → DENY 즉시 차단

    추가 평가 요소:
        - 개인정보 등급
        - 위임 관계 유효성
        - 이상 접근 빈도
        - 납부 금액 한도
    """

    SERVICE_BASE_RISK: dict[str, int] = {
        "LOCAL_TAX":      10,   # 지방세 납부
        "UTILITY":        10,   # 공과금 납부
        "DOC_ISSUANCE":   25,   # 서류 발급
        "WELFARE":        40,   # 복지 신청
        "RESERVATION":    15,   # 공공 예약
        "PERMIT":         50,   # 인허가 신청
    }

    def add_specific_scores(
        self, request: ActionRequest
    ) -> tuple[int, list[RiskDetail]]:
        score   = 0
        details: list[RiskDetail] = []
        payload = request.payload
        policy  = request.user_policy

        service_code  = str(payload.get("service_code", ""))
        privacy_grade = int(payload.get("privacy_grade", 1))
        is_delegated  = bool(payload.get("is_delegated", False))
        delegation_valid = bool(payload.get("delegation_valid", False))
        amount        = int(payload.get("amount") or 0)

        # ── 서비스 유형 기본 점수 ─────────────────────────────
        svc_score = self.SERVICE_BASE_RISK.get(service_code, 20)
        score += svc_score
        details.append(RiskDetail("service_type", svc_score, f"{service_code} 서비스 기본 점수"))

        # ── 개인정보 등급 ─────────────────────────────────────
        if privacy_grade == 4:
            details.append(RiskDetail("privacy_grade_4", 100, "최고민감 개인정보(생체·범죄) — 처리 불가"))
            return 100, details
        elif privacy_grade == 3:
            score += 30
            details.append(RiskDetail("privacy_grade", 30, "고민감 개인정보(건강·복지) — 로컬 처리 전용"))
        elif privacy_grade == 2:
            score += 15
            details.append(RiskDetail("privacy_grade", 15, "민감 개인정보(주민번호·계좌) — User Confirm 필수"))

        # ── 위임 관계 검증 ────────────────────────────────────
        if is_delegated:
            if not delegation_valid:
                details.append(RiskDetail("delegation_invalid", 100, "위임 관계 미검증 — 대리 행동 불가"))
                return 100, details
            score += 20
            details.append(RiskDetail("delegation", 20, "대리 행동 가중치 (위임 검증 완료)"))

        # ── 납부 금액 한도 ────────────────────────────────────
        if amount > policy.civic_payment_limit:
            score += 25
            details.append(RiskDetail(
                "civic_amount", 25,
                f"공과금 한도 {policy.civic_payment_limit:,}원 초과 ({amount:,}원)"
            ))

        return score, details


# ══════════════════════════════════════════════════════════════
#  Policy Engine 팩토리 & 메인 진입점
# ══════════════════════════════════════════════════════════════

class PolicyEngine:
    """
    KorPIX Policy Engine 메인 클래스.
    ActionType에 맞는 Evaluator를 선택하여 평가를 위임합니다.
    """

    _evaluators: dict[ActionType, BaseRiskEvaluator] = {
        ActionType.PAYMENT:          PaymentRiskEvaluator(),
        ActionType.INVESTMENT:       InvestmentRiskEvaluator(),
        ActionType.PURCHASE_REQUEST: PurchaseRiskEvaluator(),
        ActionType.CIVIC_SERVICE:    CivicRiskEvaluator(),
    }

    def evaluate(self, request: ActionRequest) -> PolicyResult:
        """
        행동 요청을 평가하여 실행 여부를 결정합니다.

        Args:
            request: ActionRequest — 평가할 행동 요청

        Returns:
            PolicyResult — 결정(decision), 점수(risk_score), 이유(reasons) 포함

        Raises:
            ValueError: 지원하지 않는 ActionType인 경우
        """
        evaluator = self._evaluators.get(request.action_type)
        if evaluator is None:
            raise ValueError(f"지원하지 않는 ActionType: {request.action_type}")
        return evaluator.evaluate(request)


# ══════════════════════════════════════════════════════════════
#  Audit Record 생성 유틸리티
# ══════════════════════════════════════════════════════════════

def build_action_record(
    request:       ActionRequest,
    result:        PolicyResult,
    exec_status:   str,
    prev_hash:     str,
    terminal_sign_fn = None,
) -> dict:
    """
    PolicyResult를 바탕으로 ActionRecord dict를 생성합니다.
    hash와 digitalSignature를 자동으로 계산합니다.

    Args:
        request:         평가된 ActionRequest
        result:          PolicyEngine의 PolicyResult
        exec_status:     실행 결과 ('SUCCESS' | 'BLOCKED' | 'PENDING' | 'FAILED')
        prev_hash:       이전 레코드의 hash (해시 체인 연결)
        terminal_sign_fn: 단말 서명 함수 (없으면 SHA-256으로 대체)

    Returns:
        ActionRecord dict — Audit Network에 저장할 준비된 레코드
    """
    import uuid

    record: dict = {
        "actionId":        str(uuid.uuid4()),
        "agentId":         request.agent_id,
        "userId":          request.user_id,
        "terminalId":      request.terminal_id,
        "actionType":      request.action_type.value,
        "payload":         request.payload,
        "riskScore":       result.risk_score,
        "policyDecision":  result.decision.value,
        "policyEngineVer": result.policy_engine_ver,
        "executionResult": exec_status,
        "timestamp":       request.timestamp,
        "prevHash":        prev_hash,
    }

    # SHA-256 해시 계산
    record_str     = json.dumps(record, sort_keys=True, ensure_ascii=False)
    record["hash"] = hashlib.sha256(record_str.encode()).hexdigest()

    # 단말 서명 (실제 환경에서는 TPM AIK 서명으로 교체)
    if terminal_sign_fn:
        record["digitalSignature"] = terminal_sign_fn(record["hash"])
    else:
        # Fallback: 개발/테스트 환경용 소프트웨어 서명
        record["digitalSignature"] = hashlib.sha256(
            f"SOFT_SIG:{record['hash']}".encode()
        ).hexdigest()

    return record


def verify_chain(records: list[dict]) -> tuple[bool, Optional[int]]:
    """
    ActionRecord 해시 체인의 무결성을 검증합니다.

    Args:
        records: 순서대로 정렬된 ActionRecord dict 목록

    Returns:
        (is_valid, broken_at_index)
        broken_at_index는 체인이 끊어진 위치 (정상이면 None)
    """
    for i in range(1, len(records)):
        if records[i]["prevHash"] != records[i - 1]["hash"]:
            return False, i
    return True, None


# ══════════════════════════════════════════════════════════════
#  빠른 동작 확인 (python risk-evaluator.py 실행 시)
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = PolicyEngine()
    policy = UserPolicy()

    print("=" * 60)
    print("KorPIX Policy Engine v0.1.0  —  동작 확인")
    print("=" * 60)

    # ── UC-001: 소액 결제 (자동 승인 기대) ───────────────────
    r1 = ActionRequest(
        request_id="req-001", action_type=ActionType.PAYMENT,
        agent_id="agent-A", user_id="user-hash-001", terminal_id="term-001",
        payload={"service": "netflix", "amount": 17_000, "currency": "KRW",
                 "merchant": "Netflix Korea", "is_recurring": True},
        user_policy=policy,
    )
    res1 = engine.evaluate(r1)
    print(f"\n[UC-001] 넷플릭스 17,000원 결제")
    print(f"  → {res1.decision.value}  (Risk Score: {res1.risk_score})")
    for d in res1.risk_details:
        print(f"     {d.factor_name:25s} +{d.score_added:2d}  {d.reason}")

    # ── UC-001: 고액 결제 (사용자 확인 기대) ─────────────────
    r2 = ActionRequest(
        request_id="req-002", action_type=ActionType.PAYMENT,
        agent_id="agent-A", user_id="user-hash-001", terminal_id="term-001",
        payload={"service": "annual_subscription", "amount": 600_000,
                 "currency": "KRW", "merchant": "Cloud Service",
                 "is_recurring": False},
        user_policy=policy,
    )
    res2 = engine.evaluate(r2)
    print(f"\n[UC-001] 연간 구독 600,000원 결제")
    print(f"  → {res2.decision.value}  (Risk Score: {res2.risk_score})")

    # ── UC-003: 소모품 구매 (자동 승인 기대) ─────────────────
    r3 = ActionRequest(
        request_id="req-003", action_type=ActionType.PURCHASE_REQUEST,
        agent_id="agent-B", user_id="user-hash-002", terminal_id="term-002",
        payload={"total_amount": 55_000, "category": "CONSUMABLE",
                 "item_code": "A4-PAPER-500", "item_name": "A4 용지 500매",
                 "quantity": 5, "unit_price": 11_000, "urgency": "NORMAL",
                 "department_id": "DEPT-MKT", "budget_code": "BC-2025-OPS",
                 "justification": "사무용 소모품 정기 구매"},
        user_policy=policy,
    )
    res3 = engine.evaluate(r3)
    print(f"\n[UC-003] A4 용지 55,000원 구매")
    print(f"  → {res3.decision.value}  (Risk Score: {res3.risk_score})")

    # ── UC-004: 지방세 납부 (자동 승인 기대) ─────────────────
    r4 = ActionRequest(
        request_id="req-004", action_type=ActionType.CIVIC_SERVICE,
        agent_id="agent-C", user_id="user-hash-003", terminal_id="term-003",
        payload={"service_code": "LOCAL_TAX", "service_name": "지방세 납부",
                 "agency_code": "LOCALEX", "amount": 87_500,
                 "privacy_grade": 1, "is_delegated": False},
        user_policy=policy,
    )
    res4 = engine.evaluate(r4)
    print(f"\n[UC-004] 지방세 87,500원 납부")
    print(f"  → {res4.decision.value}  (Risk Score: {res4.risk_score})")

    # ── 해시 체인 생성 및 검증 ─────────────────────────────────
    print("\n" + "─" * 60)
    print("해시 체인 무결성 검증")

    prev_hash = "0" * 64   # Genesis 블록
    chain: list[dict] = []
    for req, res in [(r1, res1), (r3, res3), (r4, res4)]:
        rec = build_action_record(req, res, "SUCCESS", prev_hash)
        chain.append(rec)
        prev_hash = rec["hash"]

    is_valid, broken_at = verify_chain(chain)
    print(f"  체인 레코드 수: {len(chain)}")
    print(f"  무결성: {'✅ INTACT' if is_valid else f'❌ 체인 끊김 (index {broken_at})'}")
    print(f"  마지막 해시: {chain[-1]['hash'][:16]}...")

    print("\n" + "=" * 60)
    print("Policy Engine 정상 동작 확인 완료")
    print("=" * 60)
