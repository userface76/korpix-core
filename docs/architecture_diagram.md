# KorPIX 아키텍처 다이어그램
 
## 전체 시스템 다이어그램
 
```
┌─────────────────────────────────────────────────────────────────┐
│                     KorPIX Trust Terminal                        │
│                                                                  │
│  ┌───────────────┐   ┌──────────────────────────────────────┐   │
│  │  AI Runtime   │   │     TEE (Secure World)               │   │
│  │  Environment  │──▶│  ┌─────────────┐  ┌──────────────┐  │   │
│  └───────────────┘   │  │policy_engine│  │key_manager_ta│  │   │
│                      │  │     _ta     │  └──────────────┘  │   │
│  ┌───────────────┐   │  └─────────────┘  ┌──────────────┐  │   │
│  │ User Auth     │   │                   │audit_signer  │  │   │
│  │ (PASS/공동인증)│   │                   │    _ta       │  │   │
│  └───────────────┘   │                   └──────────────┘  │   │
│                      └──────────────────────────────────────┘   │
│                                     │                           │
│  ┌───────────────┐                  │                           │
│  │  TPM 2.0      │◀─────────────────┘                           │
│  │  PCR · Keys   │                                              │
│  └───────────────┘                                              │
└─────────────────────────────────────────────────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────┐      ┌───────────────┐      ┌─────────────────┐
│   Policy    │      │   Execution   │      │   Audit         │
│   Engine    │      │   Gateway     │      │   Network       │
│  :8001      │      │  :8003        │      │  :8002          │
│             │      │               │      │                 │
│ Risk Score  │      │ Payment API   │      │ Gateway         │
│ Decision    │      │ Investment API│      │ HashChain       │
│ Circuit Brk │      │ ERP API       │      │ Ledger          │
│ Approval    │      │ Gov API       │      │ AnomalyDetector │
└─────────────┘      └───────────────┘      └─────────────────┘
```
 
## Policy Engine Risk Score 흐름
 
```
ActionRequest
    │
    ├─ 행동 유형 기본 점수 (+10~20)
    ├─ 이상 접근 빈도 체크  (+40 if 5회/10분)
    │
    ├─ UC-001 PAYMENT
    │    ├─ 금액 구간 점수
    │    └─ 건당 한도 초과 (+30)
    │
    ├─ UC-002 INVESTMENT
    │    ├─ VIX 구간 점수
    │    ├─ 손실 한도 초과 (+60)
    │    ├─ 섹터 집중도
    │    └─ 적합성 원칙 위반 (+30)
    │
    ├─ UC-003 PURCHASE
    │    ├─ 예산 초과 → DENY 즉시
    │    ├─ 금액 티어 점수
    │    ├─ 품목 위험도
    │    └─ 긴급 남용 패턴 (+10)
    │
    └─ UC-004 CIVIC
         ├─ 개인정보 등급4 → DENY 즉시
         ├─ 위임 미검증  → DENY 즉시
         └─ 납부 한도 초과 (+25)
 
→ 합산 Risk Score (0~100)
→ 결정: AUTO_APPROVE / USER_CONFIRM / ADMIN_APPROVE / DENY
```
 
## Audit Network 해시 체인
 
```
Genesis
prevHash: "0000...0000" (64자리)
     │
     ▼
ActionRecord[0]
prevHash: "0000...0000"
hash:     SHA256(record - hash - sig)
sig:      SOFT_SIGN(hash) or TPM_SIGN(hash)
     │
     ▼
ActionRecord[1]
prevHash: ActionRecord[0].hash
hash:     SHA256(record - hash - sig)
     │
     ▼
     ...
 
변조 탐지: 중간 레코드 수정 → 이후 prevHash 불일치 → 즉시 탐지
```
