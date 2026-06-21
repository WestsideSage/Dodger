import type { TopPerformer } from '../../../types';
import styles from './aftermathCards.module.css';

function StatChips({ player }: { player: TopPerformer }) {
  return (
    <div className={styles.statChips}>
      {player.eliminations_by_throw > 0 && (
        <span title="Eliminations by throw" className={styles.statChip}>
          {player.eliminations_by_throw}K
        </span>
      )}
      {player.catches_made > 0 && (
        <span title="Catches made" className={styles.statChip}>
          {player.catches_made}C
        </span>
      )}
      {player.dodges_successful > 0 && (
        <span title="Successful dodges" className={styles.statChip}>
          {player.dodges_successful}D
        </span>
      )}
      <span title="Impact — match-stat score, weighted up for players on the winning side" className={styles.statImpact}>
        Imp {Math.round(player.score)}
      </span>
    </div>
  );
}

export function KeyPlayersPanel({
  performers,
  playerClubName,
}: {
  performers: TopPerformer[];
  playerClubName?: string;
}) {
  const top3 = performers.slice(0, 3);
  const top3HasYours = playerClubName ? top3.some(p => p.club_name === playerClubName) : false;

  // Best user-club performer not already in top 3
  const yourStandout = !top3HasYours && playerClubName ? performers.find(p => p.club_name === playerClubName) : null;

  if (performers.length === 0) {
    return (
      <section className={styles.card} data-testid="key-players-panel">
        <div className={styles.keyHeader}>
          <p className={styles.kicker}>Key Performers</p>
        </div>
        <p className={styles.empty}>No standout performances recorded.</p>
      </section>
    );
  }

  return (
    <section className={styles.card} data-testid="key-players-panel">
      <div className={styles.keyHeader}>
        <p className={styles.kicker}>Key Performers</p>
        {/* First-hour legend: K/C/D/Imp are never expanded anywhere else, and
            tooltips alone are not discoverable. One quiet line decodes them. */}
        <p className={styles.keyLegend}>K eliminations · C catches · D dodges · Imp impact</p>
      </div>
      <div className={styles.keyList}>
        {top3.map((player, index) => {
          const isYours = Boolean(playerClubName && player.club_name === playerClubName);
          return (
            <article key={player.player_id} className={styles.keyPlayer}>
              <span
                className={`${styles.rankBadge}${isYours ? ` ${styles.rankBadgeYours}` : ''}`}
                aria-label={`Rank ${index + 1}`}
              >
                {index + 1}
              </span>
              <div>
                <strong className={styles.playerName}>{player.player_name}</strong>
                {isYours ? (
                  <span className={styles.yourBadge}>Your Club</span>
                ) : player.club_name ? (
                  <span className={styles.clubName}>{player.club_name}</span>
                ) : null}
                <StatChips player={player} />
              </div>
            </article>
          );
        })}
      </div>

      {yourStandout && (
        <div data-testid="your-standout" className={styles.yourStandout}>
          <p className={styles.kicker}>Your Club&apos;s Best</p>
          <article className={styles.keyPlayer}>
            <span className={`${styles.rankBadge} ${styles.rankBadgeYours}`} aria-label="Your standout">
              ★
            </span>
            <div>
              <strong className={styles.playerName}>{yourStandout.player_name}</strong>
              <span className={styles.yourBadge}>Your Club</span>
              <StatChips player={yourStandout} />
            </div>
          </article>
        </div>
      )}
    </section>
  );
}
