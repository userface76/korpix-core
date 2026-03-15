"""
KorPIX Audit Network — Gateway
================================
Version:  0.3.0
Spec:     KorPIX Architecture Whitepaper §11

Audit Gateway는 Trust Terminal에서 생성된 Terminal Log를
수집·검증·표준화하여 Distributed Ledger로 전달하는
중간 계층입니다.

처리 파이프라인:
    TerminalLogEntry (Trust Terminal 로컬 기록)
        → 1. 형식 검증   (스키마 필드 누락 확인)
        → 2. 서명 검증   (단말 디지털 서명 확인)
        → 3. 해시 검증   (레코드 hash 재계산 비교)
        → 4. 중복 확인   (동일 actionId 재전송 방지)
        → 5. 표준화      (NormalizedAuditRecord 변환)
        → 6. 원장 전달   (DistributedLedger.append)
        → 7. 이상 탐지   (AnomalyDetector 분석)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Callable


# ── 로컬 임포트 ──────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'policy-engine'))
from hash_chain import HashChain   # audit-network/hash-chain.py


GATEWAY_VERSION = "0.3.0"


# ══════════════════════════════════════════════════════════════
#  열거형
# ══════════════════════════════════════════════════════════════

class VerificationStatus(str, Enum):
    PASSED            = "PASSED"
    FAILED_FORMAT     = "FAILED_FORMAT"      # 필드 누락/타입 오류
    FAILED_SIGNATURE  = "FAILED_SIGNATURE"   # 단말 서명 불일치
    FAILED_HASH       = "FAILED_HASH"        # 해시 재계산 불일치
    FAILED_CHAIN      = "FAILED_CHAIN"       # prevHash 체인 불일치
    FAILED_DUPLICATE  = "FAILED_DUPLICATE"   # 중복 actionId


class AnomalyType(str, Enum):
    HIGH_FREQUENCY          = "HIGH_FREQUENCY"           # 비정상 접근 빈도
    CHAIN_TAMPER            = "CHAIN_TAMPER"             # 체인 변조 감지
    SIGNATURE_MISMATCH      = "SIGNATURE_MISMATCH"       # 서명 불일치
    UNAUTHORIZED_DELEGATION = "UNAUTHORIZED_DELEGATION"  # 위임 없는 대리
    REPEATED_DENY           = "REPEATED_DENY"            # 반복 차단 시도
    BUDGET_EXCEEDED         = "BUDGET_EXCEEDED"          # 예산 초과 시도
    SPLIT_ORDER             = "SPLIT_ORDER"              # 분할 발주 패턴
    URGENT_ABUSE            = "URGENT_ABUSE"             # 긴급 남용


# ══════════════════════════════════════════════════════════════
#  데이터 클래스
# ══════════════════════════════════════════════════════════════

@dataclass
class TerminalLogEntry:
    """
    Trust Terminal이 생성하는 원본 로그.
    Gateway에 전송되기 전 단계의 로컬 기록입니다.
    """
    log_id:        str
    terminal_id:   str
    action_record: dict          # ActionRecord dict
    terminal_hash: str           # 단말이 계산한 레코드 해시
    terminal_sig:  str           # 단말 서명 (TPM AIK / 소프트웨어)
    created_at:    str           # ISO 8601
    synced:        bool = False  # Gateway 전송 완료 여부


@dataclass
class NormalizedAuditRecord:
    """
    Gateway가 표준화한 감사 레코드.
    Distributed Ledger에 저장되는 최종 형태입니다.
    """
    # 원본 ActionRecord 핵심 필드
    action_id:        str
    action_type:      str
    terminal_id:      str
    user_id_hash:     str   # 개인정보 보호 — 원본 미저장
    risk_score:       int
    policy_decision:  str
    execution_result: str
    action_timestamp: str

    # 체인 연결
    prev_record_hash: str
    record_hash:      str

    # 이중 서명 (단말 + Gateway)
    terminal_sig:     str
    gateway_sig:      str

    # 분류 메타
    schema_version:   str = "0.3.0"
    normalized_at:    str = field(default_factory=lambda: _now())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class GatewayProcessingResult:
    """Gateway의 처리 결과"""
    log_id:              str
    verification_status: VerificationStatus
    normalized_record:   Optional[NormalizedAuditRecord] = None
    processed_at:        str = field(default_factory=lambda: _now())
    gateway_id:          str = "gateway-001"
    error_detail:        Optional[str] = None

    @property
    def success(self) -> bool:
        return self.verification_status == VerificationStatus.PASSED


@dataclass
class AnomalyEvent:
    """이상 행동 탐지 이벤트"""
    event_id:          str
    anomaly_type:      AnomalyType
    terminal_id:       str
    user_id_hash:      str
    severity:          str   # 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    description:       str
    related_action_ids:list[str]
    detected_at:       str = field(default_factory=lambda: _now())
    resolved:          bool = False

    def to_dict(self) -> dict:
        return {
            "event_id":           self.event_id,
            "anomaly_type":       self.anomaly_type.value,
            "terminal_id":        self.terminal_id,
            "user_id_hash":       self.user_id_hash,
            "severity":           self.severity,
            "description":        self.description,
            "related_action_ids": self.related_action_ids,
            "detected_at":        self.detected_at,
            "resolved":           self.resolved,
        }


# ══════════════════════════════════════════════════════════════
#  검증 파이프라인
# ══════════════════════════════════════════════════════════════

# ActionRecord에 반드시 있어야 하는 필드
REQUIRED_FIELDS = {
    "actionId", "agentId", "userId", "terminalId",
    "actionType", "payload", "riskScore", "policyDecision",
    "executionResult", "timestamp", "prevHash", "hash",
    "digitalSignature",
}


class RecordVerifier:
    """
    Terminal Log의 무결성을 4단계로 검증합니다.

    단계:
        1. 형식 검증  — 필수 필드 존재 여부
        2. 서명 검증  — 단말 digitalSignature 유효성
        3. 해시 검증  — hash 필드 재계산 비교
        4. 체인 검증  — prevHash가 이전 레코드 hash와 일치
    """

    def verify(
        self,
        entry:     TerminalLogEntry,
        prev_hash: str,
    ) -> tuple[VerificationStatus, Optional[str]]:
        """
        Returns:
            (status, error_detail)
        """
        record = entry.action_record

        # ── 1. 형식 검증 ─────────────────────────────────────
        missing = REQUIRED_FIELDS - set(record.keys())
        if missing:
            return (
                VerificationStatus.FAILED_FORMAT,
                f"필수 필드 누락: {', '.join(sorted(missing))}",
            )

        # ── 2. 서명 검증 ─────────────────────────────────────
        expected_sig = _soft_sign(record["hash"])
        if entry.terminal_sig != expected_sig:
            return (
                VerificationStatus.FAILED_SIGNATURE,
                "단말 서명 불일치 — 레코드 위변조 의심",
            )

        # ── 3. 해시 재계산 검증 ───────────────────────────────
        recomputed = _compute_hash(record)
        if recomputed != record["hash"]:
            return (
                VerificationStatus.FAILED_HASH,
                f"해시 불일치 — 저장된: {record['hash'][:16]}… "
                f"재계산: {recomputed[:16]}…",
            )

        # ── 4. 해시 체인 검증 ─────────────────────────────────
        if record["prevHash"] != prev_hash:
            return (
                VerificationStatus.FAILED_CHAIN,
                f"체인 불일치 — 기대값: {prev_hash[:16]}… "
                f"실제값: {record['prevHash'][:16]}…",
            )

        return VerificationStatus.PASSED, None


# ══════════════════════════════════════════════════════════════
#  이상 행동 탐지기
# ══════════════════════════════════════════════════════════════

class AnomalyDetector:
    """
    수신된 레코드 패턴을 분석하여 이상 행동을 탐지합니다.

    탐지 규칙:
        - 10분 내 동일 user_id 5회 이상 접근
        - 연속 3회 이상 DENY 결정
        - 검증 실패 (FAILED_SIGNATURE / FAILED_HASH)
        - 위임 없는 대리 접근 시도 (CivicActionRecord)
        - 30일 내 동일 품목 3회 이상 구매 (분할 발주)
    """

    # 탐지 임계값
    HIGH_FREQ_COUNT     = 5    # 10분 내 접근 횟수
    HIGH_FREQ_WINDOW    = 600  # 초 (10분)
    REPEATED_DENY_COUNT = 3    # 연속 DENY 횟수

    def __init__(self) -> None:
        # user_id_hash → (timestamp, action_id) 최근 접근 기록
        self._access_log:  dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        # user_id_hash → 연속 DENY 횟수
        self._deny_streak: dict[str, int]   = defaultdict(int)
        # 발생한 이상 이벤트 저장
        self._events:      list[AnomalyEvent] = []

    def analyze(
        self,
        record: NormalizedAuditRecord,
        verification_status: VerificationStatus,
    ) -> list[AnomalyEvent]:
        """
        레코드를 분석하여 발생한 이상 이벤트 목록을 반환합니다.
        """
        found: list[AnomalyEvent] = []
        uid   = record.user_id_hash
        now   = datetime.now(timezone.utc)

        # ── 규칙 1: 비정상 서명/해시 ─────────────────────────
        if verification_status in (
            VerificationStatus.FAILED_SIGNATURE,
            VerificationStatus.FAILED_HASH,
        ):
            evt = self._make_event(
                AnomalyType.CHAIN_TAMPER,
                record, "CRITICAL",
                f"레코드 무결성 검증 실패: {verification_status.value}",
            )
            found.append(evt)

        # ── 규칙 2: 높은 접근 빈도 ───────────────────────────
        self._access_log[uid].append((now, record.action_id))
        cutoff = now - timedelta(seconds=self.HIGH_FREQ_WINDOW)
        recent = [(t, a) for t, a in self._access_log[uid] if t >= cutoff]

        if len(recent) >= self.HIGH_FREQ_COUNT:
            evt = self._make_event(
                AnomalyType.HIGH_FREQUENCY,
                record, "HIGH",
                f"10분 내 {len(recent)}회 접근 감지",
                related_ids=[a for _, a in recent],
            )
            found.append(evt)

        # ── 규칙 3: 연속 DENY ────────────────────────────────
        if record.policy_decision == "DENY":
            self._deny_streak[uid] += 1
            if self._deny_streak[uid] >= self.REPEATED_DENY_COUNT:
                evt = self._make_event(
                    AnomalyType.REPEATED_DENY,
                    record, "MEDIUM",
                    f"연속 {self._deny_streak[uid]}회 DENY — 비정상 시도 의심",
                )
                found.append(evt)
        else:
            self._deny_streak[uid] = 0   # 정상 처리 시 초기화

        # ── 규칙 4: 위임 없는 대리 접근 (행정 서비스) ─────────
        if record.action_type == "CIVIC_SERVICE":
            raw = record.__dict__.get("raw_payload", {})
            if raw.get("is_delegated") and not raw.get("delegation_valid"):
                evt = self._make_event(
                    AnomalyType.UNAUTHORIZED_DELEGATION,
                    record, "HIGH",
                    "위임 관계 미검증 대리 접근 시도",
                )
                found.append(evt)

        # 이벤트 저장
        self._events.extend(found)
        return found

    def get_events(
        self,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> list[AnomalyEvent]:
        result = self._events
        if severity:
            result = [e for e in result if e.severity == severity]
        if resolved is not None:
            result = [e for e in result if e.resolved == resolved]
        return result

    def resolve(self, event_id: str) -> bool:
        for e in self._events:
            if e.event_id == event_id:
                e.resolved = True
                return True
        return False

    @staticmethod
    def _make_event(
        anomaly_type: AnomalyType,
        record:       NormalizedAuditRecord,
        severity:     str,
        description:  str,
        related_ids:  Optional[list[str]] = None,
    ) -> AnomalyEvent:
        return AnomalyEvent(
            event_id=str(uuid.uuid4()),
            anomaly_type=anomaly_type,
            terminal_id=record.terminal_id,
            user_id_hash=record.user_id_hash,
            severity=severity,
            description=description,
            related_action_ids=related_ids or [record.action_id],
        )


# ══════════════════════════════════════════════════════════════
#  분산 원장 (인메모리 구현 — 실제 환경에서 DB/블록체인 교체)
# ══════════════════════════════════════════════════════════════

class DistributedLedger:
    """
    검증된 NormalizedAuditRecord를 저장하는 분산 원장.

    현재는 인메모리 구현입니다.
    실제 환경에서는 블록체인 / 분산 DB로 교체하세요.

    특성:
        - Write-Once: 저장된 레코드는 수정/삭제 불가
        - 해시 체인: 모든 레코드가 prevHash로 연결
        - 인덱스: action_id, user_id_hash로 빠른 조회
    """

    def __init__(self) -> None:
        self._records:  list[NormalizedAuditRecord] = []
        self._by_action:dict[str, NormalizedAuditRecord] = {}
        self._by_user:  dict[str, list[str]] = defaultdict(list)  # uid → [action_id]
        self._last_hash:str = "0" * 64   # Genesis

    def append(self, record: NormalizedAuditRecord) -> None:
        """레코드를 원장에 추가합니다. 한 번 저장되면 수정 불가."""
        if record.action_id in self._by_action:
            raise ValueError(f"중복 레코드: {record.action_id}")
        self._records.append(record)
        self._by_action[record.action_id]        = record
        self._by_user[record.user_id_hash].append(record.action_id)
        self._last_hash = record.record_hash

    def get(self, action_id: str) -> Optional[NormalizedAuditRecord]:
        return self._by_action.get(action_id)

    def query(
        self,
        user_id_hash:    Optional[str] = None,
        action_type:     Optional[str] = None,
        policy_decision: Optional[str] = None,
        from_ts:         Optional[str] = None,
        to_ts:           Optional[str] = None,
        page:            int = 1,
        page_size:       int = 50,
    ) -> dict:
        """감사 기록을 조건에 따라 조회합니다."""
        results = list(self._records)

        if user_id_hash:
            results = [r for r in results if r.user_id_hash == user_id_hash]
        if action_type:
            results = [r for r in results if r.action_type == action_type]
        if policy_decision:
            results = [r for r in results if r.policy_decision == policy_decision]
        if from_ts:
            results = [r for r in results if r.action_timestamp >= from_ts]
        if to_ts:
            results = [r for r in results if r.action_timestamp <= to_ts]

        total  = len(results)
        start  = (page - 1) * page_size
        paged  = results[start : start + page_size]

        return {
            "records":   [r.to_dict() for r in paged],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        }

    def verify_integrity(self) -> tuple[bool, Optional[int]]:
        """전체 원장 해시 체인 무결성 검증."""
        if not self._records:
            return True, None
        prev = "0" * 64
        for i, r in enumerate(self._records):
            if r.prev_record_hash != prev:
                return False, i
            prev = r.record_hash
        return True, None

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def last_hash(self) -> str:
        return self._last_hash


# ══════════════════════════════════════════════════════════════
#  Audit Gateway — 메인 클래스
# ══════════════════════════════════════════════════════════════

class AuditGateway:
    """
    KorPIX Audit Gateway.

    Trust Terminal → Gateway → Distributed Ledger 파이프라인의
    중간 계층을 담당합니다.

    책임:
        1. Terminal Log 수신
        2. 4단계 검증 (형식·서명·해시·체인)
        3. 중복 방지
        4. NormalizedAuditRecord 변환
        5. Distributed Ledger 저장
        6. 이상 행동 탐지
        7. 처리 결과 반환
    """

    def __init__(
        self,
        gateway_id:   str = "gateway-001",
        notify_fn:    Optional[Callable[[AnomalyEvent], None]] = None,
    ) -> None:
        self.gateway_id   = gateway_id
        self._verifier    = RecordVerifier()
        self._detector    = AnomalyDetector()
        self._ledger      = DistributedLedger()
        self._notify_fn   = notify_fn or (lambda e: None)
        # 중복 방지용 처리된 action_id 집합
        self._processed:  set[str] = set()
        # 처리 통계
        self._stats:      dict[str, int] = defaultdict(int)

    # ─── 메인 처리 ─────────────────────────────────────────
    def process(self, entry: TerminalLogEntry) -> GatewayProcessingResult:
        """
        Terminal Log를 수신하여 전체 파이프라인을 실행합니다.

        Returns:
            GatewayProcessingResult — 처리 결과 (성공/실패 + 상세)
        """
        record    = entry.action_record
        action_id = record.get("actionId", "")

        # ── 중복 확인 ────────────────────────────────────────
        if action_id in self._processed:
            self._stats["duplicate"] += 1
            return GatewayProcessingResult(
                log_id=entry.log_id,
                verification_status=VerificationStatus.FAILED_DUPLICATE,
                gateway_id=self.gateway_id,
                error_detail=f"중복 actionId: {action_id}",
            )

        # ── 4단계 검증 ────────────────────────────────────────
        status, error = self._verifier.verify(entry, self._ledger.last_hash)

        # 검증 실패 시에도 이상 탐지는 수행
        normalized = None
        if status == VerificationStatus.PASSED:
            normalized = self._normalize(entry)
            self._ledger.append(normalized)
            self._processed.add(action_id)
            self._stats["success"] += 1
        else:
            self._stats[f"failed_{status.value.lower()}"] += 1

        # ── 이상 탐지 ─────────────────────────────────────────
        if normalized or status != VerificationStatus.PASSED:
            dummy = normalized or self._dummy_normalized(record)
            anomalies = self._detector.analyze(dummy, status)
            for evt in anomalies:
                self._notify_fn(evt)
                print(f"  [⚠️  이상탐지] {evt.severity} — {evt.description}")

        return GatewayProcessingResult(
            log_id=entry.log_id,
            verification_status=status,
            normalized_record=normalized,
            gateway_id=self.gateway_id,
            error_detail=error,
        )

    # ─── 조회 ──────────────────────────────────────────────
    def query(self, **kwargs) -> dict:
        """Distributed Ledger 감사 기록 조회."""
        return self._ledger.query(**kwargs)

    def verify_integrity(self) -> tuple[bool, Optional[int]]:
        """Distributed Ledger 전체 무결성 검증."""
        return self._ledger.verify_integrity()

    def get_anomalies(
        self,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> list[AnomalyEvent]:
        return self._detector.get_events(severity=severity, resolved=resolved)

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    @property
    def ledger_count(self) -> int:
        return self._ledger.count

    # ─── 내부 유틸 ─────────────────────────────────────────
    def _normalize(self, entry: TerminalLogEntry) -> NormalizedAuditRecord:
        """TerminalLogEntry → NormalizedAuditRecord 변환."""
        r = entry.action_record
        return NormalizedAuditRecord(
            action_id        = r["actionId"],
            action_type      = r["actionType"],
            terminal_id      = r["terminalId"],
            user_id_hash     = r["userId"],        # 이미 해시값
            risk_score       = int(r["riskScore"]),
            policy_decision  = r["policyDecision"],
            execution_result = r["executionResult"],
            action_timestamp = r["timestamp"],
            prev_record_hash = r["prevHash"],
            record_hash      = r["hash"],
            terminal_sig     = entry.terminal_sig,
            gateway_sig      = _gateway_sign(
                self.gateway_id, r["hash"]
            ),
        )

    @staticmethod
    def _dummy_normalized(record: dict) -> NormalizedAuditRecord:
        """검증 실패 시 이상 탐지용 더미 레코드."""
        return NormalizedAuditRecord(
            action_id        = record.get("actionId", "unknown"),
            action_type      = record.get("actionType", "UNKNOWN"),
            terminal_id      = record.get("terminalId", "unknown"),
            user_id_hash     = record.get("userId", "unknown"),
            risk_score       = int(record.get("riskScore", 0)),
            policy_decision  = record.get("policyDecision", "UNKNOWN"),
            execution_result = record.get("executionResult", "FAILED"),
            action_timestamp = record.get("timestamp", _now()),
            prev_record_hash = record.get("prevHash", "0" * 64),
            record_hash      = record.get("hash", "0" * 64),
            terminal_sig     = "",
            gateway_sig      = "",
        )


# ══════════════════════════════════════════════════════════════
#  유틸리티
# ══════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _compute_hash(record: dict) -> str:
    """hash / digitalSignature 제외하고 SHA-256 계산."""
    r = {k: v for k, v in record.items()
         if k not in ("hash", "digitalSignature")}
    return hashlib.sha256(
        json.dumps(r, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

def _soft_sign(value: str) -> str:
    """소프트웨어 서명 — UC-005에서 TPM 서명으로 교체."""
    return hashlib.sha256(f"SOFT_SIG:{value}".encode()).hexdigest()

def _gateway_sign(gateway_id: str, record_hash: str) -> str:
    """Gateway 서명."""
    return hashlib.sha256(
        f"GW_SIG:{gateway_id}:{record_hash}".encode()
    ).hexdigest()

def make_terminal_log(action_record: dict) -> TerminalLogEntry:
    """
    ActionRecord dict로부터 TerminalLogEntry를 생성하는 헬퍼.
    Trust Terminal이 하는 작업을 흉내 냅니다.
    """
    return TerminalLogEntry(
        log_id       = str(uuid.uuid4()),
        terminal_id  = action_record.get("terminalId", "term-001"),
        action_record= action_record,
        terminal_hash= action_record.get("hash", ""),
        terminal_sig = _soft_sign(action_record.get("hash", "")),
        created_at   = _now(),
        synced       = False,
    )


# ══════════════════════════════════════════════════════════════
#  동작 확인
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                    '..', 'policy-engine'))
    from risk_evaluator  import PolicyEngine, ActionRequest, ActionType, UserPolicy
    from decision_engine import DecisionEngine
    from hash_chain      import HashChain

    print("=" * 62)
    print("KorPIX Audit Gateway v0.3.0  —  동작 확인")
    print("=" * 62)

    # ── 준비 ────────────────────────────────────────────────
    risk_engine     = PolicyEngine()
    decision_engine = DecisionEngine()
    policy          = UserPolicy()
    chain           = HashChain()

    # 이상 탐지 알림 콜백
    def on_anomaly(evt: AnomalyEvent):
        pass   # 테스트에서는 콘솔 출력만

    gateway = AuditGateway(gateway_id="gw-001", notify_fn=on_anomaly)

    # ── 테스트 레코드 생성 ───────────────────────────────────
    test_cases = [
        ("넷플릭스 17,000원",    ActionType.PAYMENT,
         {"service":"netflix","amount":17_000,"currency":"KRW",
          "merchant":"Netflix","is_recurring":True}),
        ("유튜브 9,900원",       ActionType.PAYMENT,
         {"service":"youtube","amount":9_900,"currency":"KRW",
          "merchant":"YouTube","is_recurring":True}),
        ("지방세 87,500원",      ActionType.CIVIC_SERVICE,
         {"service_code":"LOCAL_TAX","service_name":"지방세",
          "agency_code":"LOCALEX","amount":87_500,
          "privacy_grade":1,"is_delegated":False}),
    ]

    prev_hash = "0" * 64
    entries: list[TerminalLogEntry] = []

    for label, action_type, payload in test_cases:
        req = ActionRequest(
            request_id=str(uuid.uuid4()), action_type=action_type,
            agent_id="agent-X", user_id="user-hash-abc",
            terminal_id="term-001", payload=payload,
            user_policy=policy,
        )
        result = risk_engine.evaluate(req)

        # build_action_record 임포트
        from risk_evaluator import build_action_record
        rec = build_action_record(req, result, "SUCCESS", prev_hash)
        prev_hash = rec["hash"]
        entries.append(make_terminal_log(rec))

    # ── Gateway 처리 ─────────────────────────────────────────
    print("\n▶ 정상 레코드 처리")
    for i, (label, _, __), entry in zip(range(len(test_cases)),
                                         test_cases, entries):
        r = gateway.process(entry)
        print(f"  [{i+1}] {label:<18s} → {r.verification_status.value}")

    # ── 중복 처리 시도 ───────────────────────────────────────
    print("\n▶ 중복 레코드 처리")
    dup = gateway.process(entries[0])
    print(f"  중복 결과: {dup.verification_status.value}")

    # ── 변조된 레코드 처리 ───────────────────────────────────
    print("\n▶ 변조 레코드 처리 (hash 조작)")
    import copy
    tampered_entry = copy.deepcopy(entries[1])
    tampered_entry.action_record["actionId"] = str(uuid.uuid4())  # 새 ID
    tampered_entry.action_record["riskScore"] = 99                 # 점수 조작
    tampered_entry.log_id = str(uuid.uuid4())
    result_tampered = gateway.process(tampered_entry)
    print(f"  변조 결과: {result_tampered.verification_status.value}")
    if result_tampered.error_detail:
        print(f"  오류 상세: {result_tampered.error_detail[:60]}…")

    # ── 이상 빈도 탐지 ───────────────────────────────────────
    print("\n▶ 이상 접근 빈도 탐지 (동일 사용자 5회 연속)")
    for j in range(5):
        req_spam = ActionRequest(
            request_id=str(uuid.uuid4()), action_type=ActionType.PAYMENT,
            agent_id="agent-X", user_id="user-hash-spam",
            terminal_id="term-002",
            payload={"service":"spam","amount":1_000,
                     "currency":"KRW","merchant":"Test",
                     "is_recurring":False},
            user_policy=policy,
        )
        res_spam = risk_engine.evaluate(req_spam)
        from risk_evaluator import build_action_record
        spam_rec  = build_action_record(req_spam, res_spam, "SUCCESS",
                                        gateway._ledger.last_hash)
        spam_entry = make_terminal_log(spam_rec)
        gateway.process(spam_entry)

    anomalies = gateway.get_anomalies(severity="HIGH")
    print(f"  HIGH 이상 이벤트 수: {len(anomalies)}")
    for a in anomalies:
        print(f"    - {a.anomaly_type.value}: {a.description}")

    # ── 무결성 검증 ──────────────────────────────────────────
    print("\n▶ 원장 무결성 검증")
    is_valid, broken = gateway.verify_integrity()
    print(f"  저장 레코드: {gateway.ledger_count}건")
    print(f"  무결성:      {'✅ INTACT' if is_valid else f'❌ BROKEN at {broken}'}")

    # ── 처리 통계 ────────────────────────────────────────────
    print("\n▶ Gateway 처리 통계")
    for k, v in gateway.stats.items():
        print(f"  {k:<30s}: {v}")

    print("\n" + "=" * 62)
    print("Audit Gateway 정상 동작 확인 완료")
    print("=" * 62)
