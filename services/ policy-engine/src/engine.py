"""
    KorPIX Policy Engine — FastAPI 서비스 진입점
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import Any, Optional
    import uuid
 
    from .models import ActionRequest, ActionType, UserPolicy
    from .decision import PolicyEngine
 
    app = FastAPI(title="KorPIX Policy Engine", version="0.1.0")
    engine = PolicyEngine()
 
 
    class ActionRequestDTO(BaseModel):
        requestId:   str
        actionType:  str
        agentId:     str
        userId:      str
        terminalId:  str
        payload:     dict[str, Any]
        userPolicy:  dict[str, Any]
        timestamp:   Optional[str] = None
 
 
    @app.post("/v1/evaluate")
    async def evaluate(dto: ActionRequestDTO):
        try:
            policy = UserPolicy(**{
                k: v for k, v in dto.userPolicy.items()
                if k in UserPolicy.__dataclass_fields__
            })
            req = ActionRequest(
                request_id=dto.requestId,
                action_type=ActionType(dto.actionType),
                agent_id=dto.agentId,
                user_id=dto.userId,
                terminal_id=dto.terminalId,
                payload=dto.payload,
                user_policy=policy,
                **({"timestamp": dto.timestamp} if dto.timestamp else {}),
            )
            result = engine.evaluate(req)
            return {"resultId": str(uuid.uuid4()), "requestId": dto.requestId, **result.to_dict()}
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
 
 
    @app.get("/v1/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}
 
