/**
 * KorPIX Policy Engine — 결정 타입 표준
 */

export interface PolicyResult {
  decision:   PolicyDecision;
  riskScore:  number;
  reasons:    string[];       // 점수 구성 이유 (감사용)
  timestamp:  string;
  engineVer:  string;         // Policy Engine 버전
}

// Risk Score 구성 요소
export interface RiskFactors {
  // 공통 (UC-001~005)
  actionTypeScore:    number;
  amountScore:        number;
  limitExceeded:      boolean;
  abnormalPattern:    boolean;

  // UC-002 투자 추가
  vixScore?:          number;
  lossLimitScore?:    number;
  concentrationScore?:number;

  // UC-003 구매 추가
  budgetUsageScore?:  number;
  categoryRiskScore?: number;
  urgencyScore?:      number;

  // UC-004 행정 추가
  privacyGradeScore?: number;
  delegationScore?:   number;
  accessFreqScore?:   number;
}
