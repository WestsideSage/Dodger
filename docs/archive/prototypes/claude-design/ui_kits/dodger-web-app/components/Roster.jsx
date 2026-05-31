const { useState: useStateR, useMemo: useMemoR } = React;

const archeBadgeRoster = (a) => {
  if (a === 'Balanced') return <span className="dm-badge dm-badge-cyan">BALANCED</span>;
  if (a === 'Power')    return <span className="dm-badge dm-badge-orange">POWER</span>;
  if (a === 'Tactical') return <span className="dm-badge dm-badge-violet">TACTICAL</span>;
  return <span className="dm-badge">{a.toUpperCase()}</span>;
};

const potColor = (tier) => {
  if (tier === 'Elite') return '#facc15';
  if (tier === 'High') return 'var(--dm-cyan)';
  if (tier === 'Solid') return '#84cc16';
  return '#94a3b8';
};
const potGlyph = (tier) => tier === 'Elite' ? '★' : tier === 'High' ? '◆' : tier === 'Solid' ? '»' : '⬡';

const LineupSummary = ({ roster }) => {
  const starters = roster.filter(p => p.isStarter).length;
  const rotation = roster.filter(p => p.role === 'Rotation').length;
  const bench = roster.filter(p => p.role === 'Bench').length;
  const avgOvr = Math.round(roster.reduce((s, p) => s + p.overall, 0) / roster.length);
  return (
    <div className="rl-glance-cell">
      <span className="dm-kicker">Lineup · OVR {avgOvr}</span>
      <div className="rl-line-row">
        <span className="rl-pill cyan"><span className="mono">{starters}</span> STARTERS</span>
        <span className="rl-pill violet"><span className="mono">{rotation}</span> ROTATION</span>
        <span className="rl-pill slate"><span className="mono">{bench}</span> BENCH</span>
      </div>
      <p className="sub">Backline anchored by Mika Thorn (CAT 91) and Marlon Reed (CAT 87). One rotation slot open.</p>
    </div>
  );
};

const ArchetypeMix = ({ roster }) => {
  const counts = roster.reduce((acc, p) => { acc[p.archetype] = (acc[p.archetype] || 0) + 1; return acc; }, {});
  const segments = [
    { key: 'Power', val: counts.Power || 0, color: 'var(--dm-orange)' },
    { key: 'Balanced', val: counts.Balanced || 0, color: 'var(--dm-cyan)' },
    { key: 'Tactical', val: counts.Tactical || 0, color: 'var(--dm-violet)' }
  ];
  return (
    <div className="rl-glance-cell">
      <span className="dm-kicker">Archetype Mix</span>
      <div className="rl-mix-bar">
        {segments.map(s => <div key={s.key} className="seg" style={{ flex: s.val, background: s.color }} />)}
      </div>
      <div className="rl-mix-leg">
        {segments.map(s => (
          <div key={s.key} className="item">
            <span className="dot" style={{ background: s.color }} />
            <span className="k">{s.key}</span>
            <span className="v mono">{s.val}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const PotentialBlock = ({ roster }) => {
  const tiers = ['Elite', 'High', 'Solid', 'Limited'];
  return (
    <div className="rl-glance-cell">
      <span className="dm-kicker">Potential Tiers</span>
      <div className="rl-pot-grid">
        {tiers.map(t => (
          <div key={t} className={`rl-pot-tile tier-${t.toLowerCase()}`}>
            <span className="glyph">{potGlyph(t)}</span>
            <span className="val mono">{roster.filter(p => p.potential === t).length}</span>
            <span className="lbl">{t}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const AgeCurve = ({ roster }) => {
  const ages = roster.map(p => p.age);
  const min = Math.min(...ages), max = Math.max(...ages);
  const buckets = [
    { lbl: '18-21', min: 18, max: 21 },
    { lbl: '22-25', min: 22, max: 25 },
    { lbl: '26-29', min: 26, max: 29 },
    { lbl: '30+', min: 30, max: 99 }
  ];
  const counts = buckets.map(b => roster.filter(p => p.age >= b.min && p.age <= b.max).length);
  const maxC = Math.max(...counts, 1);
  const avg = (ages.reduce((a, b) => a + b, 0) / ages.length).toFixed(1);
  
  return (
    <div className="rl-glance-cell rl-age-cell">
      <span className="dm-kicker">Age Curve</span>
      <div className="rl-age-row">
        <div className="rl-age-stat">
          <span className="val mono">{avg}</span>
          <span className="sub">avg · {min}-{max}</span>
        </div>
        <div className="rl-age-chart">
          {buckets.map((b, i) => (
            <div key={i} className="col">
              <div className="bar" style={{ height: `${(counts[i]/maxC)*100}%` }} />
              <span className="lbl">{b.lbl}</span>
              <span className="val mono">{counts[i]}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const RatingMini = ({ lbl, val }) => {
  const tier = val >= 85 ? 'elite' : val >= 70 ? 'good' : val >= 55 ? 'avg' : 'poor';
  return (
    <div className={`rl-rating-mini tier-${tier}`}>
      <span className="lbl">{lbl}</span>
      <span className="val mono">{val}</span>
      <div className="track"><div className="fill" style={{ width: `${val}%` }} /></div>
    </div>
  );
};

const RosterScreen = ({ data }) => {
  const [view, setView] = useStateR('detailed');
  const [sortKey, setSortKey] = useStateR('lineup');
  
  const sorted = useMemoR(() => {
    const arr = [...data.roster];
    if (sortKey === 'lineup') arr.sort((a, b) => Number(b.isStarter) - Number(a.isStarter) || b.overall - a.overall);
    if (sortKey === 'potential') {
      const order = { Elite: 0, High: 1, Solid: 2, Limited: 3 };
      arr.sort((a, b) => order[a.potential] - order[b.potential] || b.overall - a.overall);
    }
    if (sortKey === 'overall') arr.sort((a, b) => b.overall - a.overall);
    if (sortKey === 'age') arr.sort((a, b) => a.age - b.age);
    return arr;
  }, [data.roster, sortKey]);

  return (
    <div className="max-content rl-shell" data-screen-label="02 Roster">
      <div className="rl-head">
        <div>
          <span className="dm-kicker">Roster Lab</span>
          <h2>Team Roster</h2>
          <p className="sub">Player condition, role fit, and match readiness. {data.roster.length} contracted.</p>
        </div>
        <div className="rl-actions">
          <div className="rl-segment">
            <button className={view === 'detailed' ? 'active' : ''} onClick={() => setView('detailed')}>Detailed</button>
            <button className={view === 'compact' ? 'active' : ''} onClick={() => setView('compact')}>Compact</button>
          </div>
          <select className="rl-sort" value={sortKey} onChange={e => setSortKey(e.target.value)}>
            <option value="lineup">Sort · Lineup → OVR</option>
            <option value="potential">Sort · Potential</option>
            <option value="overall">Sort · OVR</option>
            <option value="age">Sort · Age</option>
          </select>
          <button className="do-btn ghost">Lineup Editor ▸</button>
        </div>
      </div>

      <div className="rl-glance">
        <LineupSummary roster={data.roster} />
        <ArchetypeMix roster={data.roster} />
        <PotentialBlock roster={data.roster} />
        <AgeCurve roster={data.roster} />
      </div>

      <div className="rl-table-wrap">
        <table className={`rl-table ${view}`}>
          <thead>
            {view === 'compact' ? (
              <tr>
                <th className="tc">#</th>
                <th>Player</th>
                <th className="tc">ACC</th>
                <th className="tc">POW</th>
                <th className="tc">DOD</th>
                <th className="tc">CAT</th>
                <th className="tc">STA</th>
                <th className="tc">IQ</th>
                <th className="tc">OVR</th>
                <th>Potential</th>
                <th>Role</th>
              </tr>
            ) : (
              <tr>
                <th className="tc">#</th>
                <th>Player</th>
                <th>Ratings</th>
                <th>Potential</th>
                <th>OVR</th>
                <th>Role</th>
              </tr>
            )}
          </thead>
          <tbody>
            {sorted.map((p, i) => {
              const isElite = p.potential === 'Elite';
              return (
                <tr key={p.id} className={`${isElite ? 'elite-row' : ''} ${p.isStarter ? 'starter-row' : ''}`}>
                  <td className="tc mono rank">{(i+1).toString().padStart(2,'0')}</td>
                  <td>
                    <div className="rl-player-id">
                      <span className="name">{p.name}</span>
                      <div className="meta">
                        <span>Age {p.age}</span> <span className="sep">·</span> {archeBadgeRoster(p.archetype)}
                        {p.isStarter && <span className="pin">●</span>}
                      </div>
                    </div>
                  </td>
                  {view === 'compact' ? (
                    ['acc','pow','dod','cat','sta','iq'].map(k => {
                      const v = p.ratings[k];
                      const t = v >= 85 ? 'elite' : v >= 70 ? 'good' : v >= 55 ? 'avg' : 'poor';
                      return <td key={k} className={`tc mono tier-${t}`}>{v}</td>;
                    })
                  ) : (
                    <td>
                      <div className="rl-ratings-grid">
                        {[['ACC', p.ratings.acc],['POW', p.ratings.pow],['DOD', p.ratings.dod],['CAT', p.ratings.cat],['STA', p.ratings.sta],['IQ', p.ratings.iq]].map(([l,v]) => (
                          <RatingMini key={l} lbl={l} val={v} />
                        ))}
                      </div>
                    </td>
                  )}
                  {view === 'compact' ? (
                    <td>
                      <div className="rl-pot-compact">
                        <span className="glyph" style={{color: potColor(p.potential)}}>{potGlyph(p.potential)}</span>
                        <span className="lbl">{p.potential}</span>
                      </div>
                    </td>
                  ) : (
                    <td>
                      <div className="rl-pot-detailed">
                        <div className={`gem tier-${p.potential.toLowerCase()}`}>{potGlyph(p.potential)}</div>
                        <div className="info">
                          <span className="tier" style={{color: potColor(p.potential)}}>{p.potential}</span>
                          <span className="conf">{'●'.repeat(p.confidence)}{'○'.repeat(Math.max(0, 4 - p.confidence))}</span>
                        </div>
                      </div>
                    </td>
                  )}
                  {view === 'compact' ? (
                    <td className="tc mono ovr">
                      {p.overall}
                    </td>
                  ) : (
                    <td>
                      <div className="rl-ovr-detailed">
                        <span className="val mono">{p.overall}</span>
                        <div className="track"><div className="fill" style={{ width: `${p.overall}%` }} /></div>
                      </div>
                    </td>
                  )}
                  <td>
                    <span className={`dm-badge ${p.role === 'Starter' ? 'dm-badge-cyan' : p.role === 'Rotation' ? 'dm-badge-violet' : 'dm-badge-slate'}`}>
                      {p.role.toUpperCase()}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

Object.assign(window, { RosterScreen });
