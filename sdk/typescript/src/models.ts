/**
 * KorPIX TypeScript SDK — 공개 데이터 모델 v0.1.0
 */
 
export type ActionType =
  | 'PAYMENT' | 'INVESTMENT' | 'PURCHASE_REQUEST' | 'CIVIC_SERVICE' | 'SYSTEM';
 
export const ActionType = {
  PAYMENT:          'PAYMENT'          as const,
  INVESTMENT:       'INVESTMENT'       as const,
  PURCHASE_REQUEST: 'PURCHASE_REQUEST' as const,
  CIVIC_SERVICE:    'CIVIC_SERVICE'    as const,
  SYSTEM:           'SYSTEM'           as const,
};
 
export type PolicyDecision =
  | 'AUTO_APPROVE' | 'USER_CONFIRM' | 'ADMIN_APPROVE' | 'DENY';
 
export interface UserPolicy {
  monthlyPaymentLimit?: number;
  singlePaymentLimit?:  number;
  monthlyInvestLimit?:  number;
  maxLossRate?:         number;
  civicPaymentLimit?:   number;
}
 
export interface ActionRequest {
  actionType:  ActionType;
  payload:     Record<string, unknown>;
  userPolicy?: UserPolicy;
  requestId?:  string;
}
 
export interface PolicyResponse {
  decision:       PolicyDecision;
  riskScore:      number;
  reasons:        string[];
  resultId:       string;
  decidedAt:      string;
  approvalChain?: ApprovalChain;
  notifyMessage?: string;
  requiresNotify: boolean;
}
 
export interface ApprovalChain {
  chainId:     string;
  tier:        number;
  isFastTrack: boolean;
  steps:       ApprovalStep[];
}
 
export interface ApprovalStep {
  stepId:     string;
  tier:       number;
  approverId: string;
  role:       string;
  status:     'PENDING' | 'APPROVED' | 'REJECTED' | 'TIMEOUT';
  parallel:   boolean;
  timeoutSec: number;
}
 
export interface KorPIXClientOptions {
  terminalId?: string;
  userId?:     string;
  agentId?:    string;
  userPolicy?: UserPolicy;
  baseUrl:     string;
}
 
