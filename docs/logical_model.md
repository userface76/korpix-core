# KorPIX 논리 모델
 
## 핵심 엔티티
 
### ActionRecord (AI 행동 감사 기록)
모든 AI 행동의 기본 단위. 해시 체인으로 연결됩니다.
 
| 필드 | 타입 | 설명 |
|---|---|---|
| actionId | UUID | 고유 식별자 |
| actionType | Enum | PAYMENT / INVESTMENT / PURCHASE_REQUEST / CIVIC_SERVICE |
| riskScore | int 0~100 | Policy Engine 계산 위험도 |
| policyDecision | Enum | AUTO_APPROVE / USER_CONFIRM / ADMIN_APPROVE / DENY |
| prevHash | SHA-256 | 이전 레코드 해시 (체인 연결) |
| hash | SHA-256 | 이 레코드 해시 |
| digitalSignature | string | 단말 디지털 서명 |
 
### UserPolicy (사용자 정책)
각 사용자의 행동 허용 범위를 정의합니다.
 
| 필드 | 기본값 | 설명 |
|---|---|---|
| monthly_payment_limit | 1,000,000원 | 월 결제 한도 |
| single_payment_limit | 500,000원 | 건당 결제 한도 |
| max_loss_rate | 10% | 투자 손실 한도 |
| civic_payment_limit | 500,000원 | 공과금 자동납부 한도 |
 
### Risk Score 계산 원칙
- 기본 점수 (행동 유형별) + UC별 추가 점수
- 최대 100점 (캡 적용)
- 즉시 DENY 조건: 예산 초과 / 개인정보 등급 4 / 위임 미검증 / 1억 초과 구매
 
## 해시 체인 구조
 
```
Genesis (prevHash = "000...000")
  ↓
ActionRecord[0]
  prevHash = "000...000"
  hash     = SHA256(record)
  ↓
ActionRecord[1]
  prevHash = ActionRecord[0].hash
  hash     = SHA256(record)
  ↓
  ...
```
