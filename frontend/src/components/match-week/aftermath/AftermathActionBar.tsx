function advanceLabel(result?: string): string {
  if (result === 'Win') return 'BANK THE RESULT →';
  if (result === 'Loss') return 'MOVE ON →';
  return 'SHAKE IT OFF →';
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
    <div className="command-action-bar" data-testid="after-action-bar">
      {hasReplay && (
        <button onClick={onViewReplay} className="command-action-bar-secondary">
          VIEW FULL REPLAY
        </button>
      )}
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        className={`command-action-bar-primary${isAdvancing ? ' is-advancing' : ''}`}
      >
        {isAdvancing ? 'ADVANCING...' : advanceLabel(result)}
      </button>
    </div>
  );
}
