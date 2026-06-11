import type { Aftermath } from '../../../types';

/**
 * Shown on loss aftermath screens only. Renders up to three concrete
 * next steps (weakest position group, most-depleted starter, coolest
 * critical recruit) the backend ranked from existing engine values.
 *
 * Task 11 of the 2026-05-28 multi-season playtest-fixes plan: a tough
 * loss used to leave the player with no clear next move.
 */
const CATEGORY_ACCENT: Record<string, string> = {
  position_group: '#38bdf8',
  condition: '#f59e0b',
  recruit: '#a78bfa',
};

export function NextBestImprovementPanel({
  panel,
}: {
  panel: NonNullable<Aftermath['improvement_panel']>;
}) {
  if (panel.length === 0) return null;

  return (
    <section
      data-testid="next-best-improvement"
      style={{
        border: '1px solid #1e293b',
        background: '#08101f',
        borderRadius: '6px',
        padding: '1rem',
        margin: '1rem 0',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.65rem',
      }}
    >
      <div
        style={{
          fontSize: '0.65rem',
          fontWeight: 900,
          letterSpacing: '0.08em',
          color: '#94a3b8',
          textTransform: 'uppercase',
        }}
      >
        Next best improvement
        {/* Codex issue 6: this panel is computed at the final whistle and
            does not track later front-office work — say so instead of
            looking unaware of actions taken since. */}
        <span style={{ marginLeft: '0.45rem', fontWeight: 600, letterSpacing: '0.04em', color: '#64748b', textTransform: 'none' }}>
          — postgame read; desk work since then isn't reflected
        </span>
      </div>
      <div style={{ display: 'grid', gap: '0.5rem' }}>
        {panel.map((item) => (
          <div
            key={item.category}
            style={{
              display: 'flex',
              gap: '0.75rem',
              alignItems: 'flex-start',
              padding: '0.6rem 0.7rem',
              background: '#0b1220',
              border: '1px solid #1e293b',
              borderLeft: `3px solid ${CATEGORY_ACCENT[item.category] ?? '#64748b'}`,
              borderRadius: '4px',
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ color: '#f1f5f9', fontSize: '0.85rem', fontWeight: 700 }}>{item.title}</div>
              <div style={{ color: '#94a3b8', fontSize: '0.78rem', lineHeight: 1.45, marginTop: '0.2rem' }}>
                {item.detail}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
