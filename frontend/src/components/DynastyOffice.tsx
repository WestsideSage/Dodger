import { useEffect, useState } from 'react';
import type { CommandCenterPlan, CommandCenterResponse, DynastyOfficeResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, PageHeader, StatusMessage } from './ui';
import { CredibilityStrip } from './dynasty/CredibilityStrip';
import { ProspectCard } from './dynasty/ProspectCard';
import { StaffMarketModal } from './dynasty/StaffMarketModal';
import { HistorySubTab } from './dynasty/HistorySubTab';

const DEPARTMENT_LABELS: Record<string, string> = {
  tactics: 'Tactics',
  training: 'Training',
  conditioning: 'Conditioning',
  medical: 'Medical',
  scouting: 'Scouting',
  culture: 'Culture',
};

function SettingsModal({
  plan,
  onUpdate,
  onClose,
}: {
  plan: CommandCenterPlan;
  onUpdate: (key: string, value: string) => void;
  onClose: () => void;
}) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', zIndex: 101, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="dm-panel" style={{ width: 'min(92vw, 28rem)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <p className="dm-kicker">Program Settings</p>
            <h2 style={{ margin: '0.25rem 0 0', color: '#fff' }}>Department Orders</h2>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.25rem' }}>X</button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {Object.entries(plan.department_orders).filter(([key]) => key !== 'dev_focus').map(([key, value]) => (
            <label key={key} style={{ display: 'block' }}>
              <span className="dm-kicker">{DEPARTMENT_LABELS[key] ?? key}</span>
              <input
                type="text"
                value={String(value)}
                onChange={event => onUpdate(key, event.target.value)}
                style={{ width: '100%', boxSizing: 'border-box', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.55rem 0.65rem', color: '#e2e8f0', marginTop: '0.3rem' }}
              />
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

export function DynastyOffice() {
  const { data, loading, error, setData, setLoading, setError } = useApiResource<DynastyOfficeResponse>('/api/dynasty-office');
  const [activeSubTab, setActiveSubTab] = useState<'recruit' | 'history'>('recruit');
  const [showStaffMarket, setShowStaffMarket] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [planContext, setPlanContext] = useState<CommandCenterResponse | null>(null);

  const load = () => {
    setLoading(true);
    fetch('/api/dynasty-office')
      .then(res => res.json())
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  const fetchPlan = () => {
    fetch('/api/command-center').then(res => res.json()).then(setPlanContext);
  };

  useEffect(() => {
    fetchPlan();
  }, []);

  if (loading && !data) return <StatusMessage title="Opening the program office">Loading dynasty records.</StatusMessage>;
  if (error) return <StatusMessage title="Office unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return null;

  const updateDepartmentOrder = (key: string, value: string) => {
    if (!planContext) return;
    fetch('/api/command-center/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        intent: planContext.plan.intent,
        department_orders: { [key]: value },
      }),
    })
      .then(res => res.json())
      .then(setPlanContext);
  };

  const hireStaff = (id: string) => {
    fetch('/api/dynasty-office/staff/hire', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_id: id }),
    }).then(() => { setShowStaffMarket(false); load(); });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <PageHeader
        eyebrow="Dynasty Office"
        title={data.player_club_name}
        description={`Season ${data.season_id.split('_')[1]} - Week ${data.week}`}
        stats={
          <button
            onClick={() => setShowSettings(true)}
            className="dm-kicker"
            style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer', padding: '0.55rem 0.75rem' }}
          >
            Program Settings
          </button>
        }
      />

      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem' }}>
        {(['recruit', 'history'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveSubTab(tab)}
            style={{ background: 'none', border: 'none', color: activeSubTab === tab ? '#22d3ee' : '#64748b', cursor: 'pointer', fontWeight: 700, fontSize: '0.875rem', textTransform: 'uppercase' }}
          >
            {tab === 'recruit' ? 'Recruit' : 'History'}
          </button>
        ))}
      </div>

      {activeSubTab === 'history' && <HistorySubTab clubId={data.player_club_id} />}

      {activeSubTab === 'recruit' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(13rem, 0.65fr) minmax(0, 2.6fr) minmax(13rem, 0.72fr)', gap: '1.25rem', alignItems: 'start' }}>
          <CredibilityStrip credibility={data.recruiting.credibility} />

          <div style={{ minWidth: 0 }}>
            <div className="dm-panel" style={{ marginBottom: '0.8rem', padding: '0.9rem 1rem' }}>
              <p className="dm-kicker" style={{ marginBottom: '0.6rem' }}>Weekly Recruiting Slots</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.75rem' }}>
                <div><span className="dm-kicker">Scout</span><div className="dm-data">{data.recruiting.budget.scout[0]}/{data.recruiting.budget.scout[1]}</div></div>
                <div><span className="dm-kicker">Contact</span><div className="dm-data">{data.recruiting.budget.contact[0]}/{data.recruiting.budget.contact[1]}</div></div>
                <div><span className="dm-kicker">Visit</span><div className="dm-data">{data.recruiting.budget.visit[0]}/{data.recruiting.budget.visit[1]}</div></div>
              </div>
            </div>
            {data.recruiting.prospects.map(prospect => (
              <ProspectCard key={prospect.player_id} prospect={prospect} budget={data.recruiting.budget} onAction={load} />
            ))}
          </div>

          <div className="dm-panel" style={{ minWidth: 0 }}>
            <p className="dm-kicker">Staff Room</p>
            {data.staff_market.current_staff.map(staff => (
              <div key={staff.department} style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{staff.department.toUpperCase()}</div>
                <div style={{ fontWeight: 700 }}>{staff.name}</div>
              </div>
            ))}
            <ActionButton onClick={() => setShowStaffMarket(true)}>Staff Market</ActionButton>
          </div>
        </div>
      )}

      {showStaffMarket && <StaffMarketModal candidates={data.staff_market.candidates} onHire={hireStaff} onClose={() => setShowStaffMarket(false)} />}
      {showSettings && planContext && <SettingsModal plan={planContext.plan} onUpdate={updateDepartmentOrder} onClose={() => setShowSettings(false)} />}
    </div>
  );
}
