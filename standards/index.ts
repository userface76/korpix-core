/**
 * KorPIX Standards — 타입 통합 진입점
 * ======================================
 * Version: 0.4.0
 *
 * 모든 KorPIX 표준 타입을 이 파일 하나에서 임포트하세요.
 *
 * 사용 예:
 *   import type { ActionRecord, PolicyResult, AuditGateway }
 *     from '@korpix/standards';
 */

// ── action-record.ts ─────────────────────────────────────────
export type {
  // 열거형 / 기본 타입
  ActionType,
  PolicyDecision,
  ExecutionStatus,
  ApprovalStatus,
  PrivacyGrade,
  PurchaseCategory,

  // 공통 기반
  ActionRecord,
  ApprovalStep,

  // UC별 확장
  PaymentActionRecord,
  InvestmentActionRecord,
  PurchaseActionRecord,
  CivicActionRecord,

  // 유틸리티
  AnyActionRecord,
  ActionRecordInput,
  ChainVerificationResult,
} from './action-record';

// ── policy-engine.ts ─────────────────────────────────────────
export type {
  // Risk Factor 타입
  BaseRiskFactors,
  InvestmentRiskFactors,
  PurchaseRiskFactors,
  CivicRiskFactors,
  RiskFactors,

  // 입출력 타입
  ActionRequest,
  UserPolicy,
  PolicyResult,
  PolicyAction,

  // 인터페이스 계약
  IRiskEvaluator,
  IPolicyEngine,
} from './policy-engine';

export {
  // 상수
  RISK_THRESHOLDS,
  POLICY_ENGINE_VERSION,
} from './policy-engine';

// ── audit-network.ts ─────────────────────────────────────────
export type {
  // 계층별 데이터 타입
  TerminalLogEntry,
  NormalizedAuditRecord,
  GatewayProcessingResult,
  GatewayVerificationStatus,
  AuditBlock,
  LedgerNodeStatus,

  // 조회 타입
  AuditQueryFilter,
  AuditQueryResult,
  AuditReport,

  // 이상 탐지
  AnomalyEvent,
  AnomalyType,

  // 인터페이스 계약
  IAuditNetwork,
} from './audit-network';
