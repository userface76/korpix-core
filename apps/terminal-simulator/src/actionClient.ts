/**
 * KorPIX Terminal Simulator — Action Client
 * Policy Engine API 호출 + Mock 모드 지원
 */

export type ActionType =
  | 'PAYMENT' | 'INVESTMENT' | 'PURCHASE_REQUEST' | 'CIVIC_SERVICE';

export interface ActionPayload {
  [key: string]: unknown;
}

export interface EvaluateResult {
  decision:       'AUTO_APPROVE' | 'USER_CONFIRM' | 'ADMIN_APPROVE' | 'DENY';
  riskScore:      number;
  reasons:        string[];
  requiresNotify: boolean;
  notifyMessage?: string;
  approvalChain?: unknown;
  decidedAt:      string;
}

// ── Mock 결과 생성기 (Policy Engine 미연결 시) ───────────────────
function mockResult(actionType: ActionType, payload: ActionPayload): EvaluateResult {
  const amount = Number((payload as any).amount || (payload as any).total_amount || 0);
  let score = 15;
  if (amount > 100_000)  score += 20;
  if (amount > 500_000)  score += 30;

  const decision =
    score < 30 ? 'AUTO_APPROVE' :
    score < 60 ? 'USER_CONFIRM' :
    score < 80 ? 'ADMIN_APPROVE' : 'DENY';

  return {
    decision,
    riskScore:      score,
    reasons:        [`[Mock] ${actionType} 기본 점수`, `금액 ${amount.toLocaleString()}원`],
    requiresNotify: decision !== 'AUTO_APPROVE',
    notifyMessage:  decision === 'DENY' ? '행동이 차단됐습니다.' : undefined,
    decidedAt:      new Date().toISOString(),
  };
}

class ActionClient {
  private policyUrl = 'http://localhost:8001';
  private terminalId = 'term-sim-001';
  private userId     = 'user-hash-sim';
  private agentId    = 'agent-sim-001';
  private useMock    = false;

  configure(opts: {
    policyUrl?: string;
    terminalId?: string;
    userId?: string;
    agentId?: string;
    useMock?: boolean;
  }) {
    Object.assign(this, opts);
  }

  async evaluate(
    actionType: ActionType,
    payload:    ActionPayload
  ): Promise<EvaluateResult> {
    if (this.useMock) {
      await new Promise(r => setTimeout(r, 300)); // 네트워크 지연 시뮬레이션
      return mockResult(actionType, payload);
    }

    try {
      const res = await fetch(`${this.policyUrl}/evaluate`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          action_type: actionType,
          agent_id:    this.agentId,
          user_id:     this.userId,
          terminal_id: this.terminalId,
          payload,
        }),
      });

      if (!res.ok) {
        console.warn('[ActionClient] API 오류 — Mock 모드로 전환');
        return mockResult(actionType, payload);
      }

      const data = await res.json();
      return {
        decision:       data.decision,
        riskScore:      data.risk_score,
        reasons:        data.reasons ?? [],
        requiresNotify: data.requires_notify ?? false,
        notifyMessage:  data.notify_message,
        approvalChain:  data.approval_chain,
        decidedAt:      data.decided_at,
      };
    } catch {
      console.warn('[ActionClient] 연결 실패 — Mock 모드로 전환');
      this.useMock = true;
      return mockResult(actionType, payload);
    }
  }
}

export const actionClient = new ActionClient();
