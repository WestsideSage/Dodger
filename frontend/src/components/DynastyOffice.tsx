import { useEffect, useMemo, useState } from 'react';
import type { CommandCenterPlan, CommandCenterResponse, DynastyOfficeResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from './ui';
import { CredibilityStrip } from './dynasty/CredibilityStrip';
import { ProspectCard } from './dynasty/ProspectCard';
import { HistorySubTab } from './dynasty/HistorySubTab';
import { commandApi, dynastyApi } from '../api/client';

const dynastySubtabFromUrl = (): 'recruit' | 'history' | 'staff' => {
  const subtab = new URLSearchParams(window.location.search).get('subtab');
  return subtab === 'history' || subtab === 'staff' || subtab === 'recruit' ? subtab : 'recruit';
};

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

const STAFF_DEPARTMENT_TARGETS = ['tactics', 'training', 'conditioning', 'medical', 'scouting', 'culture'];

function titleizeDepartment(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (match) => match.toUpperCase());
}

function averageRating(staff: DynastyOfficeResponse['staff_market']['current_staff']) {
  if (staff.length === 0) return 0;
  return Math.round(staff.reduce((total, member) => total + member.rating_primary, 0) / staff.length);
}

function buildVacancies(data: DynastyOfficeResponse) {
  const staffed = new Set(data.staff_market.current_staff.map((member) => member.department.toLowerCase()));
  const candidateDepartments = new Set(data.staff_market.candidates.map((candidate) => candidate.department.toLowerCase()));
  const openDepartments = STAFF_DEPARTMENT_TARGETS.filter((department) => !staffed.has(department));

  return openDepartments.map((department) => ({
    department,
    priority: candidateDepartments.has(department) ? 'high' : 'medium',
    note: candidateDepartments.has(department)
      ? 'A live candidate is already on the board for this role.'
      : 'No active hire this week. Coverage is still thin here.',
  }));
}

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
          <button
            aria-label="Close program settings"
            onClick={onClose}
            style={{ background: 'none', border: '1px solid #334155', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer', fontSize: '0.8rem', width: '2rem', height: '2rem' }}
            type="button"
          >
            X
          </button>
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
                  onChange={(event) => onUpdate(key, event.target.value)}
                  style={{ width: '100%', boxSizing: 'border-box', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.55rem 0.65rem', color: '#e2e8f0', marginTop: '0.3rem', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em' }}
                >
                  {options.map((option) => (
                    <option key={`${key}-${option}`} value={option}>{option.replaceAll('_', ' ')}</option>
                  ))}
                </select>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DoTabs({
  active,
  data,
  onSelect,
  onOpenSettings,
}: {
  active: 'recruit' | 'history' | 'staff';
  data: DynastyOfficeResponse;
  onSelect: (id: 'recruit' | 'history' | 'staff') => void;
  onOpenSettings: () => void;
}) {
  const tabs = [
    { id: 'recruit' as const, label: 'Recruit', count: data.recruiting.prospects.length },
    { id: 'history' as const, label: 'History', count: null },
    { id: 'staff' as const, label: 'Staff', count: data.staff_market.current_staff.length },
  ];

  return (
    <div className="do-tabs">
      {tabs.map((tab) => (
        <button key={tab.id} className={`do-tab ${active === tab.id ? 'is-active' : ''}`} onClick={() => onSelect(tab.id)} type="button">
          {tab.label}
          {tab.count != null && <span className="do-tab-count">{tab.count}</span>}
        </button>
      ))}
      <span className="do-tabs-spacer" />
      <button className="dm-btn" onClick={onOpenSettings} type="button">Program Settings</button>
      <span className="do-tabs-note">Front Office - Week {String(data.week).padStart(2, '0')}</span>
    </div>
  );
}

function SlotMeter({ slots }: { slots: DynastyOfficeResponse['recruiting']['budget'] }) {
  const items = [
    { key: 'scout', label: 'Scout', tone: 'cyan', help: 'Verify prospect tiers.' },
    { key: 'contact', label: 'Contact', tone: 'amber', help: 'Letters and calls. Low-cost touches.' },
    { key: 'visit', label: 'Visit', tone: 'orange', help: 'Highest-commitment signal this week.' },
  ] as const;

  return (
    <div className="do-slots">
      <div className="do-panel-head">
        <span className="dm-kicker">Weekly Recruiting</span>
        <h3>Action Slots</h3>
      </div>
      <div className="do-slot-body">
        {items.map((item) => {
          const [used, total] = slots[item.key];
          return (
            <div key={item.key} className={`do-slot tone-${item.tone}`}>
              <div className="do-slot-head">
                <span className="do-slot-lbl">{item.label}</span>
                <span className="do-slot-count"><b>{Math.max(0, total - used)}</b> / {total}</span>
              </div>
              <div className="do-slot-pips">
                {Array.from({ length: total }).map((_, index) => (
                  <span key={`${item.key}-${index}`} className={`do-slot-pip ${index < used ? 'used' : 'open'}`} />
                ))}
              </div>
              <span className="do-slot-help">
                {used >= total ? 'All used this week.' : `${total - used} remaining. ${item.help}`}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StaffBrief({ staff }: { staff: DynastyOfficeResponse['staff_market']['current_staff'] }) {
  return (
    <div className="do-staff">
      <div className="do-panel-head">
        <span className="dm-kicker">Staff Room</span>
        <h3>Department Heads</h3>
      </div>
      <div className="do-staff-list">
        {staff.map((member) => (
          <div key={`${member.department}-${member.name}`} className="do-staff-row">
            <div className="do-staff-id">
              <span className="dept">{titleizeDepartment(member.department)}</span>
              <span className="name">{member.name}</span>
              <span className="voice">"{member.voice || member.effect_summary}"</span>
            </div>
            <div className="do-staff-rating">
              <span className="num">{member.rating_primary}</span>
              <span className="lbl">OVR</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecruitBoard({
  budget,
  prospects,
  reload,
}: {
  budget: DynastyOfficeResponse['recruiting']['budget'];
  prospects: DynastyOfficeResponse['recruiting']['prospects'];
  reload: () => void;
}) {
  const [filter, setFilter] = useState<'all' | 'strong' | 'fair' | 'risk'>('all');
  const filtered = prospects.filter((prospect) => {
    if (filter === 'strong') return prospect.fit_score >= 80;
    if (filter === 'fair') return prospect.fit_score >= 65 && prospect.fit_score < 80;
    if (filter === 'risk') return prospect.fit_score < 65;
    return true;
  });

  return (
    <div className="do-board">
      <div className="do-board-head">
        <div>
          <span className="dm-kicker">Recruit Board</span>
          <h3>This Week's Prospects</h3>
        </div>
        <div className="do-board-filters">
          <button className={`do-board-filter ${filter === 'all' ? 'is-active' : ''}`} onClick={() => setFilter('all')} type="button">
            All <span className="n">{prospects.length}</span>
          </button>
          <button className={`do-board-filter ${filter === 'strong' ? 'is-active' : ''}`} onClick={() => setFilter('strong')} type="button">
            Strong Fit <span className="n">{prospects.filter((prospect) => prospect.fit_score >= 80).length}</span>
          </button>
          <button className={`do-board-filter ${filter === 'fair' ? 'is-active' : ''}`} onClick={() => setFilter('fair')} type="button">
            Fair Fit <span className="n">{prospects.filter((prospect) => prospect.fit_score >= 65 && prospect.fit_score < 80).length}</span>
          </button>
          <button className={`do-board-filter ${filter === 'risk' ? 'is-active' : ''}`} onClick={() => setFilter('risk')} type="button">
            At Risk <span className="n">{prospects.filter((prospect) => prospect.fit_score < 65).length}</span>
          </button>
          <span className="do-board-sep" />
          <span className="do-board-meta">Sorted by Fit - Desc</span>
        </div>
      </div>
      <div className="do-board-grid">
        {filtered.map((prospect, index) => (
          <ProspectCard key={prospect.player_id} prospect={prospect} budget={budget} onAction={reload} priority={index + 1} />
        ))}
        {filtered.length === 0 && (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
            No prospects match the current filter.
          </div>
        )}
      </div>
    </div>
  );
}

function StaffTab({
  data,
  onStaffUpdate,
}: {
  data: DynastyOfficeResponse;
  onStaffUpdate: (next: DynastyOfficeResponse) => void;
}) {
  const staff = data.staff_market.current_staff;
  const candidates = data.staff_market.candidates;
  const avgRating = averageRating(staff);
  const vacancies = buildVacancies(data);
  const [hiringCandidateId, setHiringCandidateId] = useState<string | null>(null);

  const handleInterview = (candidateId: string) => {
    setHiringCandidateId(candidateId);
    dynastyApi.hireStaff(candidateId)
      .then(onStaffUpdate)
      .finally(() => setHiringCandidateId(null));
  };

  return (
    <div className="do-tab-content">
      <div className="do-staff-glance">
        <div className="cell">
          <span className="lbl">Department Heads</span>
          <span className="val">{staff.length} <span>/ 6</span></span>
          <span className="trend">{vacancies.length} vacancies open</span>
        </div>
        <div className="cell">
          <span className="lbl">Avg Rating</span>
          <span className="val">{avgRating}</span>
          <span className="trend ok">Live staff average</span>
        </div>
        <div className="cell">
          <span className="lbl">Facilities</span>
          <span className="val">{data.staff_market.active_facilities.length}</span>
          <span className="trend">{data.staff_market.active_facilities.length > 0 ? data.staff_market.active_facilities.join(' · ') : 'No facility upgrades tracked'}</span>
        </div>
        <div className="cell">
          <span className="lbl">Pipeline</span>
          <span className="val">{candidates.length}</span>
          <span className="trend">{data.staff_market.recent_actions.length} recent staff moves</span>
        </div>
      </div>

      <div className="do-staff-grid">
        {staff.map((member) => (
          <div key={`${member.department}-${member.name}`} className="do-staff-card">
            <div className="do-staff-card-head">
              <div>
                <span className="dm-kicker">{titleizeDepartment(member.department)}</span>
                <p className="name">{member.name}</p>
              </div>
              <div className="rating">
                <span className="num">{member.rating_primary}</span>
                <span className="lbl">OVR</span>
              </div>
            </div>
            <p className="voice">"{member.voice || member.effect_summary}"</p>
            <div className="specs">
              <span className="dm-badge dm-badge-cyan">{titleizeDepartment(member.department)}</span>
              <span className="dm-badge dm-badge-violet">SECONDARY {member.rating_secondary}</span>
            </div>
            <dl className="meta">
              <div><dt>Primary</dt><dd>{member.rating_primary}</dd></div>
              <div><dt>Secondary</dt><dd>{member.rating_secondary}</dd></div>
              <div><dt>Facility Sync</dt><dd>{data.staff_market.active_facilities.length > 0 ? data.staff_market.active_facilities[0] : 'None tracked'}</dd></div>
              <div><dt>Recent Moves</dt><dd>{data.staff_market.recent_actions.length}</dd></div>
            </dl>
            <div className="impact">
              <span className="lbl">Season Impact</span>
              <span className="val">{member.effect_summary}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="do-grid-row">
        <div className="do-vacancy-card">
          <div className="do-panel-head">
            <span className="dm-kicker">Vacancies</span>
            <h3>Open Roles</h3>
          </div>
          <div className="do-vac-list">
            {vacancies.length > 0 ? vacancies.map((vacancy) => (
              <div key={vacancy.department} className={`do-vac-row priority-${vacancy.priority}`}>
                <div className="do-vac-id">
                  <span className="dept">{titleizeDepartment(vacancy.department)}</span>
                  <span className="note">{vacancy.note}</span>
                </div>
                <div className="do-vac-action">
                  <span className={`pr pr-${vacancy.priority}`}>{vacancy.priority}</span>
                  <button className="dm-btn" type="button" disabled>Pipeline Only</button>
                </div>
              </div>
            )) : (
              <div style={{ padding: '1rem 1.2rem', color: '#94a3b8', fontSize: '0.84rem' }}>
                All tracked departments are staffed right now.
              </div>
            )}
          </div>
        </div>

        <div className="do-pipeline-card">
          <div className="do-panel-head">
            <span className="dm-kicker">Pipeline</span>
            <h3>Candidates</h3>
          </div>
          <div className="do-pipe-list">
            {candidates.length > 0 ? candidates.map((candidate) => {
              const isHiring = hiringCandidateId === candidate.candidate_id;
              const normalizedStage = isHiring ? 'scheduled' : 'available';
              return (
                <div key={candidate.candidate_id} className="do-pipe-row">
                  <div className="do-pipe-id">
                    <span className="name">{candidate.name}</span>
                    <span className="dept">{titleizeDepartment(candidate.department)}</span>
                    <span className="note">{candidate.effect_lanes.join(' · ') || candidate.voice}</span>
                  </div>
                  <div className="do-pipe-meta">
                    <span className="rating">{candidate.rating_primary}<small> OVR</small></span>
                    <span className={`stage stage-${normalizedStage}`}>{normalizedStage.replace('-', ' ')}</span>
                    <button
                      className="dm-btn"
                      type="button"
                      disabled={hiringCandidateId !== null}
                      onClick={() => handleInterview(candidate.candidate_id)}
                    >
                      {isHiring ? 'Scheduling...' : 'Interview'}
                    </button>
                  </div>
                </div>
              );
            }) : (
              <div style={{ padding: '1rem 1.2rem', color: '#94a3b8', fontSize: '0.84rem' }}>
                No live staff candidates are on the board this week. Completed interviews appear in recent staff moves.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function DynastyOffice() {
  const { data, loading, error, setData, setError, setLoading } = useApiResource<DynastyOfficeResponse>('/api/dynasty-office');
  const [activeSubTab, setActiveSubTab] = useState<'recruit' | 'history' | 'staff'>(dynastySubtabFromUrl);
  const [showSettings, setShowSettings] = useState(false);
  const [planContext, setPlanContext] = useState<CommandCenterResponse | null>(null);
  const historyClubId = new URLSearchParams(window.location.search).get('team_id');
  const selectedHistoryClubId = historyClubId ?? data?.player_club_id ?? null;

  const reload = () => {
    setLoading(true);
    dynastyApi.office()
      .then(setData)
      .catch((nextError) => setError(nextError.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    commandApi.center().then(setPlanContext).catch(() => {});
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    params.set('subtab', activeSubTab);
    if (activeSubTab === 'history' && selectedHistoryClubId) {
      params.set('team_id', selectedHistoryClubId);
    } else {
      params.delete('team_id');
    }
    window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
  }, [activeSubTab, selectedHistoryClubId]);

  const sortedProspects = useMemo(
    () => [...(data?.recruiting.prospects ?? [])].sort((left, right) => right.fit_score - left.fit_score || left.name.localeCompare(right.name)),
    [data?.recruiting.prospects],
  );

  const updateDepartmentOrder = (key: string, value: string) => {
    if (!planContext) return;
    commandApi.savePlan({
      intent: planContext.plan.intent,
      department_orders: { [key]: value },
    }).then(setPlanContext);
  };

  if (loading && !data) return <StatusMessage title="Opening the program office">Loading dynasty records.</StatusMessage>;
  if (error) return <StatusMessage title="Office unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return null;

  return (
    <>
      <div className="max-content do-shell" data-screen-label="03 Dynasty">
        <DoTabs active={activeSubTab} data={data} onSelect={setActiveSubTab} onOpenSettings={() => setShowSettings(true)} />

        {activeSubTab === 'history' && (
          <HistorySubTab
            clubId={selectedHistoryClubId ?? data.player_club_id}
            isSelf={(selectedHistoryClubId ?? data.player_club_id) === data.player_club_id}
          />
        )}

        {activeSubTab === 'recruit' && (
          <div className="do-tab-content">
            <CredibilityStrip
              credibility={data.recruiting.credibility}
              budget={data.recruiting.budget}
              prospectCount={sortedProspects.length}
              week={data.week}
            />
            <div className="do-grid-row">
              <SlotMeter slots={data.recruiting.budget} />
              <StaffBrief staff={data.staff_market.current_staff} />
            </div>
            <RecruitBoard budget={data.recruiting.budget} prospects={sortedProspects} reload={reload} />
          </div>
        )}

        {activeSubTab === 'staff' && <StaffTab data={data} onStaffUpdate={setData} />}
      </div>

      {showSettings && planContext && (
        <SettingsModal plan={planContext.plan} onUpdate={updateDepartmentOrder} onClose={() => setShowSettings(false)} />
      )}
    </>
  );
}
