import { memo, useMemo, useState } from 'react';
import type { CommandDashboardLane, MatchReplayResponse, ReplayEvent, ReplayProofEvent } from '../types';
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

const EvidenceLanes = memo(function EvidenceLanes({ lanes }: { lanes: CommandDashboardLane[] }) {
  return (
    <Card className="p-4">
      <h3 className="font-display uppercase tracking-widest text-lg text-[var(--color-charcoal)]">Evidence Lanes</h3>
      <div className="mt-3 flex flex-col gap-3">
        {lanes.map(lane => (
          <div key={lane.title} className="border-t border-[var(--color-line)] pt-3 first:border-t-0 first:pt-0">
            <div className="font-display uppercase tracking-wider text-[11px] text-[var(--color-brick)]">{lane.title}</div>
            <p className="mt-1 text-sm font-bold leading-snug">{lane.summary}</p>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-relaxed text-[var(--color-muted)]">
              {lane.items.map(item => <li key={item}>{item}</li>)}
            </ul>
          </div>
        ))}
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

function ContextBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="proof-context-block">
      <div className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">{title}</div>
      <ul className="mt-1 space-y-1 text-sm leading-relaxed">
        {items.map(item => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function ProofInspector({
  proof,
  replay,
}: {
  proof?: ReplayProofEvent;
  replay: MatchReplayResponse;
}) {
  if (!proof) {
    return (
      <div className="proof-inspector">
        <p className="text-sm font-bold text-[var(--color-muted)]">No throw proof events were available for this replay.</p>
      </div>
    );
  }
  const odds = Object.entries(proof.odds);
  const rolls = Object.entries(proof.rolls);
  return (
    <div className="proof-inspector">
      <div className="grid grid-cols-2 gap-2">
        <StatChip label={replay.home_club_name} value={proof.score_state.home_living} />
        <StatChip label={replay.away_club_name} value={proof.score_state.away_living} />
      </div>
      <div>
        <div className="font-display uppercase tracking-wider text-[11px] text-[var(--color-brick)]">Outcome</div>
        <p className="mt-1 text-sm font-bold leading-relaxed">{proof.detail}</p>
        <div className="mt-2 flex flex-wrap gap-1">
          {proof.proof_tags.map(tag => <Badge key={tag} tone="info">{tag}</Badge>)}
        </div>
      </div>
      <ContextBlock
        title="Odds and rolls"
        items={
          odds.length || rolls.length
            ? [
                ...odds.map(([key, value]) => `${key.replaceAll('_', ' ')} ${value.toFixed(2)}`),
                ...rolls.map(([key, value]) => `${key.replaceAll('_', ' ')} roll ${value.toFixed(2)}`),
              ]
            : ['No odds or rolls were saved for this event.']
        }
      />
      <ContextBlock title="Decision context" items={proof.decision_context.items} />
      <ContextBlock title="Tactic context" items={proof.tactic_context.items.length ? proof.tactic_context.items : ['No tactic context was saved for this throw.']} />
      <ContextBlock title="Fatigue" items={proof.fatigue.items} />
      <ContextBlock title="Liability" items={proof.liability_context.items.length ? proof.liability_context.items : ['No lineup liability evidence on this throw.']} />
    </div>
  );
}

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
  const proofEvents = useMemo(() => replay.proof_events ?? [], [replay.proof_events]);
  const proofIndex = useMemo(() => {
    const exact = proofEvents.findIndex(event => event.sequence_index === eventIndex);
    if (exact >= 0) return exact;
    for (let index = proofEvents.length - 1; index >= 0; index -= 1) {
      if (proofEvents[index].sequence_index <= eventIndex) return index;
    }
    return 0;
  }, [eventIndex, proofEvents]);
  const currentProof = proofEvents[proofIndex];
  const keyEventIndex = useMemo(
    () => replay.key_play_indices?.[0] ?? -1,
    [replay.key_play_indices]
  );
  const progress = replay.events.length ? ((eventIndex + 1) / replay.events.length) * 100 : 0;

  const jumpToProof = (proof: ReplayProofEvent) => {
    setEventIndex(proof.sequence_index);
  };

  const jumpToKeyEvent = (direction = 1) => {
    const keyIndices = replay.key_play_indices ?? [];
    if (!keyIndices.length) return;
    const currentKey = keyIndices.findIndex(index => index === proofIndex);
    const nextKey = currentKey < 0
      ? keyIndices[0]
      : keyIndices[Math.max(0, Math.min(keyIndices.length - 1, currentKey + direction))];
    const proof = proofEvents[nextKey];
    if (proof) jumpToProof(proof);
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
            <ActionButton onClick={() => jumpToKeyEvent(1)} disabled={keyEventIndex < 0} variant="accent">
              Next Key
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
          <EvidenceLanes lanes={replay.report.evidence_lanes ?? []} />
          <TopPerformersList replay={replay} />
          <ActionButton onClick={onAcknowledge} disabled={acknowledging} variant="primary" className="w-full">
            {acknowledging ? 'Saving...' : 'Continue'}
          </ActionButton>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.78fr_1.22fr]">
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-display uppercase tracking-widest text-lg text-[var(--color-charcoal)]">Key Plays</h3>
            <div className="grid grid-cols-2 gap-2">
              <ActionButton onClick={() => jumpToKeyEvent(-1)} disabled={!replay.key_play_indices?.length} variant="secondary">Prev</ActionButton>
              <ActionButton onClick={() => jumpToKeyEvent(1)} disabled={!replay.key_play_indices?.length} variant="secondary">Next</ActionButton>
            </div>
          </div>
          <div className="proof-list mt-3">
            {(replay.key_play_indices ?? []).map(index => {
              const proof = proofEvents[index];
              if (!proof) return null;
              const active = proof.sequence_index === currentProof?.sequence_index;
              return (
                <button
                  key={`${proof.sequence_index}-${proof.tick}`}
                  type="button"
                  className={`proof-list-item ${active ? 'proof-list-item-active' : ''}`}
                  onClick={() => jumpToProof(proof)}
                >
                  <span>Tick {proof.tick}</span>
                  <strong>{proof.summary}</strong>
                </button>
              );
            })}
            {!replay.key_play_indices?.length && (
              <p className="text-sm font-bold text-[var(--color-muted)]">No key play was recorded for this match.</p>
            )}
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-display uppercase tracking-widest text-lg text-[var(--color-charcoal)]">Proof Inspector</h3>
          <ProofInspector proof={currentProof} replay={replay} />
        </Card>
      </div>
    </div>
  );
}
