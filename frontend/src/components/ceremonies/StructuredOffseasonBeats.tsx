import type { ReactNode } from 'react';
import { useState } from 'react';
import type { OffseasonBeat } from '../../types';
import { ActionButton, PageHeader } from '../../ui';
import styles from './StructuredOffseasonBeats.module.css';
import chrome from '../chrome.module.css';
import cer from './ceremony.module.css';

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
    <details className={styles.proofDetails}>
      <summary data-testid="broadcast-proof-toggle" className={styles.proofToggle}>
        View evidence ⌄
      </summary>
      <code className={styles.proofCode}>
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
    <section className={chrome.offseasonShell} data-testid={testId}>
      <PageHeader
        eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
        title={beat.title}
        description={description}
        stats={
          <div className={chrome.offseasonProgress} aria-label="Offseason beat progress">
            {Array.from({ length: beat.total_beats }).map((_, index) => (
              <span
                key={index}
                className={
                  index <= beat.beat_index
                    ? `${chrome.offseasonProgressStep} ${chrome.offseasonProgressStepActive}`
                    : chrome.offseasonProgressStep
                }
              />
            ))}
          </div>
        }
      />
      {children}
      {beat.can_advance && (
        <div className={`${chrome.dmPanel} ${chrome.actionBar}`}>
          <div>
            <p className={chrome.dmKicker}>Ceremony Control</p>
            <p>Continue to the next offseason beat.</p>
          </div>
          <div className={chrome.actionButtons}>
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
      <article className={`${chrome.dmPanel} ${chrome.offseasonFeature}`}>
        <p className={`${chrome.dmKicker} ${styles.kicker}`}>Records Ratified</p>

        {/* Scope filter — elevated to a full-width segmented control so it
            reads as the primary navigation choice for the screen, not a
            top-right afterthought (Brief 4.8, criterion #1). */}
        {!recordsBookEmpty && (
          <div role="group" aria-label="Records scope filter" className={styles.scopeGroup}>
            {([
              { id: 'my_club', label: 'My Club', count: myClubCount },
              { id: 'league', label: 'League', count: leagueCount },
            ] as const).map(opt => {
              const active = scope === opt.id;
              const isMine = opt.id === 'my_club';
              return (
                <button
                  key={opt.id}
                  onClick={() => setScope(opt.id)}
                  aria-pressed={active}
                  className={`${styles.scopeBtn} ${active ? styles.scopeBtnActive : ''} ${active ? (isMine ? styles.scopeBtnActiveMine : styles.scopeBtnActiveLeague) : ''}`}
                >
                  <span>{opt.label}</span>
                  <span className={`${styles.scopeCount} ${active ? (isMine ? styles.scopeCountActiveMine : styles.scopeCountActiveLeague) : ''}`}>
                    {opt.count}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {/* Milestone vs bookkeeping: a holder CHANGE (or first-time record) is
            the event and keeps the marquee card; the same leader re-breaking
            their own counter record happens ~every season and reads as noise
            when given equal drama — those compress into quiet ledger rows. */}
        {records.length === 0 ? (
          <div className={myClubEmptyButLeagueHas ? styles.emptyWrapCentered : styles.emptyWrap}>
            <p className={`${chrome.offseasonCopy} ${styles.emptyCopy}`}>{emptyMessage()}</p>
            {myClubEmptyButLeagueHas && (
              <button onClick={() => setScope('league')} className={styles.switchBtn}>
                Switch to League view ({leagueCount}) →
              </button>
            )}
          </div>
        ) : (() => {
          const milestones = records.filter(r => r.is_new_holder !== false);
          // V21 middle tier (owner: milestones should feel like real
          // milestones): same-holder extensions that crossed a round-number
          // boundary get their own band; plain extensions stay quiet.
          const careerMilestones = records.filter(
            r => r.is_new_holder === false && Boolean(r.milestone_label),
          );
          const extensions = records.filter(
            r => r.is_new_holder === false && !r.milestone_label,
          );
          return (
          <div className={styles.cards}>
            {milestones.map(record => {
              const mine = record.is_my_club === true;
              const delta = record.new_value - record.previous_value;
              const dethroned = Boolean(
                record.previous_holder_name && record.previous_holder_name !== record.holder_name,
              );
              return (
                <div
                  key={record.record_id ?? record.record_type}
                  data-broadcast-proof-source={record.proof_source ?? `record:${record.record_type}`}
                  data-my-club={mine ? 'true' : 'false'}
                  data-testid="record-milestone-card"
                  className={`${styles.card} ${mine ? styles.cardMine : ''}`}
                >
                  <div className={styles.cardTop}>
                    <p className={`${chrome.dmKicker} ${styles.cardType} ${mine ? styles.cardTypeMine : ''}`}>
                      {titleize(record.record_type)}
                    </p>
                    <span className={styles.badges}>
                      {dethroned && (
                        <span className={`${styles.badge} ${styles.badgeNewHolder}`}>
                          New Holder
                        </span>
                      )}
                      {mine && (
                        <span className={`${styles.badge} ${styles.badgeMine}`}>
                          Your Club
                        </span>
                      )}
                    </span>
                  </div>
                  <p className={styles.holder}>
                    {record.holder_name}
                  </p>
                  <div className={styles.valueRow}>
                    <span className={styles.value}>
                      {formatValue(record.previous_value)}{' → '}
                      <strong className={styles.valueNew}>{formatValue(record.new_value)}</strong>
                    </span>
                    {delta > 0 && (
                      <span className={styles.deltaChip}>
                        +{formatValue(delta)}
                      </span>
                    )}
                    {dethroned && (
                      <span className={styles.dethrone}>
                        takes the record from {record.previous_holder_name}
                      </span>
                    )}
                  </div>
                  {record.detail && (
                    <p className={styles.detail}>
                      {record.detail}
                    </p>
                  )}
                  <ProofDetails source={record.proof_source ?? `record:${record.record_type}`} />
                </div>
              );
            })}

            {careerMilestones.length > 0 && (
              <div data-testid="record-career-milestones" className={milestones.length > 0 ? styles.bandGold : undefined}>
                <p className={`${chrome.dmKicker} ${styles.bandLabel} ${styles.bandLabelGold}`}>
                  Career milestones
                </p>
                <div className={styles.bandRows}>
                  {careerMilestones.map(record => (
                    <div
                      key={record.record_id ?? record.record_type}
                      data-testid="record-milestone-row"
                      data-my-club={record.is_my_club === true ? 'true' : 'false'}
                      className={styles.milestoneRow}
                    >
                      <span className={styles.milestoneTag}>
                        Milestone
                      </span>
                      <span className={styles.milestoneName}>{record.holder_name}</span>
                      <span className={styles.milestoneLabel}>{record.milestone_label?.toLowerCase()}</span>
                      <span className={styles.milestoneNow}>
                        now {formatValue(record.new_value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {extensions.length > 0 && (
              <div data-testid="record-extensions" className={milestones.length > 0 || careerMilestones.length > 0 ? styles.bandGold : undefined}>
                <p className={`${chrome.dmKicker} ${styles.bandLabel} ${styles.bandLabelMuted}`}>
                  Extended their own records
                </p>
                <div className={styles.bandRows}>
                  {extensions.map(record => {
                    const mine = record.is_my_club === true;
                    return (
                      <div
                        key={record.record_id ?? record.record_type}
                        data-broadcast-proof-source={record.proof_source ?? `record:${record.record_type}`}
                        data-my-club={mine ? 'true' : 'false'}
                        data-testid="record-extension-row"
                        className={styles.extensionRow}
                      >
                        <span className={styles.extName}>{record.holder_name}</span>
                        <span className={styles.extDesc}>
                          extends their own {titleize(record.record_type).toLowerCase()} mark
                        </span>
                        <span className={styles.extValue}>
                          {formatValue(record.previous_value)}{' → '}
                          <strong className={styles.extValueNew}>{formatValue(record.new_value)}</strong>
                        </span>
                        {mine && (
                          <span className={styles.extMine}>
                            Your Club
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
          );
        })()}
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
      <article className={`${chrome.dmPanel} ${chrome.offseasonFeature}`}>
        <p className={chrome.dmKicker}>Hall of Fame Induction</p>
        {inductees.length === 0 ? (
          <p className={chrome.offseasonCopy}>No new inductees this off-season.</p>
        ) : (
          <div className={styles.hofGrid}>
            {inductees.map(inductee => (
              <div
                key={inductee.player_id ?? inductee.player_name}
                className={cer['hof-plaque']}
                data-broadcast-proof-source={inductee.proof_source ?? `career:${inductee.player_id ?? inductee.player_name}`}
              >
                <span className={cer['hof-enshrined']} aria-label="Enshrined in the Hall of Fame">Enshrined</span>
                <p className={cer['hof-name']}>{inductee.player_name}</p>
                <div className={cer['hof-career']}>
                  <span>{inductee.seasons_played} seasons</span>
                  <span>{inductee.championships} titles</span>
                  <span>{inductee.awards_won} awards</span>
                  <span>{inductee.total_eliminations} career elims</span>
                </div>
                {/* V21 zero-floats (owner: no fractional numbers on any
                    player-facing surface): the legacy line is integerized. */}
                <p className={cer['hof-legacy']}>
                  Legacy {Math.round(inductee.legacy_score)} · clears the {Math.round(inductee.threshold)} induction bar
                </p>
                {inductee.reasons.length > 0 && (
                  <p className={cer['hof-reasons']}>{inductee.reasons.join(' · ')}</p>
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
