# KorPIX Policy API Standard v0.1

**Policy Engine 표준 인터페이스 명세**

---

## 1. 개요

KorPIX Policy API는 AI 에이전트의 행동 요청을 평가하여
실행 가능 여부를 결정하는 표준 인터페이스입니다.
모든 KorPIX 호환 Policy Engine은 이 명세를 구현해야 합니다.

---

## 2. Risk Score 계산 표준

### 2.1 점수 범위 및 결정 기준

| Risk Score | 결정 | 의미 |
|---|---|---|
| 0 ~ 29 | AUTO_APPROVE | 자동 승인 — 즉시 실행 |
| 30 ~ 59 | USER_CONFIRM | 사용자 확인 필요 |
| 60 ~ 79 | ADMIN_APPROVE | 관리자 승인 필요 |
| 80 ~ 100 | DENY | 차단 — 실행 불가 |

### 2.2 기본 점수 구성 (모든 UC 공통)

| 요소 | 계산 방식 |
|---|---|
| 행동 유형 기본 점수 | PAYMENT=15, INVESTMENT=20, PURCHASE=10, CIVIC=10 |
| 이상 접근 빈도 | 10분 내 5회 이상 → +40 |

### 2.3 UC별 추가 점수

**UC-001 결제**
- 금액 구간: 10만 미만 +10, 50만 미만 +20, 50만 이상 +35
- 건당 한도 초과: +30

**UC-002 투자**
- VIX ≥ 35 또는 코스피 -5% 이상: 서킷 브레이커 → DENY
- 손실 한도 초과: +60
- 적합성 원칙 위반: +30

**UC-003 기업 구매**
- 1억원 초과: 즉시 DENY (이사회 이관)
- 예산 초과: 즉시 DENY
- 긴급 구매 남용 (월 3회+): +10

**UC-004 행정 서비스**
- 개인정보 등급 4: 즉시 DENY
- 위임 관계 미검증: 즉시 DENY

---

## 3. 승인 체인 표준 (UC-003)

| 티어 | 금액 범위 | 결재 경로 | 타임아웃 |
|---|---|---|---|
| Tier 1 | 100만 미만 | 자동 승인 | — |
| Tier 2 | 100만 ~ 500만 | 팀장 | 24시간 |
| Tier 3 | 500만 ~ 2,000만 | 팀장 → 재무팀 | 각 24시간 |
| Tier 4 | 2,000만 ~ 1억 | 팀장 → 재무팀 → CFO | 48시간 |
| Tier 5 | 1억 초과 | DENY — 이사회 수동 이관 | — |

긴급(URGENT) 플래그 시: Tier 3 이상 병렬 처리, 타임아웃 2시간으로 단축

---

## 4. 필수 API 엔드포인트

KorPIX 호환 Policy Engine은 다음 엔드포인트를 반드시 구현해야 합니다.

```
POST /evaluate           행동 요청 평가 (필수)
GET  /health             서비스 헬스 체크 (필수)
POST /circuit-breaker/check      서킷 브레이커 확인 (UC-002 구현 시 필수)
POST /circuit-breaker/deactivate 서킷 브레이커 해제 (UC-002 구현 시 필수)
```

전체 명세: `api/openapi.yaml` 참조

---

## 5. 응답 표준

모든 `/evaluate` 응답은 다음 필드를 반드시 포함해야 합니다.

```json
{
  "result_id":       "uuid",
  "request_id":      "uuid",
  "decision":        "AUTO_APPROVE | USER_CONFIRM | ADMIN_APPROVE | DENY",
  "risk_score":      0,
  "reasons":         ["string"],
  "requires_notify": false,
  "engine_version":  "semver",
  "decided_at":      "ISO 8601"
}
```
