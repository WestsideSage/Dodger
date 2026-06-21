import { useEffect, useMemo, useState } from 'react';
import type { CommandCenterPlan, CommandCenterResponse, DynastyOfficeResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { Dialog } from './ui';
import { StatusMessage } from '../ui';
import { CredibilityStrip } from './dynasty/CredibilityStrip';
import { ProspectCard } from './dynasty/ProspectCard';
import { HistorySubTab } from './dynasty/HistorySubTab';
import { commandApi, dynastyApi } from '../api/client';
import { formatK } from '../money';
import { EmptyState, TermTip, ProofChip } from '../legibility';
import styles from './dynasty/DynastyOffice.module.css';

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
    // V22 Phase 4: focus payoffs SCALE with the head running them — the
    // ranges here are honest bounds; each head's exact number is on their
    // staff-tab card.
    {
      key: 'tactics',
      label: 'Tactics — film week',
      effect: 'Next match, your throwers play smarter: +12–24 effective Tactical IQ (scaled by your Tactics head) on target reads, release timing, and catch-beating timing.',
      termId: 'dept.tactics',
    },
    {
      key: 'conditioning',
      label: 'Conditioning — recovery week',
      effect: 'Next match, fatigue bites lighter: the stamina drag on every action stat is cut 30–70%, scaled by your Conditioning head.',
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
      effect: 'One extra Scout action on the recruit board this week (3 → 4). Your Scouting head also scales how tightly every scout narrows a prospect’s band.',
      termId: 'dept.scouting',
    },
    {
      key: 'culture',
      label: 'Culture — locker-room week',
      effect: 'Courtship lands warmer this week: Contact and Visit gains are 15–40% stronger, scaled by your Culture head.',
      termId: 'dept.culture',
    },
  ];
  const currentFocus = String(plan.department_orders?.focus_department ?? 'tactics');

  return (
    <Dialog
      labelledBy="program-settings-title"
      label="Staff Focus"
      onClose={onClose}
      panelClassName={styles.settingsPanel}
      panelStyle={{ width: 'min(92vw, 34rem)', maxHeight: '88vh', overflowY: 'auto' }}
    >
        <div className={styles.settingsHead}>
          <div>
            <p className={styles.kicker}>Program Settings</p>
            <h2 id="program-settings-title" className={styles.heading}>Staff Focus</h2>
            <p className={styles.note}>
              Your staff concentrates on one room this week. Every option is a real,
              disclosed effect — pick where the week goes.
            </p>
          </div>
          <button
            aria-label="Close program settings"
            onClick={onClose}
            className={styles.settingsClose}
            type="button"
          >
            X
          </button>
        </div>
        <div role="radiogroup" aria-label="Weekly staff focus" className={styles.focusGroup}>
          {FOCUS_OPTIONS.map((option) => {
            const selected = currentFocus === option.key;
            return (
              <button
                key={option.key}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => onUpdate('focus_department', option.key)}
                className={`${styles.focusOption}${selected ? ` ${styles.focusOptionSelected}` : ''}`}
              >
                <span className={`${styles.focusOptionLabel}${selected ? ` ${styles.focusOptionLabelSelected}` : ''}`}>
                  <TermTip term={option.termId}>{option.label}</TermTip>
                </span>
                <p className={styles.focusOptionEffect}>
                  {option.effect}
                </p>
              </button>
            );
          })}
        </div>
        <p className={`${styles.note} ${styles.noteDim}`}>
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
    <div className={styles.tabs}>
      {tabs.map((tab) => (
        <button key={tab.id} className={`${styles.tab} ${active === tab.id ? styles.tabActive : ''}`} onClick={() => onSelect(tab.id)} type="button">
          {tab.label}
          {tab.count != null && <span className={styles.tabCount}>{tab.count}</span>}
        </button>
      ))}
      <span className={styles.tabsSpacer} />
      {/* V22 Phase 2: the club's one money number, always in view from the
          front office. Red + "hiring frozen" while negative. */}
      {typeof data.treasury_k === 'number' && (
        <span
          data-testid="treasury-chip"
          title={
            data.hiring_frozen
              ? 'Treasury is negative — staff hiring is frozen until the books recover.'
              : 'Club treasury — league payouts in, staff payroll out, settled each offseason.'
          }
          className={`${styles.treasuryChip} ${data.treasury_k < 0 ? styles.treasuryChipNegative : ''}`}
        >
          Treasury {formatK(data.treasury_k)}
          {data.hiring_frozen && <span>· hiring frozen</span>}
        </span>
      )}
      <button className={styles.btn} onClick={onOpenSettings} type="button">Program Settings</button>
      {/* Codex issue 5: the office works the UPCOMING week (its recruiting
          slots belong to it), which can read one ahead of the match banner —
          say "prepping" so the two labels stop looking contradictory. */}
      <span className={styles.tabsNote}>Front Office · prepping Week {String(data.week).padStart(2, '0')}</span>
    </div>
  );
}

// V19b: plain-language promise vocabulary (the old "Promise Lane" label
// failed owner comprehension — the term itself was the bug).
// Playtest 3 F-9: these cards are shown for UNSIGNED prospects, so the two
// roster-dependent promises must not say "this season" — they are graded
// after the prospect's first season on your roster. "We'll contend" is a
// team outcome and really does grade this season, signed or not.
const PROMISE_LABELS: Record<string, { label: string; meaning: string }> = {
  early_playing_time: {
    label: 'Early playing time',
    meaning: 'They appear in at least 6 matches in their first season on your roster.',
  },
  development_priority: {
    label: 'Development priority',
    meaning: 'In their first season on your roster, you run a focused dev plan at least 3 weeks and keep them rostered.',
  },
  contender_path: {
    label: "We'll contend",
    meaning: 'The club reaches the playoffs this season — graded whether or not they sign.',
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
    <div className={styles.promisesPanel} data-testid="promises-panel">
      <div className={styles.promisesHead}>
        <span className={styles.kicker}>
          <TermTip term="recruit.promise">Promises</TermTip>
          <span className={styles.promisesCount}>
            {open.length}/{maxActive} open
          </span>
        </span>
        <span className={styles.promisesHelp}>
          Checked at season&apos;s end — kept promises build credibility, broken ones cost more.
        </span>
      </div>
      {open.length === 0 && resolved.length === 0 ? (
        <p className={styles.note}>
          No promises yet. Use a prospect card&apos;s Promise action to commit to something
          real — playing time, development, or contention.
        </p>
      ) : (
        <div className={styles.promisesList}>
          {open.map((p) => (
            <div key={`open-${p.player_id}`} className={styles.promiseRow}>
              <span className={`${styles.chip} ${styles.chipOk}`}>OPEN</span>
              <span className={styles.promiseName}>
                {p.player_name ?? nameById.get(p.player_id) ?? p.player_id}: {PROMISE_LABELS[p.promise_type]?.label ?? p.promise_type}
              </span>
              <span className={styles.promiseMeaning}>
                — {PROMISE_LABELS[p.promise_type]?.meaning ?? ''}
              </span>
            </div>
          ))}
          {resolved.map((p) => (
            <div key={`done-${p.player_id}-${p.result_season_id}`} className={styles.promiseRow}>
              {/* 'void' = the target signed elsewhere / never joined — not the
                  manager's failure, no credibility effect (Codex issue 13). */}
              <span className={`${styles.chip} ${p.status === 'fulfilled' ? styles.chipOk : p.status === 'void' ? styles.chipNeutral : styles.chipBroken}`}>
                {p.status === 'fulfilled' ? 'KEPT' : p.status === 'void' ? 'VOIDED' : 'BROKEN'}
              </span>
              <span className={styles.promiseName}>
                {p.player_name ?? nameById.get(p.player_id) ?? p.player_id}: {PROMISE_LABELS[p.promise_type]?.label ?? p.promise_type}
              </span>
              <span className={styles.promiseMeaning}>— {p.evidence}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SlotMeter({ slots }: { slots: DynastyOfficeResponse['recruiting']['budget'] }) {
  const items = [
    { key: 'scout', label: 'Scout', help: 'Verify prospect tiers.' },
    { key: 'contact', label: 'Contact', help: 'Letters and calls. Low-cost touches.' },
    { key: 'visit', label: 'Visit', help: 'Highest-commitment signal this week.' },
  ] as const;

  return (
    <div className={styles.slots}>
      <div className={styles.panelHead}>
        <span className={styles.kicker}>Weekly Recruiting</span>
        <h3 className={styles.subheading}>Action Slots</h3>
        <p className={styles.note}>
          Each slot is one action you can take this week. Remaining slots reset next week.
        </p>
      </div>
      <div className={styles.slotBody}>
        {items.map((item) => {
          const [used, total] = slots[item.key];
          return (
            <div key={item.key} className={styles.slot}>
              <div className={styles.slotHead}>
                <span className={styles.slotLbl}>{item.label}</span>
                <span className={styles.slotCount}><b>{Math.max(0, total - used)}</b> / {total}</span>
              </div>
              <div className={styles.slotPips}>
                {Array.from({ length: total }).map((_, index) => (
                  <span key={`${item.key}-${index}`} className={`${styles.slotPip} ${index < used ? styles.slotPipUsed : ''}`} />
                ))}
              </div>
              <span className={styles.slotHelp}>
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
      <div className={styles.staff}>
        <div className={styles.panelHead}>
          <span className={styles.kicker}>Staff Room</span>
          <h3 className={styles.subheading}>Department Heads</h3>
        </div>
        <EmptyState
          title="No department heads hired"
          body="Use the Staff tab to browse pipeline candidates and hire your first department heads."
        />
      </div>
    );
  }
  return (
    <div className={styles.staff}>
      <div className={styles.panelHead}>
        <span className={styles.kicker}>Staff Room</span>
        <h3 className={styles.subheading}>Department Heads</h3>
      </div>
      <div className={styles.staffList}>
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
            <div key={`${member.department}-${member.name}`} className={styles.staffRow}>
              <div className={styles.staffId}>
                {hasTerm ? (
                  <TermTip term={termId as import('../legibility').TermId}>
                    <span className={styles.dept}>{deptLabel}</span>
                  </TermTip>
                ) : (
                  <span className={styles.dept}>{deptLabel}</span>
                )}
                <span className={styles.staffName}>{member.name}</span>
                <span className={styles.voice}>"{member.voice || member.effect_summary}"</span>
              </div>
              <div className={styles.staffRating}>
                <span className={styles.ratingNum}>{member.rating_primary}</span>
                <span className={styles.ratingLbl}>OVR</span>
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
      className={styles.context}
      role="group"
      aria-label="This week's recruiting summary"
    >
      <div className={styles.contextCell}>
        <span className={styles.cellLbl}>Board</span>
        <div className={styles.cellVal}><b>{prospectCount}</b> <span>prospects</span></div>
        <span className={`${styles.cellTrend} ${styles.cellTrendDim}`}>Sorted by program fit</span>
      </div>
      <div className={styles.contextCellWide}>
        <span className={styles.cellLbl}>Reach Remaining</span>
        <div className={styles.cellVal}><b>{scoutRemaining + contactRemaining}</b> <span>scout + contact</span></div>
        <span className={`${styles.cellTrend} ${styles.cellTrendDim}`}>{scoutRemaining} scout · {contactRemaining} contact</span>
      </div>
      <div className={styles.contextCell}>
        <span className={styles.cellLbl}>Visit Slots</span>
        <div className={styles.cellVal}><b>{visitRemaining}</b> <span>remaining</span></div>
        <span className={`${styles.cellTrend} ${visitRemaining > 0 ? styles.cellTrendDim : styles.cellTrendWarn}`}>
          {visitRemaining > 0 ? 'Use on best-fit closes' : 'Budget exhausted this week'}
        </span>
      </div>
    </div>
  );
}

// V24 Phase 6: the money-gated Scouting Network. Spending treasury raises your
// reach so more of the class renders a full sheet instead of a bare name.
function ScoutingNetworkPanel({
  network,
  reload,
}: {
  network: NonNullable<DynastyOfficeResponse['recruiting']['scouting_network']>;
  reload: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reachByLevel: Record<number, string> = {
    1: 'Home + neighbor districts (local kids only)',
    2: 'Regional reach — every district + regional prospects',
    3: 'National reach — the entire class',
  };
  const upgrade = () => {
    setBusy(true);
    setError(null);
    dynastyApi
      .upgradeNetwork()
      .then(() => reload())
      .catch((e) => setError(e instanceof Error ? e.message : 'Upgrade failed.'))
      .finally(() => setBusy(false));
  };
  return (
    <div className={styles.panel} aria-label="Scouting Network">
      <div className={styles.panelHead}>
        <span className={styles.kicker}>Scouting Network</span>
        <h4 className={styles.subheading}>
          Level {network.level}{' '}
          <span className={styles.noteDim}>· {reachByLevel[network.level]}</span>
        </h4>
      </div>
      {network.maxed ? (
        <p className={styles.note}>
          L3 — full national reach. Every prospect's sheet is open to you.
        </p>
      ) : (
        <div className={styles.networkActions}>
          <span className={styles.note}>
            Raise to L{network.next_level} to open more sheets across the class.
          </span>
          <button
            type="button"
            className={styles.btnPrimary + ' ' + styles.btn}
            disabled={busy || !network.can_afford}
            onClick={upgrade}
            title={
              network.can_afford
                ? `Spend ${formatK(network.upgrade_cost_k ?? 0)} from your treasury`
                : `Treasury ${formatK(network.treasury_k)} — not enough for this upgrade`
            }
          >
            {busy ? 'Upgrading…' : `Upgrade to L${network.next_level} — ${formatK(network.upgrade_cost_k ?? 0)}`}
          </button>
          {!network.can_afford && (
            <span className={`${styles.note} ${styles.danger}`}>
              Treasury {formatK(network.treasury_k)} — save up first.
            </span>
          )}
        </div>
      )}
      {error && (
        <p className={`${styles.note} ${styles.danger}`}>{error}</p>
      )}
    </div>
  );
}

function FacilitiesUpgradePanel({
  facilities,
  reload,
}: {
  facilities: NonNullable<DynastyOfficeResponse['facilities']>;
  reload: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const build = (facilityType: string) => {
    setBusy(facilityType);
    setError(null);
    dynastyApi
      .upgradeFacility(facilityType)
      .then(() => reload())
      .catch((e) => setError(e instanceof Error ? e.message : 'Build failed.'))
      .finally(() => setBusy(null));
  };
  return (
    <div className={styles.panel} aria-label="Facilities">
      <div className={styles.panelHead}>
        <span className={styles.kicker}>Facilities</span>
        <h4 className={styles.subheading}>Build your program — Training Hall develops, Stadium &amp; Merch draw fan income.</h4>
      </div>
      <div className={styles.facilityList}>
        {facilities.catalog.map((f) => (
          <div
            key={f.facility_type}
            className={`${styles.facilityRow} ${f.owned ? styles.facilityRowOwned : ''}`}
          >
            <span className={styles.facilityName}>{f.display_name}</span>
            <span className={styles.facilityCat}>{f.category}</span>
            <span style={{ marginLeft: 'auto' }}>
              {f.owned ? (
                <span className={styles.facilityBuilt}>Built ✓</span>
              ) : (
                <button
                  type="button"
                  className={styles.btn}
                  disabled={busy !== null || !f.can_afford}
                  onClick={() => build(f.facility_type)}
                  title={
                    f.can_afford
                      ? `Spend ${formatK(f.treasury_cost_k)} from your treasury`
                      : `Treasury ${formatK(facilities.treasury_k)} — not enough`
                  }
                >
                  {busy === f.facility_type ? 'Building…' : `Build — ${formatK(f.treasury_cost_k)}`}
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
      {error && (
        <p className={`${styles.note} ${styles.danger}`}>{error}</p>
      )}
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
      // V24 Phase 6: name-only cards have no fit score; they only show under "all".
      if (prospect.fully_visible === false) return filter === 'all';
      const fit = prospect.fit_score ?? 0;
      if (filter === 'strong') return fit >= 80;
      if (filter === 'fair') return fit >= 65 && fit < 80;
      if (filter === 'risk') return fit < 65;
      return true;
    });
    return [...base].sort((a, b) => {
      // Name-only cards always sink to the bottom regardless of sort key.
      const av0 = a.fully_visible === false ? 1 : 0;
      const bv0 = b.fully_visible === false ? 1 : 0;
      if (av0 !== bv0) return av0 - bv0;
      let av: number;
      let bv: number;
      if (sort === 'interest') {
        av = a.interest ?? 0;
        bv = b.interest ?? 0;
      } else if (sort === 'pipeline') {
        av = a.pipeline_tier ?? 1;
        bv = b.pipeline_tier ?? 1;
      } else {
        av = a.fit_score ?? 0;
        bv = b.fit_score ?? 0;
      }
      return sortDir === 'desc' ? bv - av : av - bv;
    });
  }, [prospects, filter, sort, sortDir]);

  return (
    <div className={styles.panel}>
      <div className={styles.boardHead}>
        <div>
          <span className={styles.kicker}>Recruit Board</span>
          <h3 className={styles.subheading}>This Week's Prospects</h3>
        </div>
        <div className={styles.boardFilters}>
          <button className={`${styles.filter} ${filter === 'all' ? styles.filterActive : ''}`} onClick={() => setFilter('all')} type="button">
            All <span className={styles.filterCount}>{prospects.length}</span>
          </button>
          <button className={`${styles.filter} ${filter === 'strong' ? styles.filterActive : ''}`} onClick={() => setFilter('strong')} type="button">
            Strong Fit <span className={styles.filterCount}>{prospects.filter((prospect) => prospect.fit_score >= 80).length}</span>
          </button>
          <button className={`${styles.filter} ${filter === 'fair' ? styles.filterActive : ''}`} onClick={() => setFilter('fair')} type="button">
            Fair Fit <span className={styles.filterCount}>{prospects.filter((prospect) => prospect.fit_score >= 65 && prospect.fit_score < 80).length}</span>
          </button>
          <button className={`${styles.filter} ${filter === 'risk' ? styles.filterActive : ''}`} onClick={() => setFilter('risk')} type="button">
            At Risk <span className={styles.filterCount}>{prospects.filter((prospect) => prospect.fully_visible !== false && (prospect.fit_score ?? 0) < 65).length}</span>
          </button>
          <span className={styles.boardSep} />
          <div
            role="group"
            aria-label="Sort prospects"
            className={styles.sortGroup}
          >
            <span className={styles.sortLbl}>
              Sort
            </span>
            {(['fit', 'interest', 'pipeline'] as const).map((key) => (
              <button
                key={key}
                className={`${styles.filter} ${sort === key ? styles.filterActive : ''}`}
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
                  <span aria-hidden="true">
                    {sortDir === 'desc' ? ' ↓' : ' ↑'}
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
          aria-label="Card color key: green = Strong Fit, amber = Fair Fit, dim = At Risk"
          className={styles.legend}
        >
          <span className={styles.legendStrong}>● Strong Fit ≥80</span>
          <span className={styles.legendFair}>● Fair Fit 65–79</span>
          <span className={styles.legendRisk}>● At Risk &lt;65</span>
          <span>Scout narrows the OVR range · Contact and visits build interest</span>
        </div>
      )}
      <div className={styles.boardGrid}>
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
  reload,
}: {
  data: DynastyOfficeResponse;
  onStaffUpdate: (next: DynastyOfficeResponse) => void;
  reload: () => void;
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
    <div className={styles.tabContent}>
      <div className={styles.glance}>
        <div className={styles.glanceCell}>
          <span className={styles.cellLbl}>Department Heads</span>
          <span className={styles.cellVal}>{staff.length} <span>/ 6</span></span>
          <span className={styles.cellTrend}>{vacancies.length} vacancies open</span>
        </div>
        <div className={styles.glanceCell}>
          <span className={styles.cellLbl}>Avg Rating</span>
          <span className={styles.cellVal}>{avgRating}</span>
          <span className={`${styles.cellTrend} ${styles.cellTrendOk}`}>Live staff average</span>
        </div>
        <div className={styles.glanceCell}>
          <span className={styles.cellLbl}>Facilities</span>
          <span className={styles.cellVal}>{data.staff_market.active_facilities.length}</span>
          <span className={styles.cellTrend}>{data.staff_market.active_facilities.length > 0 ? data.staff_market.active_facilities.join(' · ') : 'No facility upgrades tracked'}</span>
        </div>
        <div className={styles.glanceCell}>
          <span className={styles.cellLbl}>Pipeline</span>
          <span className={styles.cellVal}>{candidates.length}</span>
          <span className={styles.cellTrend}>{data.staff_market.recent_actions.length} recent staff moves</span>
        </div>
      </div>

      {data.facilities && <FacilitiesUpgradePanel facilities={data.facilities} reload={reload} />}

      <div className={styles.staffGrid}>
        {staff.map((member) => (
          <div key={`${member.department}-${member.name}`} className={styles.staffCard}>
            <div className={styles.staffCardHead}>
              <div>
                {(['staff.training', 'staff.tactics', 'staff.conditioning',
                   'staff.medical', 'staff.scouting', 'staff.culture'] as const).includes(
                    `staff.${member.department}` as 'staff.training'
                  ) ? (
                  <TermTip term={`staff.${member.department}` as import('../legibility').TermId}>
                    <span className={styles.kicker}>{titleizeDepartment(member.department)}</span>
                  </TermTip>
                ) : (
                  <span className={styles.kicker}>{titleizeDepartment(member.department)}</span>
                )}
                <p className={styles.staffName}>{member.name}</p>
              </div>
              <div className={styles.rating}>
                <span className={styles.ratingNum}>{member.rating_primary}</span>
                <span className={styles.ratingLbl}>OVR</span>
              </div>
            </div>
            <p className={styles.voice}>"{member.voice || member.effect_summary}"</p>
            <div className={styles.specs}>
              <span className={styles.chip}>{titleizeDepartment(member.department)}</span>
              <span className={styles.chip}>SECONDARY {member.rating_secondary}</span>
            </div>
            <dl className={styles.meta}>
              <div><dt>Primary</dt><dd>{member.rating_primary}</dd></div>
              <div><dt>Secondary</dt><dd>{member.rating_secondary}</dd></div>
              {/* V22 Phase 3: every head's annual cost on the card. */}
              {typeof member.salary_k === 'number' && (
                <div><dt>Salary</dt><dd>{formatK(member.salary_k)}/yr</dd></div>
              )}
              <div><dt>Facility Sync</dt><dd>{data.staff_market.active_facilities.length > 0 ? data.staff_market.active_facilities[0] : 'None tracked'}</dd></div>
            </dl>
            <div className={styles.impact}>
              <span className={styles.impactLbl}>
                Wired Effect
              </span>
              <span className={styles.impactVal}>
                {/* V22 Phase 4: every head shows the CONCRETE number their
                    rating drives, from the same formulas the engine runs. */}
                {member.effect_detail ?? member.effect_summary}
              </span>
              {member.department === 'training' && member.training_modifier_pct !== undefined && (
                <div>
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

      <div className={styles.gridRow}>
        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <span className={styles.kicker}>Vacancies</span>
            <h3 className={styles.subheading}>Open Roles</h3>
          </div>
          <div>
            {vacancies.length > 0 ? vacancies.map((vacancy) => (
              <div key={vacancy.department} className={styles.vacRow}>
                <div className={styles.vacId}>
                  <span className={styles.dept}>{titleizeDepartment(vacancy.department)}</span>
                  <span className={styles.note}>{vacancy.note}</span>
                </div>
                <div className={styles.vacAction}>
                  <span className={`${styles.priorityTag} ${vacancy.priority === 'high' ? styles.priorityHigh : ''}`}>{vacancy.priority}</span>
                  <button className={styles.btn} type="button" disabled>Pipeline Only</button>
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

        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <span className={styles.kicker}>Pipeline</span>
            <h3 className={styles.subheading}>Candidates</h3>
          </div>
          <p className={styles.note}>
            Candidates are generated each offseason. Hiring immediately replaces the current department head.
          </p>
          <div>
            {candidates.length > 0 ? candidates.map((candidate) => {
              const isHiring = hiringCandidateId === candidate.candidate_id;
              const normalizedStage = isHiring ? 'hiring' : 'available';
              return (
                <div key={candidate.candidate_id} className={styles.pipeRow}>
                  <div className={styles.pipeId}>
                    <span className={styles.staffName}>{candidate.name}</span>
                    {(['staff.training', 'staff.tactics', 'staff.conditioning',
                       'staff.medical', 'staff.scouting', 'staff.culture'] as const).includes(
                        `staff.${candidate.department}` as 'staff.training'
                      ) ? (
                      <TermTip term={`staff.${candidate.department}` as import('../legibility').TermId}>
                        <span className={styles.dept}>{titleizeDepartment(candidate.department)}</span>
                      </TermTip>
                    ) : (
                      <span className={styles.dept}>{titleizeDepartment(candidate.department)}</span>
                    )}
                    <span className={styles.note}>{candidate.effect_lanes[0] || candidate.voice}</span>
                  </div>
                  <div className={styles.pipeMeta}>
                    <span className={styles.ratingNum}>{candidate.rating_primary}<small> OVR</small></span>
                    {/* V22 Phase 3: the hire's payroll consequence up front. */}
                    {typeof candidate.salary_k === 'number' && (
                      <span className={styles.salary}>
                        {formatK(candidate.salary_k)}/yr
                        {typeof candidate.salary_delta_k === 'number' && candidate.salary_delta_k !== 0 && (
                          <span className={candidate.salary_delta_k > 0 ? styles.salaryUp : styles.salaryDown}>
                            {' '}({candidate.salary_delta_k > 0 ? '+' : ''}{candidate.salary_delta_k}k)
                          </span>
                        )}
                      </span>
                    )}
                    <span className={styles.stage}>{normalizedStage.replace('-', ' ')}</span>
                    <button
                      className={styles.btn}
                      type="button"
                      disabled={hiringCandidateId !== null || data.hiring_frozen === true}
                      title={
                        data.hiring_frozen
                          ? 'Treasury is negative — hiring is frozen until the books recover.'
                          : undefined
                      }
                      onClick={() => handleInterview(candidate.candidate_id)}
                    >
                      {isHiring ? 'Hiring...' : data.hiring_frozen ? 'Frozen' : 'Hire'}
                    </button>
                  </div>
                </div>
              );
            }) : (
              <div className={styles.note}>
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
    () => [...(data?.recruiting.prospects ?? [])].sort((left, right) => {
      // V24 Phase 6: name-only cards (beyond your Scouting Network) sink to the
      // bottom; their sheet fields are null so guard the fit comparison.
      const lv = left.fully_visible === false ? 1 : 0;
      const rv = right.fully_visible === false ? 1 : 0;
      if (lv !== rv) return lv - rv;
      return (right.fit_score ?? 0) - (left.fit_score ?? 0) || left.name.localeCompare(right.name);
    }),
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
      <div className={`max-content ${styles.shell}`} data-screen-label="03 Dynasty">
        <DoTabs active={activeSubTab} data={data} onSelect={setActiveSubTab} onOpenSettings={() => setShowSettings(true)} />

        {activeSubTab === 'history' && (
          <HistorySubTab
            clubId={selectedHistoryClubId ?? data.player_club_id}
            isSelf={(selectedHistoryClubId ?? data.player_club_id) === data.player_club_id}
          />
        )}

        {activeSubTab === 'recruit' && (
          <div className={styles.tabContent}>
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
            <div className={styles.gridRow}>
              <SlotMeter slots={data.recruiting.budget} />
              <StaffBrief staff={data.staff_market.current_staff} />
            </div>
            {data.recruiting.scouting_network && (
              <ScoutingNetworkPanel network={data.recruiting.scouting_network} reload={reload} />
            )}
            <RecruitBoard budget={data.recruiting.budget} prospects={sortedProspects} reload={reload} />
          </div>
        )}

        {activeSubTab === 'staff' && <StaffTab data={data} onStaffUpdate={setData} reload={reload} />}
      </div>

      {showSettings && planContext && (
        <SettingsModal plan={planContext.plan} onUpdate={updateDepartmentOrder} onClose={() => setShowSettings(false)} />
      )}
    </>
  );
}
