import type { TermId } from '../../../legibility';
import { TermTip, PLAYER_ARCHETYPE_TERM } from '../../../legibility';
import type { SeasonPreview as SeasonPreviewData } from '../../../types';

// Resolves a raw PlayerArchetype `archetype_key` (from models.py) to its
// legibility TermId via the shared archetype map (V15 index decision #2 —
// screens consume the shared map, never a local reverse-map). Returns undefined
// for an unmapped key (e.g. a future archetype added before terms.ts is updated).
function archetypeTermId(key: string): TermId | undefined {
  return PLAYER_ARCHETYPE_TERM[key];
}

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
  const stat = (label: string, value: string, accent: string, termId?: TermId) => (
    <div
      style={{
        flex: '1 1 0',
        minWidth: '6.5rem',
        background: '#0b1220',
        border: '1px solid #1e293b',
        borderTop: `2px solid ${accent}`,
        borderRadius: '6px',
        padding: '0.7rem 0.8rem',
      }}
    >
      <dt
        style={{
          fontSize: '0.58rem',
          fontWeight: 800,
          letterSpacing: '0.08em',
          color: '#64748b',
          textTransform: 'uppercase',
        }}
      >
        {termId ? <TermTip term={termId}>{label}</TermTip> : label}
      </dt>
      <dd style={{ color: '#f1f5f9', fontSize: '1.1rem', fontWeight: 800, margin: '0.25rem 0 0' }}>{value}</dd>
    </div>
  );

  // `ovr` is the GROUP average — the mean OVR across every player sharing this
  // archetype (season_preview.py -> next_best_improvement.strongest/weakest_
  // position_group), not a single player's rating. The "group" word makes that
  // unambiguous (matches the "group … avg OVR" phrasing used elsewhere, e.g.
  // manager_lesson). Bug #11.
  const archetypeTip = (key: string, display: string, ovr: number) => {
    const termId = archetypeTermId(key);
    return termId ? (
      <><TermTip term={termId}>{display}</TermTip>{' group · '}{ovr} avg OVR</>
    ) : (
      <>{display} group · {ovr} avg OVR</>
    );
  };

  // Season-shape timeline: ticks for each regular-season week, the bye marked
  // amber, then the playoff cut flag — turns three isolated numbers into a
  // shape the player can internalize (Brief 4.2, criterion #1, #7).
  const weeks = Array.from({ length: preview.regular_season_weeks }, (_, i) => i + 1);
  const byeWeek = preview.bye_week;

  return (
    <section
      data-testid="season-preview"
      aria-labelledby="season-preview-heading"
      style={{
        border: '1px solid #1e293b',
        background: 'linear-gradient(180deg, #0a1426 0%, #08101f 45%)',
        borderRadius: '10px',
        padding: '1.25rem',
        // Centered, capped column — at 1920 the full-bleed version read as a
        // wall-to-wall banner with a 1700px-wide button.
        margin: '1rem auto',
        width: '100%',
        maxWidth: '64rem',
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
            letterSpacing: '0.14em',
            color: '#38bdf8',
            textTransform: 'uppercase',
          }}
        >
          Season Preview
        </div>
        <h2 id="season-preview-heading" style={{ color: '#f8fafc', fontSize: '1.4rem', fontWeight: 900, margin: '0.3rem 0 0' }}>
          Your season ahead
        </h2>
      </div>

      {/* PT4-01: the climb context — which rung of the pyramid this season is
          played on and what's at stake at both ends of the table. Absent on
          legacy single-league saves. */}
      {preview.division && (
        <div
          data-testid="season-preview-division"
          style={{
            padding: '0.6rem 0.75rem',
            borderRadius: '6px',
            background: 'rgba(139,92,246,0.08)',
            borderLeft: '3px solid #8b5cf6',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ color: '#c4b5fd', fontSize: '0.65rem', fontWeight: 900, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
              {preview.division.short_name} · {preview.division.name}
            </span>
            <span style={{ color: '#e2e8f0', fontSize: '0.82rem', fontWeight: 600 }}>
              {preview.division.stakes}
            </span>
          </div>
          {preview.division.world_note && (
            <p style={{ margin: '0.3rem 0 0', color: '#94a3b8', fontSize: '0.72rem', lineHeight: 1.4 }}>
              {preview.division.world_note}
            </p>
          )}
        </div>
      )}

      {/* V28 The Weather: the season's officiating points of emphasis, announced
          preseason. Absent on season 1 / legacy / a called-straight season. */}
      {preview.officiating_emphasis && (
        <div
          data-testid="season-preview-officiating"
          style={{
            padding: '0.6rem 0.75rem',
            borderRadius: '6px',
            background: 'rgba(245,158,11,0.08)',
            borderLeft: '3px solid #f59e0b',
          }}
        >
          <div style={{ color: '#fbbf24', fontSize: '0.65rem', fontWeight: 900, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            League Bulletin
          </div>
          <p style={{ margin: '0.3rem 0 0', color: '#e2e8f0', fontSize: '0.82rem', fontWeight: 600, lineHeight: 1.45 }}>
            {preview.officiating_emphasis}
          </p>
        </div>
      )}

      {/* Season-shape strip */}
      <div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '2.2rem' }} aria-hidden="true">
          {weeks.map((w) => {
            const isBye = byeWeek === w;
            return (
              <div
                key={w}
                style={{
                  flex: '1 1 0',
                  minWidth: 0,
                  height: isBye ? '100%' : '55%',
                  borderRadius: '2px',
                  background: isBye
                    ? '#f59e0b'
                    : 'linear-gradient(180deg, rgba(56,189,248,0.30), rgba(56,189,248,0.10))',
                  border: isBye ? 'none' : '1px solid rgba(56,189,248,0.25)',
                  alignSelf: 'flex-end',
                }}
                title={isBye ? `Bye — Week ${w}` : `Week ${w}`}
              />
            );
          })}
          <div
            style={{
              flex: '0 0 auto',
              marginLeft: '4px',
              alignSelf: 'stretch',
              display: 'flex',
              alignItems: 'center',
              padding: '0 0.5rem',
              borderRadius: '3px',
              background: 'rgba(56,189,248,0.14)',
              border: '1px solid rgba(56,189,248,0.4)',
              color: '#7dd3fc',
              fontSize: '0.6rem',
              fontWeight: 800,
              letterSpacing: '0.04em',
              whiteSpace: 'nowrap',
            }}
          >
            CUT
          </div>
        </div>
        {/* Axis endpoints only — the bye is called out in the caption below,
            not implied by horizontal position (which previously misread). */}
        <div className="season-preview-axis" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.3rem', fontSize: '0.62rem', color: '#64748b' }}>
          <span>Week 1</span>
          <span>Week {preview.regular_season_weeks}</span>
        </div>
        {/* Amber only when a bye actually exists; "None scheduled" is a calm
            fact, not a warning. */}
        <p
          className="season-preview-bye-note"
          style={{
            color: preview.bye_week ? '#f59e0b' : '#64748b',
            fontWeight: preview.bye_week ? 700 : 500,
            margin: '0.35rem 0 0',
            fontSize: '0.62rem',
          }}
        >
          {preview.bye_week ? preview.bye_text : `Bye: ${preview.bye_text.toLowerCase()}`}
        </p>
      </div>

      <dl style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', margin: 0 }}>
        {stat('Regular Season', `${preview.regular_season_weeks} weeks`, '#38bdf8')}
        {stat('Your Bye', preview.bye_text, '#f59e0b')}
        {stat('Playoff Cut', `Top ${preview.playoff_cut} of ${preview.total_clubs}`, '#22c55e', 'standings.playoff_line')}
      </dl>

      {/* Orientation line — the goal reframed as guidance under the facts, not a
          headline that duplicates the cut tile (Brief 4.2, hierarchy). */}
      <p
        style={{
          margin: 0,
          padding: '0.6rem 0.75rem',
          borderRadius: '6px',
          background: 'rgba(34,197,94,0.08)',
          borderLeft: '3px solid #22c55e',
          color: '#d1fae5',
          fontSize: '0.85rem',
          fontWeight: 600,
          lineHeight: 1.45,
        }}
      >
        {preview.top_goal}
      </p>

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
                {archetypeTip(preview.strength.archetype_key, preview.strength.archetype, preview.strength.avg_overall)}
              </div>
              {/* Codex issue 2: say what the label MEANS, not just the
                  number — the preview should teach, not make you translate. */}
              <div style={{ color: '#64748b', fontSize: '0.72rem', marginTop: '0.25rem', lineHeight: 1.4 }}>
                Your highest-rated archetype group — build the lineup and game plan around them.
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
                {archetypeTip(preview.weakness.archetype_key, preview.weakness.archetype, preview.weakness.avg_overall)}
              </div>
              <div style={{ color: '#64748b', fontSize: '0.72rem', marginTop: '0.25rem', lineHeight: 1.4 }}>
                Your lowest-rated group — expect opponents to lean on it; target it in development and recruiting.
              </div>
            </div>
          )}
        </div>
      )}

      {/* Primary CTA gets its own full-width row; the skip preference is
          demoted to a quiet line below a divider so it can't be mistaken for
          the continue action (Brief 4.2, criterion #5). */}
      <div style={{ borderTop: '1px solid #1e293b', paddingTop: '0.9rem', display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
        <button
          type="button"
          onClick={onContinue}
          className="dm-action dm-action-primary"
          style={{ width: '100%', padding: '0.8rem 1.4rem', fontSize: '0.85rem', fontWeight: 800 }}
        >
          To the Command Center →
        </button>
        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.45rem', color: '#64748b', fontSize: '0.74rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={preview.skipped}
            onChange={(event) => onSkipChange(event.target.checked)}
          />
          Skip this preview in future seasons
        </label>
      </div>
    </section>
  );
}
