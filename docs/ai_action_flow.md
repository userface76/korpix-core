# KorPIX AI 행동 처리 흐름

## 표준 처리 순서

```
1. 사용자 인증
   공동인증서 / PASS / 생체인증 중 하나

2. ActionRequest 생성
   action_type + payload + user_id + terminal_id

3. Policy Engine 평가  →  POST /evaluate
   Risk Score 계산 → AUTO_APPROVE / USER_CONFIRM / ADMIN_APPROVE / DENY

4. 결정별 처리
   AUTO_APPROVE  : 즉시 Execution Gateway 호출
   USER_CONFIRM  : 사용자 확인 UI → 확인 후 실행
   ADMIN_APPROVE : 관리자 알림 → 승인 후 실행
   DENY          : 실행 중단, 사용자 안내

5. 실행  →  POST /execute  (승인된 경우만)

6. 감사 기록  →  POST /submit
   ActionRecord 생성 (hash + prevHash + digitalSignature 포함)
```

## UC-003 다단계 결재 흐름

```
구매 요청 → Policy Engine → Tier 결정
  Tier 1: Auto Approve (100만 미만)
  Tier 2: 팀장 승인 (100만~500만)
  Tier 3: 팀장 → 재무팀 (500만~2,000만)
     ※ 긴급(URGENT): 팀장 + 재무팀 병렬 처리, 타임아웃 2시간
  Tier 4: 팀장 → 재무팀 → CFO (2,000만~1억)
  Tier 5: DENY — 이사회 수동 이관 (1억 초과)

각 단계:
  결재자 알림 → 타임아웃(24h) 내 승인/반려
  타임아웃 발생 시 → 대리자 자동 에스컬레이션
  전 과정 Audit Network 기록 의무
```
