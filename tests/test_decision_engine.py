"""
tests/test_decision_engine.py
===============================
KorPIX Policy Engine — Decision Engine 단위 테스트

실행:
    python -m pytest tests/test_decision_engine.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'policy-engine'))
from risk_evaluator import (
    PolicyEngine, ActionRequest, ActionType, Decision,
    UserPolicy, build_action_record,
)
from decision_engine import (
    DecisionEngine, CircuitBreaker,
    ApprovalChainBuilder, OrgChartAdapter,
    ApprovalStatus, TIER_THRESHOLDS,
)


# ──────────────────────────────────────────────────────────────
#  픽스처
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def risk_engine():
    return PolicyEngine()

@pytest.fixture
def decision_engine():
    return DecisionEngine()

@pytest.fixture
def org():
    return OrgChartAdapter()

@pytest.fixture
def chain_builder(org):
    return ApprovalChainBuilder(org)

def purchase_req(amount: int, urgency: str = "NORMAL") -> ActionRequest:
    return ActionRequest(
        request_id="req-test",
        action_type=ActionType.PURCHASE_REQUEST,
        agent_id="agent-test",
        user_id="user-hash-test",
        terminal_id="term-test",
        payload={
            "total_amount": amount, "category": "IT_EQUIPMENT",
            "item_code": "ITEM-001", "item_name": "테스트 품목",
            "quantity": 1, "unit_price": amount, "urgency": urgency,
            "requester_id": "EMP-001",
            "department_id": "DEPT-IT", "budget_code": "BC-2025",
            "justification": "테스트",
        },
        user_policy=UserPolicy(),
    )


# ══════════════════════════════════════════════════════════════
#  기본 결정 흐름 테스트
# ══════════════════════════════════════════════════════════════

class TestDecisionFlow:

    def test_자동승인_알림없음(self, risk_engine, decision_engine):
        """AUTO_APPROVE → requires_notify=False"""
        req = ActionRequest(
            request_id="r1", action_type=ActionType.PAYMENT,
            agent_id="a1", user_id="u1", terminal_id="t1",
            payload={"service":"netflix","amount":17_000,
                     "currency":"KRW","merchant":"Netflix",
                     "is_recurring":True},
            user_policy=UserPolicy(),
        )
        pr  = risk_engine.evaluate(req)
        dr  = decision_engine.decide(req, pr)
        assert dr.decision == Decision.AUTO_APPROVE
        assert dr.requires_notify is False
        assert dr.approval_chain is None

    def test_차단_알림있음(self, risk_engine, decision_engine):
        """DENY → requires_notify=True, 메시지 존재"""
        req = ActionRequest(
            request_id="r2", action_type=ActionType.PAYMENT,
            agent_id="a1", user_id="u1", terminal_id="t1",
            payload={"service":"annual","amount":600_000,
                     "currency":"KRW","merchant":"Cloud",
                     "is_recurring":False},
            user_policy=UserPolicy(),
        )
        pr  = risk_engine.evaluate(req)
        dr  = decision_engine.decide(req, pr)
        assert dr.decision == Decision.DENY
        assert dr.requires_notify is True
        assert dr.notify_message is not None

    def test_result_id_존재(self, risk_engine, decision_engine):
        """DecisionResult에 항상 result_id가 존재해야 함"""
        req = ActionRequest(
            request_id="r3", action_type=ActionType.CIVIC_SERVICE,
            agent_id="a1", user_id="u1", terminal_id="t1",
            payload={"service_code":"LOCAL_TAX","service_name":"지방세",
                     "agency_code":"LOCALEX","amount":50_000,
                     "privacy_grade":1,"is_delegated":False},
            user_policy=UserPolicy(),
        )
        pr  = risk_engine.evaluate(req)
        dr  = decision_engine.decide(req, pr)
        assert dr.result_id != ""
        assert dr.decided_at != ""


# ══════════════════════════════════════════════════════════════
#  승인 체인 빌더 테스트
# ══════════════════════════════════════════════════════════════

class TestApprovalChainBuilder:

    def test_tier1_자동_체인없음(self, chain_builder):
        """100만원 미만 → Tier 1, 결재 단계 없음"""
        req    = purchase_req(500_000)
        chain  = chain_builder.build(req, risk_score=10)
        assert chain.tier  == 1
        assert len(chain.steps) == 0

    def test_tier2_팀장단독(self, chain_builder):
        """400만원 → Tier 2, 팀장 1명"""
        req   = purchase_req(4_000_000)
        chain = chain_builder.build(req, risk_score=38)
        assert chain.tier == 2
        assert len(chain.steps) == 1
        assert chain.steps[0].role == "팀장"

    def test_tier3_직렬결재(self, chain_builder):
        """1200만원 일반 → Tier 3, 팀장→재무팀 직렬 (2단계)"""
        req   = purchase_req(12_000_000)
        chain = chain_builder.build(req, risk_score=62)
        assert chain.tier == 3
        assert len(chain.steps) == 2
        assert chain.steps[0].role == "팀장"
        assert chain.steps[1].role == "재무팀"
        # 일반 구매 → 병렬 없음
        assert all(not s.parallel for s in chain.steps)

    def test_tier3_긴급_병렬결재(self, chain_builder):
        """1200만원 긴급 → Tier 3, 팀장+재무팀 병렬"""
        req   = purchase_req(12_000_000, urgency="URGENT")
        chain = chain_builder.build(req, risk_score=62, is_urgent=True)
        assert chain.tier == 3
        assert chain.is_fast_track is True
        assert len(chain.steps) == 2
        assert all(s.parallel for s in chain.steps)

    def test_tier4_cfo포함(self, chain_builder):
        """5000만원 → Tier 4, 팀장→재무팀→CFO (3단계)"""
        req   = purchase_req(50_000_000)
        chain = chain_builder.build(req, risk_score=72)
        assert chain.tier == 4
        assert len(chain.steps) == 3
        roles  = [s.role for s in chain.steps]
        assert "팀장"   in roles
        assert "재무팀" in roles
        assert "CFO"    in roles

    def test_tier5_이사회_체인없음(self, chain_builder):
        """1억5천만원 → Tier 5, 체인 없음 (DENY로 이관)"""
        req   = purchase_req(150_000_000)
        chain = chain_builder.build(req, risk_score=90)
        assert chain.tier == 5
        assert len(chain.steps) == 0

    def test_긴급_타임아웃_단축(self, chain_builder):
        """긴급 구매의 타임아웃은 일반의 1/12 (2시간 vs 24시간)"""
        req_normal = purchase_req(4_000_000, urgency="NORMAL")
        req_urgent = purchase_req(4_000_000, urgency="URGENT")

        chain_n = chain_builder.build(req_normal, risk_score=38)
        chain_u = chain_builder.build(req_urgent, risk_score=53, is_urgent=True)

        assert chain_n.steps[0].timeout_sec == 86_400  # 24시간
        assert chain_u.steps[0].timeout_sec == 7_200   # 2시간


# ══════════════════════════════════════════════════════════════
#  승인 처리 테스트
# ══════════════════════════════════════════════════════════════

class TestApprovalProcessing:

    def test_팀장승인_완료(self, risk_engine, decision_engine):
        """팀장 1명만 있는 체인 → 승인 후 체인 완료"""
        req = purchase_req(4_000_000)
        pr  = risk_engine.evaluate(req)
        dr  = decision_engine.decide(req, pr)

        assert dr.approval_chain is not None
        chain = dr.approval_chain
        step  = chain.steps[0]

        result = decision_engine.process_approval(
            chain_id=chain.chain_id,
            step_id=step.step_id,
            approver_id="EMP-010",
            approved=True,
            comment="승인합니다.",
        )
        assert result["chain_complete"] is True
        assert result["chain_rejected"] is False
        assert result["next_approver"]  is None

    def test_반려시_체인_종료(self, risk_engine, decision_engine):
        """팀장이 반려하면 체인이 즉시 반려 상태"""
        req   = purchase_req(4_000_000)
        pr    = risk_engine.evaluate(req)
        dr    = decision_engine.decide(req, pr)
        chain = dr.approval_chain
        step  = chain.steps[0]

        result = decision_engine.process_approval(
            chain_id=chain.chain_id,
            step_id=step.step_id,
            approver_id="EMP-010",
            approved=False,
            comment="예산 초과로 반려합니다.",
        )
        assert result["chain_rejected"] is True
        assert result["chain_complete"] is False

    def test_tier3_단계적_완료(self, risk_engine, decision_engine):
        """Tier 3 — 팀장 → 재무팀 순서로 모두 승인 시 체인 완료"""
        req   = purchase_req(12_000_000)
        pr    = risk_engine.evaluate(req)
        dr    = decision_engine.decide(req, pr)
        chain = dr.approval_chain
        assert len(chain.steps) >= 2

        # 1단계: 팀장 승인
        r1 = decision_engine.process_approval(
            chain_id=chain.chain_id,
            step_id=chain.steps[0].step_id,
            approver_id="EMP-010", approved=True,
        )
        assert r1["chain_complete"] is False

        # 2단계: 재무팀 승인
        r2 = decision_engine.process_approval(
            chain_id=chain.chain_id,
            step_id=chain.steps[1].step_id,
            approver_id="EMP-020", approved=True,
        )
        assert r2["chain_complete"] is True

    def test_존재하지않는_체인_예외(self, decision_engine):
        """없는 chain_id → ValueError"""
        with pytest.raises(ValueError, match="체인을 찾을 수 없음"):
            decision_engine.process_approval(
                chain_id="nonexistent",
                step_id="any",
                approver_id="EMP-001",
                approved=True,
            )


# ══════════════════════════════════════════════════════════════
#  서킷 브레이커 테스트
# ══════════════════════════════════════════════════════════════

class TestCircuitBreaker:

    def test_정상_미발동(self):
        """정상 시장 → 서킷 브레이커 미발동"""
        cb = CircuitBreaker()
        triggered = cb.check_and_trigger(vix=15.0, kospi_change=-0.01)
        assert triggered is False
        assert cb.is_triggered is False

    def test_vix초과_발동(self):
        """VIX ≥ 35 → 서킷 브레이커 발동"""
        cb = CircuitBreaker()
        triggered = cb.check_and_trigger(vix=37.5, kospi_change=-0.02)
        assert triggered is True
        assert cb.is_triggered is True

    def test_코스피급락_발동(self):
        """코스피 -5% 이상 하락 → 발동"""
        cb = CircuitBreaker()
        triggered = cb.check_and_trigger(vix=20.0, kospi_change=-0.062)
        assert triggered is True

    def test_수동확인없이_해제불가(self):
        """manual_confirm=False → 해제 실패"""
        cb = CircuitBreaker()
        cb.check_and_trigger(vix=40.0, kospi_change=-0.08)
        result = cb.deactivate(user_id="u1", manual_confirm=False)
        assert result is False
        assert cb.is_triggered is True

    def test_수동확인_해제성공(self):
        """manual_confirm=True → 해제 성공"""
        cb = CircuitBreaker()
        cb.check_and_trigger(vix=40.0, kospi_change=-0.08)
        result = cb.deactivate(user_id="u1", manual_confirm=True)
        assert result is True
        assert cb.is_triggered is False

    def test_발동상태_투자차단(self, risk_engine):
        """서킷 브레이커 발동 중 투자 요청 → DENY"""
        cb     = CircuitBreaker()
        cb.check_and_trigger(vix=40.0, kospi_change=-0.07)
        engine = DecisionEngine(circuit_breaker=cb)

        req = ActionRequest(
            request_id="r-cb", action_type=ActionType.INVESTMENT,
            agent_id="a1", user_id="u1", terminal_id="t1",
            payload={"ticker":"KODEX","quantity":1,"total_amount":50_000,
                     "order_type":"MARKET","sector":"idx",
                     "product_risk_grade":2},
            user_policy=UserPolicy(),
        )
        pr = risk_engine.evaluate(req)
        dr = engine.decide(req, pr)
        assert dr.decision == Decision.DENY
        assert "서킷 브레이커" in (dr.notify_message or "")

    def test_발동후_재발동_유지(self):
        """이미 발동 상태에서 check_and_trigger → True 유지"""
        cb = CircuitBreaker()
        cb.check_and_trigger(vix=36.0, kospi_change=-0.03)
        # 두 번째 호출도 True
        result = cb.check_and_trigger(vix=14.0, kospi_change=0.01)
        assert result is True


# ══════════════════════════════════════════════════════════════
#  실행
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
