import type { ReactNode } from 'react';
import styles from './KnownValue.module.css';

export type Knowledge = 'known' | 'estimated' | 'hidden';

export function KnownValue({
  state,
  label,
  value,
  hint,
}: {
  state: Knowledge;
  label: string;
  value?: ReactNode;
  hint?: string;
}) {
  return (
    <span
      role="group"
      aria-label={`${label}: ${state === 'hidden' ? 'unknown, scout to reveal' : state}`}
      className={`${styles.box} ${styles[state]}`}
    >
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{state === 'hidden' ? '🔒' : value ?? '—'}</span>
      {hint && state !== 'known' && <span className={styles.hint}>{hint}</span>}
    </span>
  );
}
