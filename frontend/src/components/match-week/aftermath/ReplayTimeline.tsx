import { useState } from 'react';
import type {
  CommandDashboardLane,
  MatchReplayResponse,
  MomentEvent,
} from '../../../types';
import { LateGameBanner } from './LateGameBanner';
import { OneVOneBanner } from './OneVOneBanner';
import { ComebackCard } from './ComebackCard';

type InlineBeatKind = 'dramatic_catch' | 'gassed_collapse' | 'flood_throw';

function isInlineBeat(moment: MomentEvent): moment is Extract<MomentEvent, { kind: InlineBeatKind }> {
  return (
    moment.kind === 'dramatic_catch' ||
    moment.kind === 'gassed_collapse' ||
    moment.kind === 'flood_throw'
  );
}

function BeatList({
  beats,
  beatMoments,
}: {
  beats: CommandDashboardLane[];
  beatMoments: Array<MomentEvent | undefined>;
}) {
  return (
    <ol className="command-match-flow-list">
      {beats.map((lane, i) => {
        const moment = beatMoments[i];
        return (
          <li key={i} className="command-match-flow-event">
            <span className="command-event-badge" aria-hidden="true">
              {i + 1}
            </span>
            <div>
              <span className="command-event-phase">{lane.title}</span>
              <p className="command-event-desc">{lane.summary}</p>
              {lane.items.length > 0 && (
                <ul className="command-event-items">
                  {lane.items.map((item, j) => (
                    <li key={j}>{item}</li>
                  ))}
                </ul>
              )}
              {moment?.display_text && (
                <p
                  data-testid={`replay-beat-${moment.kind}`}
                  style={{
                    marginTop: '0.4rem',
                    padding: '0.35rem 0.55rem',
                    background: '#0f172a',
                    borderLeft: '3px solid #f97316',
                    borderRadius: '3px',
                    color: '#fde68a',
                    fontSize: '0.78rem',
                    lineHeight: 1.45,
                  }}
                >
                  {moment.display_text}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

interface NarrativeBeatsLike {
  was_shutout: boolean;
  largest_deficit: number;
}

export function ReplayTimeline({
  replay,
  lanes,
  narrativeBeats,
}: {
  replay: MatchReplayResponse | null;
  lanes: CommandDashboardLane[];
  narrativeBeats?: NarrativeBeatsLike;
}) {
  const beats = lanes.filter((lane) => lane.summary.trim().length > 0);
  const [isOpen, setIsOpen] = useState(false);
  const moments: MomentEvent[] = replay?.moment_events ?? [];

  const inlineMoments = moments.filter(isInlineBeat);
  const beatMoments: Array<MomentEvent | undefined> = beats.map((_lane, i) => inlineMoments[i]);

  const lateGame = moments.find(
    (m): m is Extract<MomentEvent, { kind: 'late_game_escape' }> => m.kind === 'late_game_escape',
  );
  const oneVOne = moments.find(
    (m): m is Extract<MomentEvent, { kind: 'one_v_one_finale' }> => m.kind === 'one_v_one_finale',
  );
  const comeback = moments.find(
    (m): m is Extract<MomentEvent, { kind: 'comeback' }> => m.kind === 'comeback',
  );

  const needsScroll = beats.length > 5;

  if (beats.length === 0 && moments.length === 0) {
    return null;
  }

  return (
    <section
      className="dm-panel"
      data-testid="replay-timeline"
      style={{ padding: 0, overflow: 'hidden' }}
    >
      <button
        className="command-timeline-collapse-bar"
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
      >
        <span className="command-timeline-collapse-label">
          <span style={{ color: '#f97316', fontWeight: 700 }}>POSTGAME REPORT</span>
          <span style={{ color: '#475569' }}>
            {' '}
            · {beats.length} moment{beats.length !== 1 ? 's' : ''}
          </span>
        </span>
        <span className="command-timeline-collapse-icon" aria-hidden="true">
          {isOpen ? '▲' : '▼'}
        </span>
      </button>

      {isOpen && (
        <div
          style={{ padding: '0 1rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
        >
          {lateGame?.display_text && <LateGameBanner text={lateGame.display_text} />}
          {oneVOne?.display_text && <OneVOneBanner text={oneVOne.display_text} />}

          {beats.length > 0 && (
            needsScroll ? (
              <div className="command-match-flow-scroll-wrap">
                <div
                  className="command-match-flow-scroll"
                  tabIndex={0}
                  aria-label="Match breakdown — use arrow keys or scroll to read"
                >
                  <BeatList beats={beats} beatMoments={beatMoments} />
                </div>
                <p className="command-match-flow-scroll-hint">Scroll for more ↓</p>
              </div>
            ) : (
              <BeatList beats={beats} beatMoments={beatMoments} />
            )
          )}

          {comeback?.display_text && replay?.winner_club_id === comeback.team_id && (
            <ComebackCard text={comeback.display_text} narrativeBeats={narrativeBeats} />
          )}
        </div>
      )}
    </section>
  );
}
