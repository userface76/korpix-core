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


def soft_sign(value: str) -> str:
    """소프트웨어 서명 — UC-005에서 TPM 서명으로 교체"""
    import hashlib
    return hashlib.sha256(f"SOFT_SIG:{value}".encode()).hexdigest()
