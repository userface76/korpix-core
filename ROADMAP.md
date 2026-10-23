# KorPIX Roadmap — Sovereign Personal AI PC

> 2026-10-23 비전 정렬. **완료 표시는 해당 프로토타입 코드/명세 존재를 뜻하며, 상용 보안 인증·운영 검증 완료를 뜻하지 않습니다.**
> 전 국민 AI 개인 PC 보급은 **목표 사용 시나리오**이며 공식 정부 사업 선정·협약을 의미하지 않습니다.

## v0.1 — 행동 통제 프로토타입 (기존 자산)
- [x] ActionRecord 표준 타입 초안 (TypeScript)
- [x] Policy Engine Risk Evaluator (Python)
- [x] Decision Engine 승인 체인 + 투자 서킷 브레이커 (프로토타입)
- [x] Audit Gateway 형식/해시/체인 검증·이상탐지 (인메모리)
- [x] UC-001~004 Mock 커넥터·시나리오 및 테스트 코드
- [ ] 독립 CI에서 모든 테스트·보안 시나리오 통과 확인

## v0.1.1 — 상용화 전 필수 보안 경계 (최우선)
- [ ] **Execution Gateway가 서명·기한·행동 해시가 결합된 정책 허가증을 검증**하고 미승인/재사용 요청을 차단
- [ ] 승인자 인증·역할·위임 범위·승인 체인 정합성 검증
- [ ] 서킷 브레이커 해제 권한 검증과 감사 기록
- [ ] 감사 원장 영구 저장, 서버 재시작 후 무결성 검증, 운영용 비대칭 서명
- [ ] 운영모드에서 Mock 결과 자동 대체 금지(fail-closed)
- [ ] 위조 승인·프롬프트 인젝션·재전송·외부 반출 시나리오 보안 테스트 자동화

## v0.2 — 개인 AI PC 로컬 신뢰 계층
- [ ] Python/TypeScript SDK 정리·패키지·버전 정책, OpenAPI 상호 호환성 검증
- [ ] Personal Data Vault: 단말 암호화 저장, 최소 데이터 보존, 키/복구 정책
- [ ] Local AI Engine 어댑터: 로컬 추론 우선, 민감정보 최소화·비식별 검토
- [ ] Data Egress Gateway: 목적·수신자·전송 항목·기간·동의/철회 정책 강제
- [ ] 사용자용 동의 대시보드, 반출 이력·권리 행사 UI
- [ ] 오프라인/저사양 PC·접근성·업데이트 신뢰성 시험

## v0.3 — 공공·금융의 합법적 연계 실증
- [ ] 적용 법령·사업자 자격·기관별 공식 API 규격 및 협력 절차 검토
- [ ] 개인정보 전송요구권을 활용한 **허용된 범위**의 공공 API 파일럿
- [ ] 금융 마이데이터 적격 사업자·금융기관 협력 기반 파일럿
- [ ] 승인된 목적 외 데이터 사용, 무단 반출, 정보주체 철회 처리 검증
- [ ] 공통 증거 스키마와 기관 간 상호운용 시험

## v0.4 — 하드웨어 Trust Terminal / AI Node PC
- [ ] TPM 2.0 키 보호·단말 신원과 원격 무결성 검증
- [ ] TEE/격리 실행 및 Secure/Measured Boot 실증
- [ ] 하드웨어 기반 서명·키 폐기·복구 절차 검증
- [ ] 기종별 성능·비용·안전성·관리성 실측 (EVT → DVT)

## v1.0 — 개방형 표준·독립 평가
- [ ] KorPIX Action Gateway / Policy API 표준 v1.0
- [ ] KorPIX Consent & Data Egress Protocol v1.0
- [ ] KorPIX Evidence / Audit Protocol v1.0
- [ ] 국내 제조사·기관 상호운용성 검증, 제3자 보안·개인정보 평가
- [ ] 필요 시 해당 인증·규제 적합성 검토 (사전 인증 취득 주장 금지)

상세: [Sovereign Personal AI PC Architecture](docs/sovereign_ai_pc_architecture.md)
