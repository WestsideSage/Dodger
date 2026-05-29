import type { SeasonPreview as SeasonPreviewData } from '../../../types';

/**
 * Week 1 orientation screen. Explains season length, bye-week placement,
 * the playoff cut line, this-season top goal, and one roster strength +
 * weakness from facts the engine already has.
 *
 * Task 12 of the 2026-05-28 multi-season playtest-fixes plan: a new
 * player went weeks without being told the season's shape or goal.
 */
export function SeasonPreview({
  preview,
  onContinue,
  onSkipChange,
}: {
  preview: SeasonPreviewData;
  onContinue: () => void;
  onSkipChange: (skipped: boolean) => void;
}) {
  const stat = (label: string, value: string) => (
    <div
      style={{
        flex: '1 1 0',
        minWidth: '8rem',
        background: '#0b1220',
        border: '1px solid #1e293b',
        borderRadius: '6px',
        padding: '0.75rem 0.85rem',
      }}
    >
      <div
        style={{
          fontSize: '0.6rem',
          fontWeight: 800,
          letterSpacing: '0.08em',
          color: '#64748b',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </div>
      <div style={{ color: '#f1f5f9', fontSize: '1.1rem', fontWeight: 800, marginTop: '0.25rem' }}>{value}</div>
    </div>
  );

  return (
    <section
      data-testid="season-preview"
      style={{
        border: '1px solid #1e293b',
        background: '#08101f',
        borderRadius: '8px',
        padding: '1.25rem',
        margin: '1rem 0',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}
    >
      <div>
        <div
          style={{
            fontSize: '0.65rem',
            fontWeight: 900,
            letterSpacing: '0.1em',
            color: '#38bdf8',
            textTransform: 'uppercase',
          }}
        >
          Season Preview
        </div>
        <div style={{ color: '#f1f5f9', fontSize: '1.25rem', fontWeight: 800, marginTop: '0.3rem' }}>
          {preview.top_goal}
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}>
        {stat('Regular Season', `${preview.regular_season_weeks} weeks`)}
        {stat('Your Bye', preview.bye_text)}
        {stat('Playoff Cut', `Top ${preview.playoff_cut} of ${preview.total_clubs}`)}
      </div>

      {(preview.strength || preview.weakness) && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}>
          {preview.strength && (
            <div
              style={{
                flex: '1 1 0',
                minWidth: '12rem',
                background: '#0b1220',
                border: '1px solid #1e293b',
                borderLeft: '3px solid #22c55e',
                borderRadius: '4px',
                padding: '0.6rem 0.75rem',
              }}
            >
              <div style={{ color: '#94a3b8', fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase' }}>
                Roster strength
              </div>
              <div style={{ color: '#f1f5f9', fontSize: '0.9rem', fontWeight: 700, marginTop: '0.2rem' }}>
                {preview.strength.archetype} — {preview.strength.avg_overall} avg OVR
              </div>
            </div>
          )}
          {preview.weakness && (
            <div
              style={{
                flex: '1 1 0',
                minWidth: '12rem',
                background: '#0b1220',
                border: '1px solid #1e293b',
                borderLeft: '3px solid #f59e0b',
                borderRadius: '4px',
                padding: '0.6rem 0.75rem',
              }}
            >
              <div style={{ color: '#94a3b8', fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase' }}>
                Watch area
              </div>
              <div style={{ color: '#f1f5f9', fontSize: '0.9rem', fontWeight: 700, marginTop: '0.2rem' }}>
                {preview.weakness.archetype} — {preview.weakness.avg_overall} avg OVR
              </div>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8', fontSize: '0.8rem' }}>
          <input
            type="checkbox"
            checked={preview.skipped}
            onChange={(event) => onSkipChange(event.target.checked)}
          />
          Skip this preview in future seasons
        </label>
        <button
          type="button"
          onClick={onContinue}
          style={{
            background: '#38bdf8',
            color: '#04111f',
            border: 'none',
            borderRadius: '6px',
            padding: '0.55rem 1.4rem',
            fontWeight: 800,
            cursor: 'pointer',
          }}
        >
          To the Command Center
        </button>
      </div>
    </section>
  );
}
