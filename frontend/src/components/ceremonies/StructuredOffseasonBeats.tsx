import type { ReactNode } from 'react';
import type { OffseasonBeat } from '../../types';
import { ActionButton, PageHeader } from '../ui';

type RecordsBeat = Extract<OffseasonBeat, { key: 'records_ratified' }>;
type HofBeat = Extract<OffseasonBeat, { key: 'hof_induction' }>;

function titleize(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function ProofDetails({ source }: { source: string }) {
  return (
    <details style={{ marginTop: '0.35rem' }}>
      <summary data-testid="broadcast-proof-toggle" style={{ cursor: 'pointer', color: '#64748b', fontSize: '0.72rem' }}>
        Show proof
      </summary>
      <code style={{ display: 'block', marginTop: '0.25rem', color: '#475569', fontSize: '0.72rem' }}>
        {source}
      </code>
    </details>
  );
}

function BeatShell({
  beat,
  description,
  testId,
  onComplete,
  acting,
  children,
}: {
  beat: OffseasonBeat;
  description: string;
  testId: string;
  onComplete: () => void;
  acting?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="command-offseason-shell" data-testid={testId}>
      <PageHeader
        eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
        title={beat.title}
        description={description}
        stats={
          <div className="command-offseason-progress" aria-label="Offseason beat progress">
            {Array.from({ length: beat.total_beats }).map((_, index) => (
              <span
                key={index}
                className={
                  index <= beat.beat_index
                    ? 'command-offseason-progress-step command-offseason-progress-step-active'
                    : 'command-offseason-progress-step'
                }
              />
            ))}
          </div>
        }
      />
      {children}
      {beat.can_advance && (
        <div className="dm-panel command-action-bar">
          <div>
            <p className="dm-kicker">Ceremony Control</p>
            <p>Continue to the next offseason beat.</p>
          </div>
          <div className="command-action-buttons">
            <ActionButton variant="primary" onClick={onComplete} disabled={acting}>
              {acting ? 'Advancing...' : 'Continue'}
            </ActionButton>
          </div>
        </div>
      )}
    </section>
  );
}

export function RecordsRatified({
  beat,
  onComplete,
  acting,
}: {
  beat: RecordsBeat;
  onComplete: () => void;
  acting?: boolean;
}) {
  const records = beat.payload.records ?? [];
  return (
    <BeatShell
      beat={beat}
      testId="offseason-records-ratified"
      description="The league record book is updated for the season just completed."
      onComplete={onComplete}
      acting={acting}
    >
      <article className="dm-panel command-offseason-feature">
        <p className="dm-kicker">Records Ratified</p>
        {records.length === 0 ? (
          <p className="command-offseason-copy">No new league records were set this season.</p>
        ) : (
          <div style={{ display: 'grid', gap: '0.6rem', marginTop: '0.5rem' }}>
            {records.map(record => (
              <div
                key={record.record_id ?? record.record_type}
                data-broadcast-proof-source={record.proof_source ?? `record:${record.record_type}`}
                style={{
                  padding: '0.7rem 0.9rem',
                  background: '#0a1220',
                  border: '1px solid #1e293b',
                  borderLeft: '3px solid #f97316',
                  borderRadius: '4px',
                }}
              >
                <p className="dm-kicker" style={{ margin: 0, color: '#f97316', fontSize: '0.62rem' }}>
                  {titleize(record.record_type)}
                </p>
                <p style={{ margin: '0.2rem 0', color: '#f1f5f9', fontWeight: 700 }}>
                  {record.holder_name}
                </p>
                <p
                  style={{
                    margin: 0,
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '0.8rem',
                    color: '#10b981',
                  }}
                >
                  {formatValue(record.previous_value)}{' -> '}{formatValue(record.new_value)}
                </p>
                {record.detail && (
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.76rem', color: '#94a3b8' }}>
                    {record.detail}
                  </p>
                )}
                <ProofDetails source={record.proof_source ?? `record:${record.record_type}`} />
              </div>
            ))}
          </div>
        )}
      </article>
    </BeatShell>
  );
}

export function HallOfFameInduction({
  beat,
  onComplete,
  acting,
}: {
  beat: HofBeat;
  onComplete: () => void;
  acting?: boolean;
}) {
  const inductees = beat.payload.inductees ?? [];
  return (
    <BeatShell
      beat={beat}
      testId="offseason-hof-induction"
      description="The game's greatest careers are enshrined."
      onComplete={onComplete}
      acting={acting}
    >
      <article className="dm-panel command-offseason-feature">
        <p className="dm-kicker">Hall of Fame Induction</p>
        {inductees.length === 0 ? (
          <p className="command-offseason-copy">No new inductees this off-season.</p>
        ) : (
          <div style={{ display: 'grid', gap: '0.6rem', marginTop: '0.5rem' }}>
            {inductees.map(inductee => (
              <div
                key={inductee.player_id ?? inductee.player_name}
                data-broadcast-proof-source={inductee.proof_source ?? `career:${inductee.player_id ?? inductee.player_name}`}
                style={{
                  padding: '0.8rem 0.95rem',
                  background: '#0a1220',
                  border: '1px solid #1e293b',
                  borderLeft: '3px solid #fbbf24',
                  borderRadius: '4px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    gap: '0.75rem',
                    flexWrap: 'wrap',
                  }}
                >
                  <p style={{ margin: 0, color: '#fbbf24', fontWeight: 800, fontSize: '1rem' }}>
                    {inductee.player_name}
                  </p>
                  <p
                    style={{
                      margin: 0,
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '0.74rem',
                      color: '#94a3b8',
                    }}
                  >
                    Legacy {inductee.legacy_score.toFixed(1)} / {inductee.threshold.toFixed(1)}
                  </p>
                </div>
                <p
                  style={{
                    margin: '0.35rem 0 0',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '0.74rem',
                    color: '#cbd5e1',
                  }}
                >
                  {inductee.seasons_played} seasons | {inductee.championships} titles | {inductee.awards_won} awards | {inductee.total_eliminations} career elims
                </p>
                {inductee.reasons.length > 0 && (
                  <p style={{ margin: '0.3rem 0 0', fontSize: '0.76rem', color: '#94a3b8' }}>
                    {inductee.reasons.join(' | ')}
                  </p>
                )}
                <ProofDetails source={inductee.proof_source ?? `career:${inductee.player_id ?? inductee.player_name}`} />
              </div>
            ))}
          </div>
        )}
      </article>
    </BeatShell>
  );
}
