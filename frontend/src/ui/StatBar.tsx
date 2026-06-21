import type { CSSProperties, HTMLAttributes } from 'react';
import styles from './StatBar.module.css';

interface StatBarProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: number;
  max?: number;
}

function tierOf(v: number): 'elite' | 'good' | 'avg' | 'poor' {
  if (v >= 85) return 'elite';
  if (v >= 70) return 'good';
  if (v >= 55) return 'avg';
  return 'poor';
}

export function StatBar({ label, value, max = 100, className = '', ...rest }: StatBarProps) {
  const pct = Math.max(0, Math.min(1, value / max)) * 100;
  const tier = tierOf(value);
  const vars = { '--fill': `${pct}%` } as CSSProperties;
  return (
    <div className={`${styles.row} ${styles[tier]} ${className}`.trim()} {...rest}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{Math.round(value)}</span>
      <div className={styles.track}>
        <div className={styles.fill} data-statbar-fill style={vars} />
      </div>
    </div>
  );
}
