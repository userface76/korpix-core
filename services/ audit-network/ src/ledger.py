"""
KorPIX Audit Network — Distributed Ledger
인메모리 분산 원장 (실제 환경에서는 DB/블록체인으로 교체)
"""
from __future__ import annotations
from collections import defaultdict
from typing import Optional
 
 
class DistributedLedger:
    """Write-Once 분산 원장 — 저장된 레코드 수정/삭제 불가"""
 
    def __init__(self) -> None:
        self._records:   list[dict]              = []
        self._by_action: dict[str, dict]         = {}
        self._by_user:   dict[str, list[str]]    = defaultdict(list)
        self._last_hash: str                     = "0" * 64
 
    def append(self, record: dict) -> None:
        action_id = record.get("action_id") or record.get("actionId", "")
        if action_id in self._by_action:
            raise ValueError(f"중복 레코드: {action_id}")
        self._records.append(record)
        self._by_action[action_id] = record
        uid = record.get("user_id_hash") or record.get("userId", "")
        self._by_user[uid].append(action_id)
        self._last_hash = record.get("record_hash") or record.get("hash", "")
 
    def get(self, action_id: str) -> Optional[dict]:
        return self._by_action.get(action_id)
 
    def query(
        self,
        user_id_hash:    Optional[str] = None,
        action_type:     Optional[str] = None,
        policy_decision: Optional[str] = None,
        page:            int = 1,
        page_size:       int = 50,
    ) -> dict:
        results = list(self._records)
        if user_id_hash:
            results = [r for r in results if
                       (r.get("user_id_hash") or r.get("userId","")) == user_id_hash]
        if action_type:
            results = [r for r in results if
                       (r.get("action_type") or r.get("actionType","")) == action_type]
        if policy_decision:
            results = [r for r in results if
                       (r.get("policy_decision") or r.get("policyDecision","")) == policy_decision]
        total = len(results)
        start = (page - 1) * page_size
        return {"records": results[start:start+page_size],
                "total": total, "page": page, "page_size": page_size}
 
    def verify_integrity(self) -> tuple[bool, Optional[int]]:
        if not self._records:
            return True, None
        prev = "0" * 64
        for i, r in enumerate(self._records):
            ph = r.get("prev_record_hash") or r.get("prevHash", "")
            if ph != prev:
                return False, i
            prev = r.get("record_hash") or r.get("hash", "")
        return True, None
 
    @property
    def count(self) -> int:
        return len(self._records)
 
    @property
    def last_hash(self) -> str:
        return self._last_hash
 
