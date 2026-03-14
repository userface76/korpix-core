/**
 * KorPIX ActionRecord — AI 행동 감사 기록 표준 구조
 * Version: 0.1.0
 * 
 * 이 파일이 KorPIX의 공통어(Common Interface)입니다.
 * 모든 컨소시엄 파트너는 이 구조를 기반으로 연동합니다.
 */

// ─── 행동 유형 ────────────────────────────────────────────────
export type ActionType =
  | 'PAYMENT'           // UC-001: 결제
  | 'INVESTMENT'        // UC-002: 투자
  | 'PURCHASE_REQUEST'  // UC-003: 기업 구매
  | 'CIVIC_SERVICE'     // UC-004: 행정 서비스
  | 'SYSTEM';           // 시스템 내부 행동

// ─── 정책 결정 결과 ───────────────────────────────────────────
export type PolicyDecision =
  | 'AUTO_APPROVE'    // Risk Score 낮음 → 자동 승인
  | 'USER_CONFIRM'    // Risk Score 중간 → 사용자 확인
  | 'ADMIN_APPROVE'   // Risk Score 높음 → 관리자 승인
  | 'DENY';           // Risk Score 매우 높음 → 차단

// ─── 실행 결과 ────────────────────────────────────────────────
export type ExecutionStatus =
  | 'SUCCESS'
  | 'BLOCKED'
  | 'PENDING'
  | 'FAILED';

// ─── 핵심: ActionRecord 표준 구조 ────────────────────────────
export interface ActionRecord {
  // 식별자
  actionId:    string;  // UUID v4 — 고유 행동 식별자
  agentId:     string;  // AI 에이전트 식별자
  userId:      string;  // 위임한 사용자 ID (원본 아닌 해시)
  terminalId:  string;  // 실행 단말 ID

  // 행동 내용
  actionType:  ActionType;
  payload:     Record<string, unknown>;  // 행동별 상세 데이터

  // Policy Engine 결정
  riskScore:       number;          // 0~100
  policyDecision:  PolicyDecision;

  // 실행 결과
  executionResult: ExecutionStatus;

  // 감사 체인
  timestamp:        string;  // ISO 8601
  prevHash:         string;  // 이전 레코드 해시 (체인 연결)
  hash:             string;  // 이 레코드의 SHA-256 해시
  digitalSignature: string;  // 단말 서명 (ECDSA / Dilithium)
}

// ─── UC-001 결제 확장 ─────────────────────────────────────────
export interface PaymentActionRecord extends ActionRecord {
  actionType: 'PAYMENT';
  payload: {
    service:     string;  // 'netflix' | 'youtube' | ...
    amount:      number;  // KRW
    currency:    'KRW';
    merchant:    string;
  };
}

// ─── UC-002 투자 확장 ─────────────────────────────────────────
export interface InvestmentActionRecord extends ActionRecord {
  actionType: 'INVESTMENT';
  payload: {
    ticker:      string;  // 'KODEX200' | ...
    quantity:    number;
    unitPrice:   number;
    totalAmount: number;
    orderType:   'MARKET' | 'LIMIT';
  };
  strategyBasis: {
    vixAtExecution:      number;
    portfolioLossRate:   number;
    sectorConcentration: number;
    strategyName:        string;
    dataSourceHash:      string;  // 판단 근거 해시
  };
  regulatoryFields: {
    investorRiskGrade:  1 | 2 | 3 | 4 | 5;
    suitabilityCheck:   boolean;
    retentionPeriodYr:  5;
  };
}

// ─── UC-003 기업 구매 확장 ────────────────────────────────────
export interface PurchaseActionRecord extends ActionRecord {
  actionType: 'PURCHASE_REQUEST';
  payload: {
    prId:          string;
    itemCode:      string;
    itemName:      string;
    quantity:      number;
    unitPrice:     number;
    totalAmount:   number;
    category:      'CONSUMABLE' | 'IT_EQUIPMENT' | 'SERVICE' | 'ASSET';
    urgency:       'NORMAL' | 'URGENT';
    justification: string;
  };
  orgContext: {
    requesterId:       string;
    departmentId:      string;
    budgetCode:        string;
    budgetRemaining:   number;
    fiscalYear:        number;
  };
  approvalChain: ApprovalStep[];
  erpResult: {
    poId:          string | null;
    erpStatus:     'CREATED' | 'PENDING' | 'FAILED';
    erpTimestamp:  string | null;
  };
}

export interface ApprovalStep {
  tier:        number;
  approverId:  string;
  role:        string;
  status:      'PENDING' | 'APPROVED' | 'REJECTED';
  approvedAt:  string | null;
  signature:   string | null;
  comment:     string | null;
}

// ─── UC-004 행정 서비스 확장 ──────────────────────────────────
export interface CivicActionRecord extends ActionRecord {
  actionType: 'CIVIC_SERVICE';
  payload: {
    serviceCode:   string;
    serviceName:   string;
    agencyCode:    string;
    amount:        number | null;
    documentType:  string | null;
  };
  privacyFields: {
    subjectIdHash:      string;   // 주민번호 해시만 (원본 미저장)
    privacyGrade:       1 | 2 | 3 | 4;
    dataRetentionDays:  number;
    localProcessOnly:   boolean;
  };
  delegation?: {
    isDelegated:       boolean;
    principalIdHash:   string;
    delegateIdHash:    string;
    delegationSig:     string;
    delegationExpiry:  string;
  };
  publicApiResult: {
    receiptNumber:   string | null;
    status:          'SUCCESS' | 'FAILED' | 'PENDING';
    agencyTimestamp: string;
  };
}
