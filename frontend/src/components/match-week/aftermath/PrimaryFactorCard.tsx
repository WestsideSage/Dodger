import type { Aftermath } from '../../../types';
import styles from './aftermathCards.module.css';

const CONFIDENCE_META: Record<string, { label: string; cls: string }> = {
  high: { label: 'HIGH CONFIDENCE', cls: styles.factorHigh },
  medium: { label: 'LIKELY', cls: styles.factorMedium },
  low: { label: 'INCONCLUSIVE', cls: styles.factorLow },
};

export function PrimaryFactorCard({ factor }: { factor: NonNullable<Aftermath['primary_factor']> }) {
  const meta = CONFIDENCE_META[factor.confidence] ?? CONFIDENCE_META.low;

  return (
    <div
      data-testid="primary-factor"
      data-factor-code={factor.code}
      className={`${styles.factorCard} ${meta.cls}`}
    >
      <div className={styles.factorHead}>
        <span className={styles.kicker}>Primary Factor</span>
        <span data-testid="primary-factor-confidence" className={styles.factorBadge}>
          {meta.label}
        </span>
      </div>
      <p className={styles.factorTitle}>{factor.title}</p>
      <p className={styles.factorSentence}>{factor.sentence}</p>
      {factor.evidence_chips.length > 0 && (
        <div className={styles.factorChips}>
          {factor.evidence_chips.map((chip, index) => (
            <span key={`${index}-${chip.slice(0, 8)}`} data-testid="primary-factor-chip" className={styles.factorChip}>
              {chip}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
