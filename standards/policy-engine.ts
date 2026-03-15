/**
 * KorPIX Policy Engine — 결정 타입 표준
 * ========================================
 * Version:  0.1.0
 * Spec:     KorPIX Architecture Whitepaper §7, §8, §9
 *
 * Policy Engine은 AI 에이전트의 행동 요청을 분석하여
 * 실행 여부를 결정하는 KorPIX 핵심 통제 시스템입니다.
 *
 * 결정 흐름:
 *   ActionRequest
 *     → Identity Verification
 *     → Permission Check
 *     → Policy Evaluation
 *     → Risk Analysis         ← RiskFactors 계산
 *     → Decision              ← PolicyResult 반환
 */

import type { ActionType, PolicyDecision } from './action-record';

// ════════════════════════════════════════════════════════════════
//  Risk Score 구성 요소
// ════════════════════════════════════════════════════════════════

/**
 * 모든 UC에 공통 적용되는 기본 Risk 요소
 * 각 필드는 Risk Score에 더해지는 가중치 점수를 나타냅니다.
 */
export interface BaseRiskFactors {
  // UC-001~005 공통
  actionTypeScore:   number;   // 행동 유형 기본 점수
  amountScore:       number;   // 금액 기반 점수
  limitExceeded:     boolean;  // 한도 초과 여부 (true → +30)
  abnormalPattern:   boolean;  // 이상 패턴 감지 (true → +40)
  systemStatusScore: number;   // 시스템 상태 이상 가중치
}

/**
 * UC-002 투자 추가 Risk 요소
 */
export interface InvestmentRiskFactors extends BaseRiskFactors {
  vixScore:           number;  // VIX 지수 기반 점수
  lossLimitScore:     number;  // 손실 한도 초과 점수 (초과 시 +60)
  concentrationScore: number;  // 섹터 집중도 점수
  monthlyUsageScore:  number;  // 월 한도 소진율 점수
  suitabilityScore:   number;  // 적합성 원칙 위반 점수
  circuitBreakerTriggered: boolean;  // 서킷 브레이커 발동 여부
}

/**
 * UC-003 기업 구매 추가 Risk 요소
 */
export interface PurchaseRiskFactors extends BaseRiskFactors {
  budgetUsageScore:    number;  // 부서 예산 소진율 점수
  categoryRiskScore:   number;  // 품목 위험도 점수
  urgencyScore:        number;  // 긴급 구매 가중치
  urgencyAbuseScore:   number;  // 긴급 남용 패턴 점수
  splitOrderScore:     number;  // 분할 발주 패턴 점수
  budgetExceeded:      boolean; // 예산 초과 여부 (true → DENY)
}

/**
 * UC-004 행정 서비스 추가 Risk 요소
 */
export interface CivicRiskFactors extends BaseRiskFactors {
  privacyGradeScore:   number;  // 개인정보 등급 가중치
  delegationScore:     number;  // 대리 행동 가중치
  accessFrequencyScore:number;  // 접근 빈도 이상 점수
  delegationValid:     boolean; // 위임 관계 유효성
  isDeniedByGrade4:    boolean; // 개인정보 4등급 → 즉시 DENY
}

/** 모든 Risk Factor 유니온 */
export type RiskFactors =
  | BaseRiskFactors
  | InvestmentRiskFactors
  | PurchaseRiskFactors
  | CivicRiskFactors;

// ════════════════════════════════════════════════════════════════
//  Policy Engine 입력 / 출력 타입
// ════════════════════════════════════════════════════════════════

/**
 * Policy Engine으로 들어오는 행동 요청
 */
export interface ActionRequest {
  // 기본 식별
  requestId:   string;       // 요청 고유 ID (UUID v4)
  actionType:  ActionType;
  agentId:     string;
  userId:      string;
  terminalId:  string;

  // 행동 내용
  payload:     Record<string, unknown>;

  // 사용자 정책 (Trust Terminal에서 조회)
  userPolicy:  UserPolicy;

  // 요청 메타
  timestamp:   string;       // ISO 8601
  clientIp?:   string;       // 선택적 (로깅용)
}

/**
 * 사용자 정책 — Trust Terminal에서 로드
 */
export interface UserPolicy {
  // UC-001 결제
  monthlyPaymentLimit:  number;   // 월 결제 한도 (KRW)
  singlePaymentLimit:   number;   // 건당 결제 한도 (KRW)

  // UC-002 투자
  monthlyInvestLimit:   number;   // 월 투자 한도 (KRW)
  maxLossRate:          number;   // 손실 한도 (0.10 = 10%)
  maxSectorConcentration: number; // 최대 섹터 집중도 (0.35 = 35%)
  investorRiskGrade:    1 | 2 | 3 | 4 | 5;

  // UC-003 구매
  autoApproveThreshold: number;   // 자동 승인 한도 (KRW)

  // UC-004 행정
  civicPaymentLimit:    number;   // 공과금 자동납부 한도 (KRW)

  // 공통
  allowedActionTypes:   ActionType[];
  twoFactorRequired:    boolean;
  policyVersion:        string;
}

/**
 * Policy Engine 결정 결과 — ActionRecord에 기록됨
 */
export interface PolicyResult {
  decision:        PolicyDecision;
  riskScore:       number;          // 0 ~ 100
  riskFactors:     RiskFactors;     // 점수 구성 상세 (감사용)
  reasons:         string[];        // 결정 이유 설명
  requiresAction?: PolicyAction;    // USER_CONFIRM / ADMIN_APPROVE 시 필요 조치
  policyEngineVer: string;          // Policy Engine 버전
  evaluatedAt:     string;          // ISO 8601
}

/**
 * 추가 조치가 필요한 경우 — User Confirm / Admin Approve 상세
 */
export interface PolicyAction {
  actionRequired:  'USER_CONFIRM' | 'ADMIN_APPROVE' | 'ESCALATE';
  targetUserId?:   string;    // 승인 요청할 대상 (관리자 ID)
  message:         string;    // 사용자/관리자에게 표시할 메시지
  timeoutSeconds:  number;    // 응답 타임아웃 (초)
  approvalTier?:   number;    // UC-003: 승인 티어 (1~5)
}

// ════════════════════════════════════════════════════════════════
//  Policy Engine 인터페이스 (구현체가 따라야 할 계약)
// ════════════════════════════════════════════════════════════════

/**
 * Risk Evaluator 인터페이스
 * Python risk-evaluator.py가 이 계약을 구현합니다.
 */
export interface IRiskEvaluator {
  /**
   * 행동 요청의 위험도를 계산하여 0~100 점수를 반환합니다.
   * 점수가 높을수록 위험합니다.
   */
  calculateRiskScore(request: ActionRequest): Promise<{
    score:   number;
    factors: RiskFactors;
  }>;
}

/**
 * Policy Engine 전체 인터페이스
 */
export interface IPolicyEngine {
  /**
   * 행동 요청을 평가하여 실행 여부를 결정합니다.
   * 이 메서드 하나로 전체 Policy 검증 파이프라인이 동작합니다.
   */
  evaluate(request: ActionRequest): Promise<PolicyResult>;

  /**
   * 특정 사용자의 정책을 갱신합니다.
   */
  updateUserPolicy(userId: string, policy: Partial<UserPolicy>): Promise<void>;
}

// ════════════════════════════════════════════════════════════════
//  Risk Score → Decision 매핑 상수
// ════════════════════════════════════════════════════════════════

export const RISK_THRESHOLDS = {
  AUTO_APPROVE:  30,   // 0 ~ 29  → 자동 승인
  USER_CONFIRM:  60,   // 30 ~ 59 → 사용자 확인
  ADMIN_APPROVE: 80,   // 60 ~ 79 → 관리자 승인
  DENY:          80,   // 80 +    → 차단
} as const;

export const POLICY_ENGINE_VERSION = '0.1.0';
