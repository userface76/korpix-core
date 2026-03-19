import React, { useEffect, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts';
 
const POLICY_URL  = (window as any).__KORPIX_POLICY_URL__  || 'http://localhost:8001';
const AUDIT_URL   = (window as any).__KORPIX_AUDIT_URL__   || 'http://localhost:8002';
 
const DECISION_COLORS: Record<string, string> = {
  AUTO_APPROVE:  '#22c55e',
  USER_CONFIRM:  '#f59e0b',
  ADMIN_APPROVE: '#a78bfa',
  DENY:          '#ef4444',
};
 
// ── 데모 데이터 (API 미연결 시) ──────────────────────────────────
const DEMO_STATS = {
  totalActions:  247,
  autoApproved:  189,
  userConfirmed:  38,
  adminApproved:  14,
  denied:          6,
  chainIntegrity: 'INTACT' as const,
  ledgerCount:   247,
  anomalyCount:    2,
};
 
const DEMO_PIE = [
  { name: 'AUTO_APPROVE',  value: 189 },
  { name: 'USER_CONFIRM',  value:  38 },
  { name: 'ADMIN_APPROVE', value:  14 },
  { name: 'DENY',          value:   6 },
];
 
const DEMO_BAR = [
  { uc: 'UC-001 결제',   count: 120, avg_score: 18 },
  { uc: 'UC-002 투자',   count:  45, avg_score: 34 },
  { uc: 'UC-003 구매',   count:  52, avg_score: 29 },
  { uc: 'UC-004 행정',   count:  30, avg_score: 22 },
];
 
export default function Overview() {
  const [stats, setStats]   = useState(DEMO_STATS);
  const [loading, setLoading] = useState(true);
 
  useEffect(() => {
    Promise.all([
      fetch(`${POLICY_URL}/health`).then(r => r.json()).catch(() => null),
      fetch(`${AUDIT_URL}/integrity`).then(r => r.json()).catch(() => null),
    ]).then(([pe, audit]) => {
      if (pe || audit) {
        setStats(prev => ({
          ...prev,
          ledgerCount:    audit?.ledger_count ?? prev.ledgerCount,
          chainIntegrity: audit?.is_valid ? 'INTACT' : 'COMPROMISED',
        }));
      }
    }).finally(() => setLoading(false));
  }, []);
 
  return (
    <div>
      <h2 style={{ fontSize: 18, marginBottom: 20, color: '#f1f5f9' }}>
        시스템 개요
        {loading && <span style={{ fontSize: 12, color: '#64748b', marginLeft: 12 }}>
          로딩 중...
        </span>}
      </h2>
 
      {/* KPI 카드 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 32 }}>
        <KpiCard label="총 행동 처리"   value={stats.totalActions}  unit="건" color="#38bdf8" />
        <KpiCard label="자동 승인"       value={stats.autoApproved}  unit="건" color="#22c55e" />
        <KpiCard label="차단 (DENY)"     value={stats.denied}        unit="건" color="#ef4444" />
        <KpiCard label="이상 탐지"       value={stats.anomalyCount}  unit="건" color="#f59e0b" />
      </div>
 
      {/* 감사 상태 카드 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
        <Card title="원장 무결성">
          <IntegrityBadge status={stats.chainIntegrity} />
          <p style={{ color: '#94a3b8', fontSize: 13, marginTop: 8 }}>
            저장 레코드: {stats.ledgerCount.toLocaleString()}건
          </p>
        </Card>
        <Card title="서비스 상태">
          <StatusRow label="Policy Engine" url={POLICY_URL} />
          <StatusRow label="Audit Network" url={AUDIT_URL} />
        </Card>
      </div>
 
      {/* 차트 2개 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card title="결정 분포">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={DEMO_PIE} dataKey="value" nameKey="name"
                   cx="50%" cy="50%" outerRadius={80} label={({name, percent}) =>
                     `${(percent*100).toFixed(0)}%`}>
                {DEMO_PIE.map(entry => (
                  <Cell key={entry.name} fill={DECISION_COLORS[entry.name]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(val, name) => [val, name]}
                contentStyle={{ background: '#1e293b', border: '1px solid #334155' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>
 
        <Card title="UC별 처리 건수 / 평균 Risk Score">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={DEMO_BAR} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="uc" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
              <Legend />
              <Bar dataKey="count"     name="처리 건수" fill="#38bdf8" radius={[3,3,0,0]} />
              <Bar dataKey="avg_score" name="평균 Risk"  fill="#f59e0b" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
 
// ── 공통 컴포넌트 ─────────────────────────────────────────────────
 
function KpiCard({ label, value, unit, color }:
  { label: string; value: number; unit: string; color: string }) {
  return (
    <div style={{ background: '#1e293b', border: '1px solid #334155',
                  borderRadius: 10, padding: 20 }}>
      <p style={{ color: '#94a3b8', fontSize: 13, marginBottom: 8 }}>{label}</p>
      <p style={{ color, fontSize: 32, fontWeight: 700, lineHeight: 1 }}>
        {value.toLocaleString()}
        <span style={{ fontSize: 14, fontWeight: 400, marginLeft: 4 }}>{unit}</span>
      </p>
    </div>
  );
}
 
function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#1e293b', border: '1px solid #334155',
                  borderRadius: 10, padding: 20 }}>
      <h3 style={{ fontSize: 14, color: '#94a3b8', marginBottom: 16 }}>{title}</h3>
      {children}
    </div>
  );
}
 
function IntegrityBadge({ status }: { status: 'INTACT' | 'COMPROMISED' }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      padding: '6px 14px', borderRadius: 20,
      background: status === 'INTACT' ? '#14532d' : '#7f1d1d',
      color:      status === 'INTACT' ? '#86efac'  : '#fca5a5',
      fontSize: 14, fontWeight: 600,
    }}>
      {status === 'INTACT' ? '✅ INTACT' : '❌ COMPROMISED'}
    </span>
  );
}
 
function StatusRow({ label, url }: { label: string; url: string }) {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    fetch(`${url}/health`).then(() => setOk(true)).catch(() => setOk(false));
  }, [url]);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10,
                  marginBottom: 10, fontSize: 13 }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%',
        background: ok === null ? '#64748b' : ok ? '#22c55e' : '#ef4444',
      }} />
      <span style={{ color: '#e2e8f0' }}>{label}</span>
      <span style={{ color: '#64748b', fontSize: 11 }}>{url}</span>
    </div>
  );
}
 
