# KorPIX 보안 모델

## 신뢰 계층 구조

```
L1 — 하드웨어 신뢰 (TPM 2.0)
  키 보관 · PCR 측정 · Tamper 감지

L2 — 격리 실행 (TEE / OP-TEE)
  Policy Engine TA · Key Manager TA · Audit Signer TA

L3 — 부팅 무결성
  Secure Boot → Measured Boot → Remote Attestation

L4 — 소프트웨어 감사
  해시 체인 · 디지털 서명 · 이상 탐지
```

## 개인정보 4등급 분류 (UC-004)

| 등급 | 데이터 예시 | 처리 방식 |
|---|---|---|
| 1 (일반) | 이름·주소 | Auto Approve 가능 |
| 2 (민감) | 주민번호·계좌 | User Confirm 필수 |
| 3 (고민감) | 건강·복지 이력 | 로컬 처리 전용 |
| 4 (최고민감) | 생체·범죄 | DENY (처리 불가) |

**원칙**: 주민번호 원본 미저장 — SHA-256 해시만 Audit Record에 포함

## Audit Network 검증 4단계

```
1. 형식 검증   — 13개 필수 필드 존재 여부
2. 서명 검증   — digitalSignature 유효성
3. 해시 검증   — hash 필드 재계산 비교
4. 체인 검증   — prevHash = 이전 레코드 hash
```

4단계 모두 통과해야 Distributed Ledger에 저장됩니다.

## 서킷 브레이커 (UC-002)

발동 조건:
- VIX ≥ 35 (극단적 시장 변동성)
- 코스피 일간 하락 ≤ -5%

효과: 모든 AI 투자 행동 즉시 DENY
해제: 관리자 수동 확인 필수 (자동 해제 없음)
