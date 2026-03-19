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

korpix-core/
├── README.md · ROADMAP.md · CONTRIBUTING.md · LICENSE
├── .gitignore · .env.example · pyproject.toml · package.json · tsconfig.json
│
├── whitepaper/
│   └── KorPIX_Architecture_Whitepaper.md   ← 전체 아키텍처 백서
│
├── standards/
│   ├── KorPIX_Terminal_Standard.md          ← Trust Terminal 표준
│   ├── KorPIX_Policy_API.md                 ← Policy Engine 표준
│   └── KorPIX_Audit_Protocol.md             ← 감사 기록 표준
│
├── docs/  (6개 문서)
│   ├── system_architecture.md
│   ├── logical_model.md
│   ├── ai_action_flow.md
│   ├── security_model.md
│   ├── use_cases.md
│   └── architecture_diagram.md
│
├── schemas/  (4개 JSON Schema)
├── api/openapi.yaml
├── examples/  (샘플 3개)
│
├── services/
│   ├── policy-engine/src/     models · risk · engine · decision · main
│   ├── audit-network/src/     hashchain · ledger · gateway · main
│   └── execution-gateway/src/ gateway · main
│
├── sdk/
│   ├── python/korpix/         __init__ · models · client
│   └── typescript/src/        models · client · index
│
├── apps/
│   ├── terminal-simulator/    main · actionClient · auth (TypeScript)
│   └── policy-dashboard/      App · Overview · ActionLog · Anomalies · CircuitBreaker (React)
│
├── tests/integration/test_full_pipeline.py   ← 6/6 ALL PASSED ✅
└── scripts/   run_policy_engine · run_audit_network · seed_examples

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


## KorPIX vs 유사 프로젝트

| | AgentBouncr | Microsoft AGT | KorPIX |
| HW Trust Terminal | ❌ | ❌ | ✅ TPM+TEE |
| 금융 규제 감사 | ❌ | ❌ | ✅ 자본시장법 |
| 공공 API 연동 | ❌ | ❌ | ✅ 정부24 |
| 국가 표준 목표 | ❌ | ❌ | ✅ KorPIX Standard |

*KorPIX는 AI 자동화 시대의 행동 신뢰 표준을 목표로 합니다.*
