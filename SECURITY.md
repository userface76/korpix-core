# KorPIX Security Policy

## 보안 취약점 신고

KorPIX 코드베이스에서 보안 취약점을 발견하셨다면
**GitHub Issue가 아닌** 이메일로 비공개 신고해 주세요.

```
userface@naver.com
```

접수 후 48시간 이내 회신드립니다.

---

## 현재 알려진 보안 제한사항 (v0.1)

이 프로젝트는 **파일럿 / 개발 단계**입니다.

| 항목 | 현재 상태 | 개선 목표 |
|---|---|---|
| 디지털 서명 | SHA-256 소프트 서명 (위조 가능) | TPM 2.0 AIK 서명 (UC-005) |
| API 인증 | API Key 헤더 | JWT + OAuth 2.0 (v0.2) |
| 결재 체인 상태 | 인메모리 (재시작 시 소멸) | PostgreSQL 영속화 (v0.2) |
| 감사 원장 | 인메모리 (재시작 시 소멸) | PostgreSQL + 정기 검증 (v0.2) |
| ERP / 공공 API | Mock 구현 | 실제 파트너 API 연동 (v0.3) |

---

## 운영 전 반드시 변경해야 하는 설정

```bash
TERMINAL_ENV=production
API_KEYS=<랜덤-키-최소32자>
ALLOWED_ORIGINS=https://your-domain.com
SIGNING_MODE=tpm
```

---

## 보안 로드맵

| 버전 | 항목 |
|---|---|
| v0.1 | API Key 인증 · Rate Limiting · CORS · 운영 Swagger 비활성화 · soft_sign 운영 차단 |
| v0.2 | JWT + OAuth 2.0 · PostgreSQL 영속화 · pip-audit CI |
| v0.3 | 실제 ERP / 공공 API · PASS SDK 인증 |
| v0.5 | TPM 2.0 서명 · OP-TEE TA · CC EAL4+ 준비 |
