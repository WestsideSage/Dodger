const { useState: useStateMR, useMemo: useMemoMR, useEffect: useEffectMR } = React;

const DarkCourt = ({ activeEvent }) => {
  const hot = (activeEvent && activeEvent.type) || 'throw';
  return (
    <svg viewBox="0 0 600 320" xmlns="http://www.w3.org/2000/svg" className="mr-court-svg" aria-label="Top-down dodgeball court">
      <defs>
        <pattern id="mr-grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(34,211,238,0.05)" strokeWidth="0.6" />
        </pattern>
        <linearGradient id="mr-home-zone" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="rgba(244,63,94,0.15)" />
          <stop offset="100%" stopColor="rgba(244,63,94,0.0)" />
        </linearGradient>
        <linearGradient id="mr-away-zone" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="rgba(59,130,246,0.0)" />
          <stop offset="100%" stopColor="rgba(59,130,246,0.15)" />
        </linearGradient>
        <radialGradient id="mr-catch-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(34,211,238,0.6)" />
          <stop offset="80%" stopColor="rgba(34,211,238,0)" />
        </radialGradient>
      </defs>

      <rect width="600" height="320" fill="#020617" />
      <rect width="600" height="320" fill="url(#mr-grid)" />
      
      <rect x="0" y="0" width="300" height="320" fill="url(#mr-home-zone)" />
      <rect x="300" y="0" width="300" height="320" fill="url(#mr-away-zone)" />

      <line x1="300" y1="0" x2="300" y2="320" stroke="#334155" strokeWidth="2" strokeDasharray="6 6" />
      <circle cx="300" cy="160" r="30" fill="none" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
      
      <g fontFamily="JetBrains Mono, monospace" fontSize="10" letterSpacing="2" fill="#475569" textAnchor="middle">
        {[1, 2, 3, 4, 5, 6, 7].map(n => (
          <text key={n} x={45 + n * 63} y="15">V{n}</text>
        ))}
      </g>

      {[
        { n: 1, cx: 80, cy: 60, name: 'Thorn' },
        { n: 2, cx: 80, cy: 160, name: 'Novak' },
        { n: 3, cx: 80, cy: 260, name: 'Penn' },
        { n: 5, cx: 180, cy: 120, name: 'Zane' },
        { n: 6, cx: 180, cy: 200, name: 'Reed' },
        { n: 7, cx: 250, cy: 160, name: 'Halsey' }
      ].map(p => {
        const isZane = p.n === 5;
        const glowing = isZane && hot === 'catch';
        return (
          <g key={'h'+p.n}>
            {glowing && <circle cx={p.cx} cy={p.cy} r="26" fill="url(#mr-catch-glow)" />}
            <circle cx={p.cx} cy={p.cy} r="14" fill="#0f172a" stroke="#f43f5e" strokeWidth="2" />
            {glowing && <circle cx={p.cx} cy={p.cy} r="20" fill="none" stroke="#22d3ee" strokeWidth="2" strokeDasharray="4 4" />}
            <text x={p.cx} y={p.cy + 4} textAnchor="middle" fontFamily="Oswald, sans-serif" fontSize="12" fill="#fff">{p.n}</text>
            <text x={p.cx} y={p.cy + 26} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="#f43f5e">{p.name.toUpperCase()}</text>
          </g>
        );
      })}

      {[
        { n: 1, cx: 520, cy: 60, name: 'Vega' },
        { n: 2, cx: 520, cy: 160, name: 'Holm' },
        { n: 3, cx: 520, cy: 260, name: 'Yoon' },
        { n: 4, cx: 420, cy: 120, name: 'Park' },
        { n: 5, cx: 420, cy: 200, name: 'Reed' },
        { n: 6, cx: 350, cy: 160, name: 'Drake' }
      ].map(p => {
        const isPark = p.n === 4;
        const benched = isPark && hot === 'catch';
        return (
          <g key={'a'+p.n} opacity={benched ? 0.35 : 1}>
            <circle cx={p.cx} cy={p.cy} r="14" fill="#0f172a" stroke="#3b82f6" strokeWidth="2" />
            <text x={p.cx} y={p.cy + 4} textAnchor="middle" fontFamily="Oswald, sans-serif" fontSize="12" fill="#fff">{p.n}</text>
            <text x={p.cx} y={p.cy + 26} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="#3b82f6">{p.name.toUpperCase()}</text>
            {benched && <line x1={p.cx - 14} y1={p.cy - 14} x2={p.cx + 14} y2={p.cy + 14} stroke="#f43f5e" strokeWidth="2" />}
          </g>
        );
      })}

      {hot === 'throw' && (
        <path d="M 80 60 Q 250 20 420 120" fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="6 4" markerEnd="url(#arrow)" />
      )}
      {hot === 'elim' && (
        <path d="M 250 160 Q 300 200 520 160" fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="6 4" markerEnd="url(#arrow)" />
      )}
      {hot === 'catch' && (
        <path d="M 420 120 Q 300 100 180 120" fill="none" stroke="#22d3ee" strokeWidth="2" strokeDasharray="6 4" markerEnd="url(#arrow)" />
      )}
      {hot === 'final' && (
        <g>
          <text x="300" y="160" textAnchor="middle" fontFamily="Oswald, sans-serif" fontSize="48" fontWeight="800" fill="#10b981" letterSpacing="4">FINAL</text>
          <text x="300" y="190" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="14" fill="#10b981" letterSpacing="2">— 8-0 SURVIVORS —</text>
        </g>
      )}
    </svg>
  );
};

const PossessionBar = ({ events, activeIdx, onJump }) => {
  const owners = ['rose', 'rose', 'cyan', 'rose', 'rose', 'rose', 'rose']; 
  return (
    <div className="mr-poss-bar-wrap">
      <div className="mr-poss-header">
        <span className="dm-kicker">POSSESSION TIMELINE</span>
        <span className="mr-poss-tally">
          <span className="home-val">71%</span> <span className="home-lbl">SOLSTICE</span> 
          <span className="sep">·</span> 
          <span className="away-val">29%</span> <span className="away-lbl">CYPHERS</span>
        </span>
      </div>
      <div className="mr-poss-cells">
        {events.map((ev, i) => {
          const isSwing = i === 2;
          const owner = owners[i];
          const active = i === activeIdx;
          return (
            <button key={i} className={`mr-poss-cell ${active ? 'active' : ''} owner-${owner}`} onClick={() => onJump(i)}>
              <span className="mr-poss-idx">{(i + 1).toString().padStart(2, '0')}</span>
              {isSwing && <div className="swing-pip" />}
            </button>
          );
        })}
      </div>
    </div>
  );
};

const ReplayScoreboard = ({ data }) => {
  const mc = data.aftermath.matchCard;
  return (
    <div className="mr-scoreboard">
      <div className="mr-sb-team home">
        <div className="mr-sb-meta">HOME</div>
        <div className="mr-sb-name">{mc.home}</div>
        <div className="mr-sb-tag">CATCH-HEAVY ATTRITION</div>
      </div>
      <div className="mr-sb-score">
        <span className="mr-sb-num home-num">{mc.homeSurv}</span>
        <div className="mr-sb-center">
          <span className="mr-sb-pill">FINAL · W04</span>
          <span className="mr-sb-margin">+{mc.homeSurv - mc.awaySurv} SURVIVORS</span>
        </div>
        <span className="mr-sb-num away-num">{mc.awaySurv}</span>
      </div>
      <div className="mr-sb-team away">
        <div className="mr-sb-meta">AWAY</div>
        <div className="mr-sb-name">{mc.away}</div>
        <div className="mr-sb-tag">POWER-ARM AGGRO</div>
      </div>
    </div>
  );
};

const TurningPoint = ({ text, onShowCatch }) => (
  <div className="mr-turning-point">
    <div className="mr-tp-content">
      <span className="dm-kicker">TURNING POINT</span>
      <p>{text}</p>
    </div>
    <button className="mr-tp-btn" onClick={onShowCatch}>
      Jump to Catch <span className="arrow">▸</span>
    </button>
  </div>
);

const EventLog = ({ events, activeIdx, onSelect }) => {
  const grouped = useMemoMR(() => {
    const out = [];
    let lastPhase = null;
    events.forEach((ev, i) => {
      const phase = ev.phase.split(' --')[0];
      if (phase !== lastPhase) {
        out.push({ kind: 'group', phase });
        lastPhase = phase;
      }
      out.push({ kind: 'event', ev, idx: i });
    });
    return out;
  }, [events]);

  return (
    <div className="mr-log-scroll">
      {grouped.map((row, i) => {
        if (row.kind === 'group') {
          return <div key={`g${i}`} className="mr-log-group">{row.phase}</div>;
        }
        const { ev, idx } = row;
        const time = ev.phase.split('--')[1]?.trim() || '00:00';
        return (
          <button key={idx} className={`mr-log-item ${idx === activeIdx ? 'active' : ''}`} onClick={() => onSelect(idx)}>
            <div className="mr-log-tick">
              <span>{(idx + 1).toString().padStart(2, '0')}</span>
              <span className="time">{time}</span>
            </div>
            <div className="mr-log-body">
              <div className="mr-log-header">
                <span className={`mr-chip mr-chip-${ev.type}`}>{ev.type.toUpperCase()}</span>
                <span className="mr-title">{ev.title}</span>
              </div>
              {ev.details && (
                <div className="mr-evidence">
                  {ev.details.map((d, j) => <div key={j}>{d}</div>)}
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
};

const MatchReplayScreen = ({ data }) => {
  const events = data.replayEvents;
  const [activeIdx, setActiveIdx] = useStateMR(2);
  const [playing, setPlaying] = useStateMR(false);
  const active = events[activeIdx] || events[0];

  useEffectMR(() => {
    if (!playing) return;
    if (activeIdx >= events.length - 1) { setPlaying(false); return; }
    const t = setTimeout(() => setActiveIdx(i => i + 1), 1200);
    return () => clearTimeout(t);
  }, [playing, activeIdx, events.length]);

  return (
    <div className="max-content mr-shell">
      <ReplayScoreboard data={data} />
      <TurningPoint text={data.aftermath.turningPoint} onShowCatch={() => { setActiveIdx(2); setPlaying(false); }} />

      <div className="mr-grid">
        <div className="mr-stage">
          <div className="mr-now-showing">
            <span className="dm-kicker">NOW SHOWING</span>
            <span className="sep">·</span>
            <span className="phase">{active.phase}</span>
            <span className="sep">·</span>
            <span className="title">{active.title}</span>
          </div>
          <DarkCourt activeEvent={active} />
          <PossessionBar events={events} activeIdx={activeIdx} onJump={setActiveIdx} />
          
          <div className="mr-transport">
            <div className="mr-controls">
              <button onClick={() => { setActiveIdx(0); setPlaying(false); }}>⏮</button>
              <button onClick={() => { setActiveIdx(Math.max(0, activeIdx - 1)); setPlaying(false); }}>◂</button>
              <button className={`play-btn ${playing ? 'playing' : ''}`} onClick={() => setPlaying(!playing)}>
                {playing ? '❚❚' : '▶'}
              </button>
              <button onClick={() => { setActiveIdx(Math.min(events.length - 1, activeIdx + 1)); setPlaying(false); }}>▸</button>
              <button onClick={() => { setActiveIdx(events.length - 1); setPlaying(false); }}>⏭</button>
            </div>
            <div className="mr-meta">
              <span>EVENT <b>{(activeIdx + 1).toString().padStart(2, '0')}/{events.length.toString().padStart(2, '0')}</b></span>
              <span className="sep">·</span>
              <span>SPEED · 1.0×</span>
            </div>
          </div>
        </div>

        <div className="mr-sidebar">
          <div className="mr-sidebar-header">
            <span className="dm-kicker">EVENT LOG</span>
            <h3>Match Flow</h3>
          </div>
          <EventLog events={events} activeIdx={activeIdx} onSelect={setActiveIdx} />
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { MatchReplayScreen });
