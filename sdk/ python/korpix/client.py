"""
KorPIX Python SDK — KorPIXClient
Policy Engine, Audit Network, Execution Gateway를 통합하는 클라이언트
"""
from __future__ import annotations
import os
import sys
from typing import Any, Optional
 
from .models import ActionRequest, ActionType, PolicyResponse, UserPolicy
 
# ── 로컬 서비스 직접 임포트 (서버 없이도 동작) ──────────────────────
_SVC_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "services")
sys.path.insert(0, _SVC_PATH)
 
try:
    from policy_engine.src.models   import (
        ActionRequest as _Req, ActionType as _AT, UserPolicy as _UP
    )
    from policy_engine.src.engine   import PolicyEngine
    from policy_engine.src.decision import DecisionEngine, CircuitBreaker
    from audit_network.src.gateway  import AuditGateway, make_terminal_log
    from audit_network.src.hashchain import HashChain
    _LOCAL = True
except ImportError:
    _LOCAL = False
 
 
class KorPIXClient:
    """
    KorPIX 통합 클라이언트.
    로컬 모드(서버 없이) 또는 HTTP 모드(FastAPI 서버) 모두 지원.
 
    사용 예:
        client = KorPIXClient(terminal_id="term-001", user_id="user-hash-abc")
        result = client.evaluate(ActionRequest(
            action_type=ActionType.PAYMENT,
            payload={"service":"netflix","amount":17000,"currency":"KRW"}
        ))
        print(result.decision)    # AUTO_APPROVE
        print(result.risk_score)  # 20
    """
 
    def __init__(
        self,
        terminal_id:  str = "term-001",
        user_id:      str = "user-hash-default",
        agent_id:     str = "agent-001",
        user_policy:  Optional[UserPolicy] = None,
        base_url:     Optional[str] = None,   # HTTP 모드 URL (예: http://localhost:8001)
    ) -> None:
        self.terminal_id = terminal_id
        self.user_id     = user_id
        self.agent_id    = agent_id
        self.user_policy = user_policy or UserPolicy()
        self.base_url    = base_url
 
        # 로컬 모드 초기화
        if _LOCAL and base_url is None:
            self._engine   = PolicyEngine()
            self._decision = DecisionEngine()
            self._gateway  = AuditGateway()
            self._chain    = HashChain()
        else:
            self._engine = self._decision = self._gateway = self._chain = None
 
    def evaluate(self, request: ActionRequest) -> PolicyResponse:
        """
        행동 요청을 평가합니다.
 
        Args:
            request: ActionRequest — 평가할 행동
 
        Returns:
            PolicyResponse — decision, risk_score, reasons 포함
        """
        if self.base_url:
            return self._evaluate_http(request)
        return self._evaluate_local(request)
 
    def submit_audit(self, action_record: dict) -> dict:
        """감사 기록을 Audit Network에 제출합니다."""
        if not _LOCAL or self._gateway is None:
            raise RuntimeError("Audit Network가 초기화되지 않았습니다.")
        entry  = make_terminal_log(action_record)
        result = self._gateway.process(entry)
        return {"status": result.verification_status.value, "success": result.success}
 
    # ── 내부 구현 ────────────────────────────────────────────────
    def _evaluate_local(self, req: ActionRequest) -> PolicyResponse:
        if not _LOCAL:
            raise RuntimeError("로컬 서비스를 임포트할 수 없습니다. base_url을 설정하세요.")
 
        # ActionType 변환
        at = _AT(req.action_type.value)
        up = _UP(
            monthly_payment_limit = self.user_policy.monthly_payment_limit,
            single_payment_limit  = self.user_policy.single_payment_limit,
        )
        internal_req = _Req.new(
            action_type = at,
            agent_id    = self.agent_id,
            user_id     = self.user_id,
            terminal_id = self.terminal_id,
            payload     = req.payload,
            user_policy = up,
        )
        policy_result   = self._engine.evaluate(internal_req)
        decision_result = self._decision.decide(internal_req, policy_result)
        return PolicyResponse.from_dict(decision_result.to_dict())
 
    def _evaluate_http(self, req: ActionRequest) -> PolicyResponse:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("HTTP 모드에는 httpx가 필요합니다: pip install httpx")
        response = httpx.post(
            f"{self.base_url}/evaluate",
            json={
                "action_type": req.action_type.value,
                "agent_id":    self.agent_id,
                "user_id":     self.user_id,
                "terminal_id": self.terminal_id,
                "payload":     req.payload,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return PolicyResponse.from_dict(response.json())
 
