import React, { useState, useEffect } from 'react';

const POLICY_URL = (window as any).__KORPIX_POLICY_URL__ || 'http://localhost:8001';

export default function CircuitBreaker() {
  const [status,    setStatus]    = useState({ triggered: false, reason: null as string | null, affected_users: 0 });
  const [vix,       setVix]       = useState(15);
  const [kospi,     setKospi]     = useState(0);
  const [loading,   setLoading]   = useState(false);
  const [message,   setMessage]   = useState('');

  useEffect(() => {
    fetch(`${POLICY_URL}/health`)
      .then(r => r.json())
      .then(d => { if (d.circuit_breaker) setStatus(d.circuit_breaker); })
      .catch(() => {});
  }, []);

  const check = async () => {
    setLoading(true);
    try {
      const res  = await fetch(`${POLICY_URL}/circuit-breaker/check`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ vix, kospi_change: kospi / 100 }),
      });
      const data = await res.json();
      setStatus(data.status);
      setMessage(data.triggered ? '⚡ 서킷 브레이커 발동!' : '✅ 정상 — 서킷 브레이커 미발동');
    } catch {
      // Mock
      const triggered = vix >= 35 || kospi <= -5;
      setStatus({ triggered, reason: triggered ? `VIX=${vix}, 코스피=${kospi}%` : null, affected_users: 0 });
      setMessage(triggered ? '⚡ 서킷 브레이커 발동!' : '✅ 정상 — 서킷 브레이커 미발동');
    } finally {
      setLoading(false);
    }
  };

  const deactivate = async () => {
    setLoading(true);
    try {
      await fetch(`${POLICY_URL}/circuit-breaker/deactivate?user_id=dashboard-admin`, { method: 'POST' });
    } catch {}
    setStatus({ triggered: false, reason: null, affected_users: 0 });
    setMessage('✅ 서킷 브레이커 수동 해제 완료');
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <h2 style={{ fontSize: 18, color: '#f1f5f9', marginBottom: 20 }}>서킷 브레이커</h2>

      {/* 현재 상태 */}
      <div style={{
        background: '#1e293b', border: `1px solid ${status.triggered ? '#ef4444' : '#22c55e'}`,
        borderRadius: 12, padding: 24, marginBottom: 24,
      }}>
        <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 8 }}>현재 상태</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            fontSize: 32, fontWeight: 700,
            color: status.triggered ? '#ef4444' : '#22c55e',
          }}>
            {status.triggered ? '⚡ 발동 중' : '✅ 정상'}
          </span>
          {status.triggered && (
            <span style={{ fontSize: 13, color: '#fca5a5' }}>
              영향 사용자: {status.affected_users}명
            </span>
          )}
        </div>
        {status.reason && (
          <p style={{ color: '#fca5a5', fontSize: 13, marginTop: 8 }}>{status.reason}</p>
        )}
        {message && (
          <p style={{ color: '#94a3b8', fontSize: 13, marginTop: 12, padding: '8px 12px',
                      background: '#0f172a', borderRadius: 6 }}>
            {message}
          </p>
        )}
      </div>

      {/* 시장 지표 입력 */}
      <div style={{ background: '#1e293b', border: '1px solid #334155',
                    borderRadius: 12, padding: 24, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, color: '#94a3b8', marginBottom: 16 }}>시장 지표 확인</h3>

        <label style={{ display: 'block', fontSize: 13, color: '#e2e8f0', marginBottom: 8 }}>
          VIX 지수 (≥35이면 서킷 브레이커 발동)
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <input type="range" min={5} max={60} value={vix}
                 onChange={e => setVix(Number(e.target.value))}
                 style={{ flex: 1, accentColor: vix >= 35 ? '#ef4444' : '#38bdf8' }} />
          <span style={{ fontSize: 20, fontWeight: 700, minWidth: 40, textAlign: 'right',
                         color: vix >= 35 ? '#ef4444' : '#22c55e' }}>
            {vix}
          </span>
        </div>

        <label style={{ display: 'block', fontSize: 13, color: '#e2e8f0', marginBottom: 8 }}>
          코스피 일간 등락률 (≤-5%이면 발동)
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <input type="range" min={-15} max={5} value={kospi}
                 onChange={e => setKospi(Number(e.target.value))}
                 style={{ flex: 1, accentColor: kospi <= -5 ? '#ef4444' : '#38bdf8' }} />
          <span style={{ fontSize: 20, fontWeight: 700, minWidth: 52, textAlign: 'right',
                         color: kospi <= -5 ? '#ef4444' : '#22c55e' }}>
            {kospi}%
          </span>
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={check} disabled={loading} style={{
            flex: 1, padding: '12px', background: '#0e4d6b', border: '1px solid #0891b2',
            borderRadius: 8, color: '#bae6fd', fontSize: 14, cursor: 'pointer', fontWeight: 600,
          }}>
            {loading ? '확인 중...' : '서킷 브레이커 확인'}
          </button>

          {status.triggered && (
            <button onClick={deactivate} disabled={loading} style={{
              flex: 1, padding: '12px', background: '#14532d', border: '1px solid #166534',
              borderRadius: 8, color: '#86efac', fontSize: 14, cursor: 'pointer', fontWeight: 600,
            }}>
              수동 해제 (관리자)
            </button>
          )}
        </div>
      </div>

      <div style={{ background: '#1e293b', border: '1px solid #334155',
                    borderRadius: 10, padding: 16, fontSize: 13, color: '#64748b' }}>
        <p style={{ fontWeight: 600, color: '#94a3b8', marginBottom: 8 }}>발동 조건</p>
        <p>• VIX ≥ 35 — 극단적 시장 변동성</p>
        <p>• 코스피 일간 하락률 ≤ -5%</p>
        <p style={{ marginTop: 8 }}>발동 시 모든 AI 투자 행동이 즉시 DENY됩니다.</p>
        <p>해제는 반드시 <strong style={{ color: '#f59e0b' }}>관리자 수동 확인</strong>이 필요합니다.</p>
      </div>
    </div>
  );
}
