import type { HTMLAttributes } from 'react';
import styles from './CeilingBadge.module.css';

export type CeilingGradeLetter = 'A+' | 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C';

/** Single source of truth for the §3.5 ceiling ladder: grade → glow tier.
 *  Brighter grade = higher tier (g5 brightest → g0 dimmest). The badge and the
 *  legend both read this so the reference key can never drift from the render. */
// eslint-disable-next-line react-refresh/only-export-components -- the ladder legend is the §3.5 reference key, co-located with its badge by design
export const CEILING_LADDER: ReadonlyArray<{ grade: CeilingGradeLetter; tier: string; note: string }> = [
  { grade: 'A+', tier: 'g5', note: 'brightest — generational ceiling' },
  { grade: 'A',  tier: 'g4', note: 'strong — elite ceiling' },
  { grade: 'A-', tier: 'g3', note: 'lit outline — high ceiling' },
  { grade: 'B+', tier: 'g2', note: 'faint — solid ceiling' },
  { grade: 'B',  tier: 'g1', note: 'neutral — rotation ceiling' },
  { grade: 'B-', tier: 'g1', note: 'neutral — depth ceiling' },
  { grade: 'C',  tier: 'g0', note: 'dim — limited ceiling' },
];

const TIER_BY_GRADE: Record<CeilingGradeLetter, string> = {
  'A+': 'g5', A: 'g4', 'A-': 'g3', 'B+': 'g2', B: 'g1', 'B-': 'g1', C: 'g0',
};

interface CeilingBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  grade: CeilingGradeLetter;
}

export function CeilingBadge({ grade, className = '', ...rest }: CeilingBadgeProps) {
  const tier = TIER_BY_GRADE[grade] ?? 'g0';
  return (
    <span className={`${styles.badge} ${styles[tier]} ${className}`.trim()} {...rest}>
      {grade}
    </span>
  );
}
