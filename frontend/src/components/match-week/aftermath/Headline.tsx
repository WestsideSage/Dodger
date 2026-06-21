import styles from './aftermathCards.module.css';

export function Headline({
  text,
  week,
  contextLine,
  stage,
  kicker = 'War Room',
  subLabel,
  accent = 'default',
}: {
  text: string;
  week?: number;
  subtitle?: string;
  contextLine?: string;
  stage?: string;
  /** Override the mono kicker (e.g. "Bye Week" instead of "War Room"). */
  kicker?: string;
  /** Override the "· Wk N Debrief" sub-label (e.g. "· Rest Report"). */
  subLabel?: string;
  /** Accent variant (semantic, token-driven): default Volt, or the dim bye tone. */
  accent?: 'default' | 'bye';
}) {
  const isPlayoff = Boolean(stage && stage !== 'Regular Season');
  return (
    <div className={`${styles.headline}${accent === 'bye' ? ` ${styles.headlineBye}` : ''}`}>
      <div className={styles.headlineKickRow}>
        <span className={styles.headlineKicker}>{kicker}</span>
        {(week !== undefined || isPlayoff || subLabel) && (
          <span className={`${styles.headlineSub}${isPlayoff ? ` ${styles.headlineSubPlayoff}` : ''}`}>
            {subLabel ? `· ${subLabel}` : isPlayoff ? `· ${stage} Debrief` : `· Wk ${week} Debrief`}
          </span>
        )}
      </div>
      <div className={styles.headlineMain}>
        <span className={styles.headlineText}>{text}</span>
        {contextLine && <span className={styles.headlineContext}>{contextLine}</span>}
      </div>
    </div>
  );
}
