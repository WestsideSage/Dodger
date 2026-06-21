import styles from './aftermathCards.module.css';
import type { Aftermath } from '../../../types';

/**
 * One-screen send-off shown when the player's playoff run ends, before
 * the regular-season recap. Reads the backend ``elimination`` block
 * directly — opponent, final score, what ended the run, who carried the
 * match, and a one-line returning-core look-ahead. The player must click
 * Continue to proceed into the offseason.
 *
 * Task 9 of the 2026-05-28 multi-season playtest-fixes plan: the defeat
 * used to jump straight to the recap, wasting the emotional moment.
 */
export function EliminationCeremony({
  elimination,
  onContinue,
  isAdvancing,
}: {
  elimination: NonNullable<Aftermath['elimination']>;
  onContinue: () => void;
  isAdvancing?: boolean;
}) {
  const { stage, opponent_name, player_score, opponent_score, cause, contributors, returning } =
    elimination;

  return (
    <section
      data-testid="elimination-ceremony"
      className={styles.ceremony}
    >
      <div className={styles.ceremonyHead}>
        <span className={styles.ceremonyStage}>{stage} · Eliminated</span>
        <h2 className={styles.ceremonyTitle}>Your season ends here.</h2>
      </div>

      <div className={styles.scoreRow}>
        <span className={styles.scoreHome}>{player_score}</span>
        <span className={styles.scoreVs}>vs {opponent_name}</span>
        <span className={styles.scoreAway}>{opponent_score}</span>
      </div>

      <div className={styles.infoBlock}>
        <div className={styles.infoSection}>
          <div className={styles.infoLabel}>What ended your run</div>
          <p className={styles.infoText}>{cause}</p>
        </div>

        {contributors.length > 0 && (
          <div className={styles.infoSection}>
            <div className={styles.infoLabel}>Who carried it</div>
            <ul className={styles.contributorList}>
              {contributors.map((c) => (
                <li key={c.player_name} className={styles.contributorItem}>
                  <span className={styles.contributorName}>{c.player_name}</span>
                  <span className={styles.contributorScore}>{c.score.toFixed(1)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {returning.length > 0 && (
          <div className={styles.infoSection}>
            <div className={styles.infoLabel}>Returns next season</div>
            <p className={styles.returnText}>{returning.join(' · ')}</p>
          </div>
        )}
      </div>

      <button
        type="button"
        className={styles.continueBtn}
        onClick={onContinue}
        disabled={isAdvancing}
        data-testid="elimination-continue"
      >
        {isAdvancing ? 'Advancing…' : 'Continue to offseason ▸'}
      </button>
    </section>
  );
}
