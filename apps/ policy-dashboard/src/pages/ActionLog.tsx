import React, { useState, useEffect } from 'react';
 
const AUDIT_URL = (window as any).__KORPIX_AUDIT_URL__ || 'http://localhost:8002';
 
const DECISION_BADGE: Record<string, { bg: string; color: string }> = {
  AUTO_APPROVE:  { bg: '#14532d', color: '#86efac' },
  USER_CONFIRM:  { bg: '#78350f', color: '#fde68a' },
  ADMIN_APPROVE: { bg: '#4c1d95', color: '#c4b5fd' },
  DENY:          { bg: '#7f1d1d', color: '#fca5a5' },
};
 
const DEMO_RECORDS = [
  { action_id: 'act-001', action_type: 'PAYMENT',          policy_decision: 'AUTO_APPROVE',  risk_score: 20, execution_result: 'SUCCESS', action_timestamp: '2025-03-19T10:00:00Z' },
  { action_id: 'act-002', action_type: 'PAYMENT',          policy_decision: 'USER_CONFIRM',  risk_score: 48, execution_result: 'SUCCESS', action_timestamp: '2025-03-19T10:05:00Z' },
  { action_id: 'act-003', action_type: 'INVESTMENT',       policy_decision: 'AUTO_APPROVE',  risk_score: 25, execution_result: 'SUCCESS', action_timestamp: '2025-03-19T10:10:00Z' },
  { action_id: 'act-004', action_type: 'PURCHASE_REQUEST', policy_decision: 'USER_CONFIRM',  risk_score: 40, execution_result: 'PENDING', action_timestamp: '2025-03-19T10:15:00Z' },
  { action_id: 'act-005', action_type: 'CIVIC_SERVICE',    policy_decision: 'AUTO_APPROVE',  risk_score: 18, execution_result: 'SUCCESS', action_timestamp: '2025-03-19T10:20:00Z' },
  { action_id: 'act-006', action_type: 'PAYMENT',          policy_decision: 'DENY',          risk_score: 85, execution_result: 'BLOCKED', action_timestamp: '2025-03-19T10:25:00Z' },
];
 
export default function ActionLog() {
  const [records, setRecords]   = useState(DEMO_RECORDS);
  const [filter,  setFilter]    = useState('');
  const [loading, setLoading]   = useState(true);
 
  useEffect(() => {
    fetch(`${AUDIT_URL}/query`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ page: 1, page_size: 50 }),
    })
      .then(r => r.json())
      .then(data => { if (data.records?.length) setRecords(data.records); })
      .catch(() => {/* 데모 데이터 유지 */})
      .finally(() => setLoading(false));
  }, []);
 
  const filtered = records.filter(r =>
    !filter ||
    r.action_type.toLowerCase().includes(filter.toLowerCase()) ||
    r.policy_decision.toLowerCase().includes(filter.toLowerCase())
  );
 
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, color: '#f1f5f9' }}>행동 기록</h2>
        <input
          placeholder="검색 (유형, 결정...)"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{
            marginLeft: 'auto', padding: '7px 14px',
            background: '#1e293b', border: '1px solid #334155',
            borderRadius: 8, color: '#e2e8f0', fontSize: 13, width: 220,
          }}
        />
        <button
          onClick={() => setLoading(true)}
          style={{ padding: '7px 14px', background: '#0e4d6b', border: 'none',
                   borderRadius: 8, color: '#bae6fd', fontSize: 13, cursor: 'pointer' }}
        >
          새로고침
        </button>
      </div>
 
      <div style={{ background: '#1e293b', border: '1px solid #334155',
                    borderRadius: 10, overflow: 'hidden' }}>
        {/* 테이블 헤더 */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 1.5fr 1fr 1.5fr',
                      padding: '10px 16px', background: '#0f172a',
                      fontSize: 12, color: '#64748b', fontWeight: 600 }}>
          <span>Action ID</span>
          <span>행동 유형</span>
          <span>결정</span>
          <span>Risk Score</span>
          <span>시각</span>
        </div>
 
        {/* 행 */}
        {filtered.map((r, i) => {
          const badge = DECISION_BADGE[r.policy_decision] ?? { bg: '#334155', color: '#94a3b8' };
          return (
            <div key={r.action_id} style={{
              display: 'grid', gridTemplateColumns: '2fr 1.5fr 1.5fr 1fr 1.5fr',
              padding: '12px 16px', fontSize: 13, alignItems: 'center',
              borderTop: i > 0 ? '1px solid #1e293b' : 'none',
              background: i % 2 === 0 ? '#1e293b' : '#172032',
            }}>
              <span style={{ color: '#64748b', fontFamily: 'monospace', fontSize: 11 }}>
                {r.action_id.slice(0, 16)}…
              </span>
              <span style={{ color: '#94a3b8' }}>{r.action_type}</span>
              <span style={{ display: 'inline-block', padding: '2px 10px',
                             borderRadius: 20, background: badge.bg,
                             color: badge.color, fontSize: 11, fontWeight: 600 }}>
                {r.policy_decision}
              </span>
              <RiskBar score={r.risk_score} />
              <span style={{ color: '#64748b', fontSize: 11 }}>
                {new Date(r.action_timestamp).toLocaleString('ko-KR')}
              </span>
            </div>
          );
        })}
 
        {filtered.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>
            {loading ? '로딩 중...' : '검색 결과가 없습니다.'}
          </div>
        )}
      </div>
 
      <p style={{ marginTop: 12, color: '#64748b', fontSize: 12 }}>
        총 {filtered.length}건 표시 / {records.length}건
      </p>
    </div>
  );
}
 
function RiskBar({ score }: { score: number }) {
  const color =
    score < 30 ? '#22c55e' :
    score < 60 ? '#f59e0b' :
    score < 80 ? '#a78bfa' : '#ef4444';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, background: '#334155', borderRadius: 4, height: 6 }}>
        <div style={{ width: `${score}%`, background: color,
                      height: '100%', borderRadius: 4 }} />
      </div>
      <span style={{ color, fontSize: 11, fontWeight: 600, minWidth: 24 }}>
        {score}
      </span>
    </div>
  );
}
