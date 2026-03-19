"""
KorPIX 통합 테스트 — 전체 파이프라인
Policy Engine → Execution Gateway → Audit Network 순서 통합 검증
"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services'))

from policy_engine.src.models   import ActionRequest, ActionType, UserPolicy
from policy_engine.src.engine   import PolicyEngine
from policy_engine.src.decision import DecisionEngine, Decision, CircuitBreaker
from audit_network.src.hashchain import HashChain
from audit_network.src.gateway  import AuditGateway, make_terminal_log
from execution_gateway.src.gateway import ExecutionGateway, ExecutionRequest

import hashlib, json


# ── 공통 픽스처 ──────────────────────────────────────────────────
def make_req(action_type, payload, uid="user-hash-test"):
    return ActionRequest.new(
        action_type=action_type, agent_id="agent-test",
        user_id=uid, terminal_id="term-test",
        payload=payload, user_policy=UserPolicy(),
    )

def build_record(req, result, prev_hash="0"*64):
    record = {
        "actionId":        str(uuid.uuid4()),
        "agentId":         req.agent_id,
        "userId":          req.user_id,
        "terminalId":      req.terminal_id,
        "actionType":      req.action_type.value,
        "payload":         req.payload,
        "riskScore":       result.risk_score,
        "policyDecision":  result.decision.value,
        "policyEngineVer": "0.1.0",
        "executionResult": "SUCCESS",
        "timestamp":       req.timestamp,
        "prevHash":        prev_hash,
    }
    r = {k: v for k, v in record.items() if k not in ("hash","digitalSignature")}
    record["hash"] = hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    record["digitalSignature"] = hashlib.sha256(f"SOFT_SIG:{record['hash']}".encode()).hexdigest()
    return record


def test_uc001_payment_full_pipeline():
    """UC-001: 결제 → 자동 승인 → 실행 → 감사 기록 전체 파이프라인"""
    pe  = PolicyEngine()
    de  = DecisionEngine()
    gw  = AuditGateway("gw-integ")
    ex  = ExecutionGateway()

    req    = make_req(ActionType.PAYMENT, {"service":"netflix","amount":17000,"currency":"KRW","merchant":"N","is_recurring":True})
    pr     = pe.evaluate(req)
    dr     = de.decide(req, pr)
    assert dr.decision == Decision.AUTO_APPROVE

    exec_result = ex.execute(ExecutionRequest(
        action_id=str(uuid.uuid4()), action_type="PAYMENT", payload=req.payload
    ))
    assert exec_result.status == "SUCCESS"
    assert "receipt_id" in exec_result.response

    rec    = build_record(req, pr)
    entry  = make_terminal_log(rec)
    result = gw.process(entry)
    assert result.success
    assert gw.ledger_count == 1

    is_valid, broken = gw.verify_integrity()
    assert is_valid and broken is None


def test_uc002_investment_circuit_breaker():
    """UC-002: 서킷 브레이커 발동 → 투자 DENY → Audit 기록"""
    pe = PolicyEngine()
    cb = CircuitBreaker()
    de = DecisionEngine(circuit_breaker=cb)
    gw = AuditGateway("gw-integ-cb")

    cb.check_and_trigger(vix=40.0, kospi_change=-0.08)
    assert cb.is_triggered

    req = make_req(ActionType.INVESTMENT, {
        "ticker":"KODEX200","quantity":10,"total_amount":300000,
        "order_type":"MARKET","sector":"diversified","product_risk_grade":2
    })
    pr = pe.evaluate(req)
    dr = de.decide(req, pr)
    assert dr.decision == Decision.DENY
    assert "서킷 브레이커" in (dr.notify_message or "")

    rec   = build_record(req, pr)
    rec["policyDecision"] = "DENY"
    rec["executionResult"] = "BLOCKED"
    rec["hash"] = hashlib.sha256(
        json.dumps({k:v for k,v in rec.items() if k not in ("hash","digitalSignature")},
                   sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    rec["digitalSignature"] = hashlib.sha256(f"SOFT_SIG:{rec['hash']}".encode()).hexdigest()
    result = gw.process(make_terminal_log(rec))
    assert result.success


def test_uc003_purchase_approval_chain():
    """UC-003: 구매 요청 → Tier 2 팀장 결재 체인 → 승인 완료 → 실행"""
    pe = PolicyEngine()
    de = DecisionEngine()
    ex = ExecutionGateway()

    req = make_req(ActionType.PURCHASE_REQUEST, {
        "total_amount":4_000_000,"category":"IT_EQUIPMENT",
        "item_code":"NB-DELL","item_name":"Dell 노트북","quantity":2,
        "unit_price":2_000_000,"urgency":"NORMAL",
        "requester_id":"EMP-001","department_id":"DEPT-IT",
        "budget_code":"BC-2025","justification":"신규 장비"
    })
    pr = pe.evaluate(req)
    dr = de.decide(req, pr)
    assert dr.approval_chain is not None
    assert dr.approval_chain.tier == 2
    assert len(dr.approval_chain.steps) == 1

    chain  = dr.approval_chain
    step   = chain.steps[0]
    result = de.process_approval(chain.chain_id, step.step_id, "EMP-010", True, "승인")
    assert result["chain_complete"] is True

    exec_result = ex.execute(ExecutionRequest(
        action_id=str(uuid.uuid4()), action_type="PURCHASE_REQUEST", payload=req.payload
    ))
    assert exec_result.status == "SUCCESS"
    assert "po_id" in exec_result.response


def test_uc004_civic_privacy_guard():
    """UC-004: 개인정보 등급 4 → 즉시 DENY → Audit 기록"""
    pe = PolicyEngine()
    de = DecisionEngine()
    gw = AuditGateway("gw-integ-civic")

    req = make_req(ActionType.CIVIC_SERVICE, {
        "service_code":"SENSITIVE","service_name":"테스트",
        "agency_code":"TEST","amount":None,
        "privacy_grade":4,"is_delegated":False
    })
    pr = pe.evaluate(req)
    dr = de.decide(req, pr)
    assert dr.decision == Decision.DENY

    rec   = build_record(req, pr)
    rec["executionResult"] = "BLOCKED"
    rec["hash"] = hashlib.sha256(
        json.dumps({k:v for k,v in rec.items() if k not in ("hash","digitalSignature")},
                   sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    rec["digitalSignature"] = hashlib.sha256(f"SOFT_SIG:{rec['hash']}".encode()).hexdigest()
    result = gw.process(make_terminal_log(rec))
    assert result.success


def test_multi_record_chain_integrity():
    """다중 레코드 해시 체인 무결성 — 5건 연속 처리 후 검증"""
    pe   = PolicyEngine()
    gw   = AuditGateway("gw-integ-chain")
    prev = "0" * 64

    for i in range(5):
        req  = make_req(ActionType.PAYMENT, {
            "service":f"svc-{i}","amount":(i+1)*10000,
            "currency":"KRW","merchant":"M","is_recurring":False
        })
        pr   = pe.evaluate(req)
        rec  = build_record(req, pr, prev_hash=prev)
        prev = rec["hash"]
        r    = gw.process(make_terminal_log(rec))
        assert r.success, f"[{i}] 처리 실패: {r.error_detail}"

    assert gw.ledger_count == 5
    is_valid, broken = gw.verify_integrity()
    assert is_valid and broken is None


def test_audit_tamper_detection():
    """감사 기록 변조 탐지 — hash 조작 시 FAILED_HASH 반환"""
    from audit_network.src.gateway import TerminalLogEntry, VerificationStatus
    import copy

    pe  = PolicyEngine()
    gw  = AuditGateway("gw-integ-tamper")

    req = make_req(ActionType.PAYMENT, {
        "service":"test","amount":5000,"currency":"KRW","merchant":"T","is_recurring":False
    })
    pr  = pe.evaluate(req)
    rec = build_record(req, pr)

    tampered = copy.deepcopy(rec)
    tampered["actionId"]  = str(uuid.uuid4())
    tampered["riskScore"] = 99

    entry = TerminalLogEntry(
        log_id       = str(uuid.uuid4()),
        terminal_id  = tampered["terminalId"],
        action_record= tampered,
        terminal_hash= tampered["hash"],
        terminal_sig = hashlib.sha256(f"SOFT_SIG:{tampered['hash']}".encode()).hexdigest(),
        created_at   = tampered["timestamp"],
    )
    result = gw.process(entry)
    assert result.verification_status == VerificationStatus.FAILED_HASH


if __name__ == "__main__":
    tests = [
        ("UC-001 결제 전체 파이프라인",          test_uc001_payment_full_pipeline),
        ("UC-002 서킷 브레이커 DENY",            test_uc002_investment_circuit_breaker),
        ("UC-003 구매 승인 체인 → 실행",          test_uc003_purchase_approval_chain),
        ("UC-004 개인정보 등급4 DENY",            test_uc004_civic_privacy_guard),
        ("다중 레코드 해시 체인 무결성 (5건)",    test_multi_record_chain_integrity),
        ("감사 기록 변조 탐지",                   test_audit_tamper_detection),
    ]

    passed = failed = 0
    print("=" * 60)
    print("KorPIX 통합 테스트")
    print("=" * 60)
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅  {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌  {name}  →  {e}")
            failed += 1

    total = passed + failed
    print(f"\n결과: {passed}/{total}  {'✅ ALL PASSED' if failed==0 else f'❌ {failed}건 실패'}")
    print("=" * 60)
