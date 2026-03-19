from __future__ import annotations
from .hashchain import HashChain


class AuditLogger:
    def __init__(self) -> None:
        self._chain = HashChain()

    def record(self, action_record: dict, exec_status: str = "SUCCESS") -> dict:
        r = dict(action_record)
        r["executionResult"] = exec_status
        return self._chain.append(r)

    def verify_integrity(self) -> tuple[bool, int | None]:
        return self._chain.verify()

    def query(self, user_id=None, action_type=None, page=1, page_size=50) -> dict:
        results = self._chain.all_records()
        if user_id:      results = [r for r in results if r.get("userId") == user_id]
        if action_type:  results = [r for r in results if r.get("actionType") == action_type]
        total = len(results)
        start = (page - 1) * page_size
        return {"records": results[start:start+page_size], "total": total, "page": page}

    @property
    def count(self) -> int:
        return self._chain.count
