import styles from './CeilingGrade.module.css';

export type CeilingGradeToken = 'HIGH_CEILING' | 'SOLID' | 'STANDARD';

// Playtest 3 elite reveal (owner-approved): the Scout action grades a
// prospect's growth arc using the same trajectory the development engine
// consumes. The grade is deliberately coarse — it never leaks the exact
// trajectory tier or a number:
//   HIGH_CEILING -> STAR/GENERATIONAL arc (effective ceiling lands 90+)
//   SOLID        -> IMPACT arc (effective ceiling lands 82+)
//   STANDARD     -> no boosted arc; their natural ceiling is all there is
// Vocabulary stays clear of the roster potential tiers (Elite/High/Mid/...)
// and the pipeline metals — three different axes, three different words.
const GRADE_COPY: Record<CeilingGradeToken, { label: string; cls: string; hint: string }> = {
  HIGH_CEILING: {
    label: 'High-ceiling arc',
    cls: styles.high,
    hint: 'Scout grade: a rare growth arc — their effective ceiling lands at 90+.',
  },
  SOLID: {
    label: 'Solid arc',
    cls: styles.solid,
    hint: 'Scout grade: an above-normal growth arc — their effective ceiling lands at 82+.',
  },
  STANDARD: {
    label: 'Standard arc',
    cls: styles.standard,
    hint: 'Scout grade: no boosted growth arc — their natural ceiling is what they have.',
  },
};

export function CeilingGrade({ grade }: { grade: CeilingGradeToken }) {
  const copy = GRADE_COPY[grade];
  if (!copy) return null;
  return (
    <span
      title={copy.hint}
      aria-label={`${copy.label} — ${copy.hint}`}
      data-testid="ceiling-grade"
      className={`${styles.pill} ${copy.cls}`}
    >
      {copy.label}
    </span>
  );
}
