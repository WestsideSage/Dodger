import { useEffect, useState } from 'react';
import type { CommandCenterResponse, DynastyOfficeResponse } from '../types';
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

function SettingsModal({ plan, onUpdate, onClose }: { plan: any, onUpdate: (k: string, v: string) => void, onClose: () => void }) {
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', zIndex: 101, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="dm-panel" style={{ width: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <h2>Program Settings</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>✕</button>
        </div>
        <p className="dm-kicker">Department Orders</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
           {Object.entries(plan.department_orders).filter(([k]) => k !== 'dev_focus').map(([k, v]) => (
             <label key={k} style={{ display: 'block' }}>
               <span style={{ fontSize: '0.7rem', color: '#64748b' }}>{DEPARTMENT_LABELS[k] ?? k}</span>
               <input 
                 type="text" 
                 value={String(v)} 
                 onChange={e => onUpdate(k, e.target.value)}
                 style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.5rem', color: '#e2e8f0' }}
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
    fetch('/api/command-center').then(r => r.json()).then(setPlanContext);
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
      .then(r => r.json())
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
        description={`Season ${data.season_id.split('_')[1]} · Week ${data.week}`}
        stats={
          <div style={{ display: 'flex', gap: '0.5rem' }}>
             <button onClick={() => setShowSettings(true)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}>⚙️</button>
          </div>
        }
      />

      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem' }}>
        <button 
          onClick={() => setActiveSubTab('recruit')}
          style={{ background: 'none', border: 'none', color: activeSubTab === 'recruit' ? '#22d3ee' : '#64748b', cursor: 'pointer', fontWeight: 700, fontSize: '0.875rem', textTransform: 'uppercase' }}
        >
          Recruit
        </button>
        <button 
          onClick={() => setActiveSubTab('history')}
          style={{ background: 'none', border: 'none', color: activeSubTab === 'history' ? '#22d3ee' : '#64748b', cursor: 'pointer', fontWeight: 700, fontSize: '0.875rem', textTransform: 'uppercase' }}
        >
          History
        </button>
      </div>

      {activeSubTab === 'history' && (
        <HistorySubTab clubId={data.player_club_id} />
      )}

      {activeSubTab === 'recruit' && (
        <div style={{ display: 'flex', gap: '1.25rem' }}>
          <CredibilityStrip credibility={data.recruiting.credibility} />
          
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', gap: '1.5rem' }}>
                 <div><b>Scout:</b> {data.recruiting.budget.scout[0]}/{data.recruiting.budget.scout[1]}</div>
                 <div><b>Contact:</b> {data.recruiting.budget.contact[0]}/{data.recruiting.budget.contact[1]}</div>
                 <div><b>Visit:</b> {data.recruiting.budget.visit[0]}/{data.recruiting.budget.visit[1]}</div>
              </div>
            </div>
            {data.recruiting.prospects.map(p => (
              <ProspectCard key={p.player_id} prospect={p} budget={data.recruiting.budget} onAction={load} />
            ))}
          </div>

          <div className="dm-panel" style={{ flex: '0 0 200px' }}>
            <p className="dm-kicker">Staff Room</p>
            {data.staff_market.current_staff.map(s => (
              <div key={s.department} style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{s.department.toUpperCase()}</div>
                <div style={{ fontWeight: 700 }}>{s.name}</div>
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
