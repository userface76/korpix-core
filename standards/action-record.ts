/**
 * KorPIX ActionRecord — AI 행동 감사 기록 표준 구조
 * =====================================================
 * Version:  0.1.0
 * Spec:     KorPIX Architecture Whitepaper §12
 *
 * 이 파일이 KorPIX의 공통어(Common Interface)입니다.
 * 모든 컨소시엄 파트너는 이 구조를 기반으로 연동합니다.
 *
 * 계층 구조:
 *   ActionRecord          ← 모든 UC 공통 기반
 *   ├─ PaymentActionRecord      (UC-001 결제)
 *   ├─ InvestmentActionRecord   (UC-002 투자)
 *   ├─ PurchaseActionRecord     (UC-003 기업 구매)
 *   └─ CivicActionRecord        (UC-004 행정 서비스)
 */

// ─── 행동 유형 ────────────────────────────────────────────────
export type ActionType =
  | 'PAYMENT'            // UC-001: 결제
  | 'INVESTMENT'         // UC-002: 투자
  | 'PURCHASE_REQUEST'   // UC-003: 기업 구매
  | 'CIVIC_SERVICE'      // UC-004: 행정 서비스
  | 'SYSTEM';            // 시스템 내부 행동

// ─── 정책 결정 결과 ───────────────────────────────────────────
export type PolicyDecision =
  | 'AUTO_APPROVE'    // Risk Score  0~29  → 자동 승인
  | 'USER_CONFIRM'    // Risk Score 30~59  → 사용자 확인
  | 'ADMIN_APPROVE'   // Risk Score 60~79  → 관리자 승인
  | 'DENY';           // Risk Score 80+    → 차단

// ─── 실행 결과 ────────────────────────────────────────────────
export type ExecutionStatus =
  | 'SUCCESS'
  | 'BLOCKED'
  | 'PENDING'
  | 'FAILED';

// ─── 승인 단계 (UC-003 구매 전용) ────────────────────────────
export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export interface ApprovalStep {
  tier:       number;           // 1 ~ 5
  approverId: string;           // 결재자 사번
  role:       string;           // '팀장' | '재무팀' | 'CFO' | '이사회'
  status:     ApprovalStatus;
  approvedAt: string | null;    // ISO 8601
  signature:  string | null;    // 결재자 디지털 서명 (Dilithium3)
  comment:    string | null;    // 결재 의견
}

// ════════════════════════════════════════════════════════════════
//  BASE ActionRecord — 모든 UC 공통 기반
// ════════════════════════════════════════════════════════════════
export interface ActionRecord {
  // ── 식별자 ──────────────────────────────────────────────────
  actionId:    string;   // UUID v4 — 고유 행동 식별자
  agentId:     string;   // AI 에이전트 식별자
  userId:      string;   // 사용자 ID 해시 (원본 미저장)
  terminalId:  string;   // 실행 단말 ID

  // ── 행동 내용 ───────────────────────────────────────────────
  actionType:  ActionType;
  payload:     Record<string, unknown>;  // 행동별 상세 (하위 타입에서 구체화)

  // ── Policy Engine 결정 ──────────────────────────────────────
  riskScore:       number;          // 0 ~ 100
  policyDecision:  PolicyDecision;
  policyEngineVer: string;          // 정책 엔진 버전 (감사 추적용)

  // ── 실행 결과 ───────────────────────────────────────────────
  executionResult: ExecutionStatus;
  errorCode?:      string;          // 실패 시 오류 코드

  // ── 감사 체인 (Audit Chain) ─────────────────────────────────
  timestamp:        string;   // ISO 8601 — 행동 발생 시각
  prevHash:         string;   // 이전 레코드 해시 (체인 연결)
  hash:             string;   // 이 레코드의 SHA-256 해시
  digitalSignature: string;   // 단말 서명 (ECDSA / Dilithium3)
}

// ════════════════════════════════════════════════════════════════
//  UC-001 PaymentActionRecord — 결제 확장
// ════════════════════════════════════════════════════════════════
export interface PaymentActionRecord extends ActionRecord {
  actionType: 'PAYMENT';
  payload: {
    service:    string;   // 'netflix' | 'youtube_premium' | 'local_tax' | ...
    amount:     number;   // KRW
    currency:   'KRW';
    merchant:   string;   // 가맹점명
    isRecurring: boolean; // 정기결제 여부
  };
}

// ════════════════════════════════════════════════════════════════
//  UC-002 InvestmentActionRecord — 투자 확장
// ════════════════════════════════════════════════════════════════
export interface InvestmentActionRecord extends ActionRecord {
  actionType: 'INVESTMENT';
  payload: {
    ticker:      string;              // 'KODEX200' | 'TIGER_반도체' | ...
    quantity:    number;              // 매수 수량
    unitPrice:   number;              // 주문 단가 (KRW)
    totalAmount: number;              // 총 주문 금액 (KRW)
    orderType:   'MARKET' | 'LIMIT';
  };
  // 투자 판단 근거 — 자본시장법 감사 대응
  strategyBasis: {
    vixAtExecution:       number;  // 실행 시점 VIX 지수
    portfolioLossRate:    number;  // 현재 포트폴리오 손실률 (%)
    sectorConcentration:  number;  // 해당 섹터 비중 (%)
    strategyName:         string;  // 사용 투자 전략명
    dataSourceHash:       string;  // 판단 근거 데이터 SHA-256 (원본 별도 보관)
  };
  // 규제 필드 — 자본시장법 5년 보존
  regulatoryFields: {
    investorRiskGrade:  1 | 2 | 3 | 4 | 5;
    suitabilityCheck:   boolean;          // 적합성 원칙 통과 여부
    retentionPeriodYr:  5;                // 자본시장법 의무 보존 기간
  };
}

// ════════════════════════════════════════════════════════════════
//  UC-003 PurchaseActionRecord — 기업 구매 확장
// ════════════════════════════════════════════════════════════════
export type PurchaseCategory =
  | 'CONSUMABLE'    // 소모품 — 저위험
  | 'SERVICE'       // 서비스 계약 — 중간
  | 'IT_EQUIPMENT'  // IT 장비 — 중간
  | 'ASSET';        // 자산성 구매 — 고위험

export interface PurchaseActionRecord extends ActionRecord {
  actionType: 'PURCHASE_REQUEST';
  payload: {
    prId:          string;            // 구매 요청서 ID (PR-YYYYMMDD-XXXX)
    itemCode:      string;            // ERP 품목 코드
    itemName:      string;            // 품목명
    quantity:      number;            // 수량
    unitPrice:     number;            // 단가 (KRW)
    totalAmount:   number;            // 총 금액 (KRW)
    category:      PurchaseCategory;
    urgency:       'NORMAL' | 'URGENT';
    justification: string;            // 구매 사유
  };
  // 조직 / 예산 컨텍스트
  orgContext: {
    requesterId:      string;   // 요청자 사번
    departmentId:     string;   // 부서 코드
    budgetCode:       string;   // ERP 예산 코드
    budgetRemaining:  number;   // 요청 시점 잔여 예산
    fiscalYear:       number;   // 회계연도
  };
  // 결재 체인 — Policy Engine이 자동 생성
  approvalChain: ApprovalStep[];
  // ERP 연동 결과
  erpResult: {
    poId:          string | null;   // 생성된 발주 번호 (PO-YYYYMMDD-XXXX)
    erpStatus:     'CREATED' | 'PENDING' | 'FAILED';
    erpTimestamp:  string | null;
  };
}

// ════════════════════════════════════════════════════════════════
//  UC-004 CivicActionRecord — 행정 서비스 확장
// ════════════════════════════════════════════════════════════════
export type PrivacyGrade = 1 | 2 | 3 | 4;
//  1 — 일반 (이름·주소)          → Auto Approve 가능
//  2 — 민감 (주민번호·계좌)      → User Confirm 필수
//  3 — 고민감 (건강·복지 이력)   → 로컬 처리 전용
//  4 — 최고민감 (생체·범죄)      → 처리 불가 (DENY)

export interface CivicActionRecord extends ActionRecord {
  actionType: 'CIVIC_SERVICE';
  payload: {
    serviceCode:  string;         // 'LOCAL_TAX' | 'DOC_ISSUANCE' | 'WELFARE' | ...
    serviceName:  string;         // 서비스명
    agencyCode:   string;         // 'GOV24' | 'NHI' | 'MOHW' | 'LOCALEX' | ...
    amount:       number | null;  // 납부 금액 (해당 없으면 null)
    documentType: string | null;  // 발급 서류 유형
  };
  // 개인정보 보호 — 원본 절대 미저장, 해시만 보존
  privacyFields: {
    subjectIdHash:      string;        // 주민번호 SHA-256+Salt 해시
    privacyGrade:       PrivacyGrade;  // 처리한 개인정보 최고 등급
    dataRetentionDays:  number;        // 원본 보존 기간 (0 = 즉시 삭제)
    localProcessOnly:   boolean;       // true이면 외부 전송 차단
  };
  // 위임 관계 (가족 대리 신청 시에만 사용)
  delegation?: {
    isDelegated:       boolean;
    principalIdHash:   string;   // 본인 ID 해시
    delegateIdHash:    string;   // 대리인 ID 해시
    delegationSig:     string;   // 본인 위임 동의 디지털 서명
    delegationExpiry:  string;   // 위임 만료 시각 (ISO 8601)
  };
  // 공공 API 응답 (비개인정보만 저장)
  publicApiResult: {
    receiptNumber:   string | null;
    status:          'SUCCESS' | 'FAILED' | 'PENDING';
    agencyTimestamp: string;
  };
}

// ════════════════════════════════════════════════════════════════
//  유틸리티 타입
// ════════════════════════════════════════════════════════════════

/** 모든 ActionRecord 유니온 타입 */
export type AnyActionRecord =
  | PaymentActionRecord
  | InvestmentActionRecord
  | PurchaseActionRecord
  | CivicActionRecord;

/** ActionRecord 생성 시 hash / prevHash 제외한 입력 타입 */
export type ActionRecordInput<T extends ActionRecord> =
  Omit<T, 'hash' | 'prevHash' | 'digitalSignature'>;

/** 감사 체인 검증 결과 */
export interface ChainVerificationResult {
  isValid:       boolean;
  totalRecords:  number;
  brokenAt?:     number;   // 체인이 끊어진 레코드 인덱스
  errorMessage?: string;
}
