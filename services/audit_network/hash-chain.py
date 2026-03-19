"""
KorPIX Audit Network — Hash Chain
====================================
Version:  0.1.0
Spec:     KorPIX Architecture Whitepaper §13

AI 행동 기록을 해시 체인으로 연결하여
변조를 감지하고 무결성을 보장합니다.

핵심 구조:
    record_n["prevHash"] == record_{n-1}["hash"]
    record_n["hash"]     == SHA256(record_n 내용)

단 하나의 레코드라도 수정되면
이후 모든 레코드의 hash가 틀어져 즉시 탐지됩니다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ChainBlock:
    """해시 체인의 단일 블록"""
    index:      int
    action_id:  str
    prev_hash:  str
    hash:       str
    timestamp:  str


class HashChain:
    """
    KorPIX 감사 해시 체인.
    ActionRecord를 순서대로 연결하여
    변조 불가능한 감사 기록을 형성합니다.
    """

    GENESIS_HASH = "0" * 64   # 첫 번째 레코드의 prevHash

    def __init__(self) -> None:
        self._records:    list[dict]       = []
        self._chain:      list[ChainBlock] = []
        self._last_hash:  str              = self.GENESIS_HASH

    # ── 레코드 추가 ────────────────────────────────────────────
    def append(self, record: dict) -> dict:
        """
        새 ActionRecord를 체인에 추가합니다.
        prevHash와 hash를 자동으로 계산하여 record에 삽입합니다.

        Args:
            record: hash / prevHash / digitalSignature를 제외한 ActionRecord

        Returns:
            hash, prevHash, digitalSignature가 채워진 완성 레코드
        """
        record = dict(record)  # 원본 수정 방지
        record["prevHash"] = self._last_hash

        # 결정론적 직렬화 (sort_keys=True 필수)
        content    = json.dumps(record, sort_keys=True, ensure_ascii=False)
        new_hash   = hashlib.sha256(content.encode()).hexdigest()
        record["hash"] = new_hash

        # 소프트웨어 서명 (UC-005 이후 TPM 서명으로 교체)
        record["digitalSignature"] = self._soft_sign(new_hash)

        self._records.append(record)
        self._chain.append(ChainBlock(
            index=len(self._chain),
            action_id=record.get("actionId", ""),
            prev_hash=self._last_hash,
            hash=new_hash,
            timestamp=record.get("timestamp", ""),
        ))
        self._last_hash = new_hash
        return record

    # ── 무결성 검증 ────────────────────────────────────────────
    def verify(self) -> tuple[bool, Optional[int]]:
        """
        전체 체인의 무결성을 검증합니다.

        Returns:
            (is_valid, broken_at_index)
            broken_at_index: 체인이 끊어진 위치 (정상이면 None)
        """
        if not self._records:
            return True, None

        for i, record in enumerate(self._records):
            # prevHash 체인 연결 확인
            expected_prev = self.GENESIS_HASH if i == 0 else self._records[i - 1]["hash"]
            if record.get("prevHash") != expected_prev:
                return False, i

            # hash 재계산 확인
            r = {k: v for k, v in record.items()
                 if k not in ("hash", "digitalSignature")}
            content       = json.dumps(r, sort_keys=True, ensure_ascii=False)
            expected_hash = hashlib.sha256(content.encode()).hexdigest()
            if record.get("hash") != expected_hash:
                return False, i

        return True, None

    # ── 조회 ───────────────────────────────────────────────────
    def get_record(self, action_id: str) -> Optional[dict]:
        """action_id로 레코드를 조회합니다."""
        return next(
            (r for r in self._records if r.get("actionId") == action_id),
            None,
        )

    def get_all(self) -> list[dict]:
        return list(self._records)

    @property
    def length(self) -> int:
        return len(self._records)

    @property
    def last_hash(self) -> str:
        return self._last_hash

    # ── 내부 유틸 ──────────────────────────────────────────────
    @staticmethod
    def _soft_sign(hash_value: str) -> str:
        """
        개발·테스트용 소프트웨어 서명.
        UC-005 하드웨어 Trust Terminal에서 TPM AIK 서명으로 교체됩니다.
        """
        return hashlib.sha256(f"SOFT_SIG:{hash_value}".encode()).hexdigest()


# ── 독립 실행 확인 ─────────────────────────────────────────────
if __name__ == "__main__":
    chain = HashChain()

    # 샘플 레코드 3개 추가
    samples = [
        {"actionId": "act-001", "actionType": "PAYMENT",
         "riskScore": 15, "policyDecision": "AUTO_APPROVE",
         "executionResult": "SUCCESS",
         "timestamp": datetime.now(timezone.utc).isoformat()},
        {"actionId": "act-002", "actionType": "PAYMENT",
         "riskScore": 35, "policyDecision": "USER_CONFIRM",
         "executionResult": "SUCCESS",
         "timestamp": datetime.now(timezone.utc).isoformat()},
        {"actionId": "act-003", "actionType": "INVESTMENT",
         "riskScore": 22, "policyDecision": "AUTO_APPROVE",
         "executionResult": "SUCCESS",
         "timestamp": datetime.now(timezone.utc).isoformat()},
    ]

    for s in samples:
        chain.append(s)

    is_valid, broken = chain.verify()
    print(f"체인 길이:  {chain.length}")
    print(f"무결성:     {'✅ INTACT' if is_valid else f'❌ BROKEN at {broken}'}")
    print(f"마지막 해시: {chain.last_hash[:24]}...")
