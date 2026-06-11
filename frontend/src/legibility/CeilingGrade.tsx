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
const GRADE_STYLE: Record<CeilingGradeToken, { label: string; color: string; bg: string; hint: string }> = {
  HIGH_CEILING: {
    label: 'High-ceiling arc',
    color: '#fbbf24',
    bg: 'rgba(251, 191, 36, 0.12)',
    hint: 'Scout grade: a rare growth arc — their effective ceiling lands at 90+.',
  },
  SOLID: {
    label: 'Solid arc',
    color: '#22d3ee',
    bg: 'rgba(34, 211, 238, 0.10)',
    hint: 'Scout grade: an above-normal growth arc — their effective ceiling lands at 82+.',
  },
  STANDARD: {
    label: 'Standard arc',
    color: '#94a3b8',
    bg: 'rgba(148, 163, 184, 0.10)',
    hint: 'Scout grade: no boosted growth arc — their natural ceiling is what they have.',
  },
};

export function CeilingGrade({ grade }: { grade: CeilingGradeToken }) {
  const style = GRADE_STYLE[grade];
  if (!style) return null;
  return (
    <span
      title={style.hint}
      aria-label={`${style.label} — ${style.hint}`}
      data-testid="ceiling-grade"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '0.05rem 0.4rem',
        borderRadius: '999px',
        fontSize: '0.58rem',
        fontWeight: 800,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        color: style.color,
        background: style.bg,
        border: `1px solid ${style.color}40`,
        whiteSpace: 'nowrap',
      }}
    >
      {style.label}
    </span>
  );
}
