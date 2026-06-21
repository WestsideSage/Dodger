import type { CommandCenterPlan } from '../../types';
import { ActionButton } from '../../ui';
import styles from './WeeklyChecklist.module.css';

export function WeeklyChecklist({
  plan,
  onAcceptPlan,
  planConfirmed,
  showAction = true,
  bare = false,
}: {
  plan: CommandCenterPlan;
  onAcceptPlan: () => void;
  planConfirmed: boolean;
  showAction?: boolean;
  bare?: boolean;
}) {
  const warnings: string[] = plan?.warnings ?? [];
  const recommendations: Array<{ department: string; text: string }> = plan?.recommendations ?? [];
  const lineupSummary: string | undefined = plan?.lineup?.summary;
  const starterNames: string[] = (plan?.lineup?.players ?? []).slice(0, 6).map(player => player.name);

  const content = (
    <div className={styles.body}>

      {/* Lineup status */}
      <div>
        <p className={styles.sectionLabel}>Lineup</p>
        {starterNames.length > 0 ? (
          <p className={styles.lineupNames}>{starterNames.join(' · ')}</p>
        ) : lineupSummary ? (
          <p className={styles.lineupNames}>{lineupSummary}</p>
        ) : null}
      </div>

      {/* Readiness / warnings */}
      <div>
        <p className={styles.sectionLabel}>Readiness</p>
        {warnings.length === 0 ? (
          <div className={styles.statusRow}>
            <span className={`${styles.statusIcon} ${styles['statusIcon--ok']}`}>✓</span>
            <span className={`${styles.statusText} ${styles['statusText--ok']}`}>
              Lineup and tactics are aligned. Squad is ready for match day.
            </span>
          </div>
        ) : (
          <div className={styles.warnList}>
            {warnings.map((w, i) => (
              <div key={i} className={styles.statusRow}>
                <span className={`${styles.statusIcon} ${styles['statusIcon--warn']}`}>!</span>
                <span className={`${styles.statusText} ${styles['statusText--warn']}`}>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Gated on planConfirmed to flip right-rail Plan Status to OK after lock */}
      <div>
        <p className={styles.sectionLabel}>Plan Status</p>
        <div className={styles.statusRow}>
          <span
            className={`${styles.statusIcon} ${planConfirmed ? styles['statusIcon--ok'] : styles['statusIcon--warn']}`}
          >
            {planConfirmed ? 'OK' : '!'}
          </span>
          <span
            className={`${styles.statusText} ${planConfirmed ? styles['statusText--confirmed'] : styles['statusText--warn']}`}
          >
            {planConfirmed
              ? 'Staff plan is confirmed. Risk notes stay visible but do not block match day.'
              : 'Confirm the staff plan to unlock match simulation.'}
          </span>
        </div>
      </div>

      {/* Top staff recommendation */}
      {recommendations.length > 0 && (
        <div className={styles.divider}>
          <p className={styles.recLabel}>{recommendations[0].department} Dept.</p>
          <p className={styles.recText}>{recommendations[0].text}</p>
        </div>
      )}

      {showAction && (
        <div className={styles.divider}>
          <ActionButton variant={planConfirmed ? 'ghost' : 'primary'} onClick={onAcceptPlan}>
            {planConfirmed ? 'Plan Confirmed' : 'Confirm Plan'}
          </ActionButton>
        </div>
      )}
    </div>
  );

  if (bare) return content;

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>Pre-Game</p>
        <h3 className={styles.title}>Weekly Checklist</h3>
      </div>
      {content}
    </div>
  );
}
