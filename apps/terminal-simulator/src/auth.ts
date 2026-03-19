/**
 * KorPIX Terminal Simulator — Auth Module
 * 사용자 인증 시뮬레이션 (실제 환경에서는 공동인증서 / PASS로 교체)
 */

import { sha256 } from './util';

export interface AuthUser {
  userId:    string;   // SHA-256 해시 (원본 미저장)
  displayName: string;
  authMethod: 'PASS' | 'CERT' | 'BIOMETRIC' | 'DEMO';
  authedAt:  string;
}

/** Demo 인증 — 실제 구현에서는 PASS SDK / 공동인증서 API 연동 */
export async function authenticate(): Promise<AuthUser | null> {
  const name = window.prompt(
    'KorPIX Trust Terminal\n\n사용자 이름을 입력하세요 (데모 인증):',
    '홍길동'
  );
  if (!name) return null;

  // 실제 주민번호 대신 이름 + 타임스탬프로 해시 생성 (데모용)
  const raw    = `${name}:${Date.now()}:demo-salt`;
  const userId = await sha256(raw);

  return {
    userId,
    displayName: name,
    authMethod:  'DEMO',
    authedAt:    new Date().toISOString(),
  };
}

// util.ts가 없는 경우 인라인
export async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray  = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
