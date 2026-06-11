import { useEffect, useMemo, useState } from 'react';
import type { CommandCenterPlan, CommandCenterResponse, DynastyOfficeResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage, Dialog } from './ui';
import { CredibilityStrip } from './dynasty/CredibilityStrip';
import { ProspectCard } from './dynasty/ProspectCard';
import { HistorySubTab } from './dynasty/HistorySubTab';
import { commandApi, dynastyApi } from '../api/client';
import { EmptyState, TermTip, ProofChip } from '../legibility';

const dynastySubtabFromUrl = (): 'recruit' | 'history' | 'staff' => {
  const subtab = new URLSearchParams(window.location.search).get('subtab');
  return subtab === 'history' || subtab === 'staff' || subtab === 'recruit' ? subtab : 'recruit';
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
  // V19b: the six flavor dropdowns are retired. The staff runs ONE focused
  // department per week — a real decision with an opportunity cost, each
  // option a disclosed mechanical effect ("medical" was removed: injuries
  // are not modeled, so there was nothing to order).
  const FOCUS_OPTIONS: Array<{
    key: string;
    label: string;
    effect: string;
    termId: import('../legibility').TermId;
  }> = [
    {
      key: 'tactics',
      label: 'Tactics — film week',
      effect: 'Next match, your throwers play smarter: +18 effective Tactical IQ on target reads, release timing, and catch-beating timing.',
      termId: 'dept.tactics',
    },
    {
      key: 'conditioning',
      label: 'Conditioning — recovery week',
      effect: 'Next match, fatigue bites half as hard: the stamina drag on every action stat is halved.',
      termId: 'dept.conditioning',
    },
    {
      key: 'training',
      label: 'Training — practice block',
      effect: 'Banks a practice credit: each training week adds +0.2 OVR of offseason growth for the whole squad (cap 8 weeks).',
      termId: 'dept.training',
    },
    {
      key: 'scouting',
      label: 'Scouting — extra assignment',
      effect: 'One extra Scout action on the recruit board this week (3 → 4).',
      termId: 'dept.scouting',
    },
    {
      key: 'culture',
      label: 'Culture — locker-room week',
      effect: 'Courtship lands warmer this week: Contact and Visit interest gains are 25% stronger.',
      termId: 'dept.culture',
    },
  ];
  const currentFocus = String(plan.department_orders?.focus_department ?? 'tactics');

  return (
    <Dialog
      labelledBy="program-settings-title"
      label="Staff Focus"
      onClose={onClose}
      overlayStyle={{ background: 'rgba(0,0,0,0.8)', backgroundColor: undefined, backdropFilter: undefined, zIndex: 101, padding: '1rem' }}
      panelClassName="dm-panel"
      panelStyle={{ width: 'min(92vw, 34rem)', maxHeight: '88vh', overflowY: 'auto' }}
    >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '1.25rem' }}>
          <div>
            <p className="dm-kicker">Program Settings</p>
            <h2 id="program-settings-title" style={{ margin: '0.25rem 0 0', color: '#fff' }}>Staff Focus</h2>
            <p style={{ margin: '0.4rem 0 0', color: '#94a3b8', fontSize: '0.875rem' }}>
              Your staff concentrates on one room this week. Every option is a real,
              disclosed effect — pick where the week goes.
            </p>
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
        <div role="radiogroup" aria-label="Weekly staff focus" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {FOCUS_OPTIONS.map((option) => {
            const selected = currentFocus === option.key;
            return (
              <button
                key={option.key}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => onUpdate('focus_department', option.key)}
                style={{
                  textAlign: 'left',
                  padding: '0.7rem 0.85rem',
                  borderRadius: 6,
                  background: selected ? 'rgba(34,211,238,0.08)' : '#0f172a',
                  border: selected ? '1px solid #22d3ee' : '1px solid #1e293b',
                  borderLeft: selected ? '3px solid #22d3ee' : '3px solid #1e293b',
                  color: '#e2e8f0',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                <span className="dm-kicker" style={{ color: selected ? '#22d3ee' : '#94a3b8' }}>
                  <TermTip term={option.termId}>{option.label}</TermTip>
                </span>
                <p style={{ margin: '0.3rem 0 0', color: selected ? '#cbd5e1' : '#64748b', fontSize: '0.74rem', lineHeight: 1.45 }}>
                  {option.effect}
                </p>
              </button>
            );
          })}
        </div>
        <p style={{ margin: '0.9rem 0 0', color: '#64748b', fontSize: '0.7rem', lineHeight: 1.45 }}>
          Dev Focus (player development direction) lives on the Command Center, and match
          tactics live in the Policy Editor — both stay set independently of this week’s
          staff focus. AI clubs run the same staff system with their own weekly picks.
        </p>
    </Dialog>
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

// V19b: plain-language promise vocabulary (the old "Promise Lane" label
// failed owner comprehension — the term itself was the bug).
const PROMISE_LABELS: Record<string, { label: string; meaning: string }> = {
  early_playing_time: {
    label: 'Early playing time',
    meaning: 'They appear in at least 6 matches this season.',
  },
  development_priority: {
    label: 'Development priority',
    meaning: 'You run a focused dev plan at least 3 weeks and keep them rostered.',
  },
  contender_path: {
    label: "We'll contend",
    meaning: 'The club reaches the playoffs this season.',
  },
};

function PromisesPanel({
  promises,
  maxActive,
  prospects,
}: {
  promises: DynastyOfficeResponse['recruiting']['active_promises'];
  maxActive: number;
  prospects: DynastyOfficeResponse['recruiting']['prospects'];
}) {
  const nameById = new Map(prospects.map((p) => [p.player_id, p.name]));
  const open = promises.filter((p) => p.status === 'open');
  const resolved = promises.filter((p) => p.status !== 'open').slice(0, 4);

  return (
    <div className="dm-panel" style={{ padding: '0.85rem 1rem' }} data-testid="promises-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '0.75rem', flexWrap: 'wrap' }}>
        <span className="dm-kicker">
          <TermTip term="recruit.promise">Promises</TermTip>
          <span style={{ color: '#64748b', marginLeft: '0.4rem', textTransform: 'none', letterSpacing: 0 }}>
            {open.length}/{maxActive} open
          </span>
        </span>
        <span style={{ color: '#64748b', fontSize: '0.68rem' }}>
          Checked at season&apos;s end — kept promises build credibility, broken ones cost more.
        </span>
      </div>
      {open.length === 0 && resolved.length === 0 ? (
        <p style={{ margin: '0.5rem 0 0', color: '#64748b', fontSize: '0.74rem' }}>
          No promises yet. Use a prospect card&apos;s Promise action to commit to something
          real — playing time, development, or contention.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.55rem' }}>
          {open.map((p) => (
            <div key={`open-${p.player_id}`} style={{ display: 'flex', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.76rem' }}>
              <span className="dm-badge dm-badge-cyan">OPEN</span>
              <span style={{ color: '#e2e8f0' }}>
                {p.player_name ?? nameById.get(p.player_id) ?? p.player_id}: {PROMISE_LABELS[p.promise_type]?.label ?? p.promise_type}
              </span>
              <span style={{ color: '#64748b' }}>
                — {PROMISE_LABELS[p.promise_type]?.meaning ?? ''}
              </span>
            </div>
          ))}
          {resolved.map((p) => (
            <div key={`done-${p.player_id}-${p.result_season_id}`} style={{ display: 'flex', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.76rem' }}>
              <span className={`dm-badge ${p.status === 'fulfilled' ? 'dm-badge-cyan' : 'dm-badge-orange'}`}>
                {p.status === 'fulfilled' ? 'KEPT' : 'BROKEN'}
              </span>
              <span style={{ color: '#94a3b8' }}>
                {p.player_name ?? nameById.get(p.player_id) ?? p.player_id}: {PROMISE_LABELS[p.promise_type]?.label ?? p.promise_type}
              </span>
              <span style={{ color: '#64748b' }}>— {p.evidence}</span>
            </div>
          ))}
        </div>
      )}
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
        <p style={{ margin: '0.2rem 0 0', color: '#94a3b8', fontSize: '0.72rem', lineHeight: 1.4 }}>
          Each slot is one action you can take this week. Remaining slots reset next week.
        </p>
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
  if (staff.length === 0) {
    return (
      <div className="do-staff">
        <div className="do-panel-head">
          <span className="dm-kicker">Staff Room</span>
          <h3>Department Heads</h3>
        </div>
        <EmptyState
          title="No department heads hired"
          body="Use the Staff tab to browse pipeline candidates and hire your first department heads."
        />
      </div>
    );
  }
  return (
    <div className="do-staff">
      <div className="do-panel-head">
        <span className="dm-kicker">Staff Room</span>
        <h3>Department Heads</h3>
      </div>
      <div className="do-staff-list">
        {staff.map((member) => {
          const termId = `staff.${member.department}` as const;
          // Safe cast: the six departments match the pre-seeded staff.* term ids.
          // If a novel department appears with no term, fall back to plain copy.
          const hasTerm = [
            'staff.training', 'staff.tactics', 'staff.conditioning',
            'staff.medical', 'staff.scouting', 'staff.culture',
          ].includes(termId);
          const deptLabel = titleizeDepartment(member.department);
          return (
            <div key={`${member.department}-${member.name}`} className="do-staff-row">
              <div className="do-staff-id">
                {hasTerm ? (
                  <TermTip term={termId as import('../legibility').TermId}>
                    <span className="dept">{deptLabel}</span>
                  </TermTip>
                ) : (
                  <span className="dept">{deptLabel}</span>
                )}
                <span className="name">{member.name}</span>
                <span className="voice">"{member.voice || member.effect_summary}"</span>
              </div>
              <div className="do-staff-rating" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.2rem' }}>
                <span className="num">{member.rating_primary}</span>
                <span className="lbl">OVR</span>
                {member.department === 'training' && member.training_modifier_pct !== undefined && (
                  <ProofChip
                    label={`+${member.training_modifier_pct}% dev`}
                    source={`Training OVR ${member.rating_primary} → offseason growth modifier ${member.training_modifier_pct}% (formula: (OVR − 50) / 50 × 15%, clamped at 0).`}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RecruitingContext({
  budget,
  prospectCount,
}: {
  budget: DynastyOfficeResponse['recruiting']['budget'];
  prospectCount: number;
}) {
  const scoutRemaining = Math.max(0, budget.scout[1] - budget.scout[0]);
  const contactRemaining = Math.max(0, budget.contact[1] - budget.contact[0]);
  const visitRemaining = Math.max(0, budget.visit[1] - budget.visit[0]);

  return (
    <div
      className="do-recruit-context"
      role="group"
      aria-label="This week's recruiting summary"
      style={{
        display: 'flex',
        gap: '0.75rem',
        flexWrap: 'wrap',
        padding: '0.6rem 0.9rem',
        background: 'rgba(15,23,42,0.55)',
        border: '1px solid #1e293b',
        borderRadius: '6px',
        marginBottom: '0.75rem',
      }}
    >
      <div className="do-cred-rank" style={{ flex: '1 1 8rem', minWidth: '8rem' }}>
        <span className="lbl">Board</span>
        <div className="val"><b>{prospectCount}</b> <span>prospects</span></div>
        <span className="trend dim">Sorted by program fit</span>
      </div>
      <div className="do-cred-rank" style={{ flex: '1 1 9rem', minWidth: '9rem' }}>
        <span className="lbl">Reach Remaining</span>
        <div className="val"><b>{scoutRemaining + contactRemaining}</b> <span>scout + contact</span></div>
        <span className="trend dim">{scoutRemaining} scout · {contactRemaining} contact</span>
      </div>
      <div className={`do-cred-rank ${visitRemaining === 0 ? 'danger' : ''}`} style={{ flex: '1 1 8rem', minWidth: '8rem' }}>
        <span className="lbl">Visit Slots</span>
        <div className="val"><b>{visitRemaining}</b> <span>remaining</span></div>
        <span className={`trend ${visitRemaining > 0 ? 'dim' : 'warn'}`}>
          {visitRemaining > 0 ? 'Use on best-fit closes' : 'Budget exhausted this week'}
        </span>
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
  const [sort, setSort] = useState<'fit' | 'interest' | 'pipeline'>('fit');
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');

  const filtered = useMemo(() => {
    const base = prospects.filter((prospect) => {
      if (filter === 'strong') return prospect.fit_score >= 80;
      if (filter === 'fair') return prospect.fit_score >= 65 && prospect.fit_score < 80;
      if (filter === 'risk') return prospect.fit_score < 65;
      return true;
    });
    return [...base].sort((a, b) => {
      let av: number;
      let bv: number;
      if (sort === 'interest') {
        av = a.interest ?? 0;
        bv = b.interest ?? 0;
      } else if (sort === 'pipeline') {
        av = a.pipeline_tier ?? 1;
        bv = b.pipeline_tier ?? 1;
      } else {
        av = a.fit_score;
        bv = b.fit_score;
      }
      return sortDir === 'desc' ? bv - av : av - bv;
    });
  }, [prospects, filter, sort, sortDir]);

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
          <div
            role="group"
            aria-label="Sort prospects"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              flexWrap: 'wrap',
            }}
          >
            <span
              style={{
                fontSize: '0.6rem',
                color: '#64748b',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Sort
            </span>
            {(['fit', 'interest', 'pipeline'] as const).map((key) => (
              <button
                key={key}
                className={`do-board-filter ${sort === key ? 'is-active' : ''}`}
                onClick={() => {
                  if (sort === key) {
                    setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
                  } else {
                    setSort(key);
                    setSortDir('desc');
                  }
                }}
                type="button"
                aria-pressed={sort === key}
                aria-label={`Sort by ${key === 'fit' ? 'Fit' : key === 'interest' ? 'Interest' : 'Pipeline'}`}
                title={
                  key === 'fit'
                    ? 'Sort by Fit score (how well this prospect matches your program)'
                    : key === 'interest'
                      ? 'Sort by Interest % (how interested the prospect is in your program)'
                      : 'Sort by Pipeline Tier (1–5; higher tiers start warmer, strengthening your Signing Day offer)'
                }
              >
                {key === 'fit' ? 'Fit' : key === 'interest' ? 'Interest' : 'Pipeline'}
                {sort === key && (
                  <span aria-hidden="true" style={{ marginLeft: '0.2rem' }}>
                    {sortDir === 'desc' ? '↓' : '↑'}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
      {/* Board-level legend — shown once instead of repeating on every card. */}
      {prospects.length > 0 && (
        <div
          aria-label="Card color key: green = Strong Fit, amber = Fair Fit, red = At Risk"
          style={{
            display: 'flex',
            gap: '0.9rem',
            flexWrap: 'wrap',
            alignItems: 'center',
            margin: '0.4rem 0 0.65rem',
            fontSize: '0.62rem',
            color: '#64748b',
            letterSpacing: '0.04em',
          }}
        >
          <span style={{ color: '#34d399' }}>● Strong Fit ≥80</span>
          <span style={{ color: '#f59e0b' }}>● Fair Fit 65–79</span>
          <span style={{ color: '#f87171' }}>● At Risk &lt;65</span>
          <span>Scout narrows the OVR range · Contact and visits build interest</span>
        </div>
      )}
      <div className="do-board-grid">
        {filtered.map((prospect, index) => (
          <ProspectCard key={prospect.player_id} prospect={prospect} budget={budget} onAction={reload} priority={index + 1} />
        ))}
        {filtered.length === 0 && (
          <EmptyState
            title="No prospects match this filter"
            body={
              filter === 'all'
                ? 'The recruit board is empty this week. It refreshes each week as the season progresses.'
                : `Switch to "All" to see every prospect, or try a different filter.`
            }
          />
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
                {(['staff.training', 'staff.tactics', 'staff.conditioning',
                   'staff.medical', 'staff.scouting', 'staff.culture'] as const).includes(
                    `staff.${member.department}` as 'staff.training'
                  ) ? (
                  <TermTip term={`staff.${member.department}` as import('../legibility').TermId}>
                    <span className="dm-kicker">{titleizeDepartment(member.department)}</span>
                  </TermTip>
                ) : (
                  <span className="dm-kicker">{titleizeDepartment(member.department)}</span>
                )}
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
            <div className="impact" style={{ marginTop: '0.5rem' }}>
              <span className="lbl" style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {member.department === 'training' ? 'Development Impact' : 'Program Role'}
              </span>
              <span className="val" style={{ fontSize: '0.72rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                {member.effect_summary}
              </span>
              {member.department === 'training' && member.training_modifier_pct !== undefined && (
                <div style={{ marginTop: '0.35rem' }}>
                  <ProofChip
                    label={`+${member.training_modifier_pct}% offseason growth`}
                    source={`Training OVR ${member.rating_primary} feeds the offseason development formula: modifier = (OVR − 50) / 50 × 15%, clamped at 0. Applied to every player on your roster each offseason.`}
                  />
                </div>
              )}
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
              <EmptyState
                title="All roles are filled"
                body="All tracked department heads are currently hired. Vacancies appear here when a position opens."
              />
            )}
          </div>
        </div>

        <div className="do-pipeline-card">
          <div className="do-panel-head">
            <span className="dm-kicker">Pipeline</span>
            <h3>Candidates</h3>
          </div>
          <p style={{ fontSize: '0.68rem', color: '#94a3b8', margin: '0 0 0.5rem 0', padding: '0 1.2rem' }}>
            Candidates are generated each offseason. Hiring immediately replaces the current department head.
          </p>
          <div className="do-pipe-list">
            {candidates.length > 0 ? candidates.map((candidate) => {
              const isHiring = hiringCandidateId === candidate.candidate_id;
              const normalizedStage = isHiring ? 'hiring' : 'available';
              return (
                <div key={candidate.candidate_id} className="do-pipe-row">
                  <div className="do-pipe-id">
                    <span className="name">{candidate.name}</span>
                    {(['staff.training', 'staff.tactics', 'staff.conditioning',
                       'staff.medical', 'staff.scouting', 'staff.culture'] as const).includes(
                        `staff.${candidate.department}` as 'staff.training'
                      ) ? (
                      <TermTip term={`staff.${candidate.department}` as import('../legibility').TermId}>
                        <span className="dept">{titleizeDepartment(candidate.department)}</span>
                      </TermTip>
                    ) : (
                      <span className="dept">{titleizeDepartment(candidate.department)}</span>
                    )}
                    <span className="note">{candidate.effect_lanes[0] || candidate.voice}</span>
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
                      {isHiring ? 'Hiring...' : 'Hire'}
                    </button>
                  </div>
                </div>
              );
            }) : (
              <div style={{ padding: '1rem 1.2rem', color: '#94a3b8', fontSize: '0.84rem' }}>
                No live staff candidates are on the board this week. Completed hires appear in recent staff moves.
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
    }).then((nextPlan) => {
      setPlanContext(nextPlan);
      // A staff-focus change moves real numbers on this screen (a scouting
      // week buys a 4th Scout slot) — refetch so the budget meter is never
      // stale behind the modal.
      reload();
    });
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
            />
            <RecruitingContext
              budget={data.recruiting.budget}
              prospectCount={sortedProspects.length}
            />
            <PromisesPanel
              promises={data.recruiting.active_promises}
              maxActive={data.recruiting.rules.max_active_promises}
              prospects={data.recruiting.prospects}
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
