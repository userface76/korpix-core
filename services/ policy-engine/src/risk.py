from __future__ import annotations
from abc import ABC, abstractmethod
from .models import ActionRequest, ActionType, Decision, RiskDetail
 
 
def score_to_decision(score: int) -> Decision:
    if score < 30: return Decision.AUTO_APPROVE
    if score < 60: return Decision.USER_CONFIRM
    if score < 80: return Decision.ADMIN_APPROVE
    return Decision.DENY
 
 
class BaseRiskEvaluator(ABC):
    ACTION_BASE = {
        ActionType.PAYMENT: 15, ActionType.INVESTMENT: 20,
        ActionType.PURCHASE_REQUEST: 10, ActionType.CIVIC_SERVICE: 10,
        ActionType.SYSTEM: 5,
    }
 
    def calculate(self, req: ActionRequest) -> tuple[int, list[RiskDetail]]:
        score, details = 0, []
        base = self.ACTION_BASE.get(req.action_type, 15)
        score += base
        details.append(RiskDetail("action_type", base, f"{req.action_type.value} 기본 점수"))
        add_s, add_d = self.add_specific(req)
        return min(score + add_s, 100), details + add_d
 
    @abstractmethod
    def add_specific(self, req: ActionRequest) -> tuple[int, list[RiskDetail]]:
        ...
 
 
class PaymentRiskEvaluator(BaseRiskEvaluator):
    def add_specific(self, req):
        score, details = 0, []
        amount = int(req.payload.get("amount", 0))
        for threshold, pts in [(10_000,0),(50_000,5),(100_000,10),(500_000,20)]:
            if amount < threshold:
                score += pts
                details.append(RiskDetail("amount", pts, f"{amount:,}원 구간"))
                break
        else:
            score += 35
            details.append(RiskDetail("amount", 35, f"{amount:,}원 고액"))
        if amount > req.user_policy.single_payment_limit:
            score += 30
            details.append(RiskDetail("limit", 30, "건당 한도 초과"))
        return score, details
 
 
class InvestmentRiskEvaluator(BaseRiskEvaluator):
    def add_specific(self, req):
        score, details = 0, []
        amount = int(req.payload.get("total_amount", 0))
        product_grade = int(req.payload.get("product_risk_grade", 3))
        if   amount < 100_000:   add = 0
        elif amount < 1_000_000: add = 10
        elif amount < 5_000_000: add = 20
        else:                    add = 35
        score += add
        details.append(RiskDetail("amount", add, f"투자금액 {amount:,}원"))
        if product_grade > req.user_policy.investor_risk_grade:
            score += 30
            details.append(RiskDetail("suitability", 30, "적합성 원칙 위반"))
        return score, details
 
 
class PurchaseRiskEvaluator(BaseRiskEvaluator):
    CATEGORY_RISK = {"CONSUMABLE":0,"SERVICE":10,"IT_EQUIPMENT":15,"ASSET":25}
    AMOUNT_TIERS  = [(1_000_000,0),(5_000_000,15),(20_000_000,35),(100_000_000,55)]
 
    def add_specific(self, req):
        score, details = 0, []
        amount   = int(req.payload.get("total_amount", 0))
        category = str(req.payload.get("category", "CONSUMABLE"))
        urgency  = str(req.payload.get("urgency", "NORMAL"))
        for threshold, pts in self.AMOUNT_TIERS:
            if amount < threshold:
                score += pts
                details.append(RiskDetail("amount", pts, f"{amount:,}원"))
                break
        else:
            return 100, [RiskDetail("amount_over", 100, "1억 초과")]
        cat_pts = self.CATEGORY_RISK.get(category, 20)
        score += cat_pts
        details.append(RiskDetail("category", cat_pts, category))
        if urgency == "URGENT":
            score += 15
            details.append(RiskDetail("urgency", 15, "긴급"))
        return score, details
 
 
class CivicRiskEvaluator(BaseRiskEvaluator):
    SERVICE_BASE = {"LOCAL_TAX":10,"UTILITY":10,"DOC_ISSUANCE":25,"WELFARE":40,"RESERVATION":15}
 
    def add_specific(self, req):
        score, details = 0, []
        service_code  = str(req.payload.get("service_code", ""))
        privacy_grade = int(req.payload.get("privacy_grade", 1))
        is_delegated  = bool(req.payload.get("is_delegated", False))
        delegation_ok = bool(req.payload.get("delegation_valid", False))
        svc = self.SERVICE_BASE.get(service_code, 20)
        score += svc
        details.append(RiskDetail("service", svc, service_code))
        if privacy_grade == 4:
            return 100, [RiskDetail("privacy_4", 100, "최고민감 — 처리 불가")]
        elif privacy_grade == 3:
            score += 30
            details.append(RiskDetail("privacy_3", 30, "고민감"))
        elif privacy_grade == 2:
            score += 15
            details.append(RiskDetail("privacy_2", 15, "민감"))
        if is_delegated and not delegation_ok:
            return 100, [RiskDetail("delegation", 100, "위임 미검증")]
        if is_delegated:
            score += 20
            details.append(RiskDetail("delegation", 20, "대리 행동"))
        return score, details
 
