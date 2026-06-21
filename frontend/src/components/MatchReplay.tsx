import { Fragment, useMemo, useEffect, useRef, useState } from 'react';

import type { HighlightBeat, MatchReplayResponse, MomentEvent, ReplayGameSegment, ReplayProofEvent } from '../types';
import { rulesetDisplayName } from '../legibility/rulesetNames';
import { BroadcastFrameBlock } from './BroadcastFrameBlock';
import { formatScoreline, survivorDetail } from './match-week/matchResult';
import { MatchHighlights } from '../features/replay/MatchHighlights';
import { ReplaySpeedControl, type ReplaySpeed } from './match-week/aftermath/ReplaySpeedControl';
import { LiveCourtCanvas } from './replay/LiveCourtCanvas';
import { commandApi } from '../api/client';
import styles from './MatchReplay.module.css';

interface PlayerInfo {
  id: string;
  name: string;
  label: string; // "F. LASTNAME"
  clubId: string;
}

function playerLabel(name: string): string {
  const parts = name.trim().split(' ');
  if (parts.length === 1) return parts[0].toUpperCase().slice(0, 7);
  const first = parts[0][0].toUpperCase();
  const last = parts[parts.length - 1].toUpperCase().slice(0, 6);
  return `${first}. ${last}`;
}

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
  const ownerClass = (owner: 'swing' | 'home' | 'away') =>
    owner === 'swing' ? styles.ownerSwing : owner === 'home' ? styles.ownerHome : styles.ownerAway;
  return (
    <div className={styles.possession}>
      <div className={styles.possessionHead}>
        <span className={styles.possessionKicker}>POSSESSION TIMELINE</span>
        <span className={styles.possessionTally}>
          <span className={styles.dim}>Play by Play</span>
        </span>
      </div>
      <div className={styles.possessionStrip}>
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
                <span className={styles.possDivider} aria-hidden="true">
                  G{ev.game_number}
                </span>
              )}
              <button
                className={`${styles.possCell} ${ownerClass(owner)} ${active ? styles.possActive : ''}`}
                onClick={() => onJump(i)}
              >
                <span className={styles.num}>{(i + 1).toString().padStart(2, '0')}</span>
                {isSwing && <div className={styles.swingPip} />}
                {momentIndices.has(i) && <div className={styles.momentPip} title="Recognition moment" />}
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
//
// V20 live strip: when the event stream carries game metadata, the strip is
// LIVE-PER-EVENT during playback — a game's result is revealed only once
// playback moves past it (the current game shows ▶, later games show ·), so
// watching a replay never spoils the games you haven't reached. At the end
// of playback (or on legacy streams without metadata, where currentGame is
// null) the strip shows the full-time story as before.
const GameSegmentStrip = ({
  segments,
  currentGame,
  onJump,
  atEnd,
}: {
  segments: ReplayGameSegment[];
  currentGame: number | null;
  onJump: (proofIndex: number) => void;
  atEnd: boolean;
}) => {
  if (segments.length === 0) return null;
  const liveMode = !atEnd && currentGame != null;
  const lastRevealed = liveMode
    ? segments.filter((seg) => seg.game_number < (currentGame as number)).slice(-1)[0] ?? null
    : segments[segments.length - 1];
  const resultClass = (result: 'home' | 'away' | 'none') =>
    result === 'home' ? styles.resultHome : result === 'away' ? styles.resultAway : styles.resultNone;
  return (
    <div className={styles.setStrip} data-testid="replay-set-strip" aria-label="Game-by-game set results">
      <span className={styles.setKicker}>SETS</span>
      {segments.map((seg) => {
        const isCurrent = currentGame === seg.game_number;
        const revealed = !liveMode || seg.game_number < (currentGame as number);
        const result: 'home' | 'away' | 'none' = !revealed
          ? 'none'
          : seg.home_points > seg.away_points ? 'home' : seg.away_points > seg.home_points ? 'away' : 'none';
        const canJump = seg.first_proof_index != null;
        const title = !revealed
          ? isCurrent
            ? `Game ${seg.game_number}: in progress — keep watching`
            : `Game ${seg.game_number}: not played yet at this point of the replay`
          : seg.result_type === 'no_point'
            ? `Game ${seg.game_number}: no point — neither side closed it out`
            : seg.result_type === 'tie'
              ? `Game ${seg.game_number}: tied`
              : `Game ${seg.game_number}: ${seg.home_points}–${seg.away_points} (${seg.home_final_actives}v${seg.away_final_actives} left standing)`;
        return (
          <button
            key={seg.game_number}
            type="button"
            data-set-chip={seg.game_number}
            data-set-revealed={revealed ? 'true' : 'false'}
            className={`${styles.setChip} ${resultClass(result)} ${isCurrent ? styles.setChipCurrent : ''}`}
            title={title}
            disabled={!canJump}
            onClick={() => {
              if (seg.first_proof_index != null) onJump(seg.first_proof_index);
            }}
          >
            <span className="g">G{seg.game_number}</span>
            <span className="pts">
              {!revealed
                ? isCurrent
                  ? '▶'
                  : '·'
                : seg.result_type === 'no_point'
                  ? '—'
                  : `${seg.home_points}–${seg.away_points}`}
            </span>
          </button>
        );
      })}
      {/* Codex issue 4: during playback this is the CURRENT-moment tally,
          which sits right under the final-score header — label it "so far"
          so it never reads as contradicting the full-time score. */}
      <span className={styles.setRunning} data-testid="replay-set-running">
        {liveMode
          ? `${lastRevealed ? `${lastRevealed.home_running_points}–${lastRevealed.away_running_points}` : '0–0'} on game points so far`
          : `${lastRevealed ? `${lastRevealed.home_running_points}–${lastRevealed.away_running_points}` : '0–0'} on game points`}
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
    <div className={styles.scoreboard} data-testid="replay-scoreboard">
      <div className={`${styles.team} ${styles.teamHome}`}>
        <div className={styles.teamRec}>HOME</div>
        <div className={styles.teamName}>{homeName}</div>
        <div className={styles.teamTag}>PROGRAM</div>
      </div>
      <div className={styles.score}>
        <div className={styles.scoreCol}>
          <span className={`${styles.scoreNum} ${styles.scoreNumHome}`} data-score-side="home">{scoreHome}</span>
          <span className={styles.scoreUnit}>{survivorDetail(scoreline.home.survivors, isOfficial)}</span>
        </div>
        <div className={styles.scoreDivider}>
          <span className={styles.finalTag}>{formatTag}</span>
          <span className={styles.vs}>VS</span>
          <span className={styles.margin}>{marginLabel}</span>
        </div>
        <div className={styles.scoreCol}>
          <span className={`${styles.scoreNum} ${styles.scoreNumAway}`} data-score-side="away">{scoreAway}</span>
          <span className={styles.scoreUnit}>{survivorDetail(scoreline.away.survivors, isOfficial)}</span>
        </div>
      </div>
      <div className={`${styles.team} ${styles.teamAway} ${styles.teamAwayEdge}`}>
        <div className={styles.teamRec}>AWAY</div>
        <div className={styles.teamName}>{awayName}</div>
        <div className={styles.teamTag}>PROGRAM</div>
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
    <section className={styles.officialPanel} data-testid="official-ruleset-banner" aria-label="Official rules replay state">
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
      {data.team_policies && (
        <div>
          <span title="The locked tactics each club actually played this match under — your weekly plan's policy and theirs, disclosed after the fact (the match is tape now).">GAME PLANS</span>
          <div className={styles.officialBallList}>
            {[data.home_club_id, data.away_club_id].map((clubId) => {
              const policy = data.team_policies?.[clubId];
              if (!policy) return null;
              return (
                <span key={clubId}>
                  {(clubNameById[clubId] ?? clubId)}: {humanizeOfficialToken(String(policy.approach ?? '—'))} ·{' '}
                  {humanizeOfficialToken(String(policy.catch_posture ?? '—'))} · targets{' '}
                  {humanizeOfficialToken(String(policy.target_focus ?? '—')).toLowerCase()}
                </span>
              );
            })}
          </div>
        </div>
      )}
      <div>
        <span title="Where each ball ended at the final whistle — held means in a player's hands, dead means loose on the floor.">BALL STATES</span>
        <div className={styles.officialBallList}>
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
    <div className={styles.proofFrames}>
      {data.broadcast_frame && (
        <BroadcastFrameBlock frame={data.broadcast_frame} title="Broadcast Frame" compact />
      )}
      {data.playoff_frame && (
        <section
          className={styles.playoffFrame}
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
  <div className={styles.turning}>
    <div>
      <span className={styles.turningKicker}>BIGGEST SWING</span>
      <p className={styles.turningText}>{text}</p>
    </div>
    <button className={styles.turningJump} onClick={onShowCatch}>
      Jump to This Play <span className="arrow">▸</span>
    </button>
  </div>
);

const chipClass = (resolution: string) => {
  const r = resolution.toLowerCase();
  if (r === 'caught' || r === 'catch') return styles.chipCatch;
  if (r === 'eliminated' || r === 'hit' || r === 'failed_catch') return styles.chipElim;
  if (r === 'dodged') return styles.chipThrow;
  return styles.chipThrow;
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
    <aside className={styles.currentCard} data-testid="current-event-card" aria-label="Current replay event">
      <div className={styles.currentKicker}>
        <span>Current Event</span>
        <b>{eventIndex + 1}/{totalEvents}</b>
      </div>
      <strong>{actors}</strong>
      <div className={styles.currentMeta}>
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
    <div className={styles.log}>
      {events.map((ev, idx) => {
        return (
          <button
            key={idx}
            ref={(node) => { rowRefs.current[idx] = node; }}
            className={`${styles.logEvent} ${idx === activeIdx ? styles.logEventActive : ''}`}
            onClick={() => onSelect(idx)}
          >
            <div className={styles.logRail}>
              <span className={styles.logTick}>{(idx + 1).toString().padStart(2, '0')}</span>
              <span className={styles.logTime}>T{ev.tick}</span>
            </div>
            <div className={styles.logBody}>
              <div className={styles.logRow}>
                <span className={`${styles.logChip} ${chipClass(ev.resolution)}`}>{ev.resolution.toUpperCase()}</span>
                <span className={styles.logTitle}>{ev.summary}</span>
              </div>
              {ev.detail && (
                <ul className={styles.logEvidence}>
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
  } = useMemo(() => {
    if (!data) return { totalEvents: 0, playerRegistry: new Map<string, PlayerInfo>(), homeIds: [], awayIds: [] };
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

    return {
      totalEvents: data.proof_events.length,
      playerRegistry: reg,
      homeIds: hIds,
      awayIds: aIds,
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
      setActiveResolution(currentProof.thrower_id ? currentProof.resolution : null);
    }, 0);
    return () => clearTimeout(t0);
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
    <div className={`max-content ${styles.shell}`} data-screen-label="03 Dynasty">
      <ReplayScoreboard data={data} />
      <OfficialRulesPanel data={data} />
      <ReplayProofFrames data={data} />
      <TurningPoint
        text={data.report?.turning_point || "Crucial swing in momentum."}
        onShowCatch={() => { setEventIndex(swingJumpIdx); setIsPlaying(false); }}
      />

      <div className={styles.stage}>
        <div className={styles.activeReadout}>
          <span className={styles.readoutLbl}>NOW SHOWING</span>
          <span className={styles.readoutSep} />
          <span className={styles.readoutVal}>
            {currentGame != null ? `GAME ${currentGame} · ` : ''}TICK {currentEvent?.tick ?? 0}
          </span>
          <span className={styles.readoutSep} />
          <span className={styles.readoutTitle}>{currentEvent?.summary || 'Match Start'}</span>
        </div>
        {currentMoments.length > 0 && (
          <div className={styles.momentBanner} data-testid="replay-moment-banner">
            {currentMoments.map((moment, index) => (
              <p key={`${moment.kind}-${index}`}>
                <b>{MOMENT_KIND_LABEL[moment.kind]}</b>
                {moment.display_text ? ` ${moment.display_text}` : ''}
              </p>
            ))}
          </div>
        )}
        <div className={styles.courtWrap}>
          <LiveCourtCanvas
            homeIds={homeIds}
            awayIds={awayIds}
            playerRegistry={playerRegistry}
            eliminatedIds={eliminatedIds}
            throwerId={throwerId}
            targetId={targetId}
            activeResolution={activeResolution}
          />
        </div>
        {gameSegments.length > 0 && (
          <GameSegmentStrip
            segments={gameSegments}
            currentGame={currentGame}
            onJump={(proofIndex) => { setEventIndex(proofIndex); setIsPlaying(false); }}
            atEnd={eventIndex >= data.proof_events.length - 1}
          />
        )}
        <PossessionBar
          events={data.proof_events}
          activeIdx={eventIndex}
          onJump={setEventIndex}
          homeClubId={data.home_club_id}
          momentIndices={momentIndices}
        />

        <div className={styles.transport}>
          <button className={styles.tbtn} aria-label="First" onClick={() => { setEventIndex(0); setIsPlaying(false); }}>⏮</button>
          <button className={styles.tbtn} aria-label="Previous" onClick={() => { setEventIndex(Math.max(0, eventIndex - 1)); setIsPlaying(false); }}>◂</button>
          <button className={`${styles.tbtn} ${styles.play} ${isPlaying ? styles.playPlaying : ''}`} aria-label={isPlaying ? 'Pause' : 'Play'} onClick={() => setIsPlaying(!isPlaying)}>
            {isPlaying ? '❚❚' : '▶'}
          </button>
          <button className={styles.tbtn} aria-label="Next" onClick={() => { setEventIndex(Math.min(totalEvents - 1, eventIndex + 1)); setIsPlaying(false); }}>▸</button>
          <button className={styles.tbtn} aria-label="Last" onClick={() => { setEventIndex(totalEvents - 1); setIsPlaying(false); }}>⏭</button>
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
          <span className={styles.transportSpd}>Space · ◂ ▸</span>
          <span className={styles.transportPos}>
            EVENT <b>{(eventIndex + 1).toString().padStart(2, '0')}/{totalEvents.toString().padStart(2, '0')}</b>
          </span>
          <button className={`${styles.tbtn} ${styles.closeBtn}`} aria-label="Back to results / close replay" onClick={onContinue}>
            CLOSE
          </button>
        </div>
      </div>

      <div className={styles.sidebarWrap}>
        <CurrentEventCard
          event={currentEvent}
          eventIndex={eventIndex}
          previousEvent={previousEvent}
          totalEvents={totalEvents}
        />
        <div className={styles.sidebarHead}>
          <span className={styles.sidebarMeta}><b>EVENT LOG</b></span>
          <div className={styles.sidebarTitle}>Match Flow</div>
        </div>
        <EventLog events={data.proof_events} activeIdx={eventIndex} onSelect={setEventIndex} />
        {highlightBeats.length > 0 && (
          <div className={styles.highlights} data-testid="replay-highlights">
            <div className={styles.sidebarHead}>
              <span className={styles.sidebarMeta}><b>HIGHLIGHT REEL</b></span>
              <div className={styles.sidebarTitle}>The Story in {highlightBeats.length} Plays</div>
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

