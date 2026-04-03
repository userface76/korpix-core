from __future__ import annotations
import hashlib, json
from typing import Optional


class HashChain:
    GENESIS = "0" * 64

    def __init__(self) -> None:
        self._records: list[dict] = []
        self._by_id:   dict[str, dict] = {}
        self._last:    str = self.GENESIS

    def append(self, record: dict) -> dict:
        record = dict(record)
        record["prevHash"] = self._last
        content = json.dumps(
            {k: v for k, v in record.items() if k not in ("hash","digitalSignature")},
            sort_keys=True, ensure_ascii=False
        )
        record["hash"] = hashlib.sha256(content.encode()).hexdigest()
        record["digitalSignature"] = hashlib.sha256(f"SOFT_SIG:{record['hash']}".encode()).hexdigest()
        self._records.append(record)
        self._by_id[record.get("actionId", "")] = record
        self._last = record["hash"]
        return record

    def verify(self) -> tuple[bool, Optional[int]]:
        prev = self.GENESIS
        for i, r in enumerate(self._records):
            if r.get("prevHash") != prev:
                return False, i
            prev = r.get("hash", "")
        return True, None

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def last_hash(self) -> str:
        return self._last

    def all_records(self) -> list[dict]:
        return list(self._records)


# ── 모듈 레벨 유틸 함수 (gateway.py에서 사용) ─────────────────────

def compute_hash(record: dict) -> str:
    """hash / digitalSignature 제외하고 SHA-256 계산"""
    import hashlib, json
    r = {k: v for k, v in record.items()
         if k not in ("hash", "digitalSignature")}
    return hashlib.sha256(
        json.dumps(r, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


# 수정 — WARNING 명시 + 운영 환경 차단
import os, warnings

def soft_sign(value: str) -> str:
    """
    ⚠️  개발/테스트 전용 서명. 운영 환경에서 절대 사용 금지.
    운영: TPM AIK 서명 (UC-005) 또는 HSM 연동으로 교체 필수.
    """
    if os.getenv("TERMINAL_ENV", "development") == "production":
        raise RuntimeError(
            "soft_sign()은 운영 환경에서 사용할 수 없습니다. "
            "SIGNING_MODE=tpm 설정 후 TPM 서명으로 교체하세요."
        )
    warnings.warn("soft_sign() — 개발용 서명, 운영에서 사용 금지", stacklevel=2)
    return hashlib.sha256(f"SOFT_SIG:{value}".encode()).hexdigest()
    
