import { useEffect, useState } from 'react';
import { formatScoreline, survivorDetail } from '../matchResult';

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
  const accent = side === 'home' ? '#f97316' : '#22d3ee';

  return (
    <div
      className={`command-score-team command-score-team-${side} ${isWinner ? 'command-score-team-winner' : 'command-score-team-loser'}`}
      style={{
        borderColor: isWinner ? `${accent}88` : '#1e293b',
        boxShadow: isWinner ? `0 0 36px ${side === 'home' ? 'rgba(249,115,22,0.28)' : 'rgba(34,211,238,0.24)'}` : undefined,
      }}
    >
      <span className="dm-kicker">{side === 'home' ? 'Home' : 'Away'}</span>
      <strong style={{ color: accent, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100%', display: 'block' }} title={name}>{name}</strong>
      <span
        className="command-score-number"
        style={{
          textShadow: isWinner
            ? side === 'home'
              ? '0 0 16px rgba(249,115,22,0.55)'
              : '0 0 16px rgba(34,211,238,0.45)'
            : 'none',
        }}
      >
        {displayedSurvivors}
      </span>
      <span className="command-score-detail">
        {survivorDetail(survivors, Boolean(isOfficial))}
      </span>
      {isWinner && (
        <span
          className="dm-badge dm-badge-amber command-score-winner-badge"
          style={{
            fontSize: '0.6rem',
            padding: '2px 8px',
            letterSpacing: '1.5px',
            borderWidth: '1px',
            opacity: 0.82,
          }}
        >
          ★ Winner
        </span>
      )}
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
    <div className="command-score-sets" data-testid="aftermath-set-story" aria-label="Game-by-game set results">
      {games.map((game) => {
        const noPoint = game.result_type === 'no_point' || game.result_type === 'tie';
        const homeWon = !noPoint && game.winner_club_id === homeClubId;
        const tone = noPoint ? 'none' : homeWon ? 'home' : 'away';
        const title = noPoint
          ? `Game ${game.game_number}: no point`
          : `Game ${game.game_number}: ${game.home_points}–${game.away_points}`;
        return (
          <span key={game.game_number} className={`command-score-set-chip tone-${tone}`} title={title}>
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
    <section className="dm-panel command-score-hero" data-testid="match-score-hero" aria-label={isOfficial ? "Final game score" : "Final survivor score"}>
      <TeamScore
        name={homeTeam}
        survivors={homeSurvivors}
        displayedSurvivors={displayedHome}
        isWinner={homeWon}
        side="home"
        isOfficial={isOfficial}
      />
      <div className="command-score-center">
        <span className="dm-kicker">{scoreline.centerLabel}</span>
        <span className="command-score-vs">VS</span>
        {isDraw && (
          <span
            className="dm-badge command-score-draw-badge"
            data-testid="score-hero-draw"
            style={{
              fontSize: '0.6rem',
              padding: '2px 10px',
              letterSpacing: '1.5px',
              borderWidth: '1px',
              borderColor: 'rgba(148,163,184,0.5)',
              color: '#cbd5e1',
              background: 'rgba(148,163,184,0.1)',
            }}
          >
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
      {/* The set story reads as a horizontal timeline under the scoreline.
          Inside the 4.5rem center column a playoff-length match (12-15 games)
          stacked its chips into a tall single-file column that ballooned the
          whole hero. */}
      {isOfficial && games && games.length > 0 && (
        <SetStoryStrip games={games} homeClubId={homeClubId} />
      )}
      {/* Full-width footer — the 4.5rem center column can't hold a sentence
          without ballooning the hero's height. */}
      {isDraw && (
        <p
          style={{
            gridColumn: '1 / -1',
            margin: 0,
            padding: '0.45rem 0.9rem',
            background: '#0a1220',
            borderTop: '1px solid rgba(148,163,184,0.18)',
            fontSize: '0.7rem',
            color: '#94a3b8',
            textAlign: 'center',
            lineHeight: 1.45,
          }}
        >
          {isOfficial
            ? 'Level on game points at full time. A drawn match awards one standings point to each club.'
            : 'Level at full time. A drawn match awards one standings point to each club.'}
        </p>
      )}
    </section>
  );
}
