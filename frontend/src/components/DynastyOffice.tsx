import { useEffect, useState } from 'react';
import type { CommandCenterPlan, CommandCenterResponse, DynastyOfficeResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, PageHeader, StatusMessage } from './ui';
import { CredibilityStrip } from './dynasty/CredibilityStrip';
import { ProspectCard } from './dynasty/ProspectCard';
import { StaffMarketModal } from './dynasty/StaffMarketModal';
import { HistorySubTab } from './dynasty/HistorySubTab';
import { commandApi, dynastyApi } from '../api/client';

const DEPARTMENT_LABELS: Record<string, string> = {
  tactics: 'Tactics',
  training: 'Training',
  conditioning: 'Conditioning',
  medical: 'Medical',
  scouting: 'Scouting',
  culture: 'Culture',
};

const DEPARTMENT_OPTIONS: Record<string, string[]> = {
  tactics: ['opponent prep', 'star containment', 'possession control', 'pressure tempo'],
  training: ['fundamentals', 'throw accuracy', 'catch security', 'scrimmage reps'],
  conditioning: ['balanced maintenance', 'recovery emphasis', 'stamina push', 'fresh legs'],
  medical: ['injury prevention', 'minutes restriction', 'recovery monitoring', 'play through'],
  scouting: ['next opponent', 'prospect board', 'playoff threats', 'rival tendencies'],
  culture: ['pressure management', 'youth confidence', 'veteran leadership', 'accountability'],
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
  const departmentEntries = Object.entries(plan.department_orders).filter(([key]) => key !== 'dev_focus');

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', zIndex: 101, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
      <div className="dm-panel" style={{ width: 'min(92vw, 34rem)', maxHeight: '88vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <p className="dm-kicker">Program Settings</p>
            <h2 style={{ margin: '0.25rem 0 0', color: '#fff' }}>Department Orders</h2>
            <p style={{ margin: '0.4rem 0 0', color: '#94a3b8', fontSize: '0.875rem' }}>Choose a focused order for each staff room.</p>
          </div>
          <button aria-label="Close program settings" onClick={onClose} style={{ background: 'none', border: '1px solid #334155', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer', fontSize: '0.8rem', width: '2rem', height: '2rem' }}>X</button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {departmentEntries.map(([key, value]) => {
            const knownOptions = DEPARTMENT_OPTIONS[key] ?? [String(value)];
            const options = knownOptions.includes(String(value)) ? knownOptions : [String(value), ...knownOptions];
            return (
            <label key={key} style={{ display: 'block' }}>
              <span className="dm-kicker">{DEPARTMENT_LABELS[key] ?? key}</span>
              <select
                value={String(value)}
                onChange={event => onUpdate(key, event.target.value)}
                style={{ width: '100%', boxSizing: 'border-box', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.55rem 0.65rem', color: '#e2e8f0', marginTop: '0.3rem', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                {options.map(option => (
                  <option key={`${key}-${option}`} value={option}>{option.replaceAll('_', ' ')}</option>
                ))}
              </select>
            </label>
          )})}
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
    dynastyApi.office()
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  const fetchPlan = () => {
    commandApi.center().then(setPlanContext);
  };

  useEffect(() => {
    fetchPlan();
  }, []);

  if (loading && !data) return <StatusMessage title="Opening the program office">Loading dynasty records.</StatusMessage>;
  if (error) return <StatusMessage title="Office unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return null;
  const sortedProspects = [...data.recruiting.prospects].sort((left, right) => (
    right.fit_score - left.fit_score || left.name.localeCompare(right.name)
  ));
  const exhaustedActions = Object.entries(data.recruiting.budget)
    .filter(([, [used, total]]) => used >= total)
    .map(([key]) => key.charAt(0).toUpperCase() + key.slice(1));
  const recruitBoardNote = exhaustedActions.length > 0
    ? `${exhaustedActions.join(', ')} action${exhaustedActions.length === 1 ? ' is' : 's are'} unavailable for the rest of this week.`
    : 'Targets are prioritized by fit score so the strongest board stays at the top.';

  const updateDepartmentOrder = (key: string, value: string) => {
    if (!planContext) return;
    commandApi.savePlan({
        intent: planContext.plan.intent,
        department_orders: { [key]: value },
      })
      .then(setPlanContext);
  };

  const hireStaff = (id: string) => {
    dynastyApi.hireStaff(id).then(() => { setShowStaffMarket(false); load(); });
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

      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid #1e293b' }}>
        {(['recruit', 'history'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveSubTab(tab)}
            style={{ 
              background: 'none', 
              border: 'none', 
              borderBottom: activeSubTab === tab ? '2px solid #22d3ee' : '2px solid transparent',
              color: activeSubTab === tab ? '#22d3ee' : '#64748b', 
              cursor: 'pointer', 
              fontWeight: 700, 
              fontSize: '0.875rem', 
              textTransform: 'uppercase',
              padding: '0 0.5rem 0.75rem',
              marginBottom: '-1px',
              transition: 'color 0.15s, border-color 0.15s'
            }}
          >
            {tab === 'recruit' ? 'Recruit' : 'History'}
          </button>
        ))}
      </div>

      {activeSubTab === 'history' && <HistorySubTab clubId={data.player_club_id} />}

      {activeSubTab === 'recruit' && (
        <div className="dynasty-recruit-layout">
          <CredibilityStrip credibility={data.recruiting.credibility} />

          <div className="dynasty-recruit-main">
            <div className="dm-panel dynasty-slots-card">
              <p className="dm-kicker" style={{ marginBottom: '0.6rem' }}>Weekly Recruiting Slots</p>
              <div className="dynasty-slots-grid">
                <div><span className="dm-kicker">Scout</span><div className="dm-data">{data.recruiting.budget.scout[0]}/{data.recruiting.budget.scout[1]}</div></div>
                <div><span className="dm-kicker">Contact</span><div className="dm-data">{data.recruiting.budget.contact[0]}/{data.recruiting.budget.contact[1]}</div></div>
                <div><span className="dm-kicker">Visit</span><div className="dm-data">{data.recruiting.budget.visit[0]}/{data.recruiting.budget.visit[1]}</div></div>
              </div>
              <p className="dm-helper-copy" style={{ margin: '0.75rem 0 0' }}>{recruitBoardNote}</p>
            </div>
            {sortedProspects.length === 0 ? (
              <div className="dm-panel" style={{ padding: '1rem 1.1rem' }}>
                <p className="dm-kicker">Recruit Board</p>
                <p style={{ margin: '0.4rem 0 0', color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.5 }}>
                  No prospects are on your board right now. Check back after the next scouting update.
                </p>
              </div>
            ) : (
              sortedProspects.map((prospect, index) => (
                <ProspectCard key={prospect.player_id} prospect={prospect} budget={data.recruiting.budget} onAction={load} priority={index + 1} />
              ))
            )}
          </div>

          <div className="dm-panel dynasty-staff-room">
            <p className="dm-kicker">Staff Room</p>
            {data.staff_market.current_staff.map(staff => (
              <div key={staff.department} className="dynasty-staff-row">
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
