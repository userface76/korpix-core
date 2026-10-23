# KorPIX Core

> **국민형 AI 개인 PC를 위한 AI 행동 신뢰 인프라**  
> **KorPIX — Sovereign Personal AI Trust Architecture**  
> Kernel of Reliability Policy, Integrity & eXecution Standard

KorPIX는 **전 국민 AI 개인 PC 보급을 지향하는 구상에 대응하여**, 각 개인 PC에서 AI 에이전트의 행동·데이터 접근·외부 반출을 국민 본인의 권한과 정책에 따라 통제하고, 실행 결과를 검증 가능한 증거로 남기기 위한 개방형 아키텍처입니다.

**핵심 원칙: 국민의 데이터는 국민이 통제하고, 국가는 안전한 상호운용·보안·표준 인프라를 지원합니다.** 원본 개인정보를 국가 단일 DB로 모으거나 정부·기업에 포괄적 접근 권한을 부여하는 설계가 아닙니다.

이 문서의 `국민형 AI 개인 PC 보급`은 프로젝트의 **목표·적용 시나리오**를 말하며, 정부의 공식 사업 채택·협약·인증이 완료됐다는 뜻이 아닙니다.

## 목표 아키텍처

1. **Local-first AI / Personal Data Vault** — 가능한 분석과 민감정보 처리를 기기 안에서 수행하고, 개인 정보를 암호화·최소 보관합니다.
2. **KorPIX Policy Engine** — 신원·위임·목적·위험·동의·승인 여부를 검사합니다.
3. **KorPIX Execution / Data Egress Gateway** — 미승인 행동과 데이터 반출을 서버/OS 수준에서 차단하고, 승인된 범위의 작업만 실행합니다.
4. **Sovereign Connectors** — 적법한 인증·동의와 기관 간 합의하에 공공/금융 **공식 API**와 연계합니다.
5. **Evidence / Audit Network** — 승인·접근·반출·실행의 검증 가능한 기록을 생성합니다. 장기적으로 서명·영구저장·외부 검증을 강화합니다.
6. **Trust Terminal** — TPM 2.0, TEE, Secure Boot 등을 통한 단말 신뢰 기반은 **향후 하드웨어 통합 목표**입니다.

자세한 설계: [국민형 소버린 AI PC 아키텍처](docs/sovereign_ai_pc_architecture.md) · [시스템 구조](docs/system_architecture.md) · [보안 모델](docs/security_model.md) · [백서](whitepaper/KorPIX_Architecture_Whitepaper.md)

## 현재 코드와 향후 목표 구분

| 구성 | 저장소에서 확인되는 상태 | 향후 필요 작업 |
|---|---|---|
| Policy Engine / Decision Engine | Python 위험평가·4단계 결정·승인 체인·투자 서킷 브레이커 **프로토타입** | 승인자 신원/역할 검증, 정책·행동 결합 |
| Execution Gateway | REST API와 결제·투자·ERP·공공 **Mock 커넥터** | 서명된 실행 허가증 검증, 실제 기관 연동 |
| Audit Network | 해시 체인·이상 탐지·개발용 소프트 서명, **인메모리 원장** | 영구 저장, 운영용 서명, 독립 검증 |
| API / SDK / 대시보드 | OpenAPI 초안·SDK·데모 UI 코드 | 통합 테스트, 오류 시 fail-closed, 운영 지표 |
| Personal Data Vault / Egress Control | **구상 단계** | 기기 내 암호화 금고, 데이터 분류, 반출 정책 |
| TPM / TEE 기반 AI PC | **설계·로드맵 단계** | 실물 단말 통합 및 시험 |
| 공공·금융 마이데이터 | 유스케이스·Mock 중심 | 자격/협약/승인 후 공식 API 시범 연동 |

현재 코드는 **연구·시연용 프로토타입**입니다. 국가기관 또는 금융기관과의 공식 연계, 상용 보안 인증, 전국 단말 보급은 구현·검증됐다고 주장하지 않습니다.

## 핵심 행동 처리 흐름

`Agent ActionRequest → Policy/Risk → 인간 동의·승인(필요 시) → 서명된 실행 허가(목표) → Execution/Egress Gateway → 감사 증거`

**중요한 보안 과제:** 현재 `/execute`는 정책 결정을 독립적으로 재검증하지 않으며, 감사 원장은 메모리 기반입니다. 상용화 전에 반드시 수정해야 합니다. 상세: [보안 모델](docs/security_model.md)과 [로드맵](ROADMAP.md).

## 개발 환경에서 실행

```bash
git clone https://github.com/userface76/korpix-core.git
cd korpix-core

# Python 서비스
pip install -e ".[dev]"
./scripts/run_policy_engine.sh

# TypeScript 빌드
npm install
npm run build
```

서비스: Policy Engine `8001` · Audit Network `8002` · Execution Gateway `8003`  
API 명세: [api/openapi.yaml](api/openapi.yaml) · 행동 규격: [standards/](standards/) · 예제: [examples/](examples/)

## 파일럿 유스케이스

| ID | 분야 | 현 단계 |
|---|---|---|
| UC-001 | 소액 정기결제 | 모의 커넥터·정책 테스트 |
| UC-002 | AI 투자 자동화 | 모의 투자·서킷 브레이커 테스트 |
| UC-003 | 기업 구매 승인 | 승인 체인·모의 ERP 테스트 |
| UC-004 | AI 행정 서비스 | 개인정보 위험 분류·모의 API 테스트 |
| UC-005 | AI Node PC / Trust Terminal | 하드웨어 설계·실증 계획 |
| UC-006 (제안) | 국민형 로컬 AI·개인 데이터 금고 | 신규 파일럿 기획 |
| UC-007 (제안) | 동의 기반 공공·금융 마이데이터 | 자격·협약·보안 검토 후 실증 |

## 정책·데이터 주권 원칙

- **개인 주권:** 데이터 주체가 목적·범위·수신자·기간·철회를 이해하고 통제합니다.
- **기술 주권:** 민감정보는 로컬 우선 처리하고, 필요 시 통제 가능한 국내 인프라를 우선 검토합니다.
- **국가 인프라 주권:** 여러 제조사·기관이 활용 가능한 표준 API, 검증 및 감사 체계를 지향합니다.
- **최소 데이터 이동:** 목적에 필요한 정보만 전송하고, 원본 집중 수집이나 무단 학습을 지양합니다.
- **합법적 상호운용:** 국내·국외 이전 및 금융/공공 데이터 이용은 각각 적용 법령·계약·승인 요건을 따릅니다.

[ROADMAP](ROADMAP.md) · [CONTRIBUTING](CONTRIBUTING.md) · [LICENSE](LICENSE)
