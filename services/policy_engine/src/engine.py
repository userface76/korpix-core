"""
KorPIX Policy Engine — 메인 엔진
"""
from __future__ import annotations
from .models import ActionRequest, ActionType, PolicyResult
from .risk import (
    PaymentEvaluator, InvestmentEvaluator,
    PurchaseEvaluator, CivicEvaluator,
)


class PolicyEngine:
    _evaluators = {
        ActionType.PAYMENT:          PaymentEvaluator(),
        ActionType.INVESTMENT:       InvestmentEvaluator(),
        ActionType.PURCHASE_REQUEST: PurchaseEvaluator(),
        ActionType.CIVIC_SERVICE:    CivicEvaluator(),
    }

    def evaluate(self, request: ActionRequest) -> PolicyResult:
        evaluator = self._evaluators.get(request.action_type)
        if evaluator is None:
            raise ValueError(f"지원하지 않는 ActionType: {request.action_type}")
        return evaluator.evaluate(request)
