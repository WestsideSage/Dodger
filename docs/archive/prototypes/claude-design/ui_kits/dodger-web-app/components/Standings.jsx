const { useMemo: useMemoSt } = React;

const FORM = {
  "Foxbridge Volley":     ["W", "W", "W", "W"],
  "Glen Lake Tactics":    ["W", "L", "W", "W"],
  "Pine Hills Burn":      ["W", "W", "L", "W"],
  "Westside Solstice":    ["W", "L", "W", "W"],
  "Cedar Crest Reads":    ["W", "L", "W", "L"],
  "Bishop Bench":         ["L", "W", "W", "L"],
  "Riverton Volume":      ["W", "L", "L", "W"],
  "Carbon Bay Lash":      ["L", "W", "L", "L"],
  "Northwood Cyphers":    ["L", "L", "D", "L"],
  "Iron Hollow Steel":    ["L", "L", "L", "L"],
};

const FormStreak = ({ form }) => (
  <div className="ls-form-streak">
    {form.map((r, i) => (
      <span key={i} className={`ls-pip pip-${r}`}>{r}</span>
    ))}
  </div>
);

const DiffBar = ({ diff, max }) => {
  const num = parseInt(diff.replace('+', ''), 10);
  const pct = Math.min(100, (Math.abs(num) / max) * 100);
  const isPos = num >= 0;
  return (
    <div className="ls-diff-wrap">
      <div className="ls-diff-bar">
        <span className="ls-diff-axis" />
        <span 
          className={`ls-diff-fill ${isPos ? 'pos' : 'neg'}`} 
          style={{ 
            width: `${pct / 2}%`, 
            left: isPos ? '50%' : `calc(50% - ${pct / 2}%)` 
          }} 
        />
      </div>
      <span className={`ls-diff-val ${isPos ? 'pos' : 'neg'}`}>{diff}</span>
    </div>
  );
};

const StandingsScreen = ({ data }) => {
  const standings = data.standings;
  const us = standings.find(s => s.user);
  const playoffLine = 4;
  const top = standings[0];
  const fifth = standings.find(s => s.rank === 5);
  
  const maxDiff = useMemoSt(() => 
    Math.max(...standings.map(s => Math.abs(parseInt(s.diff, 10)))), 
  [standings]);

  return (
    <div className="max-content ls-shell" data-screen-label="04 Standings">
      <div className="ls-glance">
        <div className="ls-glance-cell">
          <span className="dm-kicker">Our Rank</span>
          <div className="ls-glance-val">
            <span className="num">{us.rank}</span> 
            <span className="sub">of 10</span>
          </div>
          <div className="ls-glance-trend ok">
            <span className="arrow">▲</span> Up 1 from W03
          </div>
        </div>
        
        <div className="ls-glance-cell">
          <span className="dm-kicker">Record · Diff</span>
          <div className="ls-glance-val">
            <span className="num">{us.w}-{us.l}-{us.d}</span> 
            <span className="sub mono highlight">{us.diff}</span>
          </div>
          <div className="ls-glance-subrow">
            <FormStreak form={FORM[us.club]} />
          </div>
        </div>

        <div className="ls-glance-cell">
          <span className="dm-kicker">Playoff Line · Top 4</span>
          <div className="ls-race">
            {standings.slice(0, 5).map(s => (
              <div key={s.rank} className={`ls-race-pip ${s.user ? 'us' : ''} ${s.rank <= playoffLine ? 'in' : 'out'}`}>
                {s.rank}
              </div>
            ))}
          </div>
          <div className="ls-glance-subrow">
            <span className="txt ok">+{us.pts - fifth.pts} pts cushion</span>
            <span className="txt warn">{top.pts - us.pts} back of #1</span>
          </div>
        </div>

        <div className="ls-glance-cell">
          <span className="dm-kicker">Next Result Needs</span>
          <div className="ls-needs-row">
            <span className="ls-btn-pill orange">WIN W04</span>
            <span className="arrow">▸</span>
            <span className="ls-btn-pill emerald">≥ #3</span>
          </div>
          <p className="ls-helper">A win vs Northwood with Pine Hills slipping would clinch the #3 seed on tiebreaker.</p>
        </div>
      </div>

      <div className="ls-grid">
        <div className="ls-table-panel">
          <div className="ls-panel-head">
            <span className="dm-kicker">League Office</span>
            <h2>2026 Standings</h2>
          </div>
          
          <table className="ls-table">
            <thead>
              <tr>
                <th className="tc">#</th>
                <th>Club</th>
                <th className="tc">W</th>
                <th className="tc">L</th>
                <th className="tc">D</th>
                <th className="tc">PTS</th>
                <th>Form</th>
                <th>Survivor Diff</th>
              </tr>
            </thead>
            <tbody>
              {standings.map((s, i) => {
                const isCut = i === playoffLine;
                return (
                  <React.Fragment key={s.rank}>
                    {isCut && (
                      <tr className="ls-cut-row">
                        <td colSpan="8">
                          <div className="ls-cut-line">
                            <span className="line" />
                            <span className="pill">PLAYOFF CUT</span>
                            <span className="line" />
                          </div>
                        </td>
                      </tr>
                    )}
                    <tr className={s.user ? 'us' : ''}>
                      <td className="tc">
                        <span className={`ls-rank ${s.rank <= playoffLine ? 'in' : 'out'}`}>{s.rank}</span>
                      </td>
                      <td>
                        <span className="ls-club-name">{s.club}</span>
                        {s.user && <span className="dm-badge dm-badge-cyan">YOU</span>}
                      </td>
                      <td className="tc mono">{s.w}</td>
                      <td className="tc mono dim">{s.l}</td>
                      <td className="tc mono dim">{s.d}</td>
                      <td className="tc mono pts">{s.pts}</td>
                      <td><FormStreak form={FORM[s.club]} /></td>
                      <td><DiffBar diff={s.diff} max={maxDiff} /></td>
                    </tr>
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="ls-side">
          <div className="ls-panel">
            <div className="ls-panel-head">
              <span className="dm-kicker">League Wire</span>
              <h3>W03 Results</h3>
            </div>
            <div className="ls-wire-list">
              {data.recentMatches.map((m, i) => {
                const match = m.summary.match(/^(.+?)\s+(\d+)-(\d+)\s+(.+)$/);
                if (!match) return null;
                const [, home, hScore, aScore, away] = match;
                return (
                  <div key={i} className="ls-wire-row">
                    <span className="ls-wire-team right">{home}</span>
                    <span className="ls-wire-score">{hScore}—{aScore}</span>
                    <span className="ls-wire-team left">{away}</span>
                    <span className={`ls-wire-tag ${m.winner === 'Draw' ? 'draw' : 'win'}`}>
                      {m.winner === 'Draw' ? 'DRAW' : m.winner.toUpperCase()}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="ls-panel">
            <div className="ls-panel-head">
              <span className="dm-kicker">Tiebreaker Read</span>
              <h3>Top 4 Lock</h3>
            </div>
            <div className="ls-tb-list">
              {[
                { pos: "#2", club: "Glen Lake", note: "Same pts, +8 vs our +4 diff", safe: true },
                { pos: "#3", club: "Pine Hills", note: "Same pts, +5 vs our +4 diff", safe: false },
                { pos: "#5", club: "Cedar Crest", note: "Trails by 3 pts", safe: true }
              ].map((t, i) => (
                <div key={i} className={`ls-tb-row ${t.safe ? 'safe' : 'risk'}`}>
                  <span className="pos">{t.pos}</span>
                  <div className="body">
                    <div className="club">{t.club}</div>
                    <div className="note">{t.note}</div>
                  </div>
                  <span className={`dm-badge ${t.safe ? 'dm-badge-emerald' : 'dm-badge-amber'}`}>
                    {t.safe ? 'SAFE' : 'AT RISK'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { StandingsScreen });
