"""
KorPIX Audit Network — Hash Chain
불변 해시 체인 생성 · 검증

서명 모드 (환경변수 SIGNING_MODE):
  software (기본) → soft_sign()  개발/테스트 전용
  tpm             → TPM AIK 서명 (UC-005 하드웨어 단말)
"""
from __future__ import annotations

import hashlib
import json
import os
import warnings
from typing import Optional

_ENV          = os.getenv("TERMINAL_ENV",  "development")
_SIGNING_MODE = os.getenv("SIGNING_MODE", "software")
_GENESIS_HASH = "0" * 64


# ── 해시 계산 ────────────────────────────────────────────────────

def compute_hash(record: dict) -> str:
    """
    ActionRecord의 SHA-256 해시를 계산합니다.
    hash / digitalSignature 필드는 계산에서 제외합니다.
    sort_keys=True 필수 — 키 순서 차이로 해시가 달라지는 것을 방지합니다.
    """
    r = {k: v for k, v in record.items()
         if k not in ("hash", "digitalSignature")}
    return hashlib.sha256(
        json.dumps(r, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


# ── 서명 ─────────────────────────────────────────────────────────

def soft_sign(value: str) -> str:
    """
    개발/테스트 전용 소프트웨어 서명.

    누구나 동일한 서명을 생성할 수 있어 보안성이 없습니다.
    TERMINAL_ENV=production 에서는 RuntimeError를 발생시킵니다.

    운영 교체 대상:
      UC-005 하드웨어 Trust Terminal → TPM 2.0 AIK + Dilithium3 서명
    """
    if _ENV == "production":
        raise RuntimeError(
            "soft_sign()은 운영 환경에서 사용할 수 없습니다.\n"
            "SIGNING_MODE=tpm 설정 후 TPM 서명을 사용하세요.\n"
            "참고: docs/security_model.md, UC-005 설계 문서"
        )
    if _ENV not in ("test",):
        warnings.warn(
            "soft_sign() — 개발용 서명입니다. 운영에서는 TPM 서명으로 교체하세요.",
            stacklevel=2,
        )
    return hashlib.sha256(f"SOFT_SIG:{value}".encode()).hexdigest()


def _tpm_sign(value: str) -> str:
    """
    TPM 2.0 AIK 서명 (UC-005 하드웨어 구현 후 연동).

    실제 구현 예시:
        from tpm2_pytss import ESAPI
        ctx = ESAPI()
        sig = ctx.sign(key_handle=AIK_HANDLE, digest=value.encode())
        return sig.hex()
    """
    raise NotImplementedError(
        "TPM 서명은 UC-005 하드웨어 Trust Terminal 구현 후 사용 가능합니다.\n"
        "현재는 SIGNING_MODE=software 로 설정하세요."
    )


def sign(value: str) -> str:
    """SIGNING_MODE 환경변수에 따라 서명 함수를 선택합니다."""
    if _SIGNING_MODE == "tpm":
        return _tpm_sign(value)
    return soft_sign(value)


# ── HashChain ────────────────────────────────────────────────────

class HashChain:
    """
    KorPIX 감사 해시 체인.

    ActionRecord를 순서대로 연결하여 변조 불가능한 감사 기록을 형성합니다.
    단 하나의 레코드라도 수정되면 이후 prevHash가 모두 불일치하여 즉시 탐지됩니다.

    주의: 현재 인메모리 구현입니다.
          서버 재시작 시 체인이 초기화됩니다.
          v0.2에서 PostgreSQL 영속화 예정입니다.
    """

    def __init__(self) -> None:
        self._records:   list[dict]      = []
        self._by_id:     dict[str, dict] = {}
        self._last_hash: str             = _GENESIS_HASH

    def append(self, record: dict) -> dict:
        """
        새 ActionRecord를 체인에 추가합니다.
        prevHash, hash, digitalSignature를 자동으로 계산해 삽입합니다.
        """
        record              = dict(record)
        record["prevHash"]  = self._last_hash

        new_hash                    = compute_hash(record)
        record["hash"]              = new_hash
        record["digitalSignature"]  = sign(new_hash)

        self._records.append(record)
        action_id = record.get("actionId", "")
        if action_id:
            self._by_id[action_id] = record
        self._last_hash = new_hash
        return record

    def verify(self) -> tuple[bool, Optional[int]]:
        """
        전체 체인의 무결성을 검증합니다.

        Returns:
            (is_valid, broken_at_index)
        """
        prev = _GENESIS_HASH
        for i, rec in enumerate(self._records):
            if rec.get("prevHash") != prev:
                return False, i
            if rec.get("hash") != compute_hash(rec):
                return False, i
            prev = rec["hash"]
        return True, None

    def get(self, action_id: str) -> Optional[dict]:
        return self._by_id.get(action_id)

    def all_records(self) -> list[dict]:
        return list(self._records)

    @property
    def length(self) -> int:
        return len(self._records)

    @property
    def last_hash(self) -> str:
        return self._last_hash
