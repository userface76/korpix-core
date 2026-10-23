# KorPIX Architecture Whitepaper

**국민형 AI 개인 PC를 위한 AI 행동 신뢰·데이터 주권 아키텍처 백서**

원본: Version 0.1 · 2025년 초안 / 비전 보완: 2026-10-23

> **현재 구현 수준:** 정책 판단·Mock 실행·인메모리 감사의 소프트웨어 프로토타입. 국민형 AI PC 보급, 정부·금융기관 연계, TPM/TEE 및 독립 보안 인증은 **향후 목표**입니다.

---

## 1. 개요

행동형 AI(Agentic AI)가 결제·투자·구매·행정을 직접 수행하는 시대가 열리고 있습니다.
이 흐름에서 가장 중요한 질문은 하나입니다.

> **"AI가 행동할 때, 그 행동을 누가 어떻게 통제하고 책임지는가?"**

KorPIX(Korea Protocol Infrastructure eXchange)는 이 질문에 대한 인프라 수준의 답입니다.
AI 에이전트가 실제 경제 활동을 수행할 때 그 행동을 **실행 · 통제 · 감사**하는
표준 신뢰 인프라를 정의하고 구현하는 것을 목표로 합니다.

### 1.1 확장 비전: 한국형 소버린 개인 AI PC

KorPIX의 출발점은 **국민형 AI 개인 PC에 내장될 공통 신뢰 아키텍처**입니다. 국내·해외 AI 서비스에 국민 데이터가 불필요하게 전송되는 위험을 줄이고, 개인이 데이터의 목적·범위·수신자·동의·철회를 통제하도록 설계합니다. 정부·금융 데이터는 법적 자격과 동의에 따른 **공식 API 및 협력 체계**로 연계합니다.

- **개인 주권:** 민감정보 로컬 우선 처리·개인 데이터 금고·동의와 철회.
- **실행 주권:** LLM의 제안과 실행 권한 분리·서명된 허가 검증·중지와 복구.
- **국가 인프라 주권:** 개방형 인터페이스·국내 선택 가능한 AI/보안 인프라·독립 증거.
- **금지되는 오해:** 국가의 원본 개인정보 중앙 수집이나 무단 AI 학습을 목표로 하지 않음.

상세 설계와 법·보안 경계는 [Sovereign Personal AI PC Architecture](../docs/sovereign_ai_pc_architecture.md)를 따릅니다.

---

## 2. 핵심 3대 시스템

### 2.1 Trust Terminal

**향후 목표:** AI 에이전트가 행동을 실행하는 보안 단말입니다. 아래 TPM/TEE 기능은 현재 저장소에 실물 구현이 있음을 뜻하지 않습니다.

- **AI Runtime Environment** — AI 에이전트 실행 공간
- **Secure Hardware Module** — TPM 2.0 기반 키 보관 및 서명
- **User Authentication** — 공동인증서 / PASS / 생체 인증
- **Local Policy Enforcement** — 로컬 정책 1차 검증
- **Secure Execution Environment** — TEE 기반 격리 실행

### 2.2 Policy Engine

모든 AI 행동 요청을 실행 전에 평가합니다.

```
ActionRequest
  → Identity Verification  (신원 확인)
  → Permission Check       (권한 확인)
  → Policy Evaluation      (정책 평가)
  → Risk Analysis          (위험도 분석)  ← Risk Score 0~100
  → Decision               (결정)

Risk Score → Decision:
  0 ~ 29  → AUTO_APPROVE    자동 승인
 30 ~ 59  → USER_CONFIRM    사용자 확인
 60 ~ 79  → ADMIN_APPROVE   관리자 승인
 80 ~ 100 → DENY            차단
```

### 2.3 Audit Network

**목표:** AI 행동을 검증 가능한 형태로 기록합니다. 현재는 개발용 해시 체인·소프트 서명·인메모리 원장으로, 영구 불변 저장과 운영용 암호서명은 미구현입니다.

```
Trust Terminal
  → Terminal Log 생성 (hash + digitalSignature)
  → Audit Gateway 전송

Audit Gateway
  → 형식 검증 → 서명 검증 → 해시 검증 → 체인 검증
  → Distributed Ledger 저장
  → 이상 탐지 (AnomalyDetector)
```

---

## 3. 전체 행동 처리 흐름

```
사용자 / AI Agent
      │
      ▼
Trust Terminal (신원 인증)
      │
      ▼
Policy Engine
  ├─ Risk Score 계산
  ├─ AUTO_APPROVE → 즉시 실행
  ├─ USER_CONFIRM → 사용자 확인 후 실행
  ├─ ADMIN_APPROVE → 관리자 승인 후 실행
  └─ DENY → 차단, 사용자 안내
      │
      ▼ (승인된 경우)
Execution Gateway
  ├─ 결제 API (UC-001)
  ├─ 증권 API (UC-002)
  ├─ ERP API  (UC-003)
  └─ 공공 API (UC-004)
      │
      ▼
Audit Network
  └─ ActionRecord → 해시 체인 → Distributed Ledger
```

---

### 3.1 데이터 주권·외부 반출 흐름 (목표 아키텍처)

```
국민의 AI 개인 PC: 로컬 AI + Personal Data Vault
    → 신원·목적·동의·위험 Policy Engine
    → 인간 승인 (필요 시)
    → 서명된 행동/반출 허가증 (향후 구현)
    → 검증하는 Execution / Data Egress Gateway
    → 적법한 공식 공공·금융 API (자격·계약·사전 협의 필요)
    → 영구 서명 증거 / 철회·감사 (향후 구현)
```

원본 개인정보는 일괄 중앙집중하지 않으며, 외부 AI 모델로 전송할 때도 필요한 필드와 목적·수신자를 통제합니다. 국내 저장만으로 보안을 보증할 수 없고, 국외 이전의 허용 여부는 해당 법령에 따라 판단합니다.

---

## 4. 파일럿 유스케이스

| UC | 영역 | 핵심 검증 포인트 |
|---|---|---|
| UC-001 | 소액 정기결제 자동화 | ActionRecord 표준 · 기본 Policy Engine |
| UC-002 | AI 투자 자동화 | 서킷 브레이커 · 손실 한도 · 자본시장법 감사 |
| UC-003 | 기업 구매 승인 자동화 | 조직 계층 결재 · ERP 연동 · 5단계 티어 |
| UC-004 | AI 행정 서비스 자동화 | 개인정보 4등급 · 공공 API · 위임 검증 |
| UC-005 | AI Node PC 하드웨어 Trust Terminal | TPM · TEE · NPU 실물 단말 전환 |

---

## 5. UC-005 하드웨어 아키텍처

**계획 단계:** 소프트웨어 프로토타입을 실제 물리 단말로 전환하는 단계의 제안 구조입니다. 아래 하드웨어 사양과 수치는 검증된 제품 성능이 아닙니다.

```
┌─────────────────────────────────┐
│   AI Node PC (KorPIX Terminal)  │
│                                 │
│  ┌─────────┐  ┌──────────────┐  │
│  │ CPU+NPU │  │  HBM Memory  │  │
│  │  SoC    │  │   32GB 1TB/s │  │
│  └─────────┘  └──────────────┘  │
│                                 │
│  ┌──────────────────────────┐   │
│  │  TEE (OP-TEE Secure World)│  │
│  │  policy_engine_ta         │  │
│  │  key_manager_ta           │  │
│  │  audit_signer_ta          │  │
│  └──────────────────────────┘   │
│                                 │
│  ┌─────────┐  ┌──────────────┐  │
│  │ TPM 2.0 │  │  NVMe 512GB  │  │
│  │ PCR·Key │  │  Write-Once  │  │
│  └─────────┘  └──────────────┘  │
└─────────────────────────────────┘
```

### 부팅 신뢰 체인
```
Secure Boot (UEFI 서명 검증)
  → Measured Boot (TPM PCR 기록)
    → Remote Attestation (원격 무결성 증명)
      → 서비스 시작
```

### 처리 속도 가정 및 목표 (실측·검증 전)

| 단계 | SW 에뮬레이터 | HW 목표 |
|---|---|---|
| Policy Engine | 120ms | 60ms 이하 |
| Dilithium3 서명 | 18ms | 3ms (NPU) |
| AES-256 암호화 | 1ms | 0.1ms (AES-NI) |
| 상시 전력 | 15W (CPU 피크) | 5W 이하 |
| 전체 체감 응답 | — | 3초 이내 |

---

## 6. 시장 차별화 목표와 객관적 검증의 구분

외부 프로젝트의 기능 부재를 입증하지 않은 상태에서 경쟁사가 해당 기능을 제공하지 않는다고 단정하지 않습니다. KorPIX가 **목표로 하는 차별화 조합**은 (1) 개인 AI PC 로컬 데이터 주권, (2) 독립 행동 권한 강제, (3) 검증 가능한 감사 증거, (4) 공공·금융의 적법한 상호운용, (5) TPM/TEE 기반 단말 신뢰입니다.

현재 코드에서는 정책 판단, Mock 실행, 개발용 감사·테스트 코드가 존재합니다. 로컬 데이터 금고·반출 통제·실 기관 연동·하드웨어 신뢰·독립 보안 인증은 **추가 실증 대상**입니다.

---

## 7. 표준화 목표

UC-001~005 파일럿 완료 후 다음 세 가지 표준을 공개합니다.

- **KorPIX Terminal Standard v1.0** — Trust Terminal 요건 및 인터페이스
- **KorPIX Policy API v1.0** — Policy Engine 표준 인터페이스
- **KorPIX Audit Protocol v1.0** — 감사 기록 표준 프로토콜
- **KorPIX Consent & Data Egress Protocol v1.0** — 동의·데이터 반출 허가·철회 규칙

이 표준들이 공개되면 타 제조사도 KorPIX 호환 단말을 만들 수 있게 됩니다.
KorPIX는 특정 제품이 아닌 **국민의 데이터 주권을 지키는 AI 행동 신뢰 인프라의 개방형 표준**을 목표로 합니다. 정부 공식 표준으로 채택되었다는 주장은 아닙니다.

---

*KorPIX Core — github.com/userface76/korpix-core*
*Apache License 2.0*
