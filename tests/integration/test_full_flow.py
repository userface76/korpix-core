"""
KorPIX 통합 테스트 — Policy Engine + Audit Network 전체 흐름
"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.policy_engine.src.models import ActionRequest, ActionType, UserPolicy
from services.policy_engine.src.decision import PolicyEngine, Decision
from services.audit_network.src.logger import AuditLogger

def make_req(action_type, payload):
    return ActionRequest(
        request_id=str(uuid.uuid4()), action_type=action_type,
        agent_id="test-agent", user_id="test-user-hash",
        terminal_id="term-test", payload=payload,
        user_policy=UserPolicy(),
    )

def test_결제_전체_흐름():
    engine = PolicyEngine()
    logger = AuditLogger()
    req    = make_req(ActionType.PAYMENT, {
        "service":"netflix","amount":17_000,"currency":"KRW",
        "merchant":"Netflix","isRecurring":True,
    })
    result = engine.evaluate(req)
    assert result.decision == Decision.AUTO_APPROVE
    record = {
        "actionId": str(uuid.uuid4()), "agentId": req.agent_id,
        "userId": req.user_id, "terminalId": req.terminal_id,
        "actionType": req.action_type.value, "payload": req.payload,
        "riskScore": result.risk_score, "policyDecision": result.decision.value,
        "policyEngineVer": result.policy_engine_ver, "executionResult": "SUCCESS",
        "timestamp": req.timestamp,
    }
    logged = logger.record(record)
    assert "hash" in logged
    ok, broken = logger.verify_integrity()
    assert ok is True and broken is None

def test_한도초과_차단_감사기록():
    engine = PolicyEngine()
    logger = AuditLogger()
    req    = make_req(ActionType.PAYMENT, {
        "service":"annual","amount":600_000,"currency":"KRW",
        "merchant":"Cloud","isRecurring":False,
    })
    result = engine.evaluate(req)
    assert result.decision == Decision.DENY
    record = {
        "actionId": str(uuid.uuid4()), "agentId": req.agent_id,
        "userId": req.user_id, "terminalId": req.terminal_id,
        "actionType": req.action_type.value, "payload": req.payload,
        "riskScore": result.risk_score, "policyDecision": result.decision.value,
        "policyEngineVer": result.policy_engine_ver, "executionResult": "BLOCKED",
        "timestamp": req.timestamp,
    }
    logger.record(record)
    ok, _ = logger.verify_integrity()
    assert ok is True

if __name__ == "__main__":
    test_결제_전체_흐름()
    test_한도초과_차단_감사기록()
    print("✅ 통합 테스트 통과")
