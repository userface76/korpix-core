/**
 * KorPIX TypeScript SDK — KorPIXClient
 */
import type {
  ActionRequest, PolicyResponse, KorPIXClientOptions
} from './models';
 
export class KorPIXClient {
  private readonly terminalId: string;
  private readonly userId:     string;
  private readonly agentId:    string;
  private readonly baseUrl:    string;
 
  constructor(options: KorPIXClientOptions) {
    this.terminalId = options.terminalId ?? 'term-001';
    this.userId     = options.userId     ?? 'user-hash-default';
    this.agentId    = options.agentId    ?? 'agent-001';
    this.baseUrl    = options.baseUrl.replace(/\/$/, '');
  }
 
  /**
   * 행동 요청을 평가합니다.
   * Policy Engine REST API 호출 (POST /evaluate)
   */
  async evaluate(request: ActionRequest): Promise<PolicyResponse> {
    const res = await fetch(`${this.baseUrl}/evaluate`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        action_type: request.actionType,
        agent_id:    this.agentId,
        user_id:     this.userId,
        terminal_id: this.terminalId,
        payload:     request.payload,
        request_id:  request.requestId,
      }),
    });
 
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(`KorPIX Policy Engine 오류 ${res.status}: ${JSON.stringify(err)}`);
    }
 
    const data = await res.json();
    return this._mapResponse(data);
  }
 
  /**
   * Audit Network에 감사 기록을 제출합니다.
   * Audit Gateway REST API 호출 (POST /submit)
   */
  async submitAudit(
    auditBaseUrl: string,
    actionRecord: Record<string, unknown>
  ): Promise<{ success: boolean; status: string }> {
    const base = auditBaseUrl.replace(/\/$/, '');
    const res  = await fetch(`${base}/submit`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ action_record: actionRecord }),
    });
    if (!res.ok) throw new Error(`Audit Network 오류 ${res.status}`);
    const data = await res.json();
    return { success: data.success, status: data.status };
  }
 
  private _mapResponse(data: Record<string, unknown>): PolicyResponse {
    return {
      decision:       data['decision']        as PolicyResponse['decision'],
      riskScore:      data['risk_score']      as number,
      reasons:        (data['reasons']        as string[]) ?? [],
      resultId:       (data['result_id']      as string)  ?? '',
      decidedAt:      (data['decided_at']     as string)  ?? '',
      approvalChain:  data['approval_chain']  as PolicyResponse['approvalChain'],
      notifyMessage:  data['notify_message']  as string | undefined,
      requiresNotify: (data['requires_notify'] as boolean) ?? false,
    };
  }
}
 
