import styles from './aftermathCards.module.css';
import type { Aftermath } from '../../../types';

/**
 * Celebration hero shown at the very top of the aftermath screen when
 * the player wins the title-clinching final. Reads the backend
 * ``championship`` block directly.
 *
 * Task 10 of the 2026-05-28 multi-season playtest-fixes plan: the title
 * win used to be undersold by the standard debrief, with the real
 * celebration buried behind an extra Continue into the offseason. This
 * makes the trophy moment the first thing the player sees.
 */
export function ChampionshipHero({
  championship,
}: {
  championship: NonNullable<Aftermath['championship']>;
}) {
  const { champion_name, opponent_name, player_score, opponent_score, decided_by } = championship;
  const how =
    decided_by === 'overtime'
      ? ' in overtime'
      : decided_by === 'seed_tiebreaker'
        ? ' on the tiebreaker'
        : '';

  return (
    <section
      data-testid="championship-hero"
      className={styles.heroSection}
    >
      <span className={styles.heroKicker}>Champions</span>
      <h2 className={styles.heroTitle}>{champion_name}</h2>
      <p className={styles.heroSubtitle}>
        {player_score}–{opponent_score} over {opponent_name}
        {how} to take the title.
      </p>
    </section>
  );
}
