/* Command Center -- pre-sim dashboard + post-sim aftermath reveals. */
const { useState, useEffect } = React;

/* Dark mini court — weak side flagged in orange */
const MiniCourt = () => (
  <svg className="cc-court-svg" viewBox="0 0 360 180" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <pattern id="cc-grid" width="12" height="12" patternUnits="userSpaceOnUse">
        <path d="M 12 0 L 0 0 0 12" fill="none" stroke="rgba(34,211,238,0.07)" strokeWidth="0.5" />
      </pattern>
      <linearGradient id="cc-weak" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stopColor="rgba(249,115,22,0.18)" />
        <stop offset="100%" stopColor="rgba(249,115,22,0.04)" />
      </linearGradient>
    </defs>
    <rect x="6" y="6" width="348" height="168" fill="#020617" stroke="#1e293b" strokeWidth="1" rx="3" />
    <rect x="6" y="6" width="348" height="168" fill="url(#cc-grid)" rx="3" />
    <rect x="200" y="6" width="84" height="168" fill="url(#cc-weak)" />
    <line x1="180" y1="10" x2="180" y2="170" stroke="#334155" strokeWidth="1" strokeDasharray="3 4" />
    <text x="14" y="20" fontFamily="JetBrains Mono, monospace" fontSize="7" letterSpacing="2" fill="#475569">HOME</text>
    <text x="318" y="20" fontFamily="JetBrains Mono, monospace" fontSize="7" letterSpacing="2" fill="#475569">AWAY</text>
    <text x="206" y="170" fontFamily="JetBrains Mono, monospace" fontSize="7" letterSpacing="2" fill="#f97316" opacity="0.85">WEAK SIDE</text>
    {[[40,40],[40,90],[40,140],[100,55],[100,125],[150,90]].map(([cx,cy],i) => (
      <g key={`h${i}`}>
        <circle cx={cx} cy={cy} r="8" fill="#0f172a" stroke="#f43f5e" strokeWidth="1.4" />
        <circle cx={cx} cy={cy} r="2.2" fill="#f43f5e" />
      </g>
    ))}
    {[[220,45],[220,135],[270,90],[320,40],[320,90],[320,140]].map(([cx,cy],i) => (
      <g key={`a${i}`}>
        <circle cx={cx} cy={cy} r="8" fill="#0f172a" stroke={i === 2 ? "#fb7185" : "#3b82f6"} strokeWidth={i === 2 ? "2" : "1.4"} />
        <circle cx={cx} cy={cy} r="2.2" fill={i === 2 ? "#fb7185" : "#3b82f6"} />
        {i === 2 && <circle cx={cx} cy={cy} r="14" fill="none" stroke="#fb7185" strokeWidth="1" strokeDasharray="2 3" opacity="0.7" />}
      </g>
    ))}
    <path d="M 150 90 Q 220 60 285 75" fill="none" stroke="#f97316" strokeWidth="1.4" strokeDasharray="3 4" opacity="0.9" />
    <polygon points="285,75 279,71 278,79" fill="#f97316" opacity="0.9" />
    <circle cx="150" cy="90" r="3" fill="#f97316" />
  </svg>
);

/* Parse "Mika Thorn (CAT 91) vs Theo Park (POW 87)" into a key-threat triple */
const parseThreat = (keyMatchup, opponentName) => {
  // Pick the opponent's side of the matchup string
  const parts = String(keyMatchup || "").split(/\s+vs\s+/i);
  const oppSide = parts[1] || parts[0] || "";
  const m = oppSide.match(/^(.+?)\s*\(([A-Z]+)\s+(\d+)\)\s*$/);
  if (m) return { name: m[1].trim(), role: `${m[2]} Anchor`, ovr: m[3] };
  return { name: opponentName || "Unknown", role: "Anchor", ovr: "—" };
};

const PreSimCommandCenter = ({ data, onSimulate }) => {
  const [intent, setIntent] = useState(data.selectedIntent);
  const wk = String(data.program.week).padStart(2, "0");
  const threat = parseThreat(data.nextMatch.keyMatchup, data.nextMatch.opponent);

  // 5 checklist items mapped to gates (first 4 + intent always green here)
  const gates = [
    ...data.checklist.slice(0, 4).map(c => ({
      lbl: c.label === "Ready" ? c.title.split(" ")[0] : c.label,
      state: c.state === "ready" ? "ok" : c.state === "pending" ? "pend" : "opt",
    })),
  ];
  // Tighten labels to fit
  const gateShort = [
    { lbl: "Lineup",    state: gates[0]?.state || "opt" },
    { lbl: "Intent",    state: gates[1]?.state || "opt" },
    { lbl: "Recruit",   state: gates[2]?.state || "opt" },
    { lbl: "Scout",     state: gates[3]?.state || "opt" },
  ];
  const readyCount = gateShort.filter(g => g.state === "ok").length;
  const pendCount  = gateShort.filter(g => g.state === "pend").length;
  const allGreen   = pendCount === 0;

  return (
    <div className="max-content">
      {/* Identity strip */}
      <div className="cc-id-strip">
        <div><span className="lbl">Program</span><span className="val">{data.program.name}</span></div>
        <div><span className="lbl">Season</span><span className="val num">{data.program.seasonYear}</span></div>
        <div><span className="lbl">Week</span><span className="val num">W{wk}</span></div>
        <div><span className="lbl">Record</span><span className="val num">{data.program.record}</span></div>
        <div><span className="lbl">Intent</span><span className="val cyan">{intent}</span></div>
        <div><span className="lbl">Status</span><span className="val orange">Ready</span></div>
      </div>

      {/* Hero */}
      <section className="cc-hero">
        <div className="cc-hero-left">
          <div className="cc-hero-kick">
            <span className="live-pip" />
            <span>Match Week</span><span className="sep" /><span>Week {wk}</span><span className="sep" /><span>{data.nextMatch.home ? "Home" : "Away"}</span>
          </div>
          <h2 className="cc-hero-headline">
            <span className="vs">vs </span><span className="opp">{data.nextMatch.opponent}</span>
          </h2>
          <div className="cc-hero-frame">
            <div className="line"><b>This Week</b>{data.nextMatch.framing}</div>
            <div className="line watch"><b>Objective</b>{data.program.objective}</div>
          </div>
          <div className="cc-hero-stats">
            <div><span className="lbl">Opp Record</span><span className="val">{data.nextMatch.opponentRecord}</span></div>
            <div><span className="lbl">Last Meeting</span><span className="val">{data.nextMatch.lastMeeting}</span></div>
            <div><span className="lbl">Risk Window</span><span className="val">{data.scoutReport.risk.split(".")[0]}</span></div>
            <div><span className="lbl">Key Matchup</span><span className="val">{data.nextMatch.keyMatchup.replace(/\s*\([^)]*\)/g, "")}</span></div>
          </div>
        </div>
        <div className="cc-hero-right">
          <div className="cc-court-card">
            <div className="head">
              <span className="lbl">Court Read</span>
              <span className="side">▸ Weak side flagged</span>
            </div>
            <MiniCourt />
          </div>
          <div className="cc-threat-card">
            <span className="lbl">Key Threat</span>
            <div className="name">{threat.name}</div>
            <div className="row">
              <span><b>{threat.role}</b></span>
              <span className="ovr">{threat.ovr} OVR</span>
            </div>
          </div>
        </div>
      </section>

      {/* Body grid */}
      <div className="cc-body">
        {/* Plan */}
        <div className="cc-panel">
          <div className="cc-panel-head">
            <span className="kicker">Operational Plan</span>
            <h2>This Week's Orders</h2>
            <p>Department leads call the moves. Aligned with <b style={{color:'#fff'}}>{intent}</b> -- pressure where their backline thins out.</p>
          </div>
          <div className="cc-panel-body">
            <div className="cc-align-callout">
              <div className="copy"><b>Profile aligned.</b> Catch-heavy attrition counters Power-Arm Aggro -- if catchers survive volley one.</div>
              <span className="cc-pill emer">Aligned</span>
            </div>
            <div className="cc-policy">
              {data.departmentOrders.map((o, i) => (
                <div key={i} className={`cc-policy-cell ${i === 2 ? 'pending' : 'ready'}`}>
                  <span className="lbl">{o.dept}</span>
                  <span className="val">{o.title}</span>
                  <span className="helper">{o.body}</span>
                </div>
              ))}
            </div>
            <div className="cc-plan-foot">
              <span className="note">{data.departmentOrders.length} orders · {pendCount} pending</span>
              <button className="dm-btn">Edit Orders ▸</button>
            </div>
          </div>
        </div>

        {/* Scout */}
        <div className="cc-panel">
          <div className="cc-panel-head">
            <span className="kicker">Opponent File</span>
            <h2>{data.nextMatch.opponent}</h2>
            <p>{data.scoutReport.awayStarter}</p>
          </div>
          <div className="cc-panel-body">
            <div className="cc-scout-edge">
              <div className="row">
                <span className="lbl">Counter Read</span>
                <span className="val">{data.scoutReport.homeStarter.split(".")[0]}</span>
              </div>
              <span className="sub">Solstice opens with sniper control. Two starters fatigued -- rotate by volley four.</span>
            </div>
            <div className="cc-scout-grid">
              <div><span className="lbl">Opp Record</span><span className="val">{data.nextMatch.opponentRecord}</span></div>
              <div><span className="lbl">Last Meeting</span><span className="val mono">{data.nextMatch.lastMeeting}</span></div>
              <div className="span-2"><span className="lbl">Risk Notes</span><span className="val mono">{data.scoutReport.risk}</span></div>
            </div>
            <div className="cc-align-callout" style={{ borderColor: 'rgba(245,158,11,0.28)', borderLeftColor: 'var(--dm-amber)', background: 'rgba(245,158,11,0.05)' }}>
              <div className="copy" style={{ color: '#fde68a' }}><b style={{ color: '#fff' }}>Recommendation.</b> Hold current plan. Verify Theo Park to "Verified" before lineup lock.</div>
              <span className="cc-pill amber">Keep Plan</span>
            </div>
          </div>
        </div>

        {/* Lock */}
        <div className="cc-panel cc-lock">
          <div className="cc-panel-head">
            <span className="kicker">Sim Lock</span>
            <h2>{data.readiness.label}</h2>
            <div className="cc-ready-row">
              <span className="pulse-em" />
              <span className="lbl">{allGreen ? `All gates green · ${readyCount}/${gateShort.length}` : `${readyCount} of ${gateShort.length} ready · ${pendCount} pending`}</span>
            </div>
          </div>
          <div className="cc-panel-body">
            <div className="cc-gates">
              {gateShort.map((g, i) => (
                <div key={i} className={`cc-gate ${g.state}`}>
                  <span className="tick">{g.state === "ok" ? "✓" : g.state === "pend" ? "!" : "·"}</span>
                  <span className="lbl">{g.lbl}</span>
                </div>
              ))}
            </div>
            <div className="cc-intent-field">
              <span className="lbl">This Week's Intent</span>
              <select value={intent} onChange={(e) => setIntent(e.target.value)}>
                {data.intents.map(i => <option key={i} value={i}>{i}</option>)}
              </select>
            </div>
            <div className="cc-lock-readout">
              <div className="lr"><span className="lbl">Decision</span><span className="val">{intent}</span></div>
              <div className="lr"><span className="lbl">Risk</span><span className="val am">High</span></div>
              <div className="lr"><span className="lbl">Readiness</span><span className="val mono em">{readyCount} / {gateShort.length}</span></div>
              <div className="lr"><span className="lbl">Recommendation</span><span className="val">Keep Plan</span></div>
              <div className="lr"><span className="lbl">Next Issue</span><span className="val">{pendCount === 0 ? "No Blockers" : `${pendCount} Pending`}</span></div>
            </div>
            <div className="cc-lock-foot">
              <div className="ctx"><b>{data.readiness.note}</b></div>
              <button className="cc-btn-sim" onClick={onSimulate}>
                <span>Simulate Week</span>
                <span className="arrow">▸</span>
              </button>
              <div className="cc-lock-meta"><span>⌘ ⏎ to confirm</span><span>Auto-saved</span></div>
            </div>
          </div>
        </div>
      </div>

      {/* Proof bar — around the league */}
      <div className="cc-proof">
        <span className="tag">League Wire</span>
        <span className="copy">
          {data.recentMatches.slice(0, 3).map((m, i) => (
            <span key={i}><b>W{m.week}</b> {m.summary}{i < 2 ? "  ·  " : ""}</span>
          ))}
        </span>
        <span className="wkbadge">Top: {data.standings[0].club}</span>
        <button className="show">View Standings ▸</button>
      </div>
    </div>
  );
};

const Headline = ({ headline, contextLine }) => (
  <div className="headline-card command-reveal">
    <Kicker color="amber">Match Result</Kicker>
    <h2>{headline}</h2>
    {contextLine && <span className="context">{contextLine}</span>}
  </div>
);

const MatchScoreHero = ({ matchCard }) => (
  <div className="score-hero command-reveal">
    <div className={`side ${matchCard.winner === 'home' ? 'winner' : 'loser'}`}>
      <span className="meta">Home -- 3-1</span>
      <span className="team">{matchCard.home}</span>
      <span className="num">{matchCard.homeSurv}</span>
      <span className="meta" style={{ color: matchCard.winner === 'home' ? 'var(--dm-orange-hover)' : 'var(--dm-text-muted)' }}>
        {matchCard.winner === 'home' ? `Winner -- ${matchCard.homeSurv} survivors` : `${matchCard.homeSurv} survivors`}
      </span>
    </div>
    <div className="center"><span className="final">FINAL</span><span className="vs">VS</span></div>
    <div className={`side away ${matchCard.winner === 'away' ? 'winner' : 'loser'}`}>
      <span className="meta">Away -- 1-3</span>
      <span className="team">{matchCard.away}</span>
      <span className="num">{matchCard.awaySurv}</span>
      <span className="meta">{matchCard.awaySurv} survivors</span>
    </div>
  </div>
);

const TacticalSummary = ({ turningPoint, lanes }) => (
  <Panel kicker="Tactical Read" title="Why this happened">
    <div className="dm-section" style={{ display: 'grid', gap: '1rem' }}>
      <p style={{ margin: 0, color: 'var(--dm-text-secondary)', fontSize: '0.95rem', lineHeight: 1.55 }}>{turningPoint}</p>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        {lanes.map((l, i) => (
          <div key={i} style={{ borderLeft: '2px solid var(--dm-cyan)', paddingLeft: 12 }}>
            <Kicker style={{ fontSize: '0.62rem', marginBottom: 2 }}>{l.title}</Kicker>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.85rem', color: '#fff', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{l.summary}</div>
            <ul style={{ margin: '6px 0 0', paddingLeft: '1rem', display: 'grid', gap: 4 }}>
              {l.items.map((it, j) => <li key={j} style={{ color: 'var(--dm-text-muted)', fontSize: '0.78rem' }}>{it}</li>)}
            </ul>
          </div>
        ))}
      </div>
    </div>
  </Panel>
);

const KeyPlayersPanel = ({ performers }) => (
  <Panel kicker="Key Performers" title="Who cooked">
    <div className="dm-section" style={{ display: 'grid', gap: '0.85rem' }}>
      {performers.map((p, i) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, alignItems: 'center', padding: '8px 0', borderBottom: i < performers.length - 1 ? '1px solid rgba(30,41,59,0.5)' : 'none' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.95rem', fontWeight: 800, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{p.name}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--dm-text-muted)', marginTop: 2 }}>{p.line}</div>
          </div>
          <Badge tone={i === 0 ? 'amber' : i === 1 ? 'cyan' : 'slate'}>+{p.score} IMP</Badge>
        </div>
      ))}
    </div>
  </Panel>
);

const FalloutGrid = ({ growth, standingsShift, recruitReactions }) => (
  <div className="fallout-grid command-reveal">
    <Panel kicker="Development" title="Player Growth">
      <div className="dm-section">
        {growth.length === 0
          ? <p style={{ margin: 0, color: 'var(--dm-text-muted)', fontSize: '0.85rem' }}>No attribute gains from this match.</p>
          : <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 6 }}>
              {growth.map((g, i) => (
                <li key={i} style={{ color: 'var(--dm-text-secondary)', fontSize: '0.85rem' }}>
                  <span style={{ color: '#fff', fontWeight: 700 }}>{g.name}</span>
                  {' '}<span style={{ color: 'var(--dm-emerald-bright)', fontFamily: 'var(--font-mono)' }}>+{g.delta} {g.attr}</span>
                </li>
              ))}
            </ul>
        }
      </div>
    </Panel>

    <Panel kicker="Standings" title="League Table">
      <div className="dm-section">
        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 6 }}>
          {standingsShift.map((s, i) => {
            const moved = s.current - s.old;
            const color = moved < 0 ? 'var(--dm-emerald-bright)' : moved > 0 ? 'var(--dm-rose)' : 'var(--dm-text-muted)';
            const arrow = moved < 0 ? '↑' : moved > 0 ? '↓' : '--';
            return (
              <li key={i} style={{ color: 'var(--dm-text-secondary)', fontSize: '0.85rem' }}>
                <span style={{ color: '#fff', fontWeight: 700 }}>{s.club}</span>
                {' '}<span style={{ color, fontFamily: 'var(--font-mono)' }}>#{s.current} {arrow} from #{s.old}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </Panel>

    <Panel kicker="Recruiting" title="Recruit Reactions">
      <div className="dm-section">
        {recruitReactions.length === 0
          ? <p style={{ margin: 0, color: 'var(--dm-text-muted)', fontSize: '0.85rem' }}>No prospect interest changes reported.</p>
          : <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 6 }}>
              {recruitReactions.map((r, i) => (
                <li key={i} style={{ color: 'var(--dm-text-secondary)', fontSize: '0.85rem' }}>
                  <span style={{ color: '#fff', fontWeight: 700 }}>{r.name}</span>
                  {' '}<span style={{ color: 'var(--dm-emerald-bright)', fontFamily: 'var(--font-mono)' }}>{r.delta} interest</span>
                  <div style={{ color: 'var(--dm-text-muted)', fontSize: '0.78rem', fontStyle: 'italic', marginTop: 2 }}>{r.evidence}</div>
                </li>
              ))}
            </ul>
        }
      </div>
    </Panel>
  </div>
);

const ActionBar = ({ onAdvance, onWatch }) => (
  <div className="action-bar command-reveal">
    <div className="secondary">
      <Button variant="ghost" onClick={onWatch}>Watch Key Moments</Button>
      <Button variant="ghost">View Box Score</Button>
    </div>
    <Button variant="primary" onClick={onAdvance}>Advance to Next Week</Button>
  </div>
);

const PostSimAftermath = ({ data, onAdvance, onWatch }) => {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    if (stage >= 4) return;
    const t = setTimeout(() => setStage(s => s + 1), 600);
    return () => clearTimeout(t);
  }, [stage]);

  const a = data.aftermath;
  return (
    <div className="post-sim">
      {stage >= 0 && <Headline headline={a.headline} contextLine={a.contextLine} />}
      {stage >= 1 && <MatchScoreHero matchCard={a.matchCard} />}
      {stage >= 2 && (
        <div className="analysis-row command-reveal">
          <TacticalSummary turningPoint={a.turningPoint} lanes={a.evidenceLanes} />
          <KeyPlayersPanel performers={a.keyPerformers} />
        </div>
      )}
      {stage >= 3 && <FalloutGrid growth={a.growth} standingsShift={a.standingsShift} recruitReactions={a.recruitReactions} />}
      {stage >= 4 && <ActionBar onAdvance={onAdvance} onWatch={onWatch} />}
    </div>
  );
};

const CommandCenterScreen = ({ data, mode, onSimulate, onAdvance, onWatch }) => {
  if (mode === 'post-sim') return <PostSimAftermath data={data} onAdvance={onAdvance} onWatch={onWatch} />;
  return <PreSimCommandCenter data={data} onSimulate={onSimulate} />;
};

Object.assign(window, { CommandCenterScreen });
