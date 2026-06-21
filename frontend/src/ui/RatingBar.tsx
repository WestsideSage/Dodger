import { useState } from 'react';
import styles from './RatingBar.module.css';

export function RatingBar({
  rating,
  max = 100,
  label,
  compact = false,
  explanation,
}: {
  rating: number;
  max?: number;
  label?: string;
  compact?: boolean;
  explanation?: string;
}) {
  const clamped = Math.min(max, Math.max(0, rating));
  const percentage = (clamped / max) * 100;
  const displayValue = Math.round(clamped);
  const [showInfo, setShowInfo] = useState(false);

  const scaledPct = (clamped / max) * 100;
  let barClass = styles.barPoor;
  if (scaledPct >= 80) barClass = styles.barElite;
  else if (scaledPct >= 60) barClass = styles.barGood;
  else if (scaledPct >= 40) barClass = styles.barAvg;

  return (
    <div className={styles.root}>
      {label && (
        <div className={styles.labelRow}>
          <span className={styles.labelText}>
            {label}
            {explanation && (
              <span
                data-testid="rating-explanation"
                data-explanation-label={label}
                role="button"
                tabIndex={0}
                aria-label={`${label} explanation: ${explanation}`}
                aria-expanded={showInfo}
                title={explanation}
                className={styles.infoBtn}
                onMouseEnter={() => setShowInfo(true)}
                onMouseLeave={() => setShowInfo(false)}
                onFocus={() => setShowInfo(true)}
                onBlur={() => setShowInfo(false)}
                onClick={() => setShowInfo((v) => !v)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setShowInfo((v) => !v);
                  } else if (e.key === 'Escape') {
                    setShowInfo(false);
                  }
                }}
              >
                ?
                {showInfo && (
                  <span role="tooltip" className={styles.tooltip}>
                    {explanation}
                  </span>
                )}
              </span>
            )}
          </span>
          <span>{displayValue}</span>
        </div>
      )}
      <div className={styles.barRow}>
        {!label && (
          <span className={styles.valueLeft}>{displayValue}</span>
        )}
        <div className={`${styles.track} ${compact ? styles.compact : ''}`}>
          <div className={`${styles.fill} ${barClass}`} style={{ width: `${percentage}%` }} />
        </div>
      </div>
    </div>
  );
}
