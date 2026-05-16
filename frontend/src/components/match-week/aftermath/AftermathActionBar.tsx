export function AftermathActionBar({
  onAdvance,
  onViewReplay,
  matchId,
  isAdvancing = false,
}: {
  onAdvance: () => void;
  onViewReplay?: () => void;
  matchId?: string;
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
        {isAdvancing ? 'ADVANCING...' : 'ADVANCE TO NEXT WEEK →'}
      </button>
    </div>
  );
}
