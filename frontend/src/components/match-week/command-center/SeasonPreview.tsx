import type { TermId } from '../../../legibility';
import { TermTip, PLAYER_ARCHETYPE_TERM } from '../../../legibility';
import type { SeasonPreview as SeasonPreviewData } from '../../../types';
import { ActionButton } from '../../../ui/ActionButton';
import styles from './SeasonPreview.module.css';

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
  // with --out, then the playoff cut flag — turns three isolated numbers into a
  // shape the player can internalize (Brief 4.2, criterion #1, #7).
  const weeks = Array.from({ length: preview.regular_season_weeks }, (_, i) => i + 1);
  const byeWeek = preview.bye_week;

  return (
    <section
      data-testid="season-preview"
      aria-labelledby="season-preview-heading"
      className={styles.root}
    >
      <div>
        <div className={styles.kicker}>Season Preview</div>
        <h2 id="season-preview-heading" className={styles.heading}>
          Your season ahead
        </h2>
      </div>

      {/* PT4-01: the climb context — which rung of the pyramid this season is
          played on and what's at stake at both ends of the table. Absent on
          legacy single-league saves. */}
      {preview.division && (
        <div
          data-testid="season-preview-division"
          className={styles.divisionCallout}
        >
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span className={styles.divisionName}>
              {preview.division.short_name} · {preview.division.name}
            </span>
            <span className={styles.divisionStakes}>
              {preview.division.stakes}
            </span>
          </div>
          {preview.division.world_note && (
            <p className={styles.divisionNote}>
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
          className={styles.bulletinCallout}
        >
          <div className={styles.bulletinLabel}>League Bulletin</div>
          <p className={styles.bulletinBody}>
            {preview.officiating_emphasis}
          </p>
        </div>
      )}

      {/* Season-shape strip */}
      <div>
        <div className={styles.timeline} aria-hidden="true">
          {weeks.map((w) => {
            const isBye = byeWeek === w;
            return (
              <div
                key={w}
                className={isBye ? `${styles.tick} ${styles.tickBye}` : styles.tick}
                title={isBye ? `Bye — Week ${w}` : `Week ${w}`}
              />
            );
          })}
          <div className={styles.cutFlag}>CUT</div>
        </div>
        {/* Axis endpoints only — the bye is called out in the caption below,
            not implied by horizontal position (which previously misread). */}
        <div className={`season-preview-axis ${styles.timelineAxis}`}>
          <span>Week 1</span>
          <span>Week {preview.regular_season_weeks}</span>
        </div>
        {/* Amber (--out) only when a bye actually exists; "None scheduled" is a
            calm fact, not a warning. */}
        <p
          className={`season-preview-bye-note ${preview.bye_week ? `${styles.byeNote} ${styles.byeNoteActive}` : styles.byeNote}`}
        >
          {preview.bye_week ? preview.bye_text : `Bye: ${preview.bye_text.toLowerCase()}`}
        </p>
      </div>

      <dl className={styles.statGrid}>
        <div className={`${styles.statTile} ${styles.statTileVolt}`}>
          <dt className={styles.statLabel}>Regular Season</dt>
          <dd className={styles.statValue}>{preview.regular_season_weeks} weeks</dd>
        </div>
        <div className={`${styles.statTile} ${styles.statTileOut}`}>
          <dt className={styles.statLabel}>Your Bye</dt>
          <dd className={styles.statValue}>{preview.bye_text}</dd>
        </div>
        <div className={`${styles.statTile} ${styles.statTileOk}`}>
          <dt className={styles.statLabel}>
            <TermTip term={'standings.playoff_line' as TermId}>Playoff Cut</TermTip>
          </dt>
          <dd className={styles.statValue}>Top {preview.playoff_cut} of {preview.total_clubs}</dd>
        </div>
      </dl>

      {/* Orientation line — the goal reframed as guidance under the facts, not a
          headline that duplicates the cut tile (Brief 4.2, hierarchy). */}
      <p className={styles.goalCallout}>
        {preview.top_goal}
      </p>

      {(preview.strength || preview.weakness) && (
        <div className={styles.insightGrid}>
          {preview.strength && (
            <div className={`${styles.insightCard} ${styles.insightCardOk}`}>
              <div className={styles.insightLabel}>Roster strength</div>
              <div className={styles.insightValue}>
                {archetypeTip(preview.strength.archetype_key, preview.strength.archetype, preview.strength.avg_overall)}
              </div>
              {/* Codex issue 2: say what the label MEANS, not just the
                  number — the preview should teach, not make you translate. */}
              <div className={styles.insightHint}>
                Your highest-rated archetype group — build the lineup and game plan around them.
              </div>
            </div>
          )}
          {preview.weakness && (
            <div className={`${styles.insightCard} ${styles.insightCardOut}`}>
              <div className={styles.insightLabel}>Watch area</div>
              <div className={styles.insightValue}>
                {archetypeTip(preview.weakness.archetype_key, preview.weakness.archetype, preview.weakness.avg_overall)}
              </div>
              <div className={styles.insightHint}>
                Your lowest-rated group — expect opponents to lean on it; target it in development and recruiting.
              </div>
            </div>
          )}
        </div>
      )}

      {/* Primary CTA gets its own full-width row; the skip preference is
          demoted to a quiet line below a divider so it can't be mistaken for
          the continue action (Brief 4.2, criterion #5). */}
      <div className={styles.footer}>
        <ActionButton
          variant="primary"
          onClick={onContinue}
          style={{ width: '100%', padding: '0.8rem 1.4rem', fontSize: '0.85rem', fontWeight: 800 }}
        >
          To the Command Center →
        </ActionButton>
        <label className={styles.skipLabel}>
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
