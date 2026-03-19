# KorPIX Terminal Standard v0.1

**KorPIX Trust Terminal 표준 명세**

---

## 1. 개요

KorPIX Trust Terminal은 AI 에이전트가 실제 행동을 수행하는 최초의 실행 환경입니다.
이 명세는 Trust Terminal이 갖춰야 할 최소 요건과 인터페이스를 정의합니다.

---

## 2. 필수 구성 요소

### 2.1 보안 하드웨어 (UC-005 이전: 소프트웨어 에뮬레이션 허용)

| 구성 요소 | 필수 여부 | 최소 사양 |
|---|---|---|
| TPM 2.0 | 권장 (SW 대체 가능) | TCG TPM 2.0, 24개 PCR |
| TEE | 권장 (SW 대체 가능) | ARM TrustZone 또는 OP-TEE |
| Secure Boot | 권장 | UEFI 서명 검증 |
| NVMe 암호화 | 권장 | AES-256 (TCG Opal 2.0) |

### 2.2 소프트웨어 환경

| 구성 요소 | 필수 여부 | 사양 |
|---|---|---|
| AI Runtime | 필수 | Python 3.11+ 또는 동등 환경 |
| Policy Engine 클라이언트 | 필수 | KorPIX SDK v0.1+ |
| Audit 기록 에이전트 | 필수 | 로컬 또는 원격 Audit Network 연결 |
| 사용자 인증 | 필수 | 공동인증서 / PASS / 생체 중 하나 |

---

## 3. Trust Terminal 행동 실행 프로토콜

모든 AI 행동은 반드시 다음 순서를 준수해야 합니다.

```
1. 사용자 인증 (Authentication)
   → 공동인증서 / PASS / 생체인증 중 하나 검증

2. 행동 요청 생성 (ActionRequest 생성)
   → action_type, payload, user_id, terminal_id 포함

3. Policy Engine 평가 요청
   → POST /evaluate
   → PolicyResult 수신

4. 결정에 따른 처리
   → AUTO_APPROVE:  즉시 실행
   → USER_CONFIRM:  사용자 확인 후 실행
   → ADMIN_APPROVE: 관리자 승인 후 실행
   → DENY:          실행 중단, 사용자 안내

5. 실행 (Execution Gateway 호출)
   → POST /execute

6. 감사 기록 (Audit Network 제출)
   → ActionRecord 생성 (hash, prevHash, digitalSignature 포함)
   → POST /submit
```

---

## 4. ActionRecord 서명 요건

모든 ActionRecord는 반드시 디지털 서명을 포함해야 합니다.

- **소프트웨어 모드**: SHA-256 기반 소프트 서명 (개발·테스트 환경)
- **하드웨어 모드**: TPM AIK 기반 Dilithium3 서명 (운영 환경)

서명 대상: `hash` 필드 (ActionRecord의 SHA-256 해시)

---

## 5. 단말 식별자 (terminal_id) 규칙

```
형식: term-{환경}-{uuid4 앞 8자리}
예시: term-prod-3a7f2b9c
      term-dev-00000001   (개발 환경)
```

---

## 6. 호환성 요건

KorPIX Terminal Standard를 준수하는 단말은 다음을 만족해야 합니다.

1. KorPIX Policy API v0.1 이상과 통신 가능
2. KorPIX Audit Protocol v0.1 이상 준수
3. ActionRecord JSON Schema 검증 통과
4. `digitalSignature` 필드 미포함 레코드 거부
