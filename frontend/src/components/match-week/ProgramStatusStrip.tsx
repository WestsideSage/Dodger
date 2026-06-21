import { useApiResource } from '../../hooks/useApiResource';
import type { StandingsResponse } from '../../types';
import styles from './aftermath/aftermathCards.module.css';

export function ProgramStatusStrip() {
  const { data } = useApiResource<StandingsResponse>('/api/standings');

  const userRow = data?.standings.find(r => r.is_user_club);
  const rank = userRow ? data!.standings.findIndex(r => r.is_user_club) + 1 : null;
  const total = data?.standings.length ?? 0;

  // V20 §7.3: officials rank on game points; the survivor diff is noise there.
  const strapDiff = userRow
    ? (data?.is_official_career ? (userRow.game_point_differential ?? 0) : userRow.elimination_differential)
    : 0;

  const pointsToneClass = userRow
    ? userRow.wins > userRow.losses ? styles.pos : userRow.wins < userRow.losses ? styles.neg : styles.neutral
    : styles.neutral;

  return (
    <div className={`command-program-status ${styles.statusStrip}`}>
      <div>
        <p className={styles.kicker}>Your Program</p>
        <h3 className={styles.statusTitle}>Season Status</h3>
      </div>

      <div className={styles.statusMetrics}>
        {userRow ? (
          <>
            {/* Rank + points */}
            <div className={styles.statusGroup}>
              {rank !== null && (
                <div>
                  <span className={styles.kicker}>League Rank</span>
                  <span className={`${styles.statusValue}${rank <= 2 ? ` ${styles.statusValueTop}` : ''}`}>
                    #{rank} <span className={styles.statusValueMuted}>of {total}</span>
                  </span>
                </div>
              )}
              <div>
                <span className={styles.kicker}>Points</span>
                <span className={`${styles.statusValue} ${pointsToneClass}`}>{userRow.points}</span>
                {strapDiff !== 0 && (
                  <span className={`${styles.statusDiff} ${strapDiff > 0 ? styles.pos : styles.neg}`}>
                    {strapDiff > 0 ? '+' : ''}{strapDiff} diff
                  </span>
                )}
              </div>
            </div>

            {/* W-L-D row */}
            <div className={styles.statusWld}>
              {[
                { label: 'Wins', value: userRow.wins, tone: styles.pos },
                { label: 'Losses', value: userRow.losses, tone: styles.neg },
                { label: 'Ties', value: userRow.draws, tone: styles.neutral },
              ].map(({ label, value, tone }) => (
                <div key={label} className={styles.statusStat}>
                  <div className={`${styles.statusStatNum} ${tone}`}>{value}</div>
                  <div className={styles.statusStatLabel}>{label}</div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className={styles.empty}>Loading...</p>
        )}
      </div>
    </div>
  );
}
