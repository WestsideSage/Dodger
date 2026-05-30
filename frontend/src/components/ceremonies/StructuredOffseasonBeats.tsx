import type { ReactNode } from 'react';
import { useState } from 'react';
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

function formatProofSource(source: string): string {
  let cleaned = source;
  if (cleaned.startsWith('record:')) {
    cleaned = cleaned.substring('record:'.length);
  }
  if (cleaned.startsWith('career:')) {
    cleaned = cleaned.substring('career:'.length);
  }
  cleaned = cleaned.replaceAll('_', ' ').replaceAll('-', ' ');
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function ProofDetails({ source }: { source: string }) {
  return (
    <details style={{ marginTop: '0.35rem' }}>
      <summary data-testid="broadcast-proof-toggle" style={{ cursor: 'pointer', color: '#64748b', fontSize: '0.72rem' }}>
        View evidence ⌄
      </summary>
      <code style={{ display: 'block', marginTop: '0.25rem', color: '#475569', fontSize: '0.72rem' }}>
        {formatProofSource(source)}
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
  const allRecords = beat.payload.records ?? [];
  const recordsBookEmpty = beat.payload.records_book_empty ?? false;

  // Phase 7: My Club / League scope filter. Default to My Club when the player's
  // club holds at least one record (open question #5 resolution: lean My Club),
  // otherwise fall back to League so the beat doesn't open on an empty panel.
  const hasMyClubRecords = allRecords.some(r => r.is_my_club);
  const [scope, setScope] = useState<'my_club' | 'league'>(
    hasMyClubRecords ? 'my_club' : 'league'
  );

  const myClubCount = allRecords.filter(r => r.is_my_club).length;
  const leagueCount = allRecords.length;

  const records = scope === 'my_club'
    ? allRecords.filter(r => r.is_my_club)
    : allRecords;

  // When My Club is empty but the league has records, the empty-state offers a
  // one-tap path to League scope (Brief 4.8, criterion #4) rather than dead-ending.
  const myClubEmptyButLeagueHas =
    scope === 'my_club' && !recordsBookEmpty && allRecords.length > 0 && !hasMyClubRecords;

  function emptyMessage(): string {
    if (recordsBookEmpty) {
      return 'The record book is empty — records will be set as seasons are played.';
    }
    if (myClubEmptyButLeagueHas) {
      return 'Your club holds no league records yet.';
    }
    return 'No new records were set this season.';
  }

  return (
    <BeatShell
      beat={beat}
      testId="offseason-records-ratified"
      description="The league record book is updated for the season just completed."
      onComplete={onComplete}
      acting={acting}
    >
      <article className="dm-panel command-offseason-feature">
        <p className="dm-kicker" style={{ margin: 0 }}>Records Ratified</p>

        {/* Scope filter — elevated to a full-width segmented control so it
            reads as the primary navigation choice for the screen, not a
            top-right afterthought (Brief 4.8, criterion #1). */}
        {!recordsBookEmpty && (
          <div
            role="group"
            aria-label="Records scope filter"
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '0.3rem',
              marginTop: '0.6rem',
              padding: '0.25rem',
              background: '#0a1220',
              border: '1px solid #1e293b',
              borderRadius: '8px',
            }}
          >
            {([
              { id: 'my_club', label: 'My Club', count: myClubCount, accent: '#fbbf24' },
              { id: 'league', label: 'League', count: leagueCount, accent: '#38bdf8' },
            ] as const).map(opt => {
              const active = scope === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => setScope(opt.id)}
                  aria-pressed={active}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.45rem',
                    padding: '0.5rem 0.5rem',
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    borderRadius: '6px',
                    border: 'none',
                    background: active ? '#162033' : 'transparent',
                    boxShadow: active ? `inset 0 0 0 1px ${opt.accent}66` : 'none',
                    color: active ? '#f1f5f9' : '#64748b',
                    cursor: 'pointer',
                    transition: 'background 120ms, color 120ms',
                  }}
                >
                  <span>{opt.label}</span>
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '0.68rem',
                      fontWeight: 800,
                      minWidth: '1.3rem',
                      padding: '0.05rem 0.35rem',
                      borderRadius: '999px',
                      background: active ? opt.accent : '#1e293b',
                      color: active ? '#04111f' : '#94a3b8',
                    }}
                  >
                    {opt.count}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {records.length === 0 ? (
          <div style={{ marginTop: '0.85rem', textAlign: myClubEmptyButLeagueHas ? 'center' : 'left' }}>
            <p className="command-offseason-copy" style={{ margin: 0 }}>{emptyMessage()}</p>
            {myClubEmptyButLeagueHas && (
              <button
                onClick={() => setScope('league')}
                style={{
                  marginTop: '0.7rem',
                  padding: '0.5rem 1rem',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  borderRadius: '6px',
                  border: '1px solid #38bdf8',
                  background: 'rgba(56,189,248,0.12)',
                  color: '#7dd3fc',
                  cursor: 'pointer',
                }}
              >
                Switch to League view ({leagueCount}) →
              </button>
            )}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '0.6rem', marginTop: '0.85rem' }}>
            {records.map(record => {
              const mine = record.is_my_club === true;
              const delta = record.new_value - record.previous_value;
              const accent = mine ? '#fbbf24' : '#475569';
              return (
                <div
                  key={record.record_id ?? record.record_type}
                  data-broadcast-proof-source={record.proof_source ?? `record:${record.record_type}`}
                  data-my-club={mine ? 'true' : 'false'}
                  style={{
                    padding: '0.75rem 0.9rem',
                    background: mine
                      ? 'linear-gradient(90deg, rgba(251,191,36,0.07), rgba(10,18,32,0) 60%)'
                      : '#0a1220',
                    border: '1px solid #1e293b',
                    borderLeft: `3px solid ${accent}`,
                    borderRadius: '4px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                    <p className="dm-kicker" style={{ margin: 0, color: accent, fontSize: '0.62rem' }}>
                      {titleize(record.record_type)}
                    </p>
                    {mine && (
                      <span
                        style={{
                          fontSize: '0.56rem',
                          fontWeight: 900,
                          letterSpacing: '0.08em',
                          textTransform: 'uppercase',
                          padding: '0.12rem 0.4rem',
                          borderRadius: '999px',
                          background: 'rgba(251,191,36,0.16)',
                          color: '#fbbf24',
                        }}
                      >
                        Your Club
                      </span>
                    )}
                  </div>
                  <p style={{ margin: '0.25rem 0 0.3rem', color: '#f1f5f9', fontWeight: 700 }}>
                    {record.holder_name}
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: '0.8rem',
                        color: '#cbd5e1',
                      }}
                    >
                      {formatValue(record.previous_value)}{' → '}
                      <strong style={{ color: '#10b981' }}>{formatValue(record.new_value)}</strong>
                    </span>
                    {delta > 0 && (
                      <span
                        style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: '0.68rem',
                          fontWeight: 800,
                          padding: '0.08rem 0.4rem',
                          borderRadius: '999px',
                          background: 'rgba(16,185,129,0.14)',
                          color: '#34d399',
                        }}
                      >
                        +{formatValue(delta)}
                      </span>
                    )}
                  </div>
                  {record.detail && (
                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.76rem', color: '#94a3b8' }}>
                      {record.detail}
                    </p>
                  )}
                  <ProofDetails source={record.proof_source ?? `record:${record.record_type}`} />
                </div>
              );
            })}
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
