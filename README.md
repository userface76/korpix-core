1. KorPIX란 무엇인가
2. 핵심 문제 정의
3. 시스템 아키텍처
4. 주요 구성요소
   - Policy Engine
   - Audit Network
   - Execution Gateway
   - Terminal Simulator
   - Policy Dashboard
5. 빠른 시작
6. 로컬 실행 방법
7. API / Schema / Use Cases 링크
8. 로드맵
9. 기여 방법
10. 라이선스


# KorPIX Core

> **AI 행동 신뢰 인프라 (AI Behavior Trust Infrastructure)**  
> Kernel of Reliability Policy, Integrity & eXecution Standard

KorPIX는 자율 행동형 AI(Agentic AI)가 실제 경제 활동을 수행할 때
그 행동을 안전하게 **실행 · 통제 · 감사**하는 오픈 표준 인프라입니다.

---

## 핵심 3대 시스템

| 시스템 | 역할 | 핵심 기술 |
|---|---|---|
| **Trust Terminal** | AI 행동 실행 환경 보호 | TPM 2.0 · TEE · Secure Boot |
| **Policy Engine** | 실행 전 위험도 검증 및 승인 결정 | Risk Score → 4단계 결정 |
| **Audit Network** | 불변 감사 기록 | 해시 체인 · 디지털 서명 |

---

## 글로벌 프로젝트와의 차별점

| | Microsoft AGT | AgentBouncr | **KorPIX** |
|---|---|---|---|
| HW Trust Terminal | ❌ | ❌ | ✅ TPM 2.0 + TEE |
| 금융 규제 감사 | ❌ | ❌ | ✅ 자본시장법 대응 |
| 공공 API 연동 | ❌ | ❌ | ✅ 정부24 · 복지로 |
| 국가 표준 목표 | ❌ | ❌ | ✅ KorPIX Terminal Standard |

---

## 빠른 시작

```bash
git clone https://github.com/korpix-team/korpix-core.git
cd korpix-core

# Python 서비스 실행
pip install -e ".[dev]"
./scripts/run_policy_engine.sh

# TypeScript SDK 빌드
npm install && npm run build
```

---

## 파일럿 유스케이스

| UC | 영역 | 상태 |
|---|---|---|
| UC-001 | 소액 정기결제 자동화 | ✅ 구현 완료 |
| UC-002 | AI 투자 자동화 | ✅ 구현 완료 |
| UC-003 | 기업 구매 승인 자동화 | ✅ 구현 완료 |
| UC-004 | AI 행정 서비스 자동화 | ✅ 구현 완료 |
| UC-005 | AI Node PC 하드웨어 Trust Terminal | 🚧 진행 중 |

기여: [CONTRIBUTING.md](CONTRIBUTING.md) | 라이선스: [Apache 2.0](LICENSE)
