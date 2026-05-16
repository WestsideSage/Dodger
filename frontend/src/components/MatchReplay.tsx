import { memo, useMemo, useEffect, useState, useCallback } from 'react';
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
const COURT_H = 280;
const PLAYER_R = 13;
const HOME_COLOR = '#f97316';
const AWAY_COLOR = '#06b6d4';

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

  // 2-column × 3-row formation: near-center column and back column
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

// ── Resolution helpers ─────────────────────────────────────────────────────

const resolutionColor = (r: string | null) =>
  r === 'eliminated'
    ? '#f43f5e'
    : r === 'caught'
    ? '#06b6d4'
    : r === 'dodged'
    ? '#a3e635'
    : '#f97316';

const resolutionActionLabel = (r: string | null) =>
  r === 'eliminated' ? 'OUT' : r === 'caught' ? 'CATCH' : r === 'dodged' ? 'DODGE' : '';

// ── Court SVG ──────────────────────────────────────────────────────────────

interface CourtViewProps {
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

const CourtView = memo(function CourtView({
  homeName,
  awayName,
  homeIds,
  awayIds,
  positions,
  playerRegistry,
  eliminatedIds,
  throwerId,
  targetId,
  activeResolution,
  flashTargetId,
  ballAnimKey,
}: CourtViewProps) {
  const throwerPos = throwerId ? positions.get(throwerId) : null;
  const targetPos = targetId ? positions.get(targetId) : null;
  const hasActiveThrow = !!(throwerId && targetId);

  const flashColor = resolutionColor(activeResolution);
  const outcomeLabel = resolutionActionLabel(activeResolution);

  // Midpoint for outcome label
  const midX = throwerPos && targetPos ? (throwerPos.x + targetPos.x) / 2 : 0;
  const midY = throwerPos && targetPos ? (throwerPos.y + targetPos.y) / 2 : 0;

  return (
    <svg
      viewBox={`0 0 ${COURT_W} ${COURT_H}`}
      style={{ width: '100%', height: 'auto', display: 'block' }}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <marker id="throw-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
          <path d="M 0 0 L 7 3.5 L 0 7 z" fill="#f97316" opacity={0.75} />
        </marker>
      </defs>

      {/* Court background */}
      <rect width={COURT_W} height={COURT_H} fill="#0f172a" rx={8} />
      {/* Half tints */}
      <rect x={0} y={0} width={COURT_W / 2} height={COURT_H} fill="rgba(249,115,22,0.05)" rx={8} />
      <rect x={COURT_W / 2} y={0} width={COURT_W / 2} height={COURT_H} fill="rgba(6,182,212,0.05)" rx={8} />
      {/* Court border */}
      <rect x={1} y={1} width={COURT_W - 2} height={COURT_H - 2} fill="none" stroke="#1e293b" strokeWidth={2} rx={8} />
      {/* Center line */}
      <line x1={COURT_W / 2} y1={16} x2={COURT_W / 2} y2={COURT_H - 16} stroke="#334155" strokeWidth={1.5} strokeDasharray="4 4" />
      <circle cx={COURT_W / 2} cy={COURT_H / 2} r={28} fill="none" stroke="#334155" strokeWidth={1.5} strokeDasharray="4 4" />

      {/* Team labels */}
      <text x={COURT_W * 0.25} y={14} textAnchor="middle" fill="#f97316" fontSize={9} fontFamily="Oswald, sans-serif" letterSpacing={1} opacity={0.7}>
        {homeName.toUpperCase()}
      </text>
      <text x={COURT_W * 0.75} y={14} textAnchor="middle" fill="#06b6d4" fontSize={9} fontFamily="Oswald, sans-serif" letterSpacing={1} opacity={0.7}>
        {awayName.toUpperCase()}
      </text>

      {/* Throw trajectory with arrowhead */}
      {throwerPos && targetPos && (
        <line
          x1={throwerPos.x}
          y1={throwerPos.y}
          x2={targetPos.x}
          y2={targetPos.y}
          stroke="#f97316"
          strokeWidth={2}
          strokeDasharray="5 3"
          opacity={0.65}
          markerEnd="url(#throw-arrow)"
        />
      )}

      {/* Outcome label at midpoint */}
      {hasActiveThrow && outcomeLabel && (
        <g>
          <rect
            x={midX - 28}
            y={midY - 18}
            width={56}
            height={20}
            rx={3}
            fill="#020617"
            opacity={0.85}
          />
          <text
            x={midX}
            y={midY - 4}
            textAnchor="middle"
            fill={flashColor}
            fontSize={11}
            fontFamily="Oswald, sans-serif"
            fontWeight={700}
            letterSpacing={2}
          >
            {outcomeLabel}
          </text>
        </g>
      )}

      {/* Players */}
      {[...homeIds, ...awayIds].map((pid) => {
        const pos = positions.get(pid);
        if (!pos) return null;
        const info = playerRegistry.get(pid);
        const isHome = homeIds.includes(pid);
        const isElim = eliminatedIds.has(pid);
        const isThrower = throwerId === pid;
        const isTarget = targetId === pid;
        const isFlash = flashTargetId === pid;
        const isActive = isThrower || isTarget;

        // Dim inactive players during an active throw
        // Eliminated stay at their visual weight; inactive alive players fade more
        const opacity = hasActiveThrow
          ? isActive
            ? 1
            : isElim
            ? 0.35
            : 0.22
          : isElim
          ? 0.4
          : 1;

        const baseColor = isHome ? HOME_COLOR : AWAY_COLOR;
        const strokeColor = isFlash
          ? resolutionColor(activeResolution)
          : isActive
          ? '#ffffff'
          : baseColor;
        const strokeW = isActive || isFlash ? 2.5 : 1.5;

        const sublabel = isThrower ? 'THROWS' : isTarget ? (outcomeLabel || '') : '';

        return (
          <g key={pid} opacity={opacity}>
            {/* Outer activity ring */}
            {isActive && !isElim && (
              <circle
                cx={pos.x}
                cy={pos.y}
                r={PLAYER_R + 6}
                fill="none"
                stroke={baseColor}
                strokeWidth={1.5}
                opacity={0.5}
              />
            )}

            {/* Flash ring on resolution */}
            {isFlash && (
              <circle cx={pos.x} cy={pos.y} r={PLAYER_R + 9} fill="none" stroke={resolutionColor(activeResolution)} strokeWidth={2} opacity={0.7}>
                <animate attributeName="r" from={PLAYER_R + 4} to={PLAYER_R + 16} dur="0.5s" fill="freeze" />
                <animate attributeName="opacity" from={0.8} to={0} dur="0.5s" fill="freeze" />
              </circle>
            )}

            {/* Player circle */}
            <circle
              cx={pos.x}
              cy={pos.y}
              r={PLAYER_R}
              fill={isElim ? '#0f172a' : `${baseColor}22`}
              stroke={isElim ? '#334155' : strokeColor}
              strokeWidth={isElim ? 1 : strokeW}
              style={!isElim ? { filter: `drop-shadow(0 0 10px ${baseColor})` } : undefined}
            />

            {/* Eliminated X */}
            {isElim && (
              <>
                <line x1={pos.x - 6} y1={pos.y - 6} x2={pos.x + 6} y2={pos.y + 6} stroke="#475569" strokeWidth={2} />
                <line x1={pos.x + 6} y1={pos.y - 6} x2={pos.x - 6} y2={pos.y + 6} stroke="#475569" strokeWidth={2} />
              </>
            )}

            {/* Player name label */}
            {!isElim && (
              <text
                x={pos.x}
                y={pos.y + 4}
                textAnchor="middle"
                fill="#ffffff"
                fontSize={7}
                fontFamily="Oswald, sans-serif"
                fontWeight={600}
                letterSpacing={0.3}
              >
                {info ? info.label.split('. ')[1] ?? info.label : pid.slice(0, 4)}
              </text>
            )}

            {/* Active player sublabel (THROWS / CATCH / DODGE / OUT) */}
            {sublabel && !isElim && (
              <text
                x={pos.x}
                y={pos.y + PLAYER_R + 11}
                textAnchor="middle"
                fill={isThrower ? '#f97316' : resolutionColor(activeResolution)}
                fontSize={7}
                fontFamily="Oswald, sans-serif"
                letterSpacing={1}
              >
                {sublabel}
              </text>
            )}
          </g>
        );
      })}

      {/* Ball animation */}
      {throwerPos && targetPos && (
        <g key={ballAnimKey}>
          <circle cx={0} cy={0} r={5} fill="#ffffff">
            <animateMotion
              dur="0.35s"
              fill="freeze"
              path={`M ${throwerPos.x},${throwerPos.y} L ${targetPos.x},${targetPos.y}`}
              calcMode="spline"
              keyTimes="0;1"
              keySplines="0.25 0.1 0.25 1"
            />
          </circle>
        </g>
      )}
    </svg>
  );
});

// ── Score Header ───────────────────────────────────────────────────────────

function ScoreHeader({
  homeName,
  awayName,
  homeLiving,
  awayLiving,
  week,
  winnerName,
  winnerClubId,
  homeClubId,
}: {
  homeName: string;
  awayName: string;
  homeLiving: number;
  awayLiving: number;
  week: number;
  winnerName: string | null;
  winnerClubId: string | null;
  homeClubId: string;
}) {
  const homeIsWinner = winnerClubId === homeClubId;

  return (
    <div
      style={{
        background: '#0f172a',
        borderBottom: '1px solid #1e293b',
        borderRadius: '8px 8px 0 0',
      }}
    >
      {winnerName && (
        <div
          style={{
            textAlign: 'center',
            padding: '4px',
            background: 'rgba(249,115,22,0.08)',
            borderBottom: '1px solid rgba(249,115,22,0.2)',
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.7rem',
            color: '#f97316',
            letterSpacing: '2px',
          }}
        >
          ★ {winnerName.toUpperCase()} WIN
        </div>
      )}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
        }}
      >
        <div
          style={{
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.85rem',
            color: '#f97316',
            letterSpacing: '1px',
          }}
        >
          {homeName.toUpperCase()}
        </div>
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              fontFamily: 'Oswald, sans-serif',
              fontSize: '1.4rem',
              fontWeight: 700,
              letterSpacing: '3px',
              color: '#fff',
            }}
          >
            <span style={{ opacity: winnerClubId && !homeIsWinner ? 0.45 : 1, color: '#f97316' }}>
              {homeLiving}
            </span>
            {' '}
            <span style={{ color: '#334155', fontSize: '0.9rem' }}>—</span>
            {' '}
            <span style={{ opacity: winnerClubId && homeIsWinner ? 0.45 : 1, color: '#22d3ee' }}>
              {awayLiving}
            </span>
          </div>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.55rem',
              color: '#334155',
              letterSpacing: '2px',
              marginTop: '2px',
            }}
          >
            WEEK {week}
          </div>
        </div>
        <div
          style={{
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.85rem',
            color: '#22d3ee',
            letterSpacing: '1px',
            textAlign: 'right',
          }}
        >
          {awayName.toUpperCase()}
        </div>
      </div>
    </div>
  );
}

// ── Event Card ─────────────────────────────────────────────────────────────

function EventCard({
  label,
  detail,
  eventType,
  isKeyPlay,
}: {
  label: string;
  detail: string;
  eventType: string;
  isKeyPlay: boolean;
}) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
        {isKeyPlay && (
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#f59e0b', background: 'rgba(245,158,11,0.1)', padding: '1px 5px', borderRadius: 3, letterSpacing: 1 }}>
            KEY PLAY
          </span>
        )}
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#475569', letterSpacing: 1, textTransform: 'uppercase' as const }}>
          {eventType.replace(/_/g, ' ')}
        </span>
      </div>
      <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: 15, color: '#ffffff', letterSpacing: 0.5 }}>
        {label}
      </div>
      {detail && (
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#94a3b8', marginTop: 3, lineHeight: 1.4 }}>
          {detail}
        </div>
      )}
    </>
  );
}

// ── Play-by-Play Panel ──────────────────────────────────────────────────────

function PlayByPlayPanel({
  events,
  currentIndex,
}: {
  events: ReplayProofEvent[];
  currentIndex: number;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {events.slice(0, currentIndex + 1).map((ev, i) => (
        <div key={i} className="dm-feed-item" style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '0.75rem', borderRadius: '4px', fontSize: '0.875rem' }}>
          <span className="dm-time" style={{ color: '#64748b', fontFamily: 'var(--font-mono-data)', marginRight: '0.5rem', fontSize: '0.75rem' }}>PLAY {i + 1}</span>
          <span style={{ color: '#e2e8f0' }}>{ev.summary}</span>
        </div>
      ))}
    </div>
  );
}

// ── Stats Panel ────────────────────────────────────────────────────────────

const StatsPanel = memo(function StatsPanel({ data }: { data: MatchReplayResponse }) {
  const { report } = data;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 12px' }}>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#f59e0b', letterSpacing: 2, marginBottom: 4 }}>TURNING POINT</div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
          {report.turning_point || '—'}
        </div>
      </div>

      {report.top_performers.length > 0 && (
        <div>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#64748b', letterSpacing: 2, marginBottom: 6 }}>TOP PERFORMERS</div>
          {report.top_performers.slice(0, 5).map((p) => (
            <div key={p.player_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #1e293b' }}>
              <span style={{ fontFamily: 'Oswald, sans-serif', fontSize: 13, color: '#e2e8f0' }}>{p.player_name}</span>
              <div style={{ display: 'flex', gap: 8, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>
                {p.eliminations_by_throw > 0 && <span style={{ color: '#f97316' }}>{p.eliminations_by_throw}K</span>}
                {p.catches_made > 0 && <span style={{ color: '#06b6d4' }}>{p.catches_made}C</span>}
                {p.dodges_successful > 0 && <span style={{ color: '#a3e635' }}>{p.dodges_successful}D</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {report.evidence_lanes?.map((lane, i) => (
        <div key={i} style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 12px' }}>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#64748b', letterSpacing: 2, marginBottom: 6 }}>{lane.title.toUpperCase()}</div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>{lane.summary}</div>
          {lane.items.map((item, j) => (
            <div key={j} style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#64748b', paddingLeft: 8, borderLeft: '2px solid #1e293b', marginTop: 3 }}>
              {item}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
});

// ── Key Plays Panel ────────────────────────────────────────────────────────

function KeyPlaysPanel({ data, currentIndex, onJump }: { data: MatchReplayResponse; currentIndex: number; onJump: (i: number) => void }) {
  const keyEvents = data.key_play_indices.map((i) => ({ index: i, event: data.events[i] })).filter((e) => e.event);
  if (keyEvents.length === 0) {
    return <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#475569', textAlign: 'center', padding: 24 }}>No key plays recorded.</div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {keyEvents.map(({ index, event }) => {
        const isActive = currentIndex === index;
        return (
          <button
            key={index}
            onClick={() => onJump(index)}
            style={{ background: isActive ? 'rgba(245,158,11,0.12)' : '#0f172a', border: `1px solid ${isActive ? '#f59e0b' : '#1e293b'}`, borderRadius: 6, padding: '8px 12px', textAlign: 'left', cursor: 'pointer', width: '100%' }}
          >
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#64748b', marginBottom: 2 }}>EVENT #{index + 1}</div>
            <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: 13, color: isActive ? '#f59e0b' : '#e2e8f0' }}>{event.label}</div>
          </button>
        );
      })}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function MatchReplay({ data, onContinue }: { data: MatchReplayResponse; onContinue: () => void }) {
  const [eventIndex, setEventIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState<'Fast' | 'Normal' | 'Slow'>('Normal');
  const [activeTab, setActiveTab] = useState<'pbp' | 'keyplays' | 'stats'>('pbp');
  const [flashTargetId, setFlashTargetId] = useState<string | null>(null);
  const [activeResolution, setActiveResolution] = useState<string | null>(null);
  const [ballAnimKey, setBallAnimKey] = useState('ball-init');

  const totalEvents = data.events.length;

  // Player registry from proof events
  const playerRegistry = useMemo(() => {
    const reg = new Map<string, PlayerInfo>();
    for (const pe of data.proof_events) {
      if (!reg.has(pe.thrower_id)) {
        reg.set(pe.thrower_id, { id: pe.thrower_id, name: pe.thrower_name, label: playerLabel(pe.thrower_name), clubId: pe.offense_club_id });
      }
      if (!reg.has(pe.target_id)) {
        reg.set(pe.target_id, { id: pe.target_id, name: pe.target_name, label: playerLabel(pe.target_name), clubId: pe.defense_club_id });
      }
    }
    return reg;
  }, [data.proof_events]);

  const { homeIds, awayIds } = useMemo(() => {
    const home: string[] = [];
    const away: string[] = [];
    for (const [id, info] of playerRegistry.entries()) {
      if (info.clubId === data.home_club_id) home.push(id);
      else away.push(id);
    }
    home.sort();
    away.sort();
    return { homeIds: home, awayIds: away };
  }, [playerRegistry, data.home_club_id]);

  const positions = useMemo(() => {
    const homePos = getFormationPositions(homeIds, 'left', COURT_W, COURT_H);
    const awayPos = getFormationPositions(awayIds, 'right', COURT_W, COURT_H);
    return new Map([...homePos, ...awayPos]);
  }, [homeIds, awayIds]);

  const currentEvent = data.events[eventIndex] ?? data.events[0];

  // Last proof event at or before current index
  const currentProof = useMemo<ReplayProofEvent | null>(() => {
    let best: ReplayProofEvent | null = null;
    for (const pe of data.proof_events) {
      if (pe.sequence_index <= eventIndex) best = pe;
      else break;
    }
    return best;
  }, [data.proof_events, eventIndex]);

  const scoreState = currentProof?.score_state ?? null;
  const homeLiving = scoreState?.home_living ?? homeIds.length;
  const awayLiving = scoreState?.away_living ?? awayIds.length;

  const eliminatedIds = useMemo(() => {
    if (!scoreState) return new Set<string>();
    return new Set([...scoreState.home_eliminated_player_ids, ...scoreState.away_eliminated_player_ids]);
  }, [scoreState]);

  const isThrowEvent = currentEvent?.event_type === 'throw';
  const throwerId = isThrowEvent && currentProof ? currentProof.thrower_id : null;
  const targetId = isThrowEvent && currentProof ? currentProof.target_id : null;

  // Determine if we're at or past game end
  const matchIsComplete = useMemo(() => {
    for (let i = 0; i <= eventIndex; i++) {
      const et = data.events[i]?.event_type;
      if (et === 'match_end') return true;
    }
    return false;
  }, [data.events, eventIndex]);

  const winnerName = matchIsComplete ? (data.winner_name || data.report?.winner_name || null) : null;

  // Flash / resolution effect
  useEffect(() => {
    const t0 = setTimeout(() => {
      setFlashTargetId(null);
      // Keep activeResolution for label display (clear only on next event change)
      if (!isThrowEvent || !currentProof) {
        setActiveResolution(null);
        return;
      }
      setActiveResolution(currentProof.resolution);
      setBallAnimKey(`ball-${currentProof.sequence_index}-${eventIndex}`);
    }, 0);

    if (!isThrowEvent || !currentProof) {
      return () => clearTimeout(t0);
    }

    const t1 = setTimeout(() => setFlashTargetId(currentProof.target_id), 360);
    const t2 = setTimeout(() => setFlashTargetId(null), 860);
    return () => {
      clearTimeout(t0);
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [currentProof, eventIndex, isThrowEvent]);

  // Auto-play
  useEffect(() => {
    if (!isPlaying) return;
    if (eventIndex >= totalEvents - 1) {
      const t = setTimeout(() => setIsPlaying(false), 0);
      return () => clearTimeout(t);
    }
    const speedDivisor = playSpeed === 'Normal' ? 3 : 1;
    const t = setTimeout(() => setEventIndex((i) => i + 1), 900 / speedDivisor);
    return () => clearTimeout(t);
  }, [isPlaying, eventIndex, playSpeed, totalEvents]);

  const stepBack = useCallback(() => { setIsPlaying(false); setEventIndex((i) => Math.max(0, i - 1)); }, []);
  const stepForward = useCallback(() => { setIsPlaying(false); setEventIndex((i) => Math.min(totalEvents - 1, i + 1)); }, [totalEvents]);
  const togglePlay = useCallback(() => setIsPlaying((p) => !p), []);
  const cycleSpeed = useCallback(() => {
    setPlaySpeed((speed) => {
      const nextSpeed = speed === 'Normal' ? 'Fast' : speed === 'Fast' ? 'Slow' : 'Normal';
      if (nextSpeed === 'Fast') {
        setEventIndex(totalEvents - 1);
        setIsPlaying(false);
      }
      return nextSpeed;
    });
  }, [totalEvents]);

  const jumpToKeyEvent = useCallback(() => {
    const kp = data.key_play_indices;
    if (kp.length === 0) return;
    const next = kp.find((i) => i > eventIndex) ?? kp[0];
    setEventIndex(next);
    setIsPlaying(false);
  }, [data.key_play_indices, eventIndex]);

  const jumpTo = useCallback((i: number) => { setEventIndex(i); setIsPlaying(false); setActiveTab('pbp'); }, []);

  const progress = totalEvents > 1 ? eventIndex / (totalEvents - 1) : 0;
  const isKeyPlay = data.key_play_indices.includes(eventIndex);
  const hasCourtData = playerRegistry.size > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', overflow: 'visible' }}>
      <ScoreHeader
        homeName={data.home_club_name}
        awayName={data.away_club_name}
        homeLiving={homeLiving}
        awayLiving={awayLiving}
        week={data.week}
        winnerName={winnerName}
        winnerClubId={data.winner_club_id}
        homeClubId={data.home_club_id}
      />

      {/* Court — full width */}
      <div style={{ background: '#060d1a', padding: '8px 0 4px' }}>
        {hasCourtData ? (
          <CourtView
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
        ) : (
          <div
            style={{
              height: 180,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#0f172a',
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              color: '#475569',
            }}
          >
            No player tracking data available.
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="dm-replay-controls" style={{ padding: '6px 12px' }}>
        <button aria-label="Previous replay event" onClick={stepBack} disabled={eventIndex === 0} style={{ background: 'transparent', border: '1px solid #334155', borderRadius: 4, color: eventIndex === 0 ? '#334155' : '#94a3b8', padding: '4px 10px', cursor: eventIndex === 0 ? 'default' : 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>{'<'}</button>
        <button aria-label={isPlaying ? 'Pause replay' : 'Play replay'} onClick={togglePlay} style={{ background: isPlaying ? '#1e293b' : '#f97316', border: 'none', borderRadius: 4, color: '#ffffff', padding: '4px 14px', cursor: 'pointer', fontFamily: 'Oswald, sans-serif', fontSize: 13, letterSpacing: 1 }}>
          {isPlaying ? 'PAUSE' : 'PLAY'}
        </button>
        <button aria-label="Next replay event" onClick={stepForward} disabled={eventIndex >= totalEvents - 1} style={{ background: 'transparent', border: '1px solid #334155', borderRadius: 4, color: eventIndex >= totalEvents - 1 ? '#334155' : '#94a3b8', padding: '4px 10px', cursor: eventIndex >= totalEvents - 1 ? 'default' : 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>{'>'}</button>
        <button onClick={cycleSpeed} style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 4, color: '#f97316', padding: '4px 10px', cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, letterSpacing: 1 }}>{playSpeed}</button>
        <div
          className="dm-replay-scrubber"
          style={{ height: 8, background: '#1e293b', borderRadius: 4, cursor: 'pointer', position: 'relative', flex: 1 }}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            setEventIndex(Math.round(((e.clientX - rect.left) / rect.width) * (totalEvents - 1)));
            setIsPlaying(false);
          }}
        >
          <div style={{ height: '100%', width: `${progress * 100}%`, background: '#f97316', borderRadius: 4, transition: 'width 0.1s' }} />
          {data.key_play_indices.map((ki) => (
            <div key={ki} style={{ position: 'absolute', top: -2, left: `${(ki / (totalEvents - 1)) * 100}%`, width: 3, height: 12, background: '#f59e0b', borderRadius: 1.5, transform: 'translateX(-50%)' }} />
          ))}
        </div>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#475569', whiteSpace: 'nowrap' as const }}>
          {eventIndex + 1} / {totalEvents}
        </span>
        {data.key_play_indices.length > 0 && (
          <button aria-label="Next key replay event" onClick={jumpToKeyEvent} style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid #f59e0b44', borderRadius: 4, color: '#f59e0b', padding: '4px 8px', cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: 1, whiteSpace: 'nowrap' as const }}>
            KEY
          </button>
        )}
      </div>

      {/* Current play strip */}
      {currentEvent && (() => {
        const stripBorderColor =
          currentEvent.event_type === 'throw'
            ? '#f97316'
            : currentEvent.event_type === 'match_start' || currentEvent.event_type === 'match_end'
            ? '#06b6d4'
            : '#334155';
        return (
          <div
            style={{
              margin: '0 12px 8px',
              borderLeft: `3px solid ${isKeyPlay ? '#f59e0b' : stripBorderColor}`,
              background: isKeyPlay ? 'rgba(245,158,11,0.06)' : '#0f172a',
              borderRadius: '0 6px 6px 0',
              padding: '8px 12px',
            }}
          >
            <EventCard
              label={currentEvent.label}
              detail={currentEvent.detail}
              eventType={currentEvent.event_type}
              isKeyPlay={isKeyPlay}
            />
          </div>
        );
      })()}

      {/* Tabbed analysis — full width below court */}
      <div style={{ borderTop: '1px solid #1e293b', flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', padding: '0 4px' }}>
          {(['pbp', 'keyplays', 'stats'] as const).map((tab) => {
            const labels = { pbp: 'PLAY-BY-PLAY', keyplays: 'KEY PLAYS', stats: 'REPORT' };
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{ background: 'transparent', border: 'none', borderBottom: `2px solid ${isActive ? '#f97316' : 'transparent'}`, color: isActive ? '#f97316' : '#475569', padding: '10px 12px', cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: 1, marginBottom: -1 }}
              >
                {labels[tab]}
              </button>
            );
          })}
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px', maxHeight: '280px' }}>
          {activeTab === 'pbp' && (
            <PlayByPlayPanel events={data.proof_events} currentIndex={eventIndex} />
          )}
          {activeTab === 'keyplays' && <KeyPlaysPanel data={data} currentIndex={eventIndex} onJump={jumpTo} />}
          {activeTab === 'stats' && <StatsPanel data={data} />}
        </div>
      </div>

      {/* Back to results */}
      <div style={{ padding: '8px 12px', borderTop: '1px solid #1e293b', background: '#020617' }}>
        <button
          onClick={onContinue}
          style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#94a3b8', padding: '8px', cursor: 'pointer', fontFamily: 'Oswald, sans-serif', fontSize: 13, letterSpacing: 1 }}
        >
          BACK TO RESULTS
        </button>
      </div>
    </div>
  );
}
