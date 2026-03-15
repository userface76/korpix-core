/**
 * KorPIX Audit Network — 감사 기록 표준 타입
 * =============================================
 * Version:  0.1.0
 * Spec:     KorPIX Architecture Whitepaper §10, §11, §12, §13
 *
 * Audit Network는 AI 에이전트가 수행한 모든 행동을
 * 변조 불가능한 형태로 기록·검증하는 감사 인프라입니다.
 *
 * 데이터 흐름:
 *   Trust Terminal (Terminal Log)
 *     → Audit Gateway  (수집·검증·표준화)
 *     → Distributed Ledger (분산 저장)
 *     → Audit Query System (조회·분석)
 */

import type { AnyActionRecord, ChainVerificationResult } from './action-record';

// ════════════════════════════════════════════════════════════════
//  Terminal Log — Trust Terminal에서 생성되는 원본 기록
// ════════════════════════════════════════════════════════════════

/**
 * Terminal Log Entry
 * Trust Terminal에서 행동이 발생할 때 최초 생성됩니다.
 * Audit Gateway로 전달되기 전 단계의 로컬 기록입니다.
 */
export interface TerminalLogEntry {
  logId:        string;   // UUID v4
  terminalId:   string;   // 생성 단말 ID
  actionRecord: AnyActionRecord;
  terminalHash: string;   // 단말이 계산한 레코드 해시
  terminalSig:  string;   // 단말 비밀키로 서명 (TPM 하드웨어 서명)
  createdAt:    string;   // ISO 8601
  synced:       boolean;  // Audit Gateway 전송 완료 여부
}

// ════════════════════════════════════════════════════════════════
//  Audit Gateway — 수집·검증·표준화 계층
// ════════════════════════════════════════════════════════════════

/** Gateway 검증 결과 */
export type GatewayVerificationStatus =
  | 'PASSED'           // 모든 검증 통과
  | 'FAILED_FORMAT'    // 형식 오류
  | 'FAILED_SIGNATURE' // 서명 검증 실패
  | 'FAILED_CHAIN'     // 해시 체인 불일치
  | 'FAILED_DUPLICATE';// 중복 레코드

/**
 * Audit Gateway가 Terminal Log를 수신·처리한 결과
 */
export interface GatewayProcessingResult {
  logId:              string;
  verificationStatus: GatewayVerificationStatus;
  normalizedRecord?:  NormalizedAuditRecord;  // 검증 통과 시에만 존재
  processedAt:        string;   // ISO 8601
  gatewayId:          string;   // 처리한 Gateway 노드 ID
  errorDetail?:       string;   // 실패 사유
}

/**
 * Gateway가 표준화한 감사 레코드 — Distributed Ledger에 저장됨
 */
export interface NormalizedAuditRecord {
  // 원본 ActionRecord 정보
  actionId:       string;
  actionType:     string;
  terminalId:     string;
  userIdHash:     string;    // 개인정보 보호 — 원본 미저장
  riskScore:      number;
  policyDecision: string;
  executionResult:string;
  actionTimestamp:string;

  // 체인 연결
  prevRecordHash: string;
  recordHash:     string;

  // 서명 (단말 + Gateway 이중 서명)
  terminalSig:    string;
  gatewaySig:     string;

  // 분류 메타
  schemaVersion:  string;
  normalizedAt:   string;
}

// ════════════════════════════════════════════════════════════════
//  Distributed Ledger — 분산 저장 계층
// ════════════════════════════════════════════════════════════════

/** 분산 원장 블록 */
export interface AuditBlock {
  blockIndex:      number;
  blockHash:       string;
  prevBlockHash:   string;
  records:         NormalizedAuditRecord[];
  merkleRoot:      string;    // 블록 내 레코드의 Merkle Tree 루트
  timestamp:       string;    // ISO 8601
  nodeId:          string;    // 블록을 생성한 노드 ID
  nodeSig:         string;    // 노드 디지털 서명
}

/** 분산 원장 노드 상태 */
export interface LedgerNodeStatus {
  nodeId:          string;
  endpoint:        string;    // API 엔드포인트
  latestBlockIndex:number;
  latestBlockHash: string;
  isSynced:        boolean;   // 다른 노드와 동기화 여부
  lastSeenAt:      string;
}

// ════════════════════════════════════════════════════════════════
//  Audit Query System — 조회·분석 계층
// ════════════════════════════════════════════════════════════════

/** 감사 기록 조회 필터 */
export interface AuditQueryFilter {
  userIdHash?:       string;
  terminalId?:       string;
  actionType?:       string;
  policyDecision?:   string;
  executionResult?:  string;
  fromTimestamp?:    string;   // ISO 8601
  toTimestamp?:      string;   // ISO 8601
  minRiskScore?:     number;
  maxRiskScore?:     number;
  page?:             number;   // 기본값: 1
  pageSize?:         number;   // 기본값: 50, 최대: 500
}

/** 감사 기록 조회 결과 */
export interface AuditQueryResult {
  records:      NormalizedAuditRecord[];
  total:        number;
  page:         number;
  pageSize:     number;
  queryId:      string;   // 조회 자체의 감사 추적 ID
}

/** 이상 행동 탐지 이벤트 */
export interface AnomalyEvent {
  eventId:       string;
  eventType:     AnomalyType;
  terminalId:    string;
  userIdHash:    string;
  detectedAt:    string;
  severity:      'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description:   string;
  relatedActionIds: string[];   // 이상 탐지에 연관된 ActionRecord ID 목록
  resolved:      boolean;
}

export type AnomalyType =
  | 'HIGH_FREQUENCY_ACCESS'    // 비정상 접근 빈도
  | 'CHAIN_TAMPER_DETECTED'    // 해시 체인 변조 감지
  | 'SIGNATURE_MISMATCH'       // 서명 불일치
  | 'UNAUTHORIZED_DELEGATION'  // 위임 없는 대리 접근
  | 'CIRCUIT_BREAKER_TRIGGERED'// 서킷 브레이커 발동
  | 'BUDGET_EXCEEDED'          // 예산 초과 시도
  | 'SPLIT_ORDER_PATTERN'      // 분할 발주 패턴
  | 'URGENT_ABUSE_PATTERN';    // 긴급 남용 패턴

/** 감사 보고서 */
export interface AuditReport {
  reportId:       string;
  generatedAt:    string;
  period: {
    from: string;
    to:   string;
  };
  summary: {
    totalActions:       number;
    autoApproved:       number;
    userConfirmed:      number;
    adminApproved:      number;
    denied:             number;
    anomaliesDetected:  number;
    chainIntegrity:     'INTACT' | 'COMPROMISED';
  };
  anomalies:      AnomalyEvent[];
  verificationResult: ChainVerificationResult;
}

// ════════════════════════════════════════════════════════════════
//  Audit Network 인터페이스 (구현체가 따라야 할 계약)
// ════════════════════════════════════════════════════════════════

export interface IAuditNetwork {
  /** Terminal Log를 Gateway로 전송 */
  submitLog(entry: TerminalLogEntry): Promise<GatewayProcessingResult>;

  /** 감사 기록 조회 */
  query(filter: AuditQueryFilter): Promise<AuditQueryResult>;

  /** 해시 체인 무결성 검증 */
  verifyChain(fromIndex?: number, toIndex?: number): Promise<ChainVerificationResult>;

  /** 이상 행동 탐지 이벤트 조회 */
  getAnomalies(severity?: AnomalyEvent['severity']): Promise<AnomalyEvent[]>;

  /** 감사 보고서 생성 */
  generateReport(from: string, to: string): Promise<AuditReport>;
}
