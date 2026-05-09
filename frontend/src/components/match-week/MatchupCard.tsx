import { useState } from 'react';
import { ActionButton } from '../ui';

// Note: Speed toggle state is UI-only for Wave 2. Real wiring lands in Subplan 12.
export function MatchupCard({ plan, onSimulate, disabled }: { plan: any, onSimulate: () => void, disabled: boolean }) {
  const [speed, setSpeed] = useState<'Fast' | 'Normal' | 'Slow'>('Normal');
  const details = plan.matchup_details || {
      opponent_record: "0-0", last_meeting: "None", key_matchup: "TBD", framing_line: "Matchup pending."
  };

  return (
    <div className="dm-panel" style={{ minHeight: '300px' }}>
      <h2>Matchup</h2>
      <p><i>{details.framing_line}</i></p>
      <div style={{ display: 'flex', gap: '2rem' }}>
        <div><b>Opponent Record:</b> {details.opponent_record}</div>
        <div><b>Last Meeting:</b> {details.last_meeting}</div>
        <div><b>Key Matchup:</b> {details.key_matchup}</div>
      </div>
      <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <ActionButton variant="accent" disabled={disabled} onClick={onSimulate}>Simulate Match</ActionButton>
        <select value={speed} onChange={e => setSpeed(e.target.value as any)}>
          <option value="Fast">Fast</option>
          <option value="Normal">Normal</option>
          <option value="Slow">Slow</option>
        </select>
      </div>
    </div>
  );
}