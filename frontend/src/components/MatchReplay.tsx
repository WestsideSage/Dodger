import { memo, useMemo, useEffect, useRef, useState } from 'react';

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

const PossessionBar = ({ events, activeIdx, onJump, homeClubId }: { events: ReplayProofEvent[], activeIdx: number, onJump: (i: number) => void, homeClubId: string }) => {
  return (
    <div className="mr-possession">
      <div className="mr-possession-head">
        <span className="mr-possession-kicker">POSSESSION TIMELINE</span>
        <span className="mr-possession-tally">
          <span className="dim">Play by Play</span>
        </span>
      </div>
      <div className="mr-possession-strip">
        {events.map((ev, i) => {
          const isSwing = ev.is_key_play;
          const owner = isSwing ? 'swing' : (ev.offense_club_id === homeClubId ? 'home' : 'away');
          const active = i === activeIdx;
          return (
            <button key={i} className={`mr-poss-cell owner-${owner} ${active ? 'is-active' : ''}`} onClick={() => onJump(i)}>
              <span className="num">{(i + 1).toString().padStart(2, '0')}</span>
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

  const isOfficial = data.scoring_model && data.scoring_model !== 'legacy';
  const scoreHome = isOfficial ? (data.home_game_points ?? 0) : homeSurv;
  const scoreAway = isOfficial ? (data.away_game_points ?? 0) : awaySurv;
  const scoreDiff = Math.abs(scoreHome - scoreAway);
  const marginLabel = isOfficial ? `+${scoreDiff} GAME PTS` : `+${diff} SURVIVORS`;
  const formatTag = isOfficial ? `USAD ${data.scoring_model?.toUpperCase()} · W${String(data.week).padStart(2, '0')}` : `FINAL · W${String(data.week).padStart(2, '0')}`;

  return (
    <div className="mr-scoreboard">
      <div className="mr-team home">
        <div className="mr-team-rec">HOME</div>
        <div className="mr-team-name">{homeName}</div>
        <div className="mr-team-tag">PROGRAM</div>
      </div>
      <div className="mr-score">
        <span className="mr-score-num home">{scoreHome}</span>
        <div className="mr-score-divider">
          <span className="mr-final-tag">{formatTag}</span>
          <span className="mr-vs">VS</span>
          <span className="mr-margin">{marginLabel}</span>
        </div>
        <span className="mr-score-num away">{scoreAway}</span>
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
  <div className="mr-turning">
    <div>
      <span className="mr-turning-kicker">TURNING POINT</span>
      <p className="mr-turning-text">{text}</p>
    </div>
    <button className="mr-turning-jump" onClick={onShowCatch}>
      Jump to Key Play <span className="arrow">▸</span>
    </button>
  </div>
);

const chipClass = (resolution: string) => {
  const r = resolution.toLowerCase();
  if (r === 'caught' || r === 'catch') return 'chip-catch';
  if (r === 'eliminated' || r === 'hit' || r === 'failed_catch') return 'chip-elim';
  if (r === 'dodged') return 'chip-throw';
  return 'chip-throw';
};

const EventLog = ({ events, activeIdx, onSelect }: { events: ReplayProofEvent[], activeIdx: number, onSelect: (i: number) => void }) => {
  const activeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [activeIdx]);

  return (
    <div className="mr-log">
      {events.map((ev, idx) => {
        const state = idx === activeIdx ? 'is-active' : idx < activeIdx ? 'is-past' : 'is-future';
        return (
          <button
            key={idx}
            ref={idx === activeIdx ? activeRef : undefined}
            className={`mr-log-event ${state}`}
            onClick={() => onSelect(idx)}
            aria-current={idx === activeIdx ? 'step' : undefined}
          >
            <div className="mr-log-rail">
              <span className="mr-log-tick">{(idx + 1).toString().padStart(2, '0')}</span>
              <span className="mr-log-time">T{ev.tick}</span>
            </div>
            <div className="mr-log-body">
              <div className="mr-log-row">
                <span className={`mr-log-chip ${chipClass(ev.resolution)}`}>{ev.resolution.toUpperCase()}</span>
                <span className="mr-log-title">{ev.summary}</span>
              </div>
              {ev.detail && (
                <ul className="mr-log-evidence">
                  <li>{ev.detail}</li>
                </ul>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
};

interface CurrentEventCardProps {
  event: ReplayProofEvent | undefined;
  prevEvent: ReplayProofEvent | undefined;
  homeClubId: string;
  homeName: string;
  awayName: string;
  index: number;
  total: number;
}

const CurrentEventCard = ({ event, prevEvent, homeClubId, homeName, awayName, index, total }: CurrentEventCardProps) => {
  if (!event) {
    return (
      <aside className="mr-current-card" data-testid="replay-current-event" aria-label="Current event">
        <div className="mr-current-head">
          <span className="mr-current-kicker">CURRENT EVENT</span>
          <span className="mr-current-pos">--/--</span>
        </div>
        <p className="mr-current-empty">Press play to begin the sequence.</p>
      </aside>
    );
  }

  const isHomeOffense = event.offense_club_id === homeClubId;
  const offenseName = isHomeOffense ? homeName : awayName;
  const defenseName = isHomeOffense ? awayName : homeName;
  const chip = chipClass(event.resolution);
  const score = event.score_state;
  const prevScore = prevEvent?.score_state;
  const homeNow = score?.home_living ?? null;
  const awayNow = score?.away_living ?? null;
  const homePrev = prevScore?.home_living ?? homeNow;
  const awayPrev = prevScore?.away_living ?? awayNow;
  const homeDelta = homeNow != null && homePrev != null ? homeNow - homePrev : 0;
  const awayDelta = awayNow != null && awayPrev != null ? awayNow - awayPrev : 0;
  const hasDelta = homeDelta !== 0 || awayDelta !== 0;

  return (
    <aside className="mr-current-card" data-testid="replay-current-event" aria-label="Current event">
      <div className="mr-current-head">
        <span className="mr-current-kicker">CURRENT EVENT</span>
        <span className="mr-current-pos">{(index + 1).toString().padStart(2, '0')}/{total.toString().padStart(2, '0')}</span>
      </div>
      <div className="mr-current-row">
        <span className={`mr-log-chip ${chip}`}>{event.resolution.toUpperCase()}</span>
        <span className="mr-current-tick">TICK {event.tick}</span>
        {event.is_key_play && <span className="mr-current-keyplay">KEY PLAY</span>}
      </div>
      <p className="mr-current-summary">{event.summary}</p>
      {event.thrower_name && (
        <div className="mr-current-actors">
          <div className="mr-current-actor">
            <span className="role">THROW</span>
            <span className="name">{event.thrower_name}</span>
            <span className="club">{offenseName}</span>
          </div>
          {event.target_name && (
            <div className="mr-current-actor">
              <span className="role">TARGET</span>
              <span className="name">{event.target_name}</span>
              <span className="club">{defenseName}</span>
            </div>
          )}
        </div>
      )}
      {event.detail && <p className="mr-current-detail">{event.detail}</p>}
      {score && (
        <div className="mr-current-score">
          <span className="mr-current-score-lbl">SURVIVORS</span>
          <div className="mr-current-score-row">
            <span className="team home">
              {homeName}
              <b>{homeNow}</b>
              {hasDelta && homeDelta !== 0 && (
                <em className={homeDelta < 0 ? 'down' : 'up'}>{homeDelta > 0 ? `+${homeDelta}` : homeDelta}</em>
              )}
            </span>
            <span className="team away">
              {awayName}
              <b>{awayNow}</b>
              {hasDelta && awayDelta !== 0 && (
                <em className={awayDelta < 0 ? 'down' : 'up'}>{awayDelta > 0 ? `+${awayDelta}` : awayDelta}</em>
              )}
            </span>
          </div>
        </div>
      )}
    </aside>
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

    data.proof_events.forEach((pe) => {
      if (pe.thrower_id) {
        const isHome = pe.offense_club_id === data.home_club_id;
        regPlayer(pe.thrower_id, pe.thrower_name || pe.thrower_id, isHome ? data.home_club_id : data.away_club_id, isHome ? hIds : aIds);
      }
      if (pe.target_id) {
        const targetIsHome = pe.defense_club_id === data.home_club_id;
        regPlayer(pe.target_id, pe.target_name || pe.target_id, targetIsHome ? data.home_club_id : data.away_club_id, targetIsHome ? hIds : aIds);
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

      <div className="mr-stage">
        <div className="mr-active-readout">
          <span className="lbl">NOW SHOWING</span>
          <span className="sep" />
          <span className="val">TICK {currentEvent?.tick ?? 0}</span>
          <span className="sep" />
          <span className="title">{currentEvent?.summary || 'Match Start'}</span>
        </div>
        <div className="mr-court-row">
          <div className="mr-court-wrap">
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
          </div>
          <CurrentEventCard
            event={currentEvent}
            prevEvent={eventIndex > 0 ? data.proof_events[eventIndex - 1] : undefined}
            homeClubId={data.home_club_id}
            homeName={data.home_club_name || 'HOME'}
            awayName={data.away_club_name || 'AWAY'}
            index={eventIndex}
            total={totalEvents}
          />
        </div>
        <PossessionBar events={data.proof_events} activeIdx={eventIndex} onJump={setEventIndex} homeClubId={data.home_club_id} />

        <div className="mr-transport">
          <button className="mr-tbtn" aria-label="First" onClick={() => { setEventIndex(0); setIsPlaying(false); }}>⏮</button>
          <button className="mr-tbtn" aria-label="Previous" onClick={() => { setEventIndex(Math.max(0, eventIndex - 1)); setIsPlaying(false); }}>◂</button>
          <button className={`mr-tbtn mr-play ${isPlaying ? 'is-playing' : ''}`} aria-label={isPlaying ? 'Pause' : 'Play'} onClick={() => setIsPlaying(!isPlaying)}>
            {isPlaying ? '❚❚' : '▶'}
          </button>
          <button className="mr-tbtn" aria-label="Next" onClick={() => { setEventIndex(Math.min(totalEvents - 1, eventIndex + 1)); setIsPlaying(false); }}>▸</button>
          <button className="mr-tbtn" aria-label="Last" onClick={() => { setEventIndex(totalEvents - 1); setIsPlaying(false); }}>⏭</button>
          <span className="mr-transport-spd">Space · ◂ ▸</span>
          <span className="mr-transport-pos">
            EVENT <b>{(eventIndex + 1).toString().padStart(2, '0')}/{totalEvents.toString().padStart(2, '0')}</b>
          </span>
          <button className="mr-tbtn" aria-label="Close replay" onClick={onContinue} style={{ width: 'auto', padding: '0 12px', fontFamily: 'var(--font-display)', fontSize: '0.7rem', letterSpacing: '0.12em' }}>
            CLOSE
          </button>
        </div>
      </div>

      <div className="mr-sidebar-wrap">
        <div className="mr-sidebar-head">
          <span className="mr-sidebar-meta"><b>EVENT LOG</b></span>
          <div className="mr-sidebar-title">Match Flow</div>
        </div>
        <EventLog events={data.proof_events} activeIdx={eventIndex} onSelect={setEventIndex} />
      </div>
    </div>
  );
}

