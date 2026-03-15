"""
tests/test_gateway.py
=======================
KorPIX Audit Network — Gateway 단위 테스트

실행:
    python -m pytest tests/test_gateway.py -v
"""

import sys
import os
import copy
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '..', 'policy-engine'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '..', 'audit-network'))

from risk_evaluator import (
    PolicyEngine, ActionRequest, ActionType,
    UserPolicy, build_action_record,
)
from gateway import (
    AuditGateway, TerminalLogEntry, VerificationStatus,
    AnomalyType, make_terminal_log, _soft_sign,
)


# ──────────────────────────────────────────────────────────────
#  픽스처
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def risk_engine():
    return PolicyEngine()

@pytest.fixture
def gw():
    return AuditGateway(gateway_id="gw-test")

@pytest.fixture
def policy():
    return UserPolicy()


def _make_record(
    engine:      PolicyEngine,
    action_type: ActionType,
    payload:     dict,
    prev_hash:   str = "0" * 64,
    user_id:     str = "user-hash-test",
) -> dict:
    """테스트용 ActionRecord dict 생성 헬퍼."""
    req = ActionRequest(
        request_id  = str(uuid.uuid4()),
        action_type = action_type,
        agent_id    = "agent-test",
        user_id     = user_id,
        terminal_id = "term-test",
        payload     = payload,
        user_policy = UserPolicy(),
    )
    result = engine.evaluate(req)
    return build_action_record(req, result, "SUCCESS", prev_hash)


# ══════════════════════════════════════════════════════════════
#  정상 처리 테스트
# ══════════════════════════════════════════════════════════════

class TestNormalProcessing:

    def test_정상_레코드_PASSED(self, risk_engine, gw):
        """유효한 레코드 → PASSED"""
        rec   = _make_record(risk_engine, ActionType.PAYMENT,
                             {"service":"netflix","amount":17_000,
                              "currency":"KRW","merchant":"N",
                              "is_recurring":True})
        entry = make_terminal_log(rec)
        result = gw.process(entry)
        assert result.success is True
        assert result.verification_status == VerificationStatus.PASSED
        assert result.normalized_record is not None

    def test_처리후_원장에_저장됨(self, risk_engine, gw):
        """PASSED 레코드는 Distributed Ledger에 저장"""
        rec   = _make_record(risk_engine, ActionType.CIVIC_SERVICE,
                             {"service_code":"LOCAL_TAX","service_name":"지방세",
                              "agency_code":"LOCALEX","amount":50_000,
                              "privacy_grade":1,"is_delegated":False})
        entry = make_terminal_log(rec)
        gw.process(entry)
        assert gw.ledger_count == 1

    def test_체인_연속처리(self, risk_engine, gw):
        """3개 레코드 순서대로 처리 → 모두 PASSED"""
        prev = "0" * 64
        payloads = [
            {"service":"svc1","amount":10_000,"currency":"KRW",
             "merchant":"M1","is_recurring":False},
            {"service":"svc2","amount":20_000,"currency":"KRW",
             "merchant":"M2","is_recurring":False},
            {"service":"svc3","amount":30_000,"currency":"KRW",
             "merchant":"M3","is_recurring":False},
        ]
        for p in payloads:
            rec   = _make_record(risk_engine, ActionType.PAYMENT, p,
                                 prev_hash=prev)
            prev  = rec["hash"]
            entry = make_terminal_log(rec)
            res   = gw.process(entry)
            assert res.success, f"실패: {res.error_detail}"

        assert gw.ledger_count == 3


# ══════════════════════════════════════════════════════════════
#  검증 실패 테스트
# ══════════════════════════════════════════════════════════════

class TestVerificationFailure:

    def test_중복레코드_거부(self, risk_engine, gw):
        """동일 actionId 재전송 → FAILED_DUPLICATE"""
        rec   = _make_record(risk_engine, ActionType.PAYMENT,
                             {"service":"t","amount":5_000,
                              "currency":"KRW","merchant":"T",
                              "is_recurring":False})
        entry = make_terminal_log(rec)
        gw.process(entry)            # 첫 번째 처리
        dup = gw.process(entry)      # 중복 처리
        assert dup.verification_status == VerificationStatus.FAILED_DUPLICATE

    def test_필드누락_FAILED_FORMAT(self, gw):
        """필수 필드 누락 → FAILED_FORMAT"""
        incomplete = {
            "actionId": str(uuid.uuid4()),
            "actionType": "PAYMENT",
            # 나머지 필드 누락
        }
        entry = TerminalLogEntry(
            log_id="log-incomplete",
            terminal_id="term-test",
            action_record=incomplete,
            terminal_hash="",
            terminal_sig="",
            created_at="2025-01-01T00:00:00+00:00",
        )
        result = gw.process(entry)
        assert result.verification_status == VerificationStatus.FAILED_FORMAT

    def test_서명불일치_FAILED_SIGNATURE(self, risk_engine, gw):
        """잘못된 서명 → FAILED_SIGNATURE"""
        rec   = _make_record(risk_engine, ActionType.PAYMENT,
                             {"service":"t","amount":5_000,
                              "currency":"KRW","merchant":"T",
                              "is_recurring":False})
        entry = make_terminal_log(rec)
        entry.terminal_sig = "wrong_signature_value"  # 서명 조작
        result = gw.process(entry)
        assert result.verification_status == VerificationStatus.FAILED_SIGNATURE

    def test_해시조작_FAILED_HASH(self, risk_engine, gw):
        """레코드 필드 조작 시 해시 불일치 → FAILED_HASH"""
        rec    = _make_record(risk_engine, ActionType.PAYMENT,
                              {"service":"t","amount":5_000,
                               "currency":"KRW","merchant":"T",
                               "is_recurring":False})
        tampered = copy.deepcopy(rec)
        tampered["actionId"] = str(uuid.uuid4())    # 새 ID (해시는 그대로)
        tampered["riskScore"] = 99                   # 점수 조작

        entry = TerminalLogEntry(
            log_id       = str(uuid.uuid4()),
            terminal_id  = tampered["terminalId"],
            action_record= tampered,
            terminal_hash= tampered["hash"],
            terminal_sig = _soft_sign(tampered["hash"]),  # 원본 hash로 서명
            created_at   = tampered["timestamp"],
        )
        result = gw.process(entry)
        assert result.verification_status == VerificationStatus.FAILED_HASH

    def test_실패_레코드_원장_미저장(self, risk_engine, gw):
        """검증 실패한 레코드는 원장에 저장 안 됨"""
        before = gw.ledger_count
        rec    = _make_record(risk_engine, ActionType.PAYMENT,
                              {"service":"t","amount":5_000,
                               "currency":"KRW","merchant":"T",
                               "is_recurring":False})
        entry  = make_terminal_log(rec)
        entry.terminal_sig = "bad_sig"

        gw.process(entry)
        assert gw.ledger_count == before


# ══════════════════════════════════════════════════════════════
#  이상 탐지 테스트
# ══════════════════════════════════════════════════════════════

class TestAnomalyDetection:

    def test_비정상_접근빈도_탐지(self, risk_engine, gw):
        """10분 내 동일 사용자 5회 → HIGH_FREQUENCY 이벤트"""
        prev = "0" * 64
        for _ in range(5):
            rec   = _make_record(
                risk_engine, ActionType.PAYMENT,
                {"service":"spam","amount":1_000,"currency":"KRW",
                 "merchant":"S","is_recurring":False},
                prev_hash=prev, user_id="spammer-hash",
            )
            prev  = rec["hash"]
            entry = make_terminal_log(rec)
            gw.process(entry)

        anomalies = gw.get_anomalies()
        types     = [a.anomaly_type for a in anomalies]
        assert AnomalyType.HIGH_FREQUENCY in types

    def test_변조레코드_CRITICAL_이벤트(self, risk_engine, gw):
        """해시 불일치 레코드 → CRITICAL 이벤트 (CHAIN_TAMPER)"""
        rec     = _make_record(risk_engine, ActionType.PAYMENT,
                               {"service":"t","amount":5_000,
                                "currency":"KRW","merchant":"T",
                                "is_recurring":False})
        tampered = copy.deepcopy(rec)
        tampered["actionId"] = str(uuid.uuid4())
        tampered["riskScore"] = 99

        entry = TerminalLogEntry(
            log_id       = str(uuid.uuid4()),
            terminal_id  = tampered["terminalId"],
            action_record= tampered,
            terminal_hash= tampered["hash"],
            terminal_sig = _soft_sign(tampered["hash"]),
            created_at   = tampered["timestamp"],
        )
        gw.process(entry)

        critical = gw.get_anomalies(severity="CRITICAL")
        assert len(critical) >= 1
        assert any(e.anomaly_type == AnomalyType.CHAIN_TAMPER
                   for e in critical)

    def test_이상이벤트_해제(self, risk_engine, gw):
        """이상 이벤트를 resolve 처리할 수 있어야 함"""
        prev = "0" * 64
        for _ in range(5):
            rec   = _make_record(
                risk_engine, ActionType.PAYMENT,
                {"service":"s","amount":500,"currency":"KRW",
                 "merchant":"S","is_recurring":False},
                prev_hash=prev, user_id="resolve-test",
            )
            prev  = rec["hash"]
            gw.process(make_terminal_log(rec))

        events = gw.get_anomalies(resolved=False)
        assert len(events) > 0

        evt_id = events[0].event_id
        gw._detector.resolve(evt_id)

        still_open = [e for e in gw.get_anomalies() if e.event_id == evt_id]
        assert still_open[0].resolved is True


# ══════════════════════════════════════════════════════════════
#  원장 조회 및 무결성 테스트
# ══════════════════════════════════════════════════════════════

class TestLedger:

    def test_action_type_필터_조회(self, risk_engine, gw):
        """action_type 필터로 조회"""
        prev = "0" * 64

        payment_rec = _make_record(
            risk_engine, ActionType.PAYMENT,
            {"service":"netflix","amount":17_000,"currency":"KRW",
             "merchant":"N","is_recurring":True},
            prev_hash=prev,
        )
        prev = payment_rec["hash"]
        gw.process(make_terminal_log(payment_rec))

        civic_rec = _make_record(
            risk_engine, ActionType.CIVIC_SERVICE,
            {"service_code":"LOCAL_TAX","service_name":"지방세",
             "agency_code":"LOCALEX","amount":50_000,
             "privacy_grade":1,"is_delegated":False},
            prev_hash=prev,
        )
        gw.process(make_terminal_log(civic_rec))

        result = gw.query(action_type="PAYMENT")
        assert result["total"] == 1
        assert result["records"][0]["action_type"] == "PAYMENT"

    def test_원장_무결성_검증_통과(self, risk_engine, gw):
        """여러 레코드 추가 후 원장 무결성 검증"""
        prev = "0" * 64
        for i in range(1, 4):
            rec = _make_record(
                risk_engine, ActionType.PAYMENT,
                {"service":f"svc{i}","amount":i*10_000,
                 "currency":"KRW","merchant":f"M{i}","is_recurring":False},
                prev_hash=prev,
            )
            prev = rec["hash"]
            gw.process(make_terminal_log(rec))

        is_valid, broken = gw.verify_integrity()
        assert is_valid is True
        assert broken is None

    def test_페이지네이션(self, risk_engine, gw):
        """page_size=2, 3건 저장 → 첫 페이지 2건, 두 번째 1건"""
        prev = "0" * 64
        for i in range(3):
            rec = _make_record(
                risk_engine, ActionType.PAYMENT,
                {"service":f"s{i}","amount":(i+1)*5_000,
                 "currency":"KRW","merchant":"M","is_recurring":False},
                prev_hash=prev,
            )
            prev = rec["hash"]
            gw.process(make_terminal_log(rec))

        p1 = gw.query(page=1, page_size=2)
        p2 = gw.query(page=2, page_size=2)

        assert len(p1["records"]) == 2
        assert len(p2["records"]) == 1
        assert p1["total"] == 3

    def test_처리_통계(self, risk_engine, gw):
        """성공/중복 통계가 올바르게 집계되어야 함"""
        rec   = _make_record(risk_engine, ActionType.PAYMENT,
                             {"service":"t","amount":1_000,
                              "currency":"KRW","merchant":"T",
                              "is_recurring":False})
        entry = make_terminal_log(rec)
        gw.process(entry)   # 성공
        gw.process(entry)   # 중복

        stats = gw.stats
        assert stats.get("success",   0) >= 1
        assert stats.get("duplicate", 0) >= 1


# ══════════════════════════════════════════════════════════════
#  실행
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
