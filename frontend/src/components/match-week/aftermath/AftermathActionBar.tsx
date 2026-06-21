import styles from './aftermathCards.module.css';

function advanceLabel(result?: string): string {
  if (result === 'Win') return 'BANK THE RESULT →';
  return 'NEXT WEEK →';
}

export function AftermathActionBar({
  onAdvance,
  onViewReplay,
  matchId,
  result,
  isAdvancing = false,
}: {
  onAdvance: () => void;
  onViewReplay?: () => void;
  matchId?: string;
  result?: string;
  isAdvancing?: boolean;
}) {
  const hasReplay = Boolean(matchId && onViewReplay);

  return (
    <div className={`command-action-bar ${styles.actionBar}`} data-testid="after-action-bar">
      {hasReplay && (
        <button onClick={onViewReplay} className={`command-action-bar-secondary ${styles.actionSecondary}`}>
          VIEW FULL REPLAY
        </button>
      )}
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        className={`command-action-bar-primary ${styles.actionPrimary}`}
      >
        {isAdvancing ? 'ADVANCING...' : advanceLabel(result)}
      </button>
    </div>
  );
}
