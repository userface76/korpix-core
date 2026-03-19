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
├ README.md
├ LICENSE
├ ROADMAP.md
├ CONTRIBUTING.md
├ .gitignore
├ pyproject.toml
├ package.json
├ tsconfig.json
├ .env.example
│
├ whitepaper/
│   └ KorPIX_Architecture_Whitepaper.md
│
├ standards/
│   ├ KorPIX_Terminal_Standard.md
│   ├ KorPIX_Policy_API.md
│   └ KorPIX_Audit_Protocol.md
│
├ docs/
│   ├ system_architecture.md
│   ├ logical_model.md
│   ├ ai_action_flow.md
│   ├ security_model.md
│   ├ use_cases.md
│   └ architecture_diagram.md
│
├ schemas/
│   ├ action_record.schema.json
│   ├ action_request.schema.json
│   ├ policy_decision.schema.json
│   └ risk_score.schema.json
│
├ api/
│   └ openapi.yaml
│
├ examples/
│   ├ sample_action_request.json
│   ├ sample_action_record.json
│   └ sample_policy_rules.yaml
│
├ apps/
│   ├ terminal-simulator/
│   │   ├ package.json
│   │   ├ src/
│   │   │   ├ main.ts
│   │   │   ├ ui.ts
│   │   │   ├ auth.ts
│   │   │   └ actionClient.ts
│   │   └ public/
│   │
│   └ policy-dashboard/
│       ├ package.json
│       ├ src/
│       │   ├ main.tsx
│       │   ├ App.tsx
│       │   ├ pages/
│       │   └ components/
│       └ public/
│
├ services/
│   ├ policy-engine/
│   │   ├ README.md
│   │   ├ src/
│   │   │   ├ main.py
│   │   │   ├ engine.py
│   │   │   ├ identity.py
│   │   │   ├ permission.py
│   │   │   ├ policy.py
│   │   │   ├ risk.py
│   │   │   ├ decision.py
│   │   │   └ models.py
│   │   └ tests/
│   │
│   ├ audit-network/
│   │   ├ README.md
│   │   ├ src/
│   │   │   ├ main.py
│   │   │   ├ logger.py
│   │   │   ├ signer.py
│   │   │   ├ hashchain.py
│   │   │   ├ ledger.py
│   │   │   └ query.py
│   │   └ tests/
│   │
│   └ execution-gateway/
│       ├ README.md
│       ├ src/
│       │   ├ main.py
│       │   ├ gateway.py
│       │   ├ handlers.py
│       │   ├ connectors.py
│       │   └ sandbox.py
│       └ tests/
│
├ sdk/
│   ├ python/
│   │   └ korpix/
│   │       ├ __init__.py
│   │       ├ client.py
│   │       ├ models.py
│   │       └ auth.py
│   │
│   └ typescript/
│       └ src/
│           ├ index.ts
│           ├ client.ts
│           ├ models.ts
│           └ auth.ts
│
├ tests/
│   ├ integration/
│   ├ unit/
│   └ fixtures/
│
└ scripts/
    ├ run_policy_engine.sh
    ├ run_audit_network.sh
    └ seed_examples.py

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


## KorPIX vs 유사 프로젝트

| | AgentBouncr | Microsoft AGT | KorPIX |
| HW Trust Terminal | ❌ | ❌ | ✅ TPM+TEE |
| 금융 규제 감사 | ❌ | ❌ | ✅ 자본시장법 |
| 공공 API 연동 | ❌ | ❌ | ✅ 정부24 |
| 국가 표준 목표 | ❌ | ❌ | ✅ KorPIX Standard |

*KorPIX는 AI 자동화 시대의 행동 신뢰 표준을 목표로 합니다.*
