const { useState: useStateDT } = React;

const HISTORY_ENTRIES = [
  { wk: 4, type: 'milestone', kicker: 'STANDINGS', title: 'Climbed to #4 in the table', body: 'First time in the playoff slot this season. Cushion is 3 pts.', tag: 'CURRENT WEEK' },
  { wk: 4, type: 'recruit', kicker: 'RECRUITING', title: 'Avery Helix interest +1', body: 'Catch-heavy attrition win moved fit from 76 to 82.', tag: 'STRONG FIT' },
  { wk: 3, type: 'match', kicker: 'W03 RESULT', title: 'Solstice 6-2 Bishop Bench', body: 'Mika Thorn anchored backline.', tag: 'WIN' },
  { wk: 3, type: 'recruit', kicker: 'RECRUITING', title: 'Sela Brooks visited Foxbridge', body: 'Top-district recruit toured a rival program.', tag: 'AT RISK' },
  { wk: 2, type: 'staff', kicker: 'STAFF', title: 'Yuki Tan extended (2 seasons)', body: 'Scouting director re-signed at 80 OVR.', tag: 'SIGNED' },
  { wk: 2, type: 'match', kicker: 'W02 RESULT', title: 'Glen Lake 4-3 Solstice', body: 'Lost on a catch-reversal in the final volley.', tag: 'LOSS' },
  { wk: 2, type: 'milestone', kicker: 'CREDIBILITY', title: 'Reached Tier C (61 / 100)', body: 'Threshold cleared after two clean weeks.', tag: 'TIER UP' },
  { wk: 1, type: 'match', kicker: 'W01 RESULT', title: 'Solstice 7-4 Cedar Crest Reads', body: 'Opener won on power-arm aggro.', tag: 'WIN' },
  { wk: 1, type: 'recruit', kicker: 'RECRUITING', title: 'Scouted 3 prospects to VERIFIED', body: 'Scouting credibility +4.', tag: 'OPEN' },
  { wk: 0, type: 'milestone', kicker: 'PROGRAM', title: 'Season 2026 program objective set', body: 'Establish a top-4 finish and target Tier B class.', tag: 'PRE-SEASON' },
];

const HISTORY_META = {
  match: { lbl: 'Match', tone: 'rose' },
  recruit: { lbl: 'Recruit', tone: 'emerald' },
  staff: { lbl: 'Staff', tone: 'violet' },
  milestone: { lbl: 'Milestone', tone: 'cyan' },
};

const HistoryTab = () => {
  const [filter, setFilter] = useStateDT('all');
  const visible = filter === 'all' ? HISTORY_ENTRIES : HISTORY_ENTRIES.filter(e => e.type === filter);

  return (
    <div className="do-tab-content">
      <div className="do-glance">
        <div className="do-glance-cell">
          <span className="dm-kicker">Through</span>
          <div className="val mono">W03</div>
          <span className="sub">4 weeks played</span>
        </div>
        <div className="do-glance-cell">
          <span className="dm-kicker">Record</span>
          <div className="val mono">3-1-0</div>
          <span className="sub ok">+4 survivor diff</span>
        </div>
        <div className="do-glance-cell">
          <span className="dm-kicker">Position</span>
          <div className="val">#4</div>
          <span className="sub ok">Up from #5</span>
        </div>
        <div className="do-glance-cell">
          <span className="dm-kicker">Credibility</span>
          <div className="val">Tier C</div>
          <span className="sub ok">61 / 100</span>
        </div>
        <div className="do-glance-cell">
          <span className="dm-kicker">Recruits Touched</span>
          <div className="val mono">12</div>
          <span className="sub">5 scouted / 7 contacted</span>
        </div>
      </div>

      <div className="do-filter-strip">
        <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>All <span>{HISTORY_ENTRIES.length}</span></button>
        <button className={filter === 'match' ? 'active' : ''} onClick={() => setFilter('match')}>Matches <span>{HISTORY_ENTRIES.filter(e => e.type === 'match').length}</span></button>
        <button className={filter === 'recruit' ? 'active' : ''} onClick={() => setFilter('recruit')}>Recruiting <span>{HISTORY_ENTRIES.filter(e => e.type === 'recruit').length}</span></button>
        <button className={filter === 'staff' ? 'active' : ''} onClick={() => setFilter('staff')}>Staff <span>{HISTORY_ENTRIES.filter(e => e.type === 'staff').length}</span></button>
        <button className={filter === 'milestone' ? 'active' : ''} onClick={() => setFilter('milestone')}>Milestones <span>{HISTORY_ENTRIES.filter(e => e.type === 'milestone').length}</span></button>
      </div>

      <div className="do-timeline">
        <div className="do-timeline-rail" />
        {visible.map((e, i) => {
          const meta = HISTORY_META[e.type];
          return (
            <div key={i} className={`do-timeline-row tone-${meta.tone}`}>
              <div className="do-timeline-wk">
                W{e.wk.toString().padStart(2, '0')}
                <span className={`do-timeline-dot tone-${meta.tone}`} />
              </div>
              <div className="do-timeline-body">
                <div className="header">
                  <span className={`dm-badge dm-badge-${meta.tone}`}>{meta.lbl.toUpperCase()}</span>
                  <span className="kicker">{e.kicker}</span>
                  <span className="tag-pill">{e.tag}</span>
                </div>
                <h4>{e.title}</h4>
                <p>{e.body}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const STAFF = [
  { dept: 'Head Coach', name: 'Reyna Calder', rating: 72, voice: 'Clipboard analyst.', spec: ['Defensive Anchor', 'Catch-Heavy'], contract: '2y to 2027', salary: '$120k', tenure: '12w', focus: 'Defense', impact: '+3 catches/match' },
  { dept: 'Recruiting', name: 'Marv Booker', rating: 68, voice: 'Old-school regional grinder.', spec: ['Regional', 'Visit Specialist'], contract: '1y to 2026', salary: '$78k', tenure: '4w', focus: 'Regional', impact: '4 verified prospects' },
  { dept: 'Scouting', name: 'Yuki Tan', rating: 80, voice: 'Numbers-first decision feel.', spec: ['Numbers-First', 'Tier Verifier'], contract: '3y to 2028', salary: '$96k', tenure: '12w', focus: 'Analytics', impact: '7 tiers verified' },
  { dept: 'Conditioning', name: 'Hal Greer', rating: 65, voice: 'Stamina-and-survive philosophy.', spec: ['Stamina-First'], contract: '1y to 2026', salary: '$54k', tenure: '4w', focus: 'Endurance', impact: '+2% stamina retention' }
];

const VACANCIES = [
  { dept: 'Catching Coach', prio: 'High', note: 'Critical for the catch-heavy attrition profile.' },
  { dept: 'Data Analyst', prio: 'Medium', note: 'Pre-match RNG verification is manual.' }
];

const PIPELINE = [
  { name: 'Brenna Holt', stage: 'Interview', dept: 'Catching Coach', rating: 71, note: 'Catch-rate +18% record at Bishop Bench.' },
  { name: 'Owen Maes', stage: 'Background', dept: 'Catching Coach', rating: 64, note: 'Cheap. Limited recent track record.' },
  { name: 'Iris Sundar', stage: 'Offer Sent', dept: 'Data Analyst', rating: 76, note: 'Worked under Yuki Tan.' }
];

const StaffTab = () => (
  <div className="do-tab-content">
    <div className="do-glance">
      <div className="do-glance-cell">
        <span className="dm-kicker">Department Heads</span>
        <div className="val mono">4 / 6</div>
        <span className="sub">2 vacancies open</span>
      </div>
      <div className="do-glance-cell">
        <span className="dm-kicker">Avg Rating</span>
        <div className="val mono">71</div>
        <span className="sub ok">Up 4 from preseason</span>
      </div>
      <div className="do-glance-cell">
        <span className="dm-kicker">Weekly Payroll</span>
        <div className="val mono">$8.6k</div>
        <span className="sub">Within budget ceiling</span>
      </div>
      <div className="do-glance-cell">
        <span className="dm-kicker">Pipeline</span>
        <div className="val mono">3</div>
        <span className="sub">1 offer - 1 background</span>
      </div>
    </div>

    <div className="do-staff-grid">
      {STAFF.map((s, i) => (
        <div key={i} className="do-staff-card">
          <div className="header">
            <div>
              <span className="dm-kicker cyan">{s.dept}</span>
              <h4>{s.name}</h4>
            </div>
            <div className="rating">
              <span className="mono num">{s.rating}</span> <span className="lbl">OVR</span>
            </div>
          </div>
          <p className="voice">"{s.voice}"</p>
          <div className="specs">
            {s.spec.map(sp => <span key={sp} className="dm-badge dm-badge-cyan">{sp}</span>)}
          </div>
          <dl className="meta">
            <div><dt>Contract</dt><dd>{s.contract}</dd></div>
            <div><dt>Salary</dt><dd>{s.salary}</dd></div>
            <div><dt>Tenure</dt><dd>{s.tenure}</dd></div>
            <div><dt>Focus</dt><dd>{s.focus}</dd></div>
          </dl>
          <div className="impact">
            <span className="dm-kicker cyan">Season Impact</span>
            <span>{s.impact}</span>
          </div>
        </div>
      ))}
    </div>

    <div className="do-hiring-row">
      <div className="do-panel">
        <div className="do-panel-head">
          <span className="dm-kicker">Vacancies</span>
          <h3>Open Roles</h3>
        </div>
        <div className="do-vac-list">
          {VACANCIES.map((v, i) => (
            <div key={i} className={`do-vac-row prio-${v.prio.toLowerCase()}`}>
              <div>
                <span className="dept">{v.dept}</span>
                <p>{v.note}</p>
              </div>
              <button className="do-btn orange">Post Search</button>
            </div>
          ))}
        </div>
      </div>
      <div className="do-panel">
        <div className="do-panel-head">
          <span className="dm-kicker">Pipeline</span>
          <h3>Candidates</h3>
        </div>
        <div className="do-pipe-list">
          {PIPELINE.map((p, i) => (
            <div key={i} className="do-pipe-row">
              <div>
                <span className="name">{p.name}</span>
                <span className="meta">{p.dept} · {p.note}</span>
              </div>
              <div className="status">
                <span className="mono rating">{p.rating} OVR</span>
                <span className={`dm-badge stage-${p.stage.replace(' ', '-').toLowerCase()}`}>{p.stage.toUpperCase()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const BUDGET = [
  { key: 'Staff Salaries', tone: 'cyan', alloc: 220, spent: 73, cap: 240, note: 'Coaches and analysts.' },
  { key: 'Recruiting', tone: 'emerald', alloc: 90, spent: 28, cap: 120, note: 'Travel and visits.' },
  { key: 'Scouting', tone: 'violet', alloc: 60, spent: 21, cap: 80, note: 'Verifications.' },
  { key: 'Facilities', tone: 'amber', alloc: 45, spent: 14, cap: 50, note: 'Court maintenance.' },
  { key: 'Player Stipends', tone: 'rose', alloc: 110, spent: 36, cap: 110, note: 'Per-player weekly.' }
];

const TX = [
  { wk: 'W04', type: 'Recruiting', who: 'Avery Helix', amt: -2.4, note: 'Booked visit' },
  { wk: 'W04', type: 'Stipend', who: 'Roster - 11p', amt: -9.0, note: 'Payroll' },
  { wk: 'W03', type: 'Scouting', who: 'Theo Park', amt: -1.8, note: 'KNOWN to VERIFIED' },
  { wk: 'W03', type: 'Facilities', who: 'Court re-line', amt: -3.5, note: 'Quarterly' },
  { wk: 'W02', type: 'Staff', who: 'Yuki Tan', amt: -2.4, note: 'Contract draw' },
  { wk: 'W02', type: 'Sponsor', who: 'Westside Coffee', amt: 12.0, note: 'Sleeve patch' }
];

const BudgetTab = () => (
  <div className="do-tab-content">
    <div className="do-glance">
      <div className="do-glance-cell hero">
        <span className="dm-kicker">Season Budget</span>
        <div className="val mono">$525k</div>
        <div className="do-budget-bar">
          <div className="fill" style={{ width: '33%' }} />
        </div>
        <div className="do-budget-meta">
          <span>$172k spent · 33%</span>
          <span className="dim">$353k remaining</span>
        </div>
      </div>
      <div className="do-glance-cell">
        <span className="dm-kicker">Weekly Burn</span>
        <div className="val mono">$43.0k</div>
        <span className="sub">Avg through W03</span>
      </div>
      <div className="do-glance-cell">
        <span className="dm-kicker">Runway</span>
        <div className="val mono">8w</div>
        <span className="sub ok">Covers season</span>
      </div>
      <div className="do-glance-cell">
        <span className="dm-kicker">Sponsorship YTD</span>
        <div className="val mono ok">+$12k</div>
        <span className="sub">Westside Coffee</span>
      </div>
    </div>

    <div className="do-panel">
      <div className="do-panel-head">
        <span className="dm-kicker">Allocation Ledger</span>
        <h3>Category Spend</h3>
      </div>
      <table className="do-budget-table">
        <thead>
          <tr>
            <th>Category</th>
            <th className="tc">Allocated</th>
            <th className="tc">Spent</th>
            <th>Utilization</th>
            <th className="tc">Remaining</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {BUDGET.map(b => (
            <tr key={b.key}>
              <td><span className={`pip tone-${b.tone}`} /> {b.key}</td>
              <td className="tc mono">${b.alloc}k</td>
              <td className="tc mono">${b.spent}k</td>
              <td>
                <div className="do-util-bar">
                  <div className={`fill tone-${b.tone}`} style={{ width: `${(b.spent/b.alloc)*100}%` }} />
                  <div className="cap-mark" style={{ left: `${(b.cap/b.alloc)*100}%` }} />
                </div>
                <span className="pct mono">{Math.round((b.spent/b.alloc)*100)}%</span>
              </td>
              <td className="tc mono">${b.alloc - b.spent}k</td>
              <td className="note">{b.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    <div className="do-panel">
      <div className="do-panel-head">
        <span className="dm-kicker">Ledger</span>
        <h3>Recent Transactions</h3>
      </div>
      <div className="do-tx-list">
        {TX.map((t, i) => (
          <div key={i} className={`do-tx-row ${t.amt > 0 ? 'credit' : 'debit'}`}>
            <span className="wk mono">{t.wk}</span>
            <span className="dm-badge dm-badge-slate">{t.type}</span>
            <div className="body">
              <span className="who">{t.who}</span>
              <span className="note">{t.note}</span>
            </div>
            <span className="amt mono">{t.amt > 0 ? '+' : '-'}${Math.abs(t.amt).toFixed(1)}k</span>
          </div>
        ))}
      </div>
    </div>
  </div>
);

Object.assign(window, { HistoryTab, StaffTab, BudgetTab });
