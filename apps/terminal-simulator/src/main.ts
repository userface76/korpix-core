/**
 * KorPIX Trust Terminal Simulator
 * 브라우저에서 동작하는 Trust Terminal 시뮬레이터
 * 실제 Policy Engine REST API와 연동하거나 Mock 모드로 동작
 */

import { actionClient } from './actionClient';
import { renderUI }     from './ui';
import { authenticate } from './auth';

const POLICY_ENGINE_URL =
  (window as any).__KORPIX_POLICY_URL__ || 'http://localhost:8001';

async function boot() {
  console.log('[KorPIX Terminal] 부팅 시작');

  // 1. 사용자 인증
  const user = await authenticate();
  if (!user) {
    console.error('[KorPIX Terminal] 인증 실패');
    return;
  }

  // 2. UI 렌더링
  renderUI({
    terminalId: `term-sim-${crypto.randomUUID().slice(0, 8)}`,
    userId:     user.userId,
    agentId:    'agent-simulator-001',
    policyUrl:  POLICY_ENGINE_URL,
    onAction:   actionClient.evaluate.bind(actionClient),
  });

  console.log(`[KorPIX Terminal] 준비 완료 — 사용자: ${user.userId.slice(0, 16)}…`);
}

document.addEventListener('DOMContentLoaded', boot);
