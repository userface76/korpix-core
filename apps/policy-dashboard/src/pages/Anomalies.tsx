import React, { useState, useEffect } from 'react';

const AUDIT_URL = (window as any).__KORPIX_AUDIT_URL__ || 'http://localhost:8002';

const SEVERITY_STYLE: Record<string, { bg: string; color: string }> = {
  CRITICAL: { bg: '#7f1d1d', color: '#fca5a5' },
  HIGH:     { bg: '#78350f', color: '#fde68a' },
  MEDIUM:   { bg: '#1e3a5f', color: '#93c5fd' },
  LOW:      { bg: '#1a2b1a', color: '#86efac' },
};

const DEMO_ANOMALIES = [
  { event_id: 'evt-001', anomaly_type: 'HIGH_FREQUENCY',     severity: 'HIGH',     description: '10분 내 5회 접근 감지', terminal_id: 'term-001', detected_at: '2025-03-19T10:30:00Z', resolved: false },
  { event_id: 'evt-002', anomaly_type: 'CHAIN_TAMPER',       severity: 'CRITICAL', description: '해시 불일치 감지', terminal_id: 'term-002', detected_at: '2025-03-19T09:15:00Z', resolved: true  },
  { event_id: 'evt-003', anomaly_type: 'REPEATED_DENY',      severity: 'MEDIUM',   description: '연속 3회 DENY', terminal_id: 'term-003', detected_at: '2025-03-19T08:00:00Z', resolved: false },
];

export default function Anomalies() {
  const [events,  setEvents]  = useState(DEMO_ANOMALIES);
  const [severity, setSeverity] = useState('');

  useEffect(() => {
    const url = severity
      ? `${AUDIT_URL}/anomalies?severity=${severity}`
      : `${AUDIT_URL}/anomalies`;
    fetch(url)
      .then(r => r.json())
      .then(data => { if (data.events?.length) setEvents(data.events); })
      .catch(() => {});
  }, [severity]);

  const resolve = (eventId: string) => {
    fetch(`${AUDIT_URL}/anomalies/${eventId}/resolve`, { method: 'POST' })
      .catch(() => {});
    setEvents(prev => prev.map(e =>
      e.event_id === eventId ? { ...e, resolved: true } : e
    ));
  };

  const filtered = events.filter(e => !severity || e.severity === severity);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, color: '#f1f5f9' }}>이상 탐지 이벤트</h2>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          {['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(s => (
            <button
              key={s}
              onClick={() => setSeverity(s)}
              style={{
                padding: '5px 12px', fontSize: 12, cursor: 'pointer',
                borderRadius: 20, border: '1px solid',
                background:   severity === s ? '#1e3a5f' : 'transparent',
                borderColor:  severity === s ? '#38bdf8' : '#334155',
                color:        severity === s ? '#38bdf8' : '#94a3b8',
              }}
            >
              {s || '전체'}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filtered.map(evt => {
          const sty = SEVERITY_STYLE[evt.severity] ?? SEVERITY_STYLE.LOW;
          return (
            <div key={evt.event_id} style={{
              background: '#1e293b', border: `1px solid ${evt.resolved ? '#334155' : '#475569'}`,
              borderLeft: `4px solid ${evt.resolved ? '#334155' : sty.color}`,
              borderRadius: 10, padding: '16px 20px',
              opacity: evt.resolved ? 0.55 : 1,
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <span style={{
                  padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                  background: sty.bg, color: sty.color, whiteSpace: 'nowrap',
                }}>
                  {evt.severity}
                </span>
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: 600, color: '#f1f5f9', marginBottom: 4 }}>
                    {evt.anomaly_type.replace(/_/g,' ')}
                  </p>
                  <p style={{ color: '#94a3b8', fontSize: 13 }}>{evt.description}</p>
                  <p style={{ color: '#64748b', fontSize: 11, marginTop: 6 }}>
                    Terminal: {evt.terminal_id} &nbsp;·&nbsp;
                    {new Date(evt.detected_at).toLocaleString('ko-KR')}
                  </p>
                </div>
                {!evt.resolved ? (
                  <button
                    onClick={() => resolve(evt.event_id)}
                    style={{
                      padding: '5px 14px', fontSize: 12, cursor: 'pointer',
                      background: '#14532d', border: '1px solid #166534',
                      borderRadius: 8, color: '#86efac',
                    }}
                  >
                    해제
                  </button>
                ) : (
                  <span style={{ fontSize: 12, color: '#64748b', padding: '5px 14px' }}>
                    해제됨
                  </span>
                )}
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#64748b',
                        background: '#1e293b', borderRadius: 10 }}>
            이상 이벤트 없음 ✅
          </div>
        )}
      </div>
    </div>
  );
}
