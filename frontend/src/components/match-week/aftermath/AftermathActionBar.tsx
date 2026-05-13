import { ActionButton } from '../../ui';

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
  return (
    <div className="dm-panel command-action-bar" data-testid="after-action-bar">
      <div>
        <p className="dm-kicker">Next decision</p>
        <p>Review the replay or move the program into next week's plan.</p>
      </div>
      <div className="command-action-buttons">
        {matchId && onViewReplay && (
          <ActionButton variant="secondary" onClick={onViewReplay}>
            Watch Replay
          </ActionButton>
        )}
        <ActionButton variant="primary" onClick={onAdvance} disabled={isAdvancing}>
          {isAdvancing ? 'Advancing...' : 'Advance to Next Week ->'}
        </ActionButton>
      </div>
    </div>
  );
}
