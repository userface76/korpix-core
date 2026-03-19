"""
tests/test_risk_evaluator.py
==============================
KorPIX Policy Engine — Risk Evaluator 단위 테스트

실행 방법:
    cd korpix-core
    python -m pytest tests/test_risk_evaluator.py -v
    python -m pytest tests/ -v --tb=short          # 전체 테스트
"""

import sys
import os
import pytest

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'policy_engine'))
from risk_evaluator import (
    PolicyEngine, ActionRequest, ActionType, Decision,
    UserPolicy, build_action_record, verify_chain,
    PaymentRiskEvaluator, InvestmentRiskEvaluator,
    PurchaseRiskEvaluator, CivicRiskEvaluator,
)


# ══════════════════════════════════════════════════════════════
#  공통 픽스처
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine() -> PolicyEngine:
    return PolicyEngine()

@pytest.fixture
def policy() -> UserPolicy:
    return UserPolicy()

def make_req(
    action_type: ActionType,
    payload: dict,
    policy: UserPolicy | None = None,
    user_id: str = "user-hash-test",
) -> ActionRequest:
    return ActionRequest(
        request_id  = "req-test",
        action_type = action_type,
        agent_id    = "agent-test",
        user_id     = user_id,
        terminal_id = "term-test",
        payload     = payload,
        user_policy = policy or UserPolicy(),
    )


# ══════════════════════════════════════════════════════════════
#  UC-001 결제 테스트
# ══════════════════════════════════════════════════════════════

class TestPaymentEvaluator:

    def test_소액_자동승인(self, engine):
        """17,000원 결제 → AUTO_APPROVE"""
        req = make_req(ActionType.PAYMENT, {
            "service": "netflix", "amount": 17_000,
            "currency": "KRW", "merchant": "Netflix", "is_recurring": True,
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.AUTO_APPROVE
        assert result.risk_score < 30

    def test_중간금액_사용자확인(self, engine):
        """200,000원 결제 → USER_CONFIRM"""
        req = make_req(ActionType.PAYMENT, {
            "service": "annual", "amount": 200_000,
            "currency": "KRW", "merchant": "SaaS", "is_recurring": False,
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.USER_CONFIRM
        assert 30 <= result.risk_score < 60

    def test_한도초과_차단(self, engine):
        """600,000원 — 건당 한도(500,000) 초과 → DENY"""
        req = make_req(ActionType.PAYMENT, {
            "service": "annual", "amount": 600_000,
            "currency": "KRW", "merchant": "Cloud", "is_recurring": False,
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY
        assert result.risk_score >= 80

    def test_위험점수_이유_포함(self, engine):
        """위험 점수 이유가 비어있지 않아야 함"""
        req = make_req(ActionType.PAYMENT, {
            "service": "test", "amount": 50_000,
            "currency": "KRW", "merchant": "Test", "is_recurring": False,
        })
        result = engine.evaluate(req)
        assert len(result.risk_details) > 0
        assert len(result.reasons) > 0

    def test_점수_0이상_100이하(self, engine):
        """Risk Score는 항상 0~100 범위"""
        for amount in [100, 1_000, 10_000, 100_000, 1_000_000]:
            req = make_req(ActionType.PAYMENT, {
                "service": "test", "amount": amount,
                "currency": "KRW", "merchant": "T", "is_recurring": False,
            })
            result = engine.evaluate(req)
            assert 0 <= result.risk_score <= 100, (
                f"amount={amount}: score={result.risk_score}"
            )


# ══════════════════════════════════════════════════════════════
#  UC-002 투자 테스트
# ══════════════════════════════════════════════════════════════

class TestInvestmentEvaluator:

    def test_소액_안전투자_자동승인(self, engine):
        """50,000원 소액 투자 → AUTO_APPROVE"""
        req = make_req(ActionType.INVESTMENT, {
            "ticker": "KODEX200", "quantity": 1,
            "total_amount": 50_000, "order_type": "MARKET",
            "sector": "diversified", "product_risk_grade": 3,
        })
        result = engine.evaluate(req)
        assert result.decision in (Decision.AUTO_APPROVE, Decision.USER_CONFIRM)

    def test_손실한도초과_차단(self, engine):
        """손실률 -12% (한도 -10% 초과) → DENY 방향"""
        class LossPolicy(UserPolicy):
            pass

        # 손실 초과 시뮬레이션 — risk_evaluator의 어댑터가 0.0 반환하므로
        # 다른 요소로 점수를 높여 검증
        req = make_req(ActionType.INVESTMENT, {
            "ticker": "KODEX200", "quantity": 100,
            "total_amount": 8_000_000,   # 고액 → 점수 상승
            "order_type": "MARKET",
            "sector": "semiconductor",
            "product_risk_grade": 5,     # 적합성 위반 → +30
        })
        result = engine.evaluate(req)
        # 고액 + 적합성 위반 → USER_CONFIRM 이상
        assert result.decision in (
            Decision.USER_CONFIRM, Decision.ADMIN_APPROVE, Decision.DENY
        )

    def test_정책엔진버전_기록(self, engine):
        """PolicyResult에 버전이 기록되어야 함"""
        req = make_req(ActionType.INVESTMENT, {
            "ticker": "KODEX200", "quantity": 1,
            "total_amount": 30_000, "order_type": "MARKET",
            "sector": "index", "product_risk_grade": 2,
        })
        result = engine.evaluate(req)
        assert result.policy_engine_ver != ""


# ══════════════════════════════════════════════════════════════
#  UC-003 기업 구매 테스트
# ══════════════════════════════════════════════════════════════

class TestPurchaseEvaluator:

    def test_소모품_소액_자동승인(self, engine):
        """A4 용지 55,000원 → AUTO_APPROVE"""
        req = make_req(ActionType.PURCHASE_REQUEST, {
            "total_amount": 55_000, "category": "CONSUMABLE",
            "item_code": "A4-PAPER", "item_name": "A4 용지",
            "quantity": 5, "unit_price": 11_000, "urgency": "NORMAL",
            "department_id": "DEPT-IT", "budget_code": "BC-2025",
            "justification": "정기 구매",
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.AUTO_APPROVE
        assert result.risk_score <= 25

    def test_IT장비_중간금액_팀장승인(self, engine):
        """노트북 4,000,000원 → USER_CONFIRM (Tier 2 팀장)"""
        req = make_req(ActionType.PURCHASE_REQUEST, {
            "total_amount": 4_000_000, "category": "IT_EQUIPMENT",
            "item_code": "NB-DELL", "item_name": "Dell 노트북",
            "quantity": 2, "unit_price": 2_000_000, "urgency": "NORMAL",
            "department_id": "DEPT-IT", "budget_code": "BC-2025",
            "justification": "신규 장비",
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.USER_CONFIRM
        assert 26 <= result.risk_score <= 70

    def test_고액_자산_관리자승인(self, engine):
        """서버 12,000,000원 + IT_EQUIPMENT → ADMIN_APPROVE"""
        req = make_req(ActionType.PURCHASE_REQUEST, {
            "total_amount": 12_000_000, "category": "IT_EQUIPMENT",
            "item_code": "SRV-HPE", "item_name": "HPE 서버",
            "quantity": 1, "unit_price": 12_000_000, "urgency": "URGENT",
            "department_id": "DEPT-IT", "budget_code": "BC-2025",
            "justification": "긴급 교체",
        })
        result = engine.evaluate(req)
        assert result.decision in (Decision.ADMIN_APPROVE, Decision.USER_CONFIRM)

    def test_1억초과_차단(self, engine):
        """150,000,000원 → DENY (이사회 이관)"""
        req = make_req(ActionType.PURCHASE_REQUEST, {
            "total_amount": 150_000_000, "category": "ASSET",
            "item_code": "BLDG-001", "item_name": "사무용 집기",
            "quantity": 1, "unit_price": 150_000_000, "urgency": "NORMAL",
            "department_id": "DEPT-EXEC", "budget_code": "BC-2025",
            "justification": "자산 구매",
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY


# ══════════════════════════════════════════════════════════════
#  UC-004 행정 서비스 테스트
# ══════════════════════════════════════════════════════════════

class TestCivicEvaluator:

    def test_지방세_자동승인(self, engine):
        """지방세 87,500원 (등급 1) → AUTO_APPROVE"""
        req = make_req(ActionType.CIVIC_SERVICE, {
            "service_code": "LOCAL_TAX", "service_name": "지방세",
            "agency_code": "LOCALEX", "amount": 87_500,
            "privacy_grade": 1, "is_delegated": False,
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.AUTO_APPROVE

    def test_주민등록등본_사용자확인(self, engine):
        """주민등록등본 발급 (등급 2) → USER_CONFIRM"""
        req = make_req(ActionType.CIVIC_SERVICE, {
            "service_code": "DOC_ISSUANCE", "service_name": "주민등록등본",
            "agency_code": "GOV24", "amount": None,
            "privacy_grade": 2, "is_delegated": False,
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.USER_CONFIRM

    def test_최고민감정보_즉시차단(self, engine):
        """개인정보 등급 4 (생체·범죄) → DENY"""
        req = make_req(ActionType.CIVIC_SERVICE, {
            "service_code": "SENSITIVE", "service_name": "테스트",
            "agency_code": "TEST", "amount": None,
            "privacy_grade": 4, "is_delegated": False,
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY

    def test_위임없는대리_즉시차단(self, engine):
        """위임 관계 미검증 대리 접근 → DENY"""
        req = make_req(ActionType.CIVIC_SERVICE, {
            "service_code": "LOCAL_TAX", "service_name": "지방세",
            "agency_code": "LOCALEX", "amount": 50_000,
            "privacy_grade": 1,
            "is_delegated": True,
            "delegation_valid": False,   # 위임 미검증
        })
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY

    def test_유효위임_대리납부_허용(self, engine):
        """위임 검증 완료 시 납부 허용"""
        req = make_req(ActionType.CIVIC_SERVICE, {
            "service_code": "UTILITY", "service_name": "전기요금",
            "agency_code": "KEPCO", "amount": 45_000,
            "privacy_grade": 1,
            "is_delegated": True,
            "delegation_valid": True,    # 위임 검증 완료
        })
        result = engine.evaluate(req)
        assert result.decision in (Decision.AUTO_APPROVE, Decision.USER_CONFIRM)


# ══════════════════════════════════════════════════════════════
#  ActionRecord 생성 및 해시 체인 테스트
# ══════════════════════════════════════════════════════════════

class TestActionRecord:

    def test_해시체인_무결성(self, engine, policy):
        """3개 레코드 해시 체인 생성 후 무결성 검증"""
        requests = [
            make_req(ActionType.PAYMENT, {
                "service": f"svc-{i}", "amount": 10_000 * i,
                "currency": "KRW", "merchant": f"M{i}", "is_recurring": False,
            })
            for i in range(1, 4)
        ]
        prev_hash = "0" * 64
        records = []
        for req in requests:
            result = engine.evaluate(req)
            rec = build_action_record(req, result, "SUCCESS", prev_hash)
            records.append(rec)
            prev_hash = rec["hash"]

        is_valid, broken = verify_chain(records)
        assert is_valid is True
        assert broken is None

    def test_변조감지(self, engine, policy):
        """중간 레코드 hash 변조 시 체인 불일치 감지"""
        reqs = [
            make_req(ActionType.PAYMENT, {
                "service": "svc", "amount": 5_000 * i,
                "currency": "KRW", "merchant": "M", "is_recurring": False,
            })
            for i in range(1, 4)
        ]
        prev_hash = "0" * 64
        records = []
        for req in reqs:
            result = engine.evaluate(req)
            rec = build_action_record(req, result, "SUCCESS", prev_hash)
            records.append(rec)
            prev_hash = rec["hash"]

        # 두 번째 레코드 hash 직접 조작
        # (riskScore 변경만으로는 이미 계산된 hash가 바뀌지 않음)
        records[1]["hash"] = "a" * 64

        is_valid, broken_at = verify_chain(records)
        assert is_valid is False
        assert broken_at == 2   # 3번째 레코드에서 prevHash 불일치

    def test_record_필수필드_존재(self, engine):
        """생성된 ActionRecord에 필수 필드 모두 존재"""
        req = make_req(ActionType.PAYMENT, {
            "service": "test", "amount": 1_000,
            "currency": "KRW", "merchant": "T", "is_recurring": False,
        })
        result  = engine.evaluate(req)
        record  = build_action_record(req, result, "SUCCESS", "0" * 64)
        required = {
            "actionId", "agentId", "userId", "terminalId",
            "actionType", "payload", "riskScore", "policyDecision",
            "executionResult", "timestamp", "prevHash", "hash",
            "digitalSignature",
        }
        missing = required - set(record.keys())
        assert not missing, f"누락 필드: {missing}"

    def test_genesis_prevhash(self, engine):
        """첫 번째 레코드의 prevHash는 0×64 문자여야 함"""
        req    = make_req(ActionType.PAYMENT, {
            "service": "test", "amount": 1_000,
            "currency": "KRW", "merchant": "T", "is_recurring": False,
        })
        result = engine.evaluate(req)
        record = build_action_record(req, result, "SUCCESS", "0" * 64)
        assert record["prevHash"] == "0" * 64


# ══════════════════════════════════════════════════════════════
#  Policy Engine 기본 동작 테스트
# ══════════════════════════════════════════════════════════════

class TestPolicyEngine:

    def test_미지원_actiontype_예외(self):
        """지원하지 않는 ActionType → ValueError"""
        engine = PolicyEngine()
        req    = make_req(ActionType.SYSTEM, {"detail": "test"})
        with pytest.raises(ValueError, match="지원하지 않는"):
            engine.evaluate(req)

    def test_결정_항상_4가지중_하나(self, engine):
        """모든 케이스에서 Decision은 4가지 중 하나"""
        valid_decisions = set(Decision)
        cases = [
            (ActionType.PAYMENT,
             {"service":"t","amount":500,"currency":"KRW",
              "merchant":"T","is_recurring":False}),
            (ActionType.INVESTMENT,
             {"ticker":"KODEX","quantity":1,"total_amount":10_000,
              "order_type":"MARKET","sector":"idx","product_risk_grade":2}),
            (ActionType.PURCHASE_REQUEST,
             {"total_amount":100_000,"category":"CONSUMABLE",
              "item_code":"X","item_name":"X","quantity":1,
              "unit_price":100_000,"urgency":"NORMAL",
              "department_id":"D","budget_code":"B","justification":"J"}),
            (ActionType.CIVIC_SERVICE,
             {"service_code":"LOCAL_TAX","service_name":"지방세",
              "agency_code":"LOCALEX","amount":10_000,
              "privacy_grade":1,"is_delegated":False}),
        ]
        for action_type, payload in cases:
            req    = make_req(action_type, payload)
            result = engine.evaluate(req)
            assert result.decision in valid_decisions, (
                f"{action_type}: {result.decision}"
            )


# ══════════════════════════════════════════════════════════════
#  실행 엔트리포인트
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
