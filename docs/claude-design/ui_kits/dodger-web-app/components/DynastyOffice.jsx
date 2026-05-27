const { useState: useStateD } = React;

const archeBadgeRecruit = (a) => {
  if (a === 'Balanced') return <span className="dm-badge dm-badge-cyan">BALANCED</span>;
  if (a === 'Power')    return <span className="dm-badge dm-badge-orange">POWER</span>;
  if (a === 'Tactical') return <span className="dm-badge dm-badge-violet">TACTICAL</span>;
  return <span className="dm-badge">{a.toUpperCase()}</span>;
};

const DoTabs = ({ active, onSelect }) => {
  const tabs = [
    { id: 'recruit', label: 'Recruit', count: 6 },
    { id: 'history', label: 'History', count: 10 },
    { id: 'staff',   label: 'Staff',   count: 4 },
    { id: 'budget',  label: 'Budget',  count: null },
  ];
  return (
    <div className="do-tabs">
      {tabs.map(t => (
        <button key={t.id} className={`do-tab ${active === t.id ? 'active' : ''}`} onClick={() => onSelect(t.id)}>
          {t.label} {t.count != null && <span className="count mono">{t.count}</span>}
        </button>
      ))}
      <span className="spacer" />
      <span className="note mono">FRONT OFFICE - Week 04</span>
    </div>
  );
};

const CredibilityHero = ({ c }) => {
  const score = c.score;
  const progress = Math.min(100, ((score - 40) / (75 - 40)) * 100);
  return (
    <div className="do-cred-hero">
      <div className="do-cred-letter">
        <span className="tier">{c.tier}</span>
        <div className="halo" />
      </div>

      <div className="do-cred-main">
        <span className="dm-kicker">Program Credibility</span>
        <h2>Tier {c.tier} · Regional</h2>
        <p className="blurb">Mid-pack credibility. Quality recruits will visit but won't commit without a top-4 finish to point at.</p>
        
        <div className="do-cred-track-wrap">
          <div className="header">
            <span className="lbl dm-kicker">Toward Tier B</span>
            <span className="val mono">{score} <span className="dim">/ 75</span></span>
          </div>
          <div className="track">
            <div className="fill" style={{ width: `${progress}%` }}>
              <span className="marker" />
            </div>
            <span className="tick" style={{ left: '0%' }}>D</span>
            <span className="tick" style={{ left: '33%' }}>C</span>
            <span className="tick" style={{ left: '66%' }}>B</span>
            <span className="tick" style={{ left: '100%' }}>A</span>
          </div>
        </div>

        <div className="do-cred-evidence">
          {c.evidence.map((e, i) => (
            <div key={i} className="item">
              <span className="mono idx">0{i + 1}</span> {e}
            </div>
          ))}
        </div>
      </div>

      <div className="do-cred-side">
        <div className="tile">
          <span className="dm-kicker">Regional Rank</span>
          <div className="val mono">#7 <span className="sub">/ 24</span></div>
          <span className="trend ok">Up +2 since W01</span>
        </div>
        <div className="tile">
          <span className="dm-kicker">Visibility</span>
          <div className="val mono">0.61</div>
          <span className="trend dim">Steady - mid-pack</span>
        </div>
        <div className="tile warn">
          <span className="dm-kicker">Prestige</span>
          <div className="val mono">0.00</div>
          <span className="trend warn">No titles - build with W</span>
        </div>
      </div>
    </div>
  );
};

const SlotMeter = ({ slots }) => {
  const items = [
    { key: 'scout', lbl: 'Scout', tone: 'cyan', help: 'Verify prospect tiers.' },
    { key: 'contact', lbl: 'Contact', tone: 'amber', help: 'Letters and calls; cheap touch.' },
    { key: 'visit', lbl: 'Visit', tone: 'orange', help: 'Single-week tool. High signal.' }
  ];
  return (
    <div className="do-panel do-slots">
      <div className="do-panel-head">
        <span className="dm-kicker">Weekly Recruiting</span>
        <h3>Action Slots</h3>
      </div>
      <div className="do-slots-body">
        {items.map(it => {
          const [used, max] = slots[it.key];
          return (
            <div key={it.key} className={`do-slot tone-${it.tone}`}>
              <div className="header">
                <span className="lbl">{it.lbl}</span>
                <span className="count mono">{used} / {max}</span>
              </div>
              <div className="pips">
                {Array.from({ length: max }).map((_, i) => (
                  <span key={i} className={`pip ${i < used ? 'used' : 'open'}`} />
                ))}
              </div>
              <span className="help">{max - used === 0 ? 'All used this week.' : `${max - used} remaining. ${it.help}`}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const StaffBrief = ({ staff }) => (
  <div className="do-panel do-staff-brief">
    <div className="do-panel-head">
      <span className="dm-kicker">Staff Room</span>
      <h3>Department Heads</h3>
    </div>
    <div className="do-staff-list">
      {staff.map((s, i) => (
        <div key={i} className="do-staff-row">
          <div className="info">
            <span className="dm-kicker cyan">{s.dept}</span>
            <span className="name">{s.name}</span>
            <span className="voice">"{s.voice}"</span>
          </div>
          <div className="rating mono">{s.rating} <span className="lbl">OVR</span></div>
        </div>
      ))}
    </div>
  </div>
);

const RecruitCard = ({ r }) => {
  const fitLabel = r.fitTier === 'strong' ? 'Strong Fit' : r.fitTier === 'risk' ? 'At Risk' : 'Neutral';
  return (
    <div className={`do-recruit-card fit-${r.fitTier}`}>
      <div className="rail" />
      <div className="header">
        <div className="info">
          <span className="name" title={r.name}>{r.name}</span>
          <div className="meta">
            <span>{r.hometown}</span> <span className="sep">·</span> {archeBadgeRecruit(r.archetype)}
          </div>
        </div>
        <div className="fit-score">
          <span className="dm-kicker">FIT</span>
          <span className="val mono">{r.fitScore}</span>
        </div>
      </div>
      <div className="meter-wrap">
        <div className="meter"><div className="fill" style={{ width: `${r.fitScore}%` }} /></div>
        <div className="meter-labels">
          <span className="lbl">{fitLabel.toUpperCase()}</span>
          <span className="ovr mono">OVR {r.ovrBand[0]}-{r.ovrBand[1]}</span>
        </div>
      </div>
      <div className="evidence">
        <span className="bar" />
        <span className="copy">{r.evidence}</span>
      </div>
      <div className="actions">
        <button className="do-btn">Scout</button>
        <button className="do-btn">Contact</button>
        <button className={`do-btn ${r.fitTier === 'strong' ? 'orange' : ''}`}>Visit</button>
      </div>
    </div>
  );
};

const RecruitBoard = ({ recruits }) => {
  const [filter, setFilter] = useStateD('all');
  const filtered = recruits.filter(r =>
    filter === 'all' ? true :
    filter === 'strong' ? r.fitTier === 'strong' :
    filter === 'visit' ? r.fitTier !== 'risk' : true
  );

  return (
    <div className="do-panel do-board">
      <div className="do-board-head">
        <div className="title">
          <span className="dm-kicker">Recruit Board</span>
          <h3>This Week's Prospects</h3>
        </div>
        <div className="filters">
          <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>
            All <span className="mono">{recruits.length}</span>
          </button>
          <button className={filter === 'strong' ? 'active' : ''} onClick={() => setFilter('strong')}>
            Strong Fit <span className="mono">{recruits.filter(r => r.fitTier === 'strong').length}</span>
          </button>
          <button className={filter === 'visit' ? 'active' : ''} onClick={() => setFilter('visit')}>
            Visit-Ready <span className="mono">{recruits.filter(r => r.fitTier !== 'risk').length}</span>
          </button>
          <span className="sep" />
          <span className="dm-kicker">Sorted by FIT - Desc</span>
        </div>
      </div>
      <div className="do-board-grid">
        {filtered.map(r => <RecruitCard key={r.id} r={r} />)}
      </div>
    </div>
  );
};

const RecruitTab = ({ data }) => (
  <div className="do-tab-content">
    <CredibilityHero c={data.credibility} />
    <div className="do-row">
      <SlotMeter slots={data.slots} />
      <StaffBrief staff={data.staff} />
    </div>
    <RecruitBoard recruits={data.recruits} />
  </div>
);

const DynastyOfficeScreen = ({ data }) => {
  const [activeTab, setActiveTab] = useStateD('recruit');
  return (
    <div className="max-content do-shell" data-screen-label="03 Dynasty">
      <DoTabs active={activeTab} onSelect={setActiveTab} />
      {activeTab === 'recruit' && <RecruitTab data={data} />}
      {activeTab === 'history' && <HistoryTab data={data} />}
      {activeTab === 'staff'   && <StaffTab   data={data} />}
      {activeTab === 'budget'  && <BudgetTab  data={data} />}
    </div>
  );
};

Object.assign(window, { DynastyOfficeScreen });
