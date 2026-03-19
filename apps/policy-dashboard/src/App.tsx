import React, { useState } from 'react';
import Overview    from './pages/Overview';
import ActionLog   from './pages/ActionLog';
import Anomalies   from './pages/Anomalies';
import CircuitBreaker from './pages/CircuitBreaker';

const TABS = [
  { id: 'overview',        label: '📊 개요'          },
  { id: 'actions',         label: '📋 행동 기록'      },
  { id: 'anomalies',       label: '⚠️  이상 탐지'     },
  { id: 'circuit-breaker', label: '⚡ 서킷 브레이커'  },
] as const;

type TabId = typeof TABS[number]['id'];

export default function App() {
  const [tab, setTab] = useState<TabId>('overview');

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#e2e8f0',
                  fontFamily: "'Segoe UI', sans-serif" }}>

      {/* 헤더 */}
      <header style={{ background: '#1e293b', borderBottom: '1px solid #334155',
                       padding: '0 24px', display: 'flex', alignItems: 'center',
                       gap: 24, height: 56 }}>
        <span style={{ color: '#38bdf8', fontWeight: 700, fontSize: 18 }}>
          🔒 KorPIX Policy Dashboard
        </span>
        <span style={{ color: '#64748b', fontSize: 12 }}>v0.1.0</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <StatusDot color="#22c55e" label="Policy Engine" />
          <StatusDot color="#22c55e" label="Audit Network" />
        </div>
      </header>

      {/* 탭 네비게이션 */}
      <nav style={{ background: '#1e293b', borderBottom: '1px solid #334155',
                    padding: '0 24px', display: 'flex', gap: 4 }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding:      '10px 16px',
              background:   'none',
              border:       'none',
              borderBottom: tab === t.id ? '2px solid #38bdf8' : '2px solid transparent',
              color:        tab === t.id ? '#38bdf8' : '#94a3b8',
              cursor:       'pointer',
              fontSize:     13,
              fontWeight:   tab === t.id ? 600 : 400,
              transition:   'all .15s',
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* 페이지 */}
      <main style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        {tab === 'overview'        && <Overview />}
        {tab === 'actions'         && <ActionLog />}
        {tab === 'anomalies'       && <Anomalies />}
        {tab === 'circuit-breaker' && <CircuitBreaker />}
      </main>
    </div>
  );
}

function StatusDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 6,
                   fontSize: 12, color: '#94a3b8' }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%',
                     background: color, display: 'inline-block' }} />
      {label}
    </span>
  );
}
