# KorPIX Architecture Whitepaper
 
**AI 행동 신뢰 인프라 아키텍처 백서**
Version 0.1 · 2025년 초안
 
---
 
## 1. 개요
 
행동형 AI(Agentic AI)가 결제·투자·구매·행정을 직접 수행하는 시대가 열리고 있습니다.
이 흐름에서 가장 중요한 질문은 하나입니다.
 
> **"AI가 행동할 때, 그 행동을 누가 어떻게 통제하고 책임지는가?"**
 
KorPIX(Korea Protocol Infrastructure eXchange)는 이 질문에 대한 인프라 수준의 답입니다.
AI 에이전트가 실제 경제 활동을 수행할 때 그 행동을 **실행 · 통제 · 감사**하는
표준 신뢰 인프라를 정의하고 구현합니다.
 
---
 
## 2. 핵심 3대 시스템
 
### 2.1 Trust Terminal
 
AI 에이전트가 행동을 실행하는 보안 단말입니다.
 
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
 
모든 AI 행동을 불변 형태로 기록합니다.
 
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
 
소프트웨어 에뮬레이터에서 실제 물리 단말로 전환하는 최종 단계입니다.
 
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
 
### 처리 속도 목표
 
| 단계 | SW 에뮬레이터 | HW 목표 |
|---|---|---|
| Policy Engine | 120ms | 60ms 이하 |
| Dilithium3 서명 | 18ms | 3ms (NPU) |
| AES-256 암호화 | 1ms | 0.1ms (AES-NI) |
| 상시 전력 | 15W (CPU 피크) | 5W 이하 |
| 전체 체감 응답 | — | 3초 이내 |
 
---
 
## 6. 글로벌 유사 프로젝트 비교
 
| 프로젝트 | Policy Engine | 해시 체인 | HW 신뢰 | 금융 규제 | 공공 API |
|---|---|---|---|---|---|
| Microsoft AGT | ✅ | ✅ | ❌ | ❌ | ❌ |
| AgentBouncr | ✅ | ✅ | ❌ | ❌ | ❌ |
| Agentic Contract | ✅ | ✅ | ❌ | ❌ | ❌ |
| **KorPIX** | **✅** | **✅** | **✅ TPM+TEE** | **✅ 자본시장법** | **✅ 정부24** |
 
**KorPIX 차별점**: 하드웨어 신뢰(TPM·TEE) + 금융·공공 규제 대응 + 국가 표준 목표
 
---
 
## 7. 표준화 목표
 
UC-001~005 파일럿 완료 후 다음 세 가지 표준을 공개합니다.
 
- **KorPIX Terminal Standard v1.0** — Trust Terminal 요건 및 인터페이스
- **KorPIX Policy API v1.0** — Policy Engine 표준 인터페이스
- **KorPIX Audit Protocol v1.0** — 감사 기록 표준 프로토콜
 
이 표준들이 공개되면 타 제조사도 KorPIX 호환 단말을 만들 수 있게 됩니다.
KorPIX는 특정 제품이 아닌 **AI 행동 신뢰 인프라의 국가 표준**을 목표로 합니다.
 
---
 
*KorPIX Core — github.com/korpix-team/korpix-core*
*Apache License 2.0*
