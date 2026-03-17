# Contributing to KorPIX Core

## 1. Welcome
- thanks for taking the time to contribute!
- 신뢰 가능한 AI 실행과 감사 가능한 자동화를 위한 표준, 서비스, SDK를 구축하는 오픈 아키텍처 프로젝트입니다.
- 구현 코드뿐 아니라 기술 문서, 표준 명세, JSON 스키마, OpenAPI 정의, 테스트 케이스, 예제 데이터, 보안 개선 제안, 버그 리포트, 아키텍처 및 정책 제안 등 폭넓은 기여를 받습니다.
  - 코드
  - 기술 문서
  - 표준안 제안
  - 버그 제보
  - 테스트
  - 예제 추가

## 2. Scope of Contributions
- 기여는 다음 영역에서 가능합니다.
  - whitepaper/  KorPIX의 비전, 핵심 철학, 전체 아키텍처 방향을 설명하는 백서 개선
  - standards/   단말 표준, 정책 API, 감사 프로토콜 등 공식 표준 문서 보완 및 제안
  - docs/        시스템 아키텍처, 논리 모델, AI 실행 흐름, 보안 모델, 활용 사례 등 기술 문서 작성 및 개선
  - schemas/     액션 요청, 정책 결정, 감사 기록, 리스크 점수 등 JSON 스키마 정의 및 정합성 개선
  - api/         API 명세 보완, 엔드포인트 구조 정리, 요청·응답 규격 일관성 강화
  - apps/        터미널 시뮬레이터와 정책 대시보드의 UI/UX, 기능, 시각화, 인증 흐름 개선
  - services/    정책 엔진, 감사 네트워크, 실행 게이트웨이의 핵심 로직 구현 및 안정성 향상
  - sdk/         Python 및 TypeScript SDK의 사용성, 모델 정의, 인증 처리, 클라이언트 기능 개선
  - tests/       단위 테스트, 통합 테스트, 검증 시나리오, 테스트 픽스처 추가
  - scripts/     개발 편의 스크립트, 실행 자동화, 예제 데이터 시드 도구 개선
  - Security and Audit Integrity/ 권한 검증, 정책 집행, 서명, 해시체인, 감사 무결성, 샌드박스 실행 안전성 강화
  - Architecture and Governance Proposals/ KorPIX의 확장 구조, 호환성 정책, 표준화 방향, 운영 원칙에 대한 제안
 
    

## 3. 시작하기 전에

기여를 시작하기 전에, 먼저 등록된 이슈와 토론 내용을 확인해 주세요. 이를 통해 중복 작업을 줄이고, 현재 프로젝트의 방향성과 우선순위를 더 잘 이해할 수 있습니다.

새로운 표준 제안, 스키마 개정, API 구조 변경, 여러 서비스에 영향을 주는 리팩터링 등 큰 변경을 계획하고 있다면, 바로 작업을 진행하기보다 먼저 이슈 또는 Discussion을 생성해 주세요. 사전 논의를 통해 설계 일관성을 유지하고 불필요한 재작업을 줄일 수 있습니다.

동일한 문제나 기능에 대해 중복된 Pull Request가 올라오지 않도록, 작업 전에 열려 있는 이슈와 PR을 함께 확인해 주세요. 이미 관련 작업이 진행 중이라면, 기존 스레드에서 먼저 의견을 나누고 협업하는 것을 권장합니다.

`standards/` 아래의 문서를 수정하는 경우에는 반드시 영향 범위를 함께 설명해 주세요. 특히 해당 변경이 `schemas/`, `api/`, `examples/`, `docs/`, `services/`, `sdk/`에 어떤 후속 수정이나 호환성 영향을 주는지 명확히 밝혀야 합니다.

## 4. Development Environment
- 필수 도구
  - Python 버전
  - Node.js 버전
  - package manager
- 설치 방법
  - repo clone
  - dependencies install
  - env 설정
- 예시 명령어

## 5. Repository Structure
- 주요 폴더 설명
- 각 디렉터리의 책임 범위
- 어디에 무엇을 추가해야 하는지 안내

## 6. Contribution Workflow
- fork / branch 생성 규칙
- branch naming 규칙
- 작업 → 테스트 → 커밋 → PR 절차
- PR 전에 체크해야 할 사항

## 7. Coding Standards
### Python
- 스타일 규칙
- 타입힌트
- 함수/클래스 네이밍
- lint/format 도구

### TypeScript / Frontend
- 스타일 규칙
- 컴포넌트 구조
- 상태 관리 원칙
- lint/format 도구

### Documentation
- 용어 일관성
- 제목 규칙
- 표준 문서 작성 방식
- normative language 사용 여부 (MUST, SHOULD 등)

### Schemas / API
- backward compatibility 원칙
- breaking change 처리 원칙
- example 파일 동기화 규칙

## 8. Commit Message Guidelines
- 커밋 메시지 형식
- 예시
  - feat:
  - fix:
  - docs:
  - refactor:
  - test:
  - chore:

## 9. Pull Request Guidelines
- PR 제목 규칙
- PR 본문 템플릿
- 포함해야 할 내용
  - 무엇을 변경했는지
  - 왜 필요한지
  - 영향 범위
  - 테스트 결과
  - 관련 이슈

## 10. Testing Requirements
- unit / integration 테스트 원칙
- 새 기능에는 테스트 포함
- 스키마/API 변경 시 검증 필요
- 예제 파일 업데이트 필요

## 11. Standards Change Policy
- standards/ 문서 변경 시 별도 검토 필요
- schema, api, docs와 연계 검토
- 호환성 영향 기재
- 감사/정책/리스크 모델 영향 명시

## 12. Security and Responsible Disclosure
- 보안 취약점은 공개 이슈로 올리지 않기
- 별도 연락 채널 안내
- 민감한 정책/권한 관련 제보 방식

## 13. License
- 기여물은 프로젝트 라이선스를 따른다는 내용

## 14. Code of Conduct / Community Expectations
- 존중 기반 협업 원칙
- 공격적/모욕적 행동 금지
- 건설적 피드백 장려
