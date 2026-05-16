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
          WATCH REPLAY
        </button>
      )}
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        style={{
          flex: 1,
          background: isAdvancing ? '#7c3d12' : '#f97316',
          border: 'none',
          borderRadius: '8px',
          color: '#fff',
          padding: '10px 16px',
          fontFamily: 'Oswald, sans-serif',
          fontSize: '0.85rem',
          letterSpacing: '2px',
          cursor: isAdvancing ? 'default' : 'pointer',
        }}
        onFocus={(e) => {
          e.currentTarget.style.outline = '2px solid #f97316';
          e.currentTarget.style.outlineOffset = '2px';
        }}
        onBlur={(e) => {
          e.currentTarget.style.outline = 'none';
          e.currentTarget.style.outlineOffset = '0';
        }}
      >
        {isAdvancing ? 'ADVANCING...' : 'ADVANCE TO NEXT WEEK →'}
      </button>
    </div>
  );
}
