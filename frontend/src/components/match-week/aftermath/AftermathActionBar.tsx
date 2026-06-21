import styles from './aftermathCards.module.css';
import chrome from '../../chrome.module.css';

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
    <div className={`${chrome.actionBar} ${styles.actionBar}`} data-testid="after-action-bar">
      {hasReplay && (
        <button onClick={onViewReplay} className={`${chrome.actionBarSecondary} ${styles.actionSecondary}`}>
          VIEW FULL REPLAY
        </button>
      )}
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        data-testid="aftermath-advance"
        className={`${chrome.actionBarPrimary} ${styles.actionPrimary}`}
      >
        {isAdvancing ? 'ADVANCING...' : advanceLabel(result)}
      </button>
    </div>
  );
}
