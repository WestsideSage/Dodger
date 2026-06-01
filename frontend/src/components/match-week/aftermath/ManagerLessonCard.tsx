import type { Aftermath } from '../../../types';

/**
 * WT-32: the "Manager Lesson" — an ADJACENT card to the Primary Factor, shown
 * ONLY when the backend surfaces `manager_lesson` (i.e. the Primary Factor was
 * inconclusive on a close loss). The Primary Factor answers "what decided the
 * match?"; this answers the player's other question, "what could *I* have
 * changed?", strictly from controllable prep.
 *
 * Two honest states, visually distinct so the player is never misled:
 *   - `controllable: true`  -> a real lever (amber, actionable, with chips);
 *   - `controllable: false` -> the honest "nothing you controlled would have
 *     changed this" message (muted slate, no chips, no false call-to-action).
 *
 * It is a sibling of PrimaryFactorCard, NOT a replacement: rendered separately
 * by MatchWeek so the event-derived Primary Factor stands on its own.
 */
export function ManagerLessonCard({
  lesson,
}: {
  lesson: NonNullable<Aftermath['manager_lesson']>;
}) {
  const controllable = lesson.controllable;
  const accent = controllable ? '#f59e0b' : '#64748b';
  const badgeLabel = controllable ? 'CONTROLLABLE' : 'NOT ON YOU';
  const badgeBg = controllable ? 'rgba(245,158,11,0.1)' : 'rgba(148,163,184,0.1)';
  const badgeBorder = controllable ? 'rgba(245,158,11,0.3)' : 'rgba(148,163,184,0.3)';

  return (
    <div
      data-testid="manager-lesson"
      data-lesson-code={lesson.code}
      data-controllable={controllable ? 'true' : 'false'}
      style={{
        margin: '8px 0 0',
        padding: '0.7rem 0.85rem',
        background: '#08101f',
        border: '1px solid #1e293b',
        borderLeft: `3px solid ${accent}`,
        borderRadius: '4px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
        <span className="dm-kicker" style={{ fontSize: '0.625rem', color: '#64748b' }}>Manager Lesson</span>
        <span
          data-testid="manager-lesson-badge"
          style={{
            fontSize: '0.5625rem',
            fontFamily: 'var(--font-mono-data)',
            fontWeight: 900,
            letterSpacing: '0.05em',
            color: accent,
            background: badgeBg,
            border: `1px solid ${badgeBorder}`,
            padding: '0.1rem 0.35rem',
            borderRadius: '3px',
          }}
        >
          {badgeLabel}
        </span>
      </div>
      <p style={{ margin: '0 0 0.5rem', fontFamily: 'Oswald, sans-serif', fontSize: '0.95rem', color: '#e2e8f0', letterSpacing: '0.3px' }}>
        {lesson.title}
      </p>
      <p style={{ margin: 0, color: '#cbd5e1', fontSize: '0.82rem', lineHeight: 1.5 }}>
        {lesson.sentence}
      </p>
      {lesson.evidence_chips.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.55rem' }}>
          {lesson.evidence_chips.map((chip, index) => (
            <span
              key={`${index}-${chip.slice(0, 8)}`}
              data-testid="manager-lesson-chip"
              style={{
                fontSize: '0.6875rem',
                fontFamily: 'var(--font-mono-data)',
                color: '#cbd5e1',
                background: '#0f172a',
                border: '1px solid #1e293b',
                padding: '0.15rem 0.45rem',
                borderRadius: '3px',
              }}
            >
              {chip}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
