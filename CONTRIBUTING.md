# Contributing to KorPIX Core

## 1. Welcome
- 프로젝트에 기여해줘서 감사하다는 메시지
- 이 저장소의 목적 한 줄 설명
- 어떤 종류의 기여를 받는지 안내
  - 코드
  - 문서
  - 표준안 제안
  - 버그 제보
  - 테스트
  - 예제 추가

## 2. Scope of Contributions
- 어떤 영역에 기여할 수 있는지 정리
  - whitepaper/
  - standards/
  - docs/
  - schemas/
  - api/
  - apps/
  - services/
  - sdk/
  - tests/
  - scripts/

## 3. Before You Start
- 이슈 확인 후 작업 권장
- 큰 변경은 먼저 discussion / issue 생성
- 중복 PR 방지
- 표준 문서 변경 시 영향 범위 명시

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
