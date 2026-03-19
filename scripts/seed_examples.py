"""
KorPIX 예제 데이터 시딩 스크립트
Policy Engine + Audit Network에 샘플 행동 레코드를 생성합니다.
 
실행: python scripts/seed_examples.py
"""
import sys, os, uuid, hashlib, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))
 
from policy_engine.src.models  import ActionRequest, ActionType, UserPolicy
from policy_engine.src.engine  import PolicyEngine
from audit_network.src.gateway import AuditGateway, make_terminal_log
 
 
def build_record(req, result, prev_hash):
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
    record["hash"] = hashlib.sha256(
        json.dumps(r, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    record["digitalSignature"] = hashlib.sha256(
        f"SOFT_SIG:{record['hash']}".encode()
    ).hexdigest()
    return record
 
 
SEED_DATA = [
    (ActionType.PAYMENT, {"service":"netflix","amount":17000,"currency":"KRW","merchant":"Netflix Korea","is_recurring":True}),
    (ActionType.PAYMENT, {"service":"youtube_premium","amount":9900,"currency":"KRW","merchant":"YouTube","is_recurring":True}),
    (ActionType.PAYMENT, {"service":"spotify","amount":10900,"currency":"KRW","merchant":"Spotify","is_recurring":True}),
    (ActionType.INVESTMENT, {"ticker":"KODEX200","quantity":5,"total_amount":150000,"order_type":"MARKET","sector":"diversified","product_risk_grade":2}),
    (ActionType.PURCHASE_REQUEST, {"total_amount":55000,"category":"CONSUMABLE","item_code":"A4-PAPER","item_name":"A4 용지 500매","quantity":5,"unit_price":11000,"urgency":"NORMAL","department_id":"DEPT-IT","budget_code":"BC-2025","justification":"정기 구매","requester_id":"EMP-001"}),
    (ActionType.CIVIC_SERVICE, {"service_code":"LOCAL_TAX","service_name":"지방세 납부","agency_code":"LOCALEX","amount":87500,"privacy_grade":1,"is_delegated":False}),
    (ActionType.CIVIC_SERVICE, {"service_code":"UTILITY","service_name":"전기요금 납부","agency_code":"KEPCO","amount":45200,"privacy_grade":1,"is_delegated":False}),
]
 
 
def main():
    print("=" * 55)
    print("  KorPIX 예제 데이터 시딩")
    print("=" * 55)
 
    engine  = PolicyEngine()
    gateway = AuditGateway("gateway-seed")
    prev    = "0" * 64
    success = 0
 
    for action_type, payload in SEED_DATA:
        req = ActionRequest.new(
            action_type=action_type,
            agent_id="agent-seed",
            user_id="user-hash-seed-001",
            terminal_id="term-seed-001",
            payload=payload,
            user_policy=UserPolicy(),
        )
        result = engine.evaluate(req)
        record = build_record(req, result, prev)
        entry  = make_terminal_log(record)
        r      = gateway.process(entry)
 
        status = "✅ PASSED" if r.success else f"❌ {r.verification_status.value}"
        print(f"  {status}  {action_type.value:<20s}  Risk={result.risk_score:3d}  Decision={result.decision.value}")
 
        if r.success:
            prev = record["hash"]
            success += 1
 
    print()
    ok, broken = gateway.verify_integrity()
    print(f"  원장 레코드: {gateway.ledger_count}건")
    print(f"  해시 체인:   {'✅ INTACT' if ok else f'❌ BROKEN at {broken}'}")
    print(f"  처리 성공:   {success}/{len(SEED_DATA)}")
    print("=" * 55)
    print("  시딩 완료. Policy Engine과 Audit Network를 시작하세요.")
    print("  bash scripts/run_policy_engine.sh")
    print("  bash scripts/run_audit_network.sh")
    print("=" * 55)
 
 
if __name__ == "__main__":
    main()
 
