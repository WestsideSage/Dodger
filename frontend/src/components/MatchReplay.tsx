import { Fragment, memo, useMemo, useEffect, useRef, useState } from 'react';

import type { HighlightBeat, MatchReplayResponse, MomentEvent, ReplayGameSegment, ReplayProofEvent } from '../types';
import { rulesetDisplayName } from '../legibility/rulesetNames';
import { BroadcastFrameBlock } from './BroadcastFrameBlock';
import { formatScoreline, survivorDetail } from './match-week/matchResult';
import { MatchHighlights } from '../features/replay/MatchHighlights';
import { ReplaySpeedControl, type ReplaySpeed } from './match-week/aftermath/ReplaySpeedControl';
import { commandApi } from '../api/client';

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

// How long autoplay holds each play, before the speed factor: outs and
// catches get a beat to land, misses move the broadcast along.
const eventHoldMs = (p: ReplayProofEvent | undefined, hasMoment: boolean): number => {
  if (!p) return 1200;
  if (hasMoment) return 1600;
  const r = p.resolution;
  if (r === 'catch' || r === 'failed_catch') return 1300;
  if (r === 'hit') return 1100;
  if (r === 'dodged') return 750;
  return 500;
};

const SPEED_FACTOR: Record<Exclude<ReplaySpeed, 'instant'>, number> = { '1x': 1, '2x': 0.5, '4x': 0.25 };

const MOMENT_KIND_LABEL: Record<MomentEvent['kind'], string> = {
  dramatic_catch: 'DRAMATIC CATCH',
  late_game_escape: 'LAST STAND',
  one_v_one_finale: 'ONE-V-ONE FINALE',
  gassed_collapse: 'GASSED COLLAPSE',
  flood_throw: 'FLOOD THROW',
  comeback: 'COMEBACK',
};

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

        // Keep the non-active court readable during a throw: 0.45 still
        // foregrounds the thrower/target but names stay legible.
        const opacity = hasActiveThrow ? (isActive ? 1 : isElim ? 0.3 : 0.45) : (isElim ? 0.35 : 1);
        const baseColor = isHome ? '#f43f5e' : '#3b82f6';
        const labelColor = isHome ? '#fda4af' : '#93c5fd';
        
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
            <text x={pos.x} y={pos.y + 27} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9.5" fontWeight="600" fill={labelColor}>
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

const PossessionBar = ({
  events,
  activeIdx,
  onJump,
  homeClubId,
  momentIndices,
}: {
  events: ReplayProofEvent[];
  activeIdx: number;
  onJump: (i: number) => void;
  homeClubId: string;
  momentIndices: Set<number>;
}) => {
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
          // Official matches: a divider where a new game starts, so the strip
          // reads as sets instead of one undifferentiated stream.
          const startsNewGame =
            i > 0 && ev.game_number != null && events[i - 1].game_number !== ev.game_number;
          return (
            <Fragment key={i}>
              {startsNewGame && (
                <span className="mr-poss-divider" aria-hidden="true">
                  G{ev.game_number}
                </span>
              )}
              <button className={`mr-poss-cell owner-${owner} ${active ? 'is-active' : ''}`} onClick={() => onJump(i)}>
                <span className="num">{(i + 1).toString().padStart(2, '0')}</span>
                {isSwing && <div className="swing-pip" />}
                {momentIndices.has(i) && <div className="moment-pip" title="Recognition moment" />}
              </button>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
};

// Set-by-set story of an official match. Every value comes from the persisted
// per-game official score; chips jump to the game's first event when the
// event stream carries game metadata (newly simulated matches).
const GameSegmentStrip = ({
  segments,
  currentGame,
  onJump,
}: {
  segments: ReplayGameSegment[];
  currentGame: number | null;
  onJump: (proofIndex: number) => void;
}) => {
  if (segments.length === 0) return null;
  return (
    <div className="mr-set-strip" data-testid="replay-set-strip" aria-label="Game-by-game set results">
      <span className="mr-set-kicker">SETS</span>
      {segments.map((seg) => {
        const result =
          seg.home_points > seg.away_points ? 'home' : seg.away_points > seg.home_points ? 'away' : 'none';
        const isCurrent = currentGame === seg.game_number;
        const canJump = seg.first_proof_index != null;
        const title =
          seg.result_type === 'no_point'
            ? `Game ${seg.game_number}: no point — neither side closed it out`
            : seg.result_type === 'tie'
              ? `Game ${seg.game_number}: tied`
              : `Game ${seg.game_number}: ${seg.home_points}–${seg.away_points} (${seg.home_final_actives}v${seg.away_final_actives} left standing)`;
        return (
          <button
            key={seg.game_number}
            type="button"
            className={`mr-set-chip result-${result} ${isCurrent ? 'is-current' : ''}`}
            title={title}
            disabled={!canJump}
            onClick={() => {
              if (seg.first_proof_index != null) onJump(seg.first_proof_index);
            }}
          >
            <span className="g">G{seg.game_number}</span>
            <span className="pts">
              {seg.result_type === 'no_point' ? '—' : `${seg.home_points}–${seg.away_points}`}
            </span>
          </button>
        );
      })}
      <span className="mr-set-running" data-testid="replay-set-running">
        {segments[segments.length - 1].home_running_points}–{segments[segments.length - 1].away_running_points} on game points
      </span>
    </div>
  );
};

const ReplayScoreboard = ({ data }: { data: MatchReplayResponse }) => {
  const homeName = data.home_club_name || 'HOME';
  const awayName = data.away_club_name || 'AWAY';

  // The header is the FINAL match result. It must use the same single-source
  // scoreline the aftermath hero and playoff bracket use (formatScoreline),
  // so this surface can never drift back to printing survivors for an official
  // match — an official 1-1 game-points draw reads 1-1 here, never the 0-0
  // survivor tally (BUG #2). The live, mid-replay survivor state is shown
  // separately on the court and in the Current Event card.
  const scoreline = formatScoreline({
    scoring_model: data.scoring_model ?? undefined,
    home_game_points: data.home_game_points ?? undefined,
    away_game_points: data.away_game_points ?? undefined,
    home_survivors: data.home_survivors ?? 0,
    away_survivors: data.away_survivors ?? 0,
  });
  const isOfficial = scoreline.isOfficial;
  const scoreHome = scoreline.home.value;
  const scoreAway = scoreline.away.value;
  const scoreDiff = Math.abs(scoreHome - scoreAway);
  const marginLabel = isOfficial ? `+${scoreDiff} GAME PTS` : `+${scoreDiff} SURVIVORS`;
  const formatTag = isOfficial ? `${rulesetDisplayName(data.scoring_model, 'short')} · W${String(data.week).padStart(2, '0')}` : `FINAL · W${String(data.week).padStart(2, '0')}`;

  return (
    <div className="mr-scoreboard">
      <div className="mr-team home">
        <div className="mr-team-rec">HOME</div>
        <div className="mr-team-name">{homeName}</div>
        <div className="mr-team-tag">PROGRAM</div>
      </div>
      <div className="mr-score">
        <div className="mr-score-col">
          <span className="mr-score-num home">{scoreHome}</span>
          <span className="mr-score-unit">{survivorDetail(scoreline.home.survivors, isOfficial)}</span>
        </div>
        <div className="mr-score-divider">
          <span className="mr-final-tag">{formatTag}</span>
          <span className="mr-vs">VS</span>
          <span className="mr-margin">{marginLabel}</span>
        </div>
        <div className="mr-score-col">
          <span className="mr-score-num away">{scoreAway}</span>
          <span className="mr-score-unit">{survivorDetail(scoreline.away.survivors, isOfficial)}</span>
        </div>
      </div>
      <div className="mr-team away">
        <div className="mr-team-rec">AWAY</div>
        <div className="mr-team-name">{awayName}</div>
        <div className="mr-team-tag">PROGRAM</div>
      </div>
    </div>
  );
};

function formatClock(clock?: { limit_seconds: number; elapsed_seconds: number } | null): string {
  if (!clock) return 'Not tracked';
  const remaining = Math.max(0, clock.limit_seconds - clock.elapsed_seconds);
  const minutes = Math.floor(remaining / 60).toString().padStart(2, '0');
  const seconds = (remaining % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds} left`;
}

// Raw engine enums (no_blocking, zero_called, a0:held...) read as debug output
// to a first-hour player; humanize every value at this presentation boundary
// without inventing state the payload does not carry.
function humanizeOfficialToken(value: string): string {
  const text = value.replaceAll('_', ' ').trim().toLowerCase();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : value;
}

const OfficialRulesPanel = ({ data }: { data: MatchReplayResponse }) => {
  const official = data.official_state;
  if (!official) return null;

  const clubNameById: Record<string, string> = {
    [data.home_club_id]: data.home_club_name || data.home_club_id,
    [data.away_club_id]: data.away_club_name || data.away_club_id,
  };

  const burden = official.burden && official.burden.team_id
    ? `${clubNameById[official.burden.team_id] ?? official.burden.team_id} · throw clock ${humanizeOfficialToken(official.burden.clock_status).toLowerCase()}`
    : 'No team on the clock';

  // Grouped rule-call readout: "3 calls · Rule 11 ×2, Rule 34" beats a bare
  // "11 · 11" (the labels are USA Dodgeball rulebook section numbers).
  const callCounts = new Map<string, number>();
  for (const call of official.rule_calls) {
    callCounts.set(call.rule_label, (callCounts.get(call.rule_label) ?? 0) + 1);
  }
  const callGroups = Array.from(callCounts.entries())
    .slice(0, 3)
    .map(([label, count]) => (count > 1 ? `Rule ${label} ×${count}` : `Rule ${label}`))
    .join(', ');
  const ruleCalls = official.rule_calls.length
    ? `${official.rule_calls.length} call${official.rule_calls.length === 1 ? '' : 's'} · ${callGroups}`
    : 'None';

  return (
    <section className="mr-official-panel" data-testid="official-ruleset-banner" aria-label="Official rules replay state">
      <div>
        <span title="Officiating snapshot taken at the final whistle — clocks read 00:00 because the match is over.">FULL TIME</span>
        <strong>Official state</strong>
      </div>
      <div>
        <span>RULESET</span>
        <strong>{rulesetDisplayName(official.ruleset, 'short')}</strong>
      </div>
      <div>
        <span title="The officiating mode in force when the match ended. No Blocking is the official endgame call — once active, held balls stop blocking throws and play runs until someone wins the game.">MODE</span>
        <strong>{humanizeOfficialToken(official.mode)}</strong>
      </div>
      <div>
        <span>GAME CLOCK</span>
        <strong>{formatClock(official.game_clock)}</strong>
      </div>
      <div>
        <span>MATCH CLOCK</span>
        <strong>{formatClock(official.match_clock)}</strong>
      </div>
      <div>
        <span title="The burden team must attack before the throw clock expires.">BURDEN</span>
        <strong>{burden}</strong>
      </div>
      <div>
        <span title="Where each ball ended at the final whistle — held means in a player's hands, dead means loose on the floor.">BALL STATES</span>
        <div className="mr-official-ball-list">
          {official.balls.length
            ? official.balls.map(ball => (
                <span key={ball.ball_id}>
                  {ball.ball_id.toUpperCase()} {humanizeOfficialToken(ball.state).toLowerCase()}
                </span>
              ))
            : <span>No ball state</span>}
        </div>
      </div>
      <div>
        <span title="Officiating calls logged during the match, by USA Dodgeball rulebook section number.">RULE CALLS</span>
        <strong>{ruleCalls}</strong>
      </div>
    </section>
  );
};

const ReplayProofFrames = ({ data }: { data: MatchReplayResponse }) => {
  const hasBroadcast = Boolean(data.broadcast_frame);
  const hasPlayoff = Boolean(data.playoff_frame);
  if (!hasBroadcast && !hasPlayoff) return null;
  return (
    <div className="mr-proof-frames">
      {data.broadcast_frame && (
        <BroadcastFrameBlock frame={data.broadcast_frame} title="Broadcast Frame" compact />
      )}
      {data.playoff_frame && (
        <section
          className="mr-playoff-frame"
          data-testid="playoff-frame"
          data-broadcast-proof-source={data.playoff_frame.proof_source}
        >
          <span>Playoff Frame</span>
          <strong>{data.playoff_frame.title}</strong>
          <p>{data.playoff_frame.label}</p>
        </section>
      )}
    </div>
  );
};

// The headline is the replay's biggest swing in living-count differential
// (lead flips weighted highest), selected server-side from the same proof
// timeline the jump lands on — never just "the first hit of the match".
const TurningPoint = ({ text, onShowCatch }: { text: string, onShowCatch: () => void }) => (
  <div className="mr-turning">
    <div>
      <span className="mr-turning-kicker">BIGGEST SWING</span>
      <p className="mr-turning-text">{text}</p>
    </div>
    <button className="mr-turning-jump" onClick={onShowCatch}>
      Jump to This Play <span className="arrow">▸</span>
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

const scoreDeltaLabel = (current?: ReplayProofEvent, previous?: ReplayProofEvent) => {
  if (!current?.score_state) return 'No score state';
  // Official game boundary: survivor counts genuinely reset (every game
  // starts 6v6), so a delta against the previous game would be meaningless.
  if (
    previous &&
    current.game_number != null &&
    previous.game_number !== current.game_number
  ) {
    return `Game ${current.game_number} — fresh court`;
  }
  const prevHome = previous?.score_state?.home_living ?? current.score_state.home_living;
  const prevAway = previous?.score_state?.away_living ?? current.score_state.away_living;
  const homeDelta = current.score_state.home_living - prevHome;
  const awayDelta = current.score_state.away_living - prevAway;
  if (homeDelta === 0 && awayDelta === 0) return 'No survivor change';
  const parts = [];
  if (homeDelta !== 0) parts.push(`Home ${homeDelta > 0 ? '+' : ''}${homeDelta}`);
  if (awayDelta !== 0) parts.push(`Away ${awayDelta > 0 ? '+' : ''}${awayDelta}`);
  return parts.join(' / ');
};

const CurrentEventCard = ({
  event,
  eventIndex,
  previousEvent,
  totalEvents,
}: {
  event: ReplayProofEvent | undefined;
  eventIndex: number;
  previousEvent: ReplayProofEvent | undefined;
  totalEvents: number;
}) => {
  if (!event) return null;
  const actors = [event.thrower_name, event.target_name].filter(Boolean).join(' -> ') || 'Match event';
  return (
    <aside className="mr-current-card" data-testid="current-event-card" aria-label="Current replay event">
      <div className="mr-current-kicker">
        <span>Current Event</span>
        <b>{eventIndex + 1}/{totalEvents}</b>
      </div>
      <strong>{actors}</strong>
      <div className="mr-current-meta">
        <span>{event.game_number != null ? `G${event.game_number} · ` : ''}T{event.tick}</span>
        <span>{event.resolution}</span>
        <span>{scoreDeltaLabel(event, previousEvent)}</span>
      </div>
      <p>{event.summary}</p>
      {event.detail && <small>{event.detail}</small>}
    </aside>
  );
};

const EventLog = ({ events, activeIdx, onSelect }: { events: ReplayProofEvent[], activeIdx: number, onSelect: (i: number) => void }) => {
  const rowRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  useEffect(() => {
    rowRefs.current[activeIdx]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [activeIdx]);

  return (
    <div className="mr-log">
      {events.map((ev, idx) => {
        return (
          <button
            key={idx}
            ref={(node) => { rowRefs.current[idx] = node; }}
            className={`mr-log-event ${idx === activeIdx ? 'is-active' : ''}`}
            onClick={() => onSelect(idx)}
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

// ── MatchReplay Component ───────────────────────────────────────────────────

export default function MatchReplay({ data, onContinue }: { data: MatchReplayResponse; onContinue: () => void }) {
  // Start on the first key play so the NOW SHOWING caption agrees with the
  // TURNING POINT headline rather than landing on a meaningless tick-0 throw.
  const initialIdx = data.key_play_indices && data.key_play_indices.length > 0 ? data.key_play_indices[0] : 0;
  const [eventIndex, setEventIndex] = useState(initialIdx);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<ReplaySpeed>('1x');
  const [highlightBeats, setHighlightBeats] = useState<HighlightBeat[]>([]);

  const [activeResolution, setActiveResolution] = useState<string | null>(null);
  const [flashTargetId, setFlashTargetId] = useState<string | null>(null);
  const [ballAnimKey, setBallAnimKey] = useState<string>('init');

  // V13 highlight package (deterministic, event-id-keyed) — gives the replay
  // a story summary with jump links. Optional: failures just hide the block.
  useEffect(() => {
    let cancelled = false;
    commandApi.highlights(data.match_id)
      .then((payload) => {
        if (!cancelled) setHighlightBeats(payload.beats ?? []);
      })
      .catch(() => {
        if (!cancelled) setHighlightBeats([]);
      });
    return () => {
      cancelled = true;
    };
  }, [data.match_id]);

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

    // The current event's score_state IS the live court truth: the backend
    // already accumulates eliminations, takes catch-returns back off, and
    // resets at official game boundaries. Unioning across all prior events
    // here would re-mark returned players and dead games as eliminated.
    const current = data.proof_events[eventIndex];
    if (current?.score_state) {
      current.score_state.home_eliminated_player_ids.forEach((id) => elims.add(id));
      current.score_state.away_eliminated_player_ids.forEach((id) => elims.add(id));
    }
    return {
      eliminatedIds: elims,
      throwerId: current ? current.thrower_id : null,
      targetId: current ? current.target_id : null,
    };
  }, [data, eventIndex, totalEvents]);

  // Moments anchored into the proof timeline (server-resolved). Map proof
  // index -> moments so playback can banner them at the right play.
  const momentsByIndex = useMemo(() => {
    const map = new Map<number, MomentEvent[]>();
    (data?.moment_events ?? []).forEach((moment) => {
      const anchor = moment.anchor_index;
      if (anchor == null || anchor < 0) return;
      const existing = map.get(anchor) ?? [];
      existing.push(moment);
      map.set(anchor, existing);
    });
    return map;
  }, [data]);
  const momentIndices = useMemo(() => new Set(momentsByIndex.keys()), [momentsByIndex]);

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

  // Auto-play loop: outs/catches hold longer than misses, scaled by the
  // selected speed, so a 200-event official match stays watchable.
  useEffect(() => {
    if (!isPlaying) return;
    if (eventIndex >= totalEvents - 1) {
      const t = setTimeout(() => setIsPlaying(false), 0);
      return () => clearTimeout(t);
    }
    const factor = speed === 'instant' ? 0.1 : SPEED_FACTOR[speed];
    const hold = Math.max(120, eventHoldMs(data.proof_events[eventIndex], momentIndices.has(eventIndex)) * factor);
    const t = setTimeout(() => setEventIndex((i) => i + 1), hold);
    return () => clearTimeout(t);
  }, [isPlaying, eventIndex, totalEvents, speed, data, momentIndices]);

  const currentEvent = data.proof_events[eventIndex];
  const previousEvent = eventIndex > 0 ? data.proof_events[eventIndex - 1] : undefined;
  const firstKeyPlayIdx = data.key_play_indices?.length > 0 ? data.key_play_indices[0] : 0;
  const swingJumpIdx = data.report?.turning_point_index ?? firstKeyPlayIdx;
  const currentMoments = momentsByIndex.get(eventIndex) ?? [];
  const gameSegments = data.game_segments ?? [];
  const currentGame = currentEvent?.game_number ?? null;
  // events[] index (highlight source coordinates) -> proof index for jumps.
  const proofIndexBySequence = useMemo(() => {
    const map = new Map<number, number>();
    data.proof_events.forEach((proof, index) => map.set(proof.sequence_index, index));
    return map;
  }, [data]);

  return (
    <div className="max-content mr-shell" data-screen-label="03 Dynasty">
      <ReplayScoreboard data={data} />
      <OfficialRulesPanel data={data} />
      <ReplayProofFrames data={data} />
      <TurningPoint
        text={data.report?.turning_point || "Crucial swing in momentum."}
        onShowCatch={() => { setEventIndex(swingJumpIdx); setIsPlaying(false); }}
      />

      <div className="mr-stage">
        <div className="mr-active-readout">
          <span className="lbl">NOW SHOWING</span>
          <span className="sep" />
          <span className="val">
            {currentGame != null ? `GAME ${currentGame} · ` : ''}TICK {currentEvent?.tick ?? 0}
          </span>
          <span className="sep" />
          <span className="title">{currentEvent?.summary || 'Match Start'}</span>
        </div>
        {currentMoments.length > 0 && (
          <div className="mr-moment-banner" data-testid="replay-moment-banner">
            {currentMoments.map((moment, index) => (
              <p key={`${moment.kind}-${index}`}>
                <b>{MOMENT_KIND_LABEL[moment.kind]}</b>
                {moment.display_text ? ` ${moment.display_text}` : ''}
              </p>
            ))}
          </div>
        )}
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
        {gameSegments.length > 0 && (
          <GameSegmentStrip
            segments={gameSegments}
            currentGame={currentGame}
            onJump={(proofIndex) => { setEventIndex(proofIndex); setIsPlaying(false); }}
          />
        )}
        <PossessionBar
          events={data.proof_events}
          activeIdx={eventIndex}
          onJump={setEventIndex}
          homeClubId={data.home_club_id}
          momentIndices={momentIndices}
        />

        <div className="mr-transport">
          <button className="mr-tbtn" aria-label="First" onClick={() => { setEventIndex(0); setIsPlaying(false); }}>⏮</button>
          <button className="mr-tbtn" aria-label="Previous" onClick={() => { setEventIndex(Math.max(0, eventIndex - 1)); setIsPlaying(false); }}>◂</button>
          <button className={`mr-tbtn mr-play ${isPlaying ? 'is-playing' : ''}`} aria-label={isPlaying ? 'Pause' : 'Play'} onClick={() => setIsPlaying(!isPlaying)}>
            {isPlaying ? '❚❚' : '▶'}
          </button>
          <button className="mr-tbtn" aria-label="Next" onClick={() => { setEventIndex(Math.min(totalEvents - 1, eventIndex + 1)); setIsPlaying(false); }}>▸</button>
          <button className="mr-tbtn" aria-label="Last" onClick={() => { setEventIndex(totalEvents - 1); setIsPlaying(false); }}>⏭</button>
          <ReplaySpeedControl
            speed={speed}
            onChange={(next) => {
              if (next === 'instant') {
                // "Instant" is a skip: land on the final play, paused.
                setEventIndex(totalEvents - 1);
                setIsPlaying(false);
                return;
              }
              setSpeed(next);
            }}
          />
          <span className="mr-transport-spd">Space · ◂ ▸</span>
          <span className="mr-transport-pos">
            EVENT <b>{(eventIndex + 1).toString().padStart(2, '0')}/{totalEvents.toString().padStart(2, '0')}</b>
          </span>
          <button className="mr-tbtn" aria-label="Back to results / close replay" onClick={onContinue} style={{ width: 'auto', padding: '0 12px', fontFamily: 'var(--font-display)', fontSize: '0.7rem', letterSpacing: '0.12em' }}>
            CLOSE
          </button>
        </div>
      </div>

      <div className="mr-sidebar-wrap">
        <CurrentEventCard
          event={currentEvent}
          eventIndex={eventIndex}
          previousEvent={previousEvent}
          totalEvents={totalEvents}
        />
        <div className="mr-sidebar-head">
          <span className="mr-sidebar-meta"><b>EVENT LOG</b></span>
          <div className="mr-sidebar-title">Match Flow</div>
        </div>
        <EventLog events={data.proof_events} activeIdx={eventIndex} onSelect={setEventIndex} />
        {highlightBeats.length > 0 && (
          <div className="mr-highlights" data-testid="replay-highlights">
            <div className="mr-sidebar-head">
              <span className="mr-sidebar-meta"><b>HIGHLIGHT REEL</b></span>
              <div className="mr-sidebar-title">The Story in {highlightBeats.length} Plays</div>
            </div>
            <MatchHighlights
              beats={highlightBeats}
              onShowInTimeline={(sourceEventIndex) => {
                const proofIndex = proofIndexBySequence.get(sourceEventIndex);
                if (proofIndex != null) {
                  setEventIndex(proofIndex);
                  setIsPlaying(false);
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

