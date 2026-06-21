import { useEffect, useState } from 'react';
import { formatScoreline, survivorDetail } from '../matchResult';
import { Truncate } from '../../../ui';
import styles from './MatchScoreHero.module.css';

function useCountUp(value: number, durationMs = 1500) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let frame = 0;
    let startTime: number | null = null;

    const tick = (now: number) => {
      if (startTime === null) startTime = now;
      const progress = Math.min(1, (now - startTime) / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(value * eased));
      if (progress < 1) frame = window.requestAnimationFrame(tick);
    };

    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [durationMs, value]);

  return displayValue;
}

function TeamScore({
  name,
  survivors,
  displayedSurvivors,
  isWinner,
  side,
  isOfficial,
}: {
  name: string;
  survivors: number;
  displayedSurvivors: number;
  isWinner: boolean;
  side: 'home' | 'away';
  isOfficial?: boolean;
}) {
  return (
    <div className={`${styles.team}${isWinner ? ` ${styles.teamWinner}` : ''}`}>
      <span className={styles.kicker}>{side === 'home' ? 'Home' : 'Away'}</span>
      <Truncate className={`${styles.name}${isWinner ? ` ${styles.nameWinner}` : ''}`} title={name}>
        {name}
      </Truncate>
      <span className={`${styles.number}${isWinner ? ` ${styles.numberWinner}` : ''}`}>{displayedSurvivors}</span>
      <span className={styles.detail}>{survivorDetail(survivors, Boolean(isOfficial))}</span>
      {isWinner && <span className={styles.winnerBadge}>★ Winner</span>}
    </div>
  );
}

interface MatchCardGame {
  game_number: number;
  winner_club_id: string | null;
  home_points: number;
  away_points: number;
  result_type: string;
}

// Set-by-set chips under the hero: HOW the game points accumulated, straight
// from the persisted per-game official score. A 9-2 rout and a seesaw 9-2
// read identically without this.
function SetStoryStrip({ games, homeClubId }: { games: MatchCardGame[]; homeClubId: string }) {
  if (games.length === 0) return null;
  return (
    <div className={styles.sets} data-testid="aftermath-set-story" aria-label="Game-by-game set results">
      {games.map((game) => {
        const noPoint = game.result_type === 'no_point' || game.result_type === 'tie';
        const homeWon = !noPoint && game.winner_club_id === homeClubId;
        const toneClass = noPoint ? '' : homeWon ? styles.setChipHome : styles.setChipAway;
        const title = noPoint
          ? `Game ${game.game_number}: no point`
          : `Game ${game.game_number}: ${game.home_points}–${game.away_points}`;
        return (
          <span key={game.game_number} className={`${styles.setChip}${toneClass ? ` ${toneClass}` : ''}`} title={title}>
            <span className="g">G{game.game_number}</span>
            <span className="r">{noPoint ? '—' : homeWon ? '◂' : '▸'}</span>
          </span>
        );
      })}
    </div>
  );
}

export function MatchScoreHero({
  homeTeam,
  awayTeam,
  homeSurvivors,
  awaySurvivors,
  winnerClubId,
  homeClubId,
  scoringModel,
  homeGamePoints,
  awayGamePoints,
  games,
  isPlayoff = false,
}: {
  homeTeam: string;
  awayTeam: string;
  homeSurvivors: number;
  awaySurvivors: number;
  winnerClubId: string | null;
  homeClubId: string;
  scoringModel?: string;
  homeGamePoints?: number;
  awayGamePoints?: number;
  games?: MatchCardGame[];
  // Playoff context: a drawn playoff match does NOT award standings points —
  // it is settled by the resolution banner above (overtime/seed tiebreak).
  isPlayoff?: boolean;
}) {
  const scoreline = formatScoreline({
    scoring_model: scoringModel,
    home_game_points: homeGamePoints,
    away_game_points: awayGamePoints,
    home_survivors: homeSurvivors,
    away_survivors: awaySurvivors,
  });
  const isOfficial = scoreline.isOfficial;
  const displayedHome = useCountUp(scoreline.home.value);
  const displayedAway = useCountUp(scoreline.away.value);
  const homeWon = winnerClubId === homeClubId;
  const awayWon = Boolean(winnerClubId) && !homeWon;
  // Draws are a real, intended outcome (official matches can end level on
  // game points at full time), but with no winner badge the hero used to say
  // nothing at all — the result read as missing rather than drawn.
  const isDraw = !winnerClubId;

  return (
    <section
      className={styles.hero}
      data-testid="match-score-hero"
      aria-label={isOfficial ? 'Final game score' : 'Final survivor score'}
    >
      <TeamScore
        name={homeTeam}
        survivors={homeSurvivors}
        displayedSurvivors={displayedHome}
        isWinner={homeWon}
        side="home"
        isOfficial={isOfficial}
      />
      <div className={styles.center}>
        <span className={styles.kicker}>{scoreline.centerLabel}</span>
        <span className={styles.vs}>VS</span>
        {isDraw && (
          <span className={styles.drawBadge} data-testid="score-hero-draw">
            ◆ Draw
          </span>
        )}
      </div>
      <TeamScore
        name={awayTeam}
        survivors={awaySurvivors}
        displayedSurvivors={displayedAway}
        isWinner={awayWon}
        side="away"
        isOfficial={isOfficial}
      />
      {/* The set story reads as a horizontal timeline under the scoreline. */}
      {isOfficial && games && games.length > 0 && <SetStoryStrip games={games} homeClubId={homeClubId} />}
      {/* Full-width footer — the center column can't hold a sentence. */}
      {isDraw && (
        <p className={styles.drawFooter}>
          {/* In the playoffs a tie cannot stand: the resolution banner above
              names who advances and why, so this footer must not promise
              standings points that do not exist there. */}
          {isPlayoff
            ? "Neither side blinked — level on game points when the clock ran out. A playoff tie can't stand: the resolution call above says who advances."
            : isOfficial
              ? 'Neither side blinked — level on game points when the clock ran out. Both clubs walk away with a standings point.'
              : 'Neither side blinked — dead level at full time. Both clubs walk away with a standings point.'}
        </p>
      )}
    </section>
  );
}
