import styles from './aftermathCards.module.css';
import type { Aftermath } from '../../../types';
import type { ReactNode } from 'react';

function FalloutCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className={styles.falloutCard}>
      <p className={styles.falloutCardKicker}>{title}</p>
      <div className={styles.falloutCardBody}>{children}</div>
    </article>
  );
}

export function FalloutGrid({
  byeRecovery,
  developmentFeedback,
  playerGrowth,
  standingsShift,
  recruitReactions,
}: {
  byeRecovery?: Aftermath['bye_recovery'];
  developmentFeedback?: Aftermath['development_feedback'];
  playerGrowth: Aftermath['player_growth_deltas'];
  standingsShift: Aftermath['standings_shift'];
  recruitReactions: Aftermath['recruit_reactions'];
}) {
  return (
    <section className={styles.fallout} data-testid="fallout-grid">
      <div className={styles.falloutHeader}>
        <span className={styles.falloutKicker}>Aftermath</span>
        <span className={styles.falloutTitle}>Week Fallout</span>
      </div>
      <div className={styles.falloutGrid}>
        <FalloutCard title={playerGrowth.length > 0 ? 'Who Grew' : 'Training Impact'}>
          {playerGrowth.length > 0 ? (
            <ul className={styles.falloutList}>
              {playerGrowth.slice(0, 4).map((item) => (
                <li key={`${item.player_id}-${item.attribute}`} className={styles.falloutItem}>
                  <strong className={styles.falloutItemName}>{item.player_name}</strong>
                  <span
                    className={`${styles.falloutItemValue} ${item.delta > 0 ? styles.falloutValuePos : styles.falloutValueNeg}`}
                  >
                    {item.attribute} {item.delta > 0 ? '+' : ''}{item.delta}
                  </span>
                </li>
              ))}
            </ul>
          ) : developmentFeedback ? (
            <div className={styles.trainingImpact}>
              <strong className={styles.trainingFocus}>{developmentFeedback.focus_label}</strong>
              <p className={styles.infoText}>{developmentFeedback.summary}</p>
              <span className={styles.trainingProgress}>{developmentFeedback.progress}</span>
              {byeRecovery && <small className={styles.trainingBye}>{byeRecovery.summary}</small>}
            </div>
          ) : (
            <p className={styles.falloutEmpty}>No growth logged this week.</p>
          )}
        </FalloutCard>

        <FalloutCard title="Standings Shift">
          {standingsShift.length > 0 ? (
            <>
              <div className={styles.falloutStandingsHeader}>
                <span>Club</span>
                <span>Prev → New</span>
              </div>
              <ul className={`${styles.falloutList} ${styles.falloutListCompact}`}>
                {standingsShift.slice(0, 3).map((item) => {
                  const moved = item.new_rank - item.old_rank;
                  const up = moved < 0;
                  return (
                    <li key={item.club_id} className={styles.falloutItem}>
                      <strong className={styles.falloutItemName}>{item.club_name}</strong>
                      <span
                        className={`${styles.falloutItemValue} ${up ? styles.falloutValuePos : styles.falloutValueNeg}`}
                      >
                        {up ? '↑' : '↓'} #{item.old_rank} → #{item.new_rank}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p className={styles.falloutEmpty}>Records updated — no rank changes this week.</p>
          )}
        </FalloutCard>

        <FalloutCard title="Prospect Pulse">
          {recruitReactions.length > 0 ? (
            <ul className={`${styles.falloutList} ${styles.falloutListLoose}`}>
              {recruitReactions.slice(0, 3).map((item) => {
                const delta = parseInt(item.interest_delta, 10);
                const isPositive = !isNaN(delta) && delta > 0;
                const isZero = !isNaN(delta) && delta === 0;
                return (
                  <li key={item.prospect_id}>
                    <div className={styles.falloutItem}>
                      <strong className={styles.falloutItemName}>{item.prospect_name}</strong>
                      <span
                        className={`${styles.falloutItemValue} ${
                          isPositive
                            ? styles.falloutValuePos
                            : isZero
                              ? styles.falloutValueNeutral
                              : styles.falloutValueNeg
                        }`}
                      >
                        {item.interest_delta}
                      </span>
                    </div>
                    <small className={styles.falloutItemDetail}>{item.evidence}</small>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className={styles.falloutEmpty}>No prospect movement this week.</p>
          )}
        </FalloutCard>
      </div>
    </section>
  );
}
