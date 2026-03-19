# KorPIX 기여 가이드

## 브랜치 전략
- `main` — 안정 버전
- `develop` — 개발 브랜치
- `feature/xxx` — 기능 개발
- `fix/xxx` — 버그 수정

## 커밋 규칙
```
feat: 새 기능 추가
fix: 버그 수정
docs: 문서 변경
test: 테스트 추가/수정
chore: 빌드/설정 변경
```

## Pull Request
1. `develop` 브랜치에서 분기
2. 테스트 추가 필수
3. `services/` 변경 시 해당 `tests/` 업데이트 필요
4. 표준 명세(`standards/`) 변경은 반드시 이슈 논의 후 진행

## 코딩 컨벤션
- Python: PEP 8, type hints 필수
- TypeScript: strict 모드
- 모든 공개 함수에 docstring/JSDoc 필수
