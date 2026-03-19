"""
KorPIX Policy Engine — Risk Evaluator
UC-001~004 통합 위험도 계산 엔진
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from .models import ActionRequest, ActionType, Decision, PolicyResult, RiskDetail


# ── 외부 어댑터 (실제 환경에서 ERP/증권/시장 API로 교체) ──────────
class _AccessLog:
    def get_recent_count(self, user_id: str, minutes: int) -> int:
        return 0

class _Portfolio:
    def get_loss_rate(self, user_id: str) -> float:                    return 0.0
    def get_sector_concentration(self, uid: str, s: str) -> float:     return 0.0
    def get_monthly_used_rate(self, user_id: str) -> float:            return 0.0

class _Market:
    def get_vix(self) -> float:                      return 15.0
    def get_daily_change(self, index: str) -> float: return 0.0

class _ERP:
    def get_budget_used_rate(self, d: str, b: str) -> float:           return 0.5
    def get_urgent_count(self, dept_id: str) -> int:                   return 0
    def get_recent_purchase_count(self, item: str, days: int) -> int:  return 0

_access    = _AccessLog()
_portfolio = _Portfolio()
_market    = _Market()
_erp       = _ERP()


# ── 점수 → 결정 변환 ──────────────────────────────────────────────
def _decide(score: int) -> Decision:
    if score < 30: return Decision.AUTO_APPROVE
    if score < 60: return Decision.USER_CONFIRM
    if score < 80: return Decision.ADMIN_APPROVE
    return Decision.DENY


# ── 기반 클래스 ───────────────────────────────────────────────────
class BaseRiskEvaluator(ABC):
    ACTION_BASE: dict[ActionType, int] = {
        ActionType.PAYMENT:          15,
        ActionType.INVESTMENT:       20,
        ActionType.PURCHASE_REQUEST: 10,
        ActionType.CIVIC_SERVICE:    10,
        ActionType.SYSTEM:            5,
    }

    def evaluate(self, req: ActionRequest) -> PolicyResult:
        """메인 평가 메서드 — 기본 점수 + UC별 점수 합산 후 PolicyResult 반환"""
        score, details = 0, []

        # 공통: 행동 유형 기본 점수
        base = self.ACTION_BASE.get(req.action_type, 15)
        score += base
        details.append(RiskDetail("action_type", base,
                                  f"{req.action_type.value} 기본 점수"))

        # 공통: 이상 접근 빈도 (10분 내 5회 이상)
        if _access.get_recent_count(req.user_id, 10) >= 5:
            score += 40
            details.append(RiskDetail("abnormal_pattern", 40,
                                      "10분 내 5회 이상 비정상 접근"))

        # UC별 추가 점수
        add, more = self.add_specific_scores(req)
        score   += add
        details += more

        final    = min(score, 100)
        decision = _decide(final)
        return PolicyResult(
            decision         = decision,
            risk_score       = final,
            risk_details     = details,
            reasons          = [d.reason for d in details if d.score_added > 0],
        )

    @abstractmethod
    def add_specific_scores(
        self, req: ActionRequest
    ) -> tuple[int, list[RiskDetail]]:
        """UC별 추가 Risk Score — 하위 클래스에서 구현"""
        ...


# ══════════════════════════════════════════════════════════════════
#  UC-001 결제
# ══════════════════════════════════════════════════════════════════
class PaymentEvaluator(BaseRiskEvaluator):
    def add_specific_scores(self, req):
        score, details = 0, []
        amount = int(req.payload.get("amount", 0))

        if   amount < 10_000:  add = 0
        elif amount < 50_000:  add = 5
        elif amount < 100_000: add = 10
        elif amount < 500_000: add = 20
        else:                  add = 35
        score += add
        details.append(RiskDetail("amount_range", add,
                                  f"결제 금액 {amount:,}원 구간 점수"))

        if amount > req.user_policy.single_payment_limit:
            score += 30
            details.append(RiskDetail("limit_exceeded", 30,
                f"건당 한도 {req.user_policy.single_payment_limit:,}원 초과"))
        return score, details


# ══════════════════════════════════════════════════════════════════
#  UC-002 투자
# ══════════════════════════════════════════════════════════════════
class InvestmentEvaluator(BaseRiskEvaluator):
    CB_VIX   = 35.0
    CB_KOSPI = -0.05

    def add_specific_scores(self, req):
        score, details = 0, []
        vix   = _market.get_vix()
        kospi = _market.get_daily_change("KOSPI")

        # 서킷 브레이커
        if vix >= self.CB_VIX or kospi <= self.CB_KOSPI:
            details.append(RiskDetail("circuit_breaker", 100,
                f"서킷 브레이커 (VIX={vix:.1f}, 코스피={kospi:.1%})"))
            return 100, details

        # VIX 구간
        if   vix < 15: add = 0
        elif vix < 25: add = 10
        elif vix < 35: add = 25
        else:          add = 50
        score += add
        details.append(RiskDetail("vix", add, f"VIX={vix:.1f} 변동성 점수"))

        # 손실 한도
        loss = _portfolio.get_loss_rate(req.user_id)
        if loss <= -abs(req.user_policy.max_loss_rate):
            score += 60
            details.append(RiskDetail("loss_limit", 60,
                                      f"손실 한도 초과 ({loss:.1%})"))

        # 금액 구간
        amount = int(req.payload.get("total_amount", 0))
        if   amount < 100_000:   add = 0
        elif amount < 1_000_000: add = 10
        elif amount < 5_000_000: add = 20
        else:                    add = 35
        score += add
        details.append(RiskDetail("amount", add, f"투자 금액 {amount:,}원"))

        # 적합성 원칙
        pg = int(req.payload.get("product_risk_grade", 3))
        if pg > req.user_policy.investor_risk_grade:
            score += 30
            details.append(RiskDetail("suitability", 30,
                f"적합성 위반 (투자자 등급 {req.user_policy.investor_risk_grade} < 상품 {pg})"))
        return score, details


# ══════════════════════════════════════════════════════════════════
#  UC-003 기업 구매
# ══════════════════════════════════════════════════════════════════
class PurchaseEvaluator(BaseRiskEvaluator):
    AMOUNT_TIERS = [
        (1_000_000,    0),
        (5_000_000,   15),
        (20_000_000,  35),
        (100_000_000, 55),
    ]
    CATEGORY_RISK = {
        "CONSUMABLE":   0,
        "SERVICE":     10,
        "IT_EQUIPMENT":15,
        "ASSET":       25,
    }

    def add_specific_scores(self, req):
        score, details = 0, []
        amount      = int(req.payload.get("total_amount", 0))
        category    = str(req.payload.get("category", "CONSUMABLE"))
        urgency     = str(req.payload.get("urgency", "NORMAL"))
        dept_id     = str(req.payload.get("department_id", ""))
        budget_code = str(req.payload.get("budget_code", ""))
        item_code   = str(req.payload.get("item_code", ""))

        # 예산 초과 즉시 DENY
        if dept_id and budget_code:
            used = _erp.get_budget_used_rate(dept_id, budget_code)
            if used > 1.0:
                details.append(RiskDetail("budget_exceeded", 100,
                                          f"부서 예산 초과 ({used:.0%})"))
                return 100, details
            if used > 0.90:
                score += 20
                details.append(RiskDetail("budget_usage", 20, f"예산 {used:.0%} 소진"))
            elif used > 0.75:
                score += 10
                details.append(RiskDetail("budget_usage", 10, f"예산 {used:.0%} 소진"))

        # 금액 구간
        matched = False
        for threshold, pts in self.AMOUNT_TIERS:
            if amount < threshold:
                score += pts
                details.append(RiskDetail("amount", pts, f"구매 금액 {amount:,}원"))
                matched = True
                break
        if not matched:
            details.append(RiskDetail("amount_over", 100, "1억원 초과 — 이사회 이관"))
            return 100, details

        # 품목 위험도
        cat = self.CATEGORY_RISK.get(category, 20)
        score += cat
        details.append(RiskDetail("category", cat, f"{category} 위험도"))

        # 긴급 구매
        if urgency == "URGENT":
            score += 15
            details.append(RiskDetail("urgency", 15, "긴급 구매 가중치"))
            if dept_id and _erp.get_urgent_count(dept_id) >= 3:
                score += 10
                details.append(RiskDetail("urgency_abuse", 10, "긴급 남용 패턴"))

        # 분할 발주 패턴
        if item_code and _erp.get_recent_purchase_count(item_code, 30) >= 3:
            score += 8
            details.append(RiskDetail("split_order", 8, "분할 발주 패턴"))
        return score, details


# ══════════════════════════════════════════════════════════════════
#  UC-004 행정 서비스
# ══════════════════════════════════════════════════════════════════
class CivicEvaluator(BaseRiskEvaluator):
    SERVICE_BASE = {
        "LOCAL_TAX":    10,
        "UTILITY":      10,
        "DOC_ISSUANCE": 25,
        "WELFARE":      40,
        "RESERVATION":  15,
        "PERMIT":       50,
    }

    def add_specific_scores(self, req):
        score, details = 0, []
        svc              = str(req.payload.get("service_code", ""))
        grade            = int(req.payload.get("privacy_grade", 1))
        is_delegated     = bool(req.payload.get("is_delegated", False))
        delegation_valid = bool(req.payload.get("delegation_valid", True))
        amount           = int(req.payload.get("amount") or 0)

        # 서비스 기본 점수
        svc_score = self.SERVICE_BASE.get(svc, 20)
        score += svc_score
        details.append(RiskDetail("service_type", svc_score, f"{svc} 기본 점수"))

        # 개인정보 등급
        if grade == 4:
            details.append(RiskDetail("privacy_grade4", 100,
                                      "최고민감 개인정보(생체·범죄) — 처리 불가"))
            return 100, details
        elif grade == 3:
            score += 30
            details.append(RiskDetail("privacy_grade", 30,
                                      "고민감 개인정보(건강·복지) — 로컬 처리"))
        elif grade == 2:
            score += 15
            details.append(RiskDetail("privacy_grade", 15,
                                      "민감 개인정보(주민번호·계좌) — User Confirm"))

        # 위임 관계 검증
        if is_delegated:
            if not delegation_valid:
                details.append(RiskDetail("delegation_invalid", 100,
                                          "위임 관계 미검증 — 대리 행동 불가"))
                return 100, details
            score += 20
            details.append(RiskDetail("delegation", 20, "대리 행동 (위임 검증 완료)"))

        # 납부 금액 한도
        if amount > req.user_policy.civic_payment_limit:
            score += 25
            details.append(RiskDetail("civic_amount", 25,
                f"공과금 한도 {req.user_policy.civic_payment_limit:,}원 초과"))
        return score, details
