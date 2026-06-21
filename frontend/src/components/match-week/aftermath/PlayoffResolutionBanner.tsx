import type { Aftermath } from '../../../types';
import styles from './PlayoffResolutionBanner.module.css';

/**
 * Renders an explicit "you advanced / you were eliminated" banner at
 * the top of the aftermath flow when a playoff match needed a
 * tiebreaker. Reads `decided_by` directly — never derives from score.
 *
 * Task 1 of the 2026-05-27 rookie-run playtest-fixes plan. The single
 * most-cited trust break in the playtest was a tied 0-0 semifinal that
 * silently advanced by seed and jumped straight to offseason. This
 * component is the user-facing half of the fix.
 */
export function PlayoffResolutionBanner({
  resolution,
}: {
  resolution: NonNullable<Aftermath['playoff_resolution']>;
}) {
  if (resolution.decided_by === 'regulation') return null;

  const chip = resolution.decided_by === 'overtime' ? 'OVERTIME' : 'TIEBREAKER';
  const isAdvanced = resolution.player_outcome === 'advanced';
  const isEliminated = resolution.player_outcome === 'eliminated';

  let title: string;
  if (resolution.decided_by === 'seed_tiebreaker') {
    if (isAdvanced) {
      title = 'Advanced — won on the seed tiebreaker';
    } else if (isEliminated) {
      title = 'Eliminated — lost on the seed tiebreaker';
    } else {
      title = 'Decided on the seed tiebreaker';
    }
  } else if (isAdvanced) {
    title = `Advanced — won in ${decidedByLabel(resolution.decided_by)}`;
  } else if (isEliminated) {
    title = `Eliminated — lost in ${decidedByLabel(resolution.decided_by)}`;
  } else {
    // AI-only match: still surface the resolution without addressing the player.
    title = `Decided in ${decidedByLabel(resolution.decided_by)}`;
  }

  const outcomeClass = isAdvanced ? styles.advanced : isEliminated ? styles.eliminated : styles.neutral;

  return (
    <section
      data-testid="playoff-resolution-banner"
      data-decided-by={resolution.decided_by}
      data-player-outcome={resolution.player_outcome ?? 'neutral'}
      className={`${styles.banner} ${outcomeClass}`}
    >
      <div className={styles.head}>
        <span className={styles.chip}>{chip}</span>
        <span className={styles.stage}>{resolution.stage}</span>
      </div>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.note}>{resolution.narrative_note}</p>
    </section>
  );
}

function decidedByLabel(decidedBy: 'overtime' | 'seed_tiebreaker' | 'regulation'): string {
  if (decidedBy === 'overtime') return 'overtime';
  if (decidedBy === 'seed_tiebreaker') return 'the seed tiebreaker';
  return 'regulation';
}
