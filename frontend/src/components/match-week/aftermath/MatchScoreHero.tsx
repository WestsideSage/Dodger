import { useEffect, useState } from 'react';

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
        {isOfficial ? `${survivors} survivors (Final)` : `${survivors} survivors`}
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
}) {
  const isOfficial = Boolean(scoringModel && scoringModel !== 'legacy');
  const displayedHome = useCountUp(isOfficial ? (homeGamePoints ?? 0) : homeSurvivors);
  const displayedAway = useCountUp(isOfficial ? (awayGamePoints ?? 0) : awaySurvivors);
  const homeWon = winnerClubId === homeClubId;
  const awayWon = Boolean(winnerClubId) && !homeWon;

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
        <span className="dm-kicker">{isOfficial ? `Final (USAD ${scoringModel?.toUpperCase()})` : 'Final'}</span>
        <span className="command-score-vs">VS</span>
      </div>
      <TeamScore
        name={awayTeam}
        survivors={awaySurvivors}
        displayedSurvivors={displayedAway}
        isWinner={awayWon}
        side="away"
        isOfficial={isOfficial}
      />
    </section>
  );
}
