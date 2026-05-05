import { memo, useMemo, useState } from 'react';
import type { MatchReplayResponse, ReplayEvent } from '../types';
import { ActionButton, Badge, Card, KeyValueRow, PageHeader, StatChip } from './ui';

function valueLine(items: Record<string, number>) {
  return Object.entries(items)
    .map(([key, value]) => `${key.replaceAll('_', ' ')} ${value.toFixed(2)}`)
    .join(' | ');
}

const ReplayDebugDetails = memo(function ReplayDebugDetails({ event }: { event?: ReplayEvent }) {
  if (!event) return null;
  const hasProbabilities = event.probabilities && Object.keys(event.probabilities).length > 0;
  const hasRolls = event.rolls && Object.keys(event.rolls).length > 0;
  if (!hasProbabilities && !hasRolls) return null;

  return (
    <details className="rounded-md border border-[var(--color-line)] bg-[var(--color-paper)] p-3 text-xs text-[var(--color-muted)]">
      <summary className="cursor-pointer font-display uppercase tracking-wider text-[11px] text-[var(--color-brick)]">
        Replay details
      </summary>
      <div className="mt-2 space-y-1 font-mono">
        {hasProbabilities && <div>Probabilities: {valueLine(event.probabilities)}</div>}
        {hasRolls && <div>Rolls: {valueLine(event.rolls)}</div>}
      </div>
    </details>
  );
});

const MatchReportPanel = memo(function MatchReportPanel({ replay }: { replay: MatchReplayResponse }) {
  return (
    <Card className="p-4">
      <h3 className="font-display uppercase tracking-widest text-lg text-[var(--color-charcoal)]">Match Report</h3>
      <div className="mt-3">
        <KeyValueRow label="Winner" value={replay.report.winner_name} />
        <KeyValueRow label="MVP" value={replay.report.match_mvp_name ?? '-'} />
        <div className="pt-3">
          <span className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">Turning Point</span>
          <p className="mt-1 text-sm font-bold leading-relaxed">{replay.report.turning_point}</p>
        </div>
      </div>
    </Card>
  );
});

const TopPerformersList = memo(function TopPerformersList({ replay }: { replay: MatchReplayResponse }) {
  return (
    <Card className="p-4">
      <h3 className="font-display uppercase tracking-widest text-lg text-[var(--color-charcoal)]">Top Performers</h3>
      <div className="mt-3 flex flex-col">
        {replay.report.top_performers.map(player => (
          <div key={player.player_id} className="grid grid-cols-[1fr_56px] gap-2 border-b border-[var(--color-line)] py-2 text-sm last:border-0">
            <span className="font-bold">{player.player_name}</span>
            <span className="text-right font-mono font-bold">{player.score.toFixed(1)}</span>
          </div>
        ))}
      </div>
    </Card>
  );
});

export function MatchReplay({
  replay,
  acknowledging,
  onAcknowledge,
}: {
  replay: MatchReplayResponse;
  acknowledging: boolean;
  onAcknowledge: () => void;
}) {
  const [eventIndex, setEventIndex] = useState(0);
  const current = replay.events[Math.min(eventIndex, Math.max(0, replay.events.length - 1))];
  const keyEventIndex = useMemo(
    () => replay.events.findIndex(event => {
      const resolution = event.outcome?.resolution;
      return event.event_type === 'throw' && ['hit', 'failed_catch', 'catch'].includes(String(resolution));
    }),
    [replay.events]
  );
  const progress = replay.events.length ? ((eventIndex + 1) / replay.events.length) * 100 : 0;

  const jumpToKeyEvent = () => {
    if (keyEventIndex >= 0) setEventIndex(keyEventIndex);
  };

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Match day"
        title="Replay Cockpit"
        description={`Week ${replay.week}: ${replay.home_club_name} vs ${replay.away_club_name}`}
        stats={
          <>
            <StatChip label={replay.home_club_name} value={replay.home_survivors} />
            <StatChip label={replay.away_club_name} value={replay.away_survivors} />
            <StatChip label="Winner" value={replay.winner_name} tone="warning" />
          </>
        }
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.35fr_0.65fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-[var(--color-border)] bg-[var(--color-charcoal)] p-4 text-[var(--color-paper)]">
            <div className="flex items-center justify-between gap-3">
              <Badge tone="info">Tick {current?.tick ?? 0}</Badge>
              <span className="font-display uppercase tracking-wider text-xs opacity-80">
                {replay.events.length ? `${eventIndex + 1} / ${replay.events.length}` : '0 / 0'}
              </span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--color-paper)_16%,transparent)]">
              <div className="h-full rounded-full bg-[var(--color-mustard)] transition-all duration-200" style={{ width: `${progress}%` }} />
            </div>
          </div>

          <div className="court-panel m-4 flex min-h-56 items-center justify-center rounded-md border border-[var(--color-border)] p-6 text-center">
            <div className="max-w-2xl">
              <div className="font-display uppercase tracking-widest text-2xl md:text-3xl text-[var(--color-charcoal)]">
                {current?.label ?? 'No events'}
              </div>
              <div className="mt-3 text-sm leading-relaxed text-[var(--color-muted)]">
                {current?.detail ?? 'Replay data is unavailable.'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 px-4 pb-4">
            <ActionButton
              onClick={() => setEventIndex(index => Math.max(0, index - 1))}
              disabled={eventIndex === 0}
              variant="secondary"
            >
              Back
            </ActionButton>
            <ActionButton onClick={jumpToKeyEvent} disabled={keyEventIndex < 0} variant="accent">
              Key Play
            </ActionButton>
            <ActionButton
              onClick={() => setEventIndex(index => Math.min(replay.events.length - 1, index + 1))}
              disabled={eventIndex >= replay.events.length - 1}
              variant="secondary"
            >
              Next
            </ActionButton>
          </div>

          <div className="px-4 pb-4">
            <ReplayDebugDetails event={current} />
          </div>
        </Card>

        <div className="flex flex-col gap-5">
          <MatchReportPanel replay={replay} />
          <TopPerformersList replay={replay} />
          <ActionButton onClick={onAcknowledge} disabled={acknowledging} variant="primary" className="w-full">
            {acknowledging ? 'Saving...' : 'Continue'}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
