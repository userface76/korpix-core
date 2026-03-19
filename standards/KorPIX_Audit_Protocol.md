KorPIX Audit Protocol Standard v0.1
감사 기록 프로토콜 표준 명세

1. 개요
KorPIX Audit Protocol은 AI 에이전트의 모든 행동을
변조 불가능한 방식으로 기록·검증하는 표준입니다.
신뢰의 핵심은 해시 체인과 디지털 서명 두 가지입니다.

2. 해시 체인 구조
Genesis
  prevHash: "000...000" (64자리)
  │
  ▼
ActionRecord[0]
  prevHash: "000...000"
  hash:     SHA256(record - {hash, digitalSignature})
  │
  ▼
ActionRecord[1]
  prevHash: ActionRecord[0].hash
  hash:     SHA256(record - {hash, digitalSignature})
  │
  ▼
  ...
단 하나의 레코드라도 수정되면 이후 모든 prevHash가 불일치하여
변조가 즉시 탐지됩니다.

3. 해시 계산 표준
pythonimport hashlib, json

def compute_hash(record: dict) -> str:
    # hash, digitalSignature 제외
    r = {k: v for k, v in record.items()
         if k not in ("hash", "digitalSignature")}
    return hashlib.sha256(
        json.dumps(r, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
중요: sort_keys=True 필수 — 키 순서가 다르면 해시가 달라집니다.

4. 디지털 서명 표준
환경서명 방식비고소프트웨어 (개발)SHA-256 소프트 서명테스트 전용하드웨어 (운영)TPM AIK + Dilithium3UC-005 이후 적용
서명 대상: hash 필드 값 (문자열)

5. Audit Gateway 검증 4단계
Gateway가 Terminal Log를 수신하면 반드시 다음 순서로 검증합니다.
1. 형식 검증   — 필수 13개 필드 존재 여부
2. 서명 검증   — digitalSignature 유효성
3. 해시 검증   — hash 필드 재계산 비교
4. 체인 검증   — prevHash = 이전 레코드 hash
4단계 모두 통과해야 Distributed Ledger에 저장됩니다.

6. 이상 탐지 필수 규칙
KorPIX 호환 Audit Network는 다음 패턴을 탐지해야 합니다.
규칙임계값심각도비정상 접근 빈도10분 내 5회 이상HIGH해시/서명 불일치1건이라도 발생CRITICAL연속 DENY3회 연속MEDIUM위임 없는 대리 접근1건이라도 발생HIGH

7. 데이터 보존 기준
서비스 유형의무 보존 기간근거금융 투자 (UC-002)5년자본시장법기업 구매 (UC-003)5년법인세법행정 서비스 (UC-004)5년전자정부법기타1년내부 정책

8. 필수 API 엔드포인트
POST /submit                      감사 기록 제출 (필수)
POST /query                       감사 기록 조회 (필수)
GET  /integrity                   해시 체인 무결성 검증 (필수)
GET  /anomalies                   이상 이벤트 조회 (필수)
POST /anomalies/{event_id}/resolve 이상 이벤트 해제 (필수)
GET  /health                      헬스 체크 (필수)
