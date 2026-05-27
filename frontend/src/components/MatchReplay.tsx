import { memo, useMemo, useEffect, useState } from 'react';

import type { MatchReplayResponse, ReplayProofEvent } from '../types';

interface PlayerInfo {
  id: string;
  name: string;
  label: string; // "F. LASTNAME"
  clubId: string;
}

interface Vec2 {
  x: number;
  y: number;
}

const COURT_W = 600;
const COURT_H = 320;
const PLAYER_R = 14;

function playerLabel(name: string): string {
  const parts = name.trim().split(' ');
  if (parts.length === 1) return parts[0].toUpperCase().slice(0, 7);
  const first = parts[0][0].toUpperCase();
  const last = parts[parts.length - 1].toUpperCase().slice(0, 6);
  return `${first}. ${last}`;
}

function getFormationPositions(ids: string[], side: 'left' | 'right', courtWidth: number, courtHeight: number): Map<string, Vec2> {
  const map = new Map<string, Vec2>();
  if (ids.length === 0) return map;

  const hMid = courtHeight / 2;
  const vGap = courtHeight / 3.2;

  // 2-column × 3-row formation
  const colX = {
    left:  [courtWidth / 2 - 55, courtWidth / 4],
    right: [courtWidth / 2 + 55, 3 * courtWidth / 4],
  };
  const rowY = [hMid - vGap, hMid, hMid + vGap];

  ids.forEach((id, i) => {
    const col = i < 3 ? 0 : 1;
    const row = i % 3;
    map.set(id, { x: colX[side][col], y: rowY[row] });
  });
  return map;
}

const resolutionColor = (r: string | null) =>
  r === 'eliminated' || r === 'hit' || r === 'failed_catch'
    ? '#f43f5e'
    : r === 'caught' || r === 'catch'
    ? '#22d3ee'
    : r === 'dodged'
    ? '#a3e635'
    : '#f97316';

const resolutionActionLabel = (r: string | null) =>
  r === 'eliminated' || r === 'hit' || r === 'failed_catch'
    ? 'OUT'
    : r === 'caught' || r === 'catch'
    ? 'CATCH'
    : r === 'dodged'
    ? 'DODGE'
    : '';

// ── UI Kit Integrated Court ───────────────────────────────────────────────────

interface DarkCourtProps {
  homeName: string;
  awayName: string;
  homeIds: string[];
  awayIds: string[];
  positions: Map<string, Vec2>;
  playerRegistry: Map<string, PlayerInfo>;
  eliminatedIds: Set<string>;
  throwerId: string | null;
  targetId: string | null;
  activeResolution: string | null;
  flashTargetId: string | null;
  ballAnimKey: string;
}

const DarkCourt = memo(function DarkCourt({
  homeIds,
  awayIds,
  positions,
  playerRegistry,
  eliminatedIds,
  throwerId,
  targetId,
  activeResolution,
  flashTargetId,
}: DarkCourtProps) {
  const throwerPos = throwerId ? positions.get(throwerId) : null;
  const targetPos = targetId ? positions.get(targetId) : null;
  const hasActiveThrow = !!(throwerId && targetId);

  const flashColor = resolutionColor(activeResolution);
  const outcomeLabel = resolutionActionLabel(activeResolution);
  
  const midX = throwerPos && targetPos ? (throwerPos.x + targetPos.x) / 2 : 0;
  const midY = throwerPos && targetPos ? (throwerPos.y + targetPos.y) / 2 : 0;

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
        <marker id="mr-arrow-orange" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
          <path d="M 0 0 L 7 3.5 L 0 7 z" fill="#f97316" opacity="0.75" />
        </marker>
        <marker id="mr-arrow-cyan" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
          <path d="M 0 0 L 7 3.5 L 0 7 z" fill="#22d3ee" opacity="0.75" />
        </marker>
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

      {/* Throw trajectory */}
      {throwerPos && targetPos && (
        <line
          x1={throwerPos.x} y1={throwerPos.y}
          x2={targetPos.x} y2={targetPos.y}
          stroke={activeResolution === 'caught' || activeResolution === 'catch' ? "#22d3ee" : "#f97316"}
          strokeWidth="2"
          strokeDasharray="6 4"
          markerEnd={activeResolution === 'caught' || activeResolution === 'catch' ? "url(#mr-arrow-cyan)" : "url(#mr-arrow-orange)"}
        />
      )}

      {/* Outcome label */}
      {hasActiveThrow && outcomeLabel && (
        <g>
          <rect x={midX - 28} y={midY - 18} width="56" height="20" rx="3" fill="#020617" opacity="0.85" />
          <text x={midX} y={midY - 4} textAnchor="middle" fill={flashColor} fontSize="11" fontFamily="Oswald, sans-serif" fontWeight="700" letterSpacing="2">
            {outcomeLabel}
          </text>
        </g>
      )}

      {/* Players */}
      {[...homeIds, ...awayIds].map((pid, idx) => {
        const pos = positions.get(pid);
        if (!pos) return null;
        const info = playerRegistry.get(pid);
        const isHome = homeIds.includes(pid);
        const isElim = eliminatedIds.has(pid);
        const isThrower = throwerId === pid;
        const isTarget = targetId === pid;
        const isFlash = flashTargetId === pid;
        const isActive = isThrower || isTarget;

        const opacity = hasActiveThrow ? (isActive ? 1 : isElim ? 0.35 : 0.22) : (isElim ? 0.35 : 1);
        const baseColor = isHome ? '#f43f5e' : '#3b82f6';
        
        const isCatchTarget = isTarget && (activeResolution === 'caught' || activeResolution === 'catch');
        const glowing = isCatchTarget && isFlash;

        return (
          <g key={pid} opacity={opacity}>
            {glowing && <circle cx={pos.x} cy={pos.y} r="26" fill="url(#mr-catch-glow)" />}
            <circle cx={pos.x} cy={pos.y} r={PLAYER_R} fill="#0f172a" stroke={baseColor} strokeWidth="2" />
            {glowing && <circle cx={pos.x} cy={pos.y} r="20" fill="none" stroke="#22d3ee" strokeWidth="2" strokeDasharray="4 4" />}
            <text x={pos.x} y={pos.y + 4} textAnchor="middle" fontFamily="Oswald, sans-serif" fontSize="12" fill="#fff">
              {isHome ? idx + 1 : idx - homeIds.length + 1}
            </text>
            <text x={pos.x} y={pos.y + 26} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fill={baseColor}>
              {info?.label || ''}
            </text>
            {isElim && <line x1={pos.x - 14} y1={pos.y - 14} x2={pos.x + 14} y2={pos.y + 14} stroke={baseColor} strokeWidth="2" />}
          </g>
        );
      })}
    </svg>
  );
});

// ── Components ──────────────────────────────────────────────────────────────

const PossessionBar = ({ events, activeIdx, onJump }: { events: ReplayProofEvent[], activeIdx: number, onJump: (i: number) => void }) => {
  return (
    <div className="mr-poss-bar-wrap">
      <div className="mr-poss-header">
        <span className="dm-kicker">POSSESSION TIMELINE</span>
        <span className="mr-poss-tally">
           <span className="dim">Play by Play</span>
        </span>
      </div>
      <div className="mr-poss-cells">
        {events.map((ev, i) => {
          const isSwing = ev.is_key_play;
          const owner = ev.offense_club_id === ev.target_id ? 'cyan' : 'rose';
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

const ReplayScoreboard = ({ data }: { data: MatchReplayResponse }) => {
  const homeName = data.home_club_name || 'HOME';
  const awayName = data.away_club_name || 'AWAY';
  const homeSurv = data.home_survivors ?? 0;
  const awaySurv = data.away_survivors ?? 0;
  const diff = Math.abs(homeSurv - awaySurv);

  return (
    <div className="mr-scoreboard">
      <div className="mr-team home">
        <div className="mr-team-rec">HOME</div>
        <div className="mr-team-name">{homeName}</div>
        <div className="mr-team-tag">PROGRAM</div>
      </div>
      <div className="mr-score">
        <span className="mr-score-num home">{homeSurv}</span>
        <div className="mr-score-divider">
          <span className="mr-final-tag">FINAL · W{String(data.week).padStart(2, '0')}</span>
          <span className="mr-vs">VS</span>
          <span className="mr-margin">+{diff} SURVIVORS</span>
        </div>
        <span className="mr-score-num away">{awaySurv}</span>
      </div>
      <div className="mr-team away">
        <div className="mr-team-rec">AWAY</div>
        <div className="mr-team-name">{awayName}</div>
        <div className="mr-team-tag">PROGRAM</div>
      </div>
    </div>
  );
};

const TurningPoint = ({ text, onShowCatch }: { text: string, onShowCatch: () => void }) => (
  <div className="mr-turning-point">
    <div className="mr-tp-content">
      <span className="dm-kicker">TURNING POINT</span>
      <p>{text}</p>
    </div>
    <button className="mr-tp-btn" onClick={onShowCatch}>
      Jump to Key Play <span className="arrow">▸</span>
    </button>
  </div>
);

const EventLog = ({ events, activeIdx, onSelect }: { events: ReplayProofEvent[], activeIdx: number, onSelect: (i: number) => void }) => {
  return (
    <div className="mr-log-scroll">
      {events.map((ev, idx) => {
        return (
          <button key={idx} className={`mr-log-item ${idx === activeIdx ? 'active' : ''}`} onClick={() => onSelect(idx)}>
            <div className="mr-log-tick">
              <span>{(idx + 1).toString().padStart(2, '0')}</span>
              <span className="time">{ev.tick}</span>
            </div>
            <div className="mr-log-body">
              <div className="mr-log-header">
                <span className={`mr-chip mr-chip-${ev.resolution}`}>{ev.resolution.toUpperCase()}</span>
                <span className="mr-title">{ev.summary}</span>
              </div>
              <div className="mr-evidence">
                <div>{ev.detail}</div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};

// ── MatchReplay Component ───────────────────────────────────────────────────

export default function MatchReplay({ data, onContinue }: { data: MatchReplayResponse; onContinue: () => void }) {
  // Start on the first key play so the NOW SHOWING caption agrees with the
  // TURNING POINT headline rather than landing on a meaningless tick-0 throw.
  const initialIdx = data.key_play_indices && data.key_play_indices.length > 0 ? data.key_play_indices[0] : 0;
  const [eventIndex, setEventIndex] = useState(initialIdx);
  const [isPlaying, setIsPlaying] = useState(false);

  const [activeResolution, setActiveResolution] = useState<string | null>(null);
  const [flashTargetId, setFlashTargetId] = useState<string | null>(null);
  const [ballAnimKey, setBallAnimKey] = useState<string>('init');

  // Autoplay on mount
  useEffect(() => {
    const t = setTimeout(() => setIsPlaying(true), 500);
    return () => clearTimeout(t);
  }, []);

  const {
    totalEvents,
    playerRegistry,
    homeIds,
    awayIds,
    positions,
  } = useMemo(() => {
    if (!data) return { totalEvents: 0, playerRegistry: new Map(), homeIds: [], awayIds: [], positions: new Map() };
    const reg = new Map<string, PlayerInfo>();
    const hIds: string[] = [];
    const aIds: string[] = [];

    const regPlayer = (id: string, name: string, cId: string, list: string[]) => {
      if (!reg.has(id)) {
        reg.set(id, { id, name, label: playerLabel(name), clubId: cId });
        list.push(id);
      }
    };

    data.events.forEach((ev) => {
      if (ev.event_type === 'match_start') {
        const hs = ev.state_diff.home_living as { id: string; name: string }[] | undefined;
        const as = ev.state_diff.away_living as { id: string; name: string }[] | undefined;
        hs?.forEach((p) => regPlayer(p.id, p.name, data.home_club_id, hIds));
        as?.forEach((p) => regPlayer(p.id, p.name, data.away_club_id, aIds));
      }
    });

    const pos = new Map<string, Vec2>();
    getFormationPositions(hIds, 'left', COURT_W, COURT_H).forEach((v, k) => pos.set(k, v));
    getFormationPositions(aIds, 'right', COURT_W, COURT_H).forEach((v, k) => pos.set(k, v));

    return {
      totalEvents: data.proof_events.length,
      playerRegistry: reg,
      homeIds: hIds,
      awayIds: aIds,
      positions: pos,
    };
  }, [data]);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA'
      ) {
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying((p) => !p);
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        setIsPlaying(false);
        setEventIndex((i) => Math.max(0, i - 1));
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        setIsPlaying(false);
        setEventIndex((i) => Math.min(totalEvents - 1, i + 1));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [totalEvents]);

  const { eliminatedIds, throwerId, targetId } = useMemo(() => {
    const elims = new Set<string>();
    if (!data || totalEvents === 0) return { eliminatedIds: elims, throwerId: null, targetId: null };

    for (let i = 0; i <= eventIndex; i++) {
      const p = data.proof_events[i];
      if (p?.score_state) {
        p.score_state.home_eliminated_player_ids.forEach((id) => elims.add(id));
        p.score_state.away_eliminated_player_ids.forEach((id) => elims.add(id));
      }
    }

    const current = data.proof_events[eventIndex];
    return {
      eliminatedIds: elims,
      throwerId: current ? current.thrower_id : null,
      targetId: current ? current.target_id : null,
    };
  }, [data, eventIndex, totalEvents]);

  useEffect(() => {
    const currentProof = data?.proof_events[eventIndex];
    if (!currentProof) return;

    const t0 = setTimeout(() => {
      setFlashTargetId(null);
      if (!currentProof.thrower_id) {
        setActiveResolution(null);
        return;
      }
      setActiveResolution(currentProof.resolution);
      setBallAnimKey(`ball-${currentProof.sequence_index}-${eventIndex}`);
    }, 0);

    if (!currentProof.thrower_id) {
      return () => clearTimeout(t0);
    }

    const t1 = setTimeout(() => setFlashTargetId(currentProof.target_id), 360);
    const t2 = setTimeout(() => setFlashTargetId(null), 860);
    return () => {
      clearTimeout(t0);
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [data, eventIndex]);

  // Auto-play loop
  useEffect(() => {
    if (!isPlaying) return;
    if (eventIndex >= totalEvents - 1) {
      const t = setTimeout(() => setIsPlaying(false), 0);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setEventIndex((i) => i + 1), 1200);
    return () => clearTimeout(t);
  }, [isPlaying, eventIndex, totalEvents]);

  const currentEvent = data.proof_events[eventIndex];
  const firstKeyPlayIdx = data.key_play_indices?.length > 0 ? data.key_play_indices[0] : 0;

  return (
    <div className="max-content mr-shell" data-screen-label="03 Dynasty">
      <ReplayScoreboard data={data} />
      <TurningPoint 
        text={data.report?.turning_point || "Crucial swing in momentum."} 
        onShowCatch={() => { setEventIndex(firstKeyPlayIdx); setIsPlaying(false); }} 
      />

      <div className="mr-grid">
        <div className="mr-stage">
          <div className="mr-now-showing">
            <span className="dm-kicker">NOW SHOWING</span>
            <span className="sep">·</span>
            <span className="phase">TICK {currentEvent?.tick || 0}</span>
            <span className="sep">·</span>
            <span className="title">{currentEvent?.summary || 'Match Start'}</span>
          </div>
          <DarkCourt 
            homeName={data.home_club_name}
            awayName={data.away_club_name}
            homeIds={homeIds}
            awayIds={awayIds}
            positions={positions}
            playerRegistry={playerRegistry}
            eliminatedIds={eliminatedIds}
            throwerId={throwerId}
            targetId={targetId}
            activeResolution={activeResolution}
            flashTargetId={flashTargetId}
            ballAnimKey={ballAnimKey}
          />
          <PossessionBar events={data.proof_events} activeIdx={eventIndex} onJump={setEventIndex} />
          
          <div className="mr-transport">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', alignItems: 'center' }}>
              <div className="mr-controls">
                <button onClick={() => { setEventIndex(0); setIsPlaying(false); }}>⏮</button>
                <button onClick={() => { setEventIndex(Math.max(0, eventIndex - 1)); setIsPlaying(false); }}>◂</button>
                <button className={`play-btn ${isPlaying ? 'playing' : ''}`} onClick={() => setIsPlaying(!isPlaying)}>
                  {isPlaying ? '❚❚' : '▶'}
                </button>
                <button onClick={() => { setEventIndex(Math.min(totalEvents - 1, eventIndex + 1)); setIsPlaying(false); }}>▸</button>
                <button onClick={() => { setEventIndex(totalEvents - 1); setIsPlaying(false); }}>⏭</button>
              </div>
              <span style={{ fontSize: '0.625rem', color: '#64748b', letterSpacing: '0.05em', textTransform: 'uppercase', fontFamily: 'var(--font-mono-data)' }}>
                Space play · ◂ ▸ step
              </span>
            </div>
            <div className="mr-meta">
              <span>EVENT <b>{(eventIndex + 1).toString().padStart(2, '0')}/{totalEvents.toString().padStart(2, '0')}</b></span>
              <span className="sep">·</span>
              <button onClick={onContinue} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontFamily: 'Oswald, sans-serif', fontSize: 13, letterSpacing: 1, textDecoration: 'underline' }}>
                CLOSE REPLAY
              </button>
            </div>
          </div>
        </div>

        <div className="mr-sidebar">
          <div className="mr-sidebar-header">
            <span className="dm-kicker">EVENT LOG</span>
            <h3>Match Flow</h3>
          </div>
          <EventLog events={data.proof_events} activeIdx={eventIndex} onSelect={setEventIndex} />
        </div>
      </div>
    </div>
  );
}

