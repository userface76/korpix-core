# KorPIX Core

**AI 행동 신뢰 인프라 (AI Behavior Trust Infrastructure)**

KorPIX는 자율 행동형 AI(Agentic AI)가 실제 경제 활동을 수행할 때
그 행동을 안전하게 **실행 · 통제 · 감사**하는 표준 인프라입니다.

---

## 핵심 3대 시스템

| 시스템 | 역할 | 핵심 기술 |
|---|---|---|
| **Trust Terminal** | AI 행동 실행 환경 보호 | TPM 2.0 · TEE · Secure Boot |
| **Policy Engine** | 실행 전 위험도 검증 및 승인 결정 | Risk Score → 4단계 결정 |
| **Audit Network** | 불변 감사 기록 | 해시 체인 · 디지털 서명 |

---

## 파일 구조

```
korpix-core/
│
├── standards/                   ← KorPIX 공통 인터페이스 (TypeScript)
│   ├── action-record.ts         ← ActionRecord 타입 (UC-001~004 전체)
│   ├── policy-engine.ts         ← PolicyResult · RiskFactors 타입
│   └── audit-network.ts         ← AuditBlock · AnomalyEvent 타입
│
├── policy-engine/               ← Policy Engine 구현 (Python)
│   └── risk-evaluator.py        ← Risk Score 계산 · 결정 로직
│
├── audit-network/               ← Audit Network 구현 (Python)
│   └── hash-chain.py            ← 해시 체인 생성 · 검증
│
└── docs/                        ← 파일럿 유스케이스 문서
    ├── UC-001-payment.md
    ├── UC-002-investment.md
    ├── UC-003-purchase.md
    ├── UC-004-civic.md
    └── UC-005-hardware.md
```

---

## 빠른 동작 확인

```bash
# Policy Engine 동작 확인
python policy-engine/risk-evaluator.py

# Audit Network 해시 체인 확인
python audit-network/hash-chain.py
```

---

## 파일럿 유스케이스

| UC | 영역 | 핵심 검증 포인트 |
|---|---|---|
| **UC-001** | 소액 정기결제 자동화 | ActionRecord 표준 · 기본 Policy Engine |
| **UC-002** | AI 투자 자동화 | 서킷 브레이커 · 손실 한도 · 규제 감사 |
| **UC-003** | 기업 구매 승인 자동화 | 조직 계층 결재 · ERP 연동 |
| **UC-004** | AI 행정 서비스 자동화 | 개인정보 4등급 · 공공 API 게이트웨이 |
| **UC-005** | AI Node PC 하드웨어 전환 | TPM · TEE · NPU 실물 단말 |

---

## standards/ — 공통 인터페이스

`standards/` 폴더의 TypeScript 타입 정의가 KorPIX의 **공통어**입니다.
모든 컨소시엄 파트너는 이 구조를 기반으로 연동합니다.

```typescript
// 모든 AI 행동은 이 구조로 기록됩니다
import type { ActionRecord } from './standards/action-record';
```

---

## 관련 문서

- KorPIX Architecture Whitepaper (한국어)
- UC-001~005 파일럿 유스케이스 계획서

---

*KorPIX는 AI 자동화 시대의 행동 신뢰 표준을 목표로 합니다.*
