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
    <div
      className="command-action-bar"
      data-testid="after-action-bar"
      style={{ position: 'sticky', bottom: 0, background: '#0a0f1c', zIndex: 10, borderTop: '1px solid #1e293b' }}
    >
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
