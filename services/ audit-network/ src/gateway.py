"""
KorPIX Audit Network — Audit Gateway
Terminal Log 수집 · 검증 · 표준화 · 이상탐지
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
 
from .hashchain import compute_hash, soft_sign
from .ledger import DistributedLedger
 
 
GATEWAY_VERSION = "0.3.0"
 
REQUIRED_FIELDS = {
    "actionId", "agentId", "userId", "terminalId",
    "actionType", "payload", "riskScore", "policyDecision",
    "executionResult", "timestamp", "prevHash", "hash", "digitalSignature",
}
 
 
# ── 열거형 ─────────────────────────────────────────────────────────
class VerificationStatus(str, Enum):
    PASSED           = "PASSED"
    FAILED_FORMAT    = "FAILED_FORMAT"
    FAILED_SIGNATURE = "FAILED_SIGNATURE"
    FAILED_HASH      = "FAILED_HASH"
    FAILED_CHAIN     = "FAILED_CHAIN"
    FAILED_DUPLICATE = "FAILED_DUPLICATE"
 
 
class AnomalyType(str, Enum):
    HIGH_FREQUENCY          = "HIGH_FREQUENCY"
    CHAIN_TAMPER            = "CHAIN_TAMPER"
    SIGNATURE_MISMATCH      = "SIGNATURE_MISMATCH"
    UNAUTHORIZED_DELEGATION = "UNAUTHORIZED_DELEGATION"
    REPEATED_DENY           = "REPEATED_DENY"
 
 
# ── 데이터 클래스 ──────────────────────────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
 
 
@dataclass
class TerminalLogEntry:
    log_id:        str
    terminal_id:   str
    action_record: dict
    terminal_hash: str
    terminal_sig:  str
    created_at:    str
    synced:        bool = False
 
 
@dataclass
class NormalizedAuditRecord:
    action_id:        str
    action_type:      str
    terminal_id:      str
    user_id_hash:     str
    risk_score:       int
    policy_decision:  str
    execution_result: str
    action_timestamp: str
    prev_record_hash: str
    record_hash:      str
    terminal_sig:     str
    gateway_sig:      str
    schema_version:   str = "0.3.0"
    normalized_at:    str = field(default_factory=_now)
 
    def to_dict(self) -> dict:
        return self.__dict__.copy()
 
 
@dataclass
class GatewayProcessingResult:
    log_id:              str
    verification_status: VerificationStatus
    normalized_record:   Optional[NormalizedAuditRecord] = None
    processed_at:        str = field(default_factory=_now)
    gateway_id:          str = "gateway-001"
    error_detail:        Optional[str] = None
 
    @property
    def success(self) -> bool:
        return self.verification_status == VerificationStatus.PASSED
 
 
@dataclass
class AnomalyEvent:
    event_id:           str
    anomaly_type:       AnomalyType
    terminal_id:        str
    user_id_hash:       str
    severity:           str
    description:        str
    related_action_ids: list[str]
    detected_at:        str = field(default_factory=_now)
    resolved:           bool = False
 
    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["anomaly_type"] = self.anomaly_type.value
        return d
 
 
# ── 검증기 ─────────────────────────────────────────────────────────
class RecordVerifier:
    def verify(
        self, entry: TerminalLogEntry, prev_hash: str
    ) -> tuple[VerificationStatus, Optional[str]]:
        rec = entry.action_record
 
        # 1. 형식
        missing = REQUIRED_FIELDS - set(rec.keys())
        if missing:
            return VerificationStatus.FAILED_FORMAT, f"필수 필드 누락: {', '.join(sorted(missing))}"
 
        # 2. 서명
        if entry.terminal_sig != soft_sign(rec["hash"]):
            return VerificationStatus.FAILED_SIGNATURE, "단말 서명 불일치"
 
        # 3. 해시
        recomputed = compute_hash(rec)
        if recomputed != rec["hash"]:
            return VerificationStatus.FAILED_HASH, \
                f"해시 불일치 — 저장: {rec['hash'][:16]}… 재계산: {recomputed[:16]}…"
 
        # 4. 체인
        if rec["prevHash"] != prev_hash:
            return VerificationStatus.FAILED_CHAIN, \
                f"체인 불일치 — 기대: {prev_hash[:16]}… 실제: {rec['prevHash'][:16]}…"
 
        return VerificationStatus.PASSED, None
 
 
# ── 이상 탐지기 ────────────────────────────────────────────────────
class AnomalyDetector:
    HIGH_FREQ_COUNT  = 5
    HIGH_FREQ_WINDOW = 600   # 10분
    DENY_STREAK_LIMIT= 3
 
    def __init__(self) -> None:
        self._access:  dict[str, deque]    = defaultdict(lambda: deque(maxlen=20))
        self._denies:  dict[str, int]      = defaultdict(int)
        self._events:  list[AnomalyEvent]  = []
 
    def analyze(
        self,
        record: NormalizedAuditRecord,
        status: VerificationStatus,
    ) -> list[AnomalyEvent]:
        found: list[AnomalyEvent] = []
        uid   = record.user_id_hash
        now   = datetime.now(timezone.utc)
 
        # 무결성 실패
        if status in (VerificationStatus.FAILED_SIGNATURE, VerificationStatus.FAILED_HASH):
            found.append(self._evt(AnomalyType.CHAIN_TAMPER, record, "CRITICAL",
                f"레코드 무결성 검증 실패: {status.value}"))
 
        # 높은 접근 빈도
        self._access[uid].append((now, record.action_id))
        cutoff = now - timedelta(seconds=self.HIGH_FREQ_WINDOW)
        recent = [(t, a) for t, a in self._access[uid] if t >= cutoff]
        if len(recent) >= self.HIGH_FREQ_COUNT:
            found.append(self._evt(AnomalyType.HIGH_FREQUENCY, record, "HIGH",
                f"10분 내 {len(recent)}회 접근 감지",
                related_ids=[a for _, a in recent]))
 
        # 연속 DENY
        if record.policy_decision == "DENY":
            self._denies[uid] += 1
            if self._denies[uid] >= self.DENY_STREAK_LIMIT:
                found.append(self._evt(AnomalyType.REPEATED_DENY, record, "MEDIUM",
                    f"연속 {self._denies[uid]}회 DENY 감지"))
        else:
            self._denies[uid] = 0
 
        self._events.extend(found)
        return found
 
    def get_events(
        self,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> list[AnomalyEvent]:
        r = self._events
        if severity:
            r = [e for e in r if e.severity == severity]
        if resolved is not None:
            r = [e for e in r if e.resolved == resolved]
        return r
 
    def resolve(self, event_id: str) -> bool:
        for e in self._events:
            if e.event_id == event_id:
                e.resolved = True
                return True
        return False
 
    @staticmethod
    def _evt(
        anomaly_type: AnomalyType,
        record: NormalizedAuditRecord,
        severity: str,
        description: str,
        related_ids: Optional[list[str]] = None,
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
 
 
# ── 메인 Gateway ───────────────────────────────────────────────────
def _gateway_sign(gateway_id: str, record_hash: str) -> str:
    return hashlib.sha256(f"GW_SIG:{gateway_id}:{record_hash}".encode()).hexdigest()
 
 
def make_terminal_log(action_record: dict) -> TerminalLogEntry:
    """ActionRecord dict로부터 TerminalLogEntry 생성 헬퍼"""
    return TerminalLogEntry(
        log_id       = str(uuid.uuid4()),
        terminal_id  = action_record.get("terminalId", "term-001"),
        action_record= action_record,
        terminal_hash= action_record.get("hash", ""),
        terminal_sig = soft_sign(action_record.get("hash", "")),
        created_at   = _now(),
    )
 
 
class AuditGateway:
    """
    KorPIX Audit Gateway.
    Terminal Log → 검증 → 정규화 → Distributed Ledger → 이상탐지
    """
 
    def __init__(
        self,
        gateway_id: str = "gateway-001",
        notify_fn:  Optional[Callable[[AnomalyEvent], None]] = None,
    ) -> None:
        self.gateway_id  = gateway_id
        self._verifier   = RecordVerifier()
        self._detector   = AnomalyDetector()
        self._ledger     = DistributedLedger()
        self._notify_fn  = notify_fn or (lambda e: None)
        self._processed: set[str] = set()
        self._stats:     dict[str, int] = defaultdict(int)
 
    def process(self, entry: TerminalLogEntry) -> GatewayProcessingResult:
        rec       = entry.action_record
        action_id = rec.get("actionId", "")
 
        # 중복 확인
        if action_id in self._processed:
            self._stats["duplicate"] += 1
            return GatewayProcessingResult(
                log_id=entry.log_id,
                verification_status=VerificationStatus.FAILED_DUPLICATE,
                gateway_id=self.gateway_id,
                error_detail=f"중복 actionId: {action_id}",
            )
 
        # 4단계 검증
        status, error = self._verifier.verify(entry, self._ledger.last_hash)
 
        normalized = None
        if status == VerificationStatus.PASSED:
            normalized = self._normalize(entry)
            self._ledger.append(normalized.to_dict())
            self._processed.add(action_id)
            self._stats["success"] += 1
        else:
            self._stats[f"failed_{status.value.lower()}"] += 1
 
        # 이상 탐지
        dummy = normalized or self._dummy(rec)
        for evt in self._detector.analyze(dummy, status):
            self._notify_fn(evt)
 
        return GatewayProcessingResult(
            log_id=entry.log_id,
            verification_status=status,
            normalized_record=normalized,
            gateway_id=self.gateway_id,
            error_detail=error,
        )
 
    def query(self, **kwargs) -> dict:
        return self._ledger.query(**kwargs)
 
    def verify_integrity(self) -> tuple[bool, Optional[int]]:
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
 
    def _normalize(self, entry: TerminalLogEntry) -> NormalizedAuditRecord:
        r = entry.action_record
        return NormalizedAuditRecord(
            action_id        = r["actionId"],
            action_type      = r["actionType"],
            terminal_id      = r["terminalId"],
            user_id_hash     = r["userId"],
            risk_score       = int(r["riskScore"]),
            policy_decision  = r["policyDecision"],
            execution_result = r["executionResult"],
            action_timestamp = r["timestamp"],
            prev_record_hash = r["prevHash"],
            record_hash      = r["hash"],
            terminal_sig     = entry.terminal_sig,
            gateway_sig      = _gateway_sign(self.gateway_id, r["hash"]),
        )
 
    @staticmethod
    def _dummy(rec: dict) -> NormalizedAuditRecord:
        return NormalizedAuditRecord(
            action_id        = rec.get("actionId", "unknown"),
            action_type      = rec.get("actionType", "UNKNOWN"),
            terminal_id      = rec.get("terminalId", "unknown"),
            user_id_hash     = rec.get("userId", "unknown"),
            risk_score       = int(rec.get("riskScore", 0)),
            policy_decision  = rec.get("policyDecision", "UNKNOWN"),
            execution_result = rec.get("executionResult", "FAILED"),
            action_timestamp = rec.get("timestamp", _now()),
            prev_record_hash = rec.get("prevHash", "0" * 64),
            record_hash      = rec.get("hash", "0" * 64),
            terminal_sig     = "",
            gateway_sig      = "",
        )
 
