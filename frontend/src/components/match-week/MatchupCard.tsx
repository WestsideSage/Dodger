import { useState } from 'react';
import type { CommandCenterPlan } from '../../types';
import { ActionButton } from '../ui';

export function MatchupCard({
  plan,
  onSimulate,
  disabled,
  disabledReason,
}: {
  plan: CommandCenterPlan;
  onSimulate: () => void;
  disabled: boolean;
  disabledReason?: string;
}) {
  const [speed, setSpeed] = useState<'Fast' | 'Normal' | 'Slow'>('Normal');
  const details = plan.matchup_details ?? {
    opponent_record: 'No record', last_meeting: 'None', key_matchup: 'Opponent file unavailable.', framing_line: 'Matchup report unavailable.',
  };

  return (
    <div className="dm-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">This Week</p>
        <h2 className="dm-panel-title">Matchup</h2>
      </div>

      <div style={{ padding: '1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <p style={{ fontStyle: 'italic', color: '#94a3b8', margin: 0, fontSize: '0.9375rem', lineHeight: 1.5 }}>
          {details.framing_line}
        </p>

        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          <div>
            <p className="dm-kicker" style={{ marginBottom: '0.25rem', fontSize: '0.625rem' }}>Opponent Record</p>
            <span className="dm-data" style={{ color: '#e2e8f0', fontWeight: 700 }}>{details.opponent_record}</span>
          </div>
          <div>
            <p className="dm-kicker" style={{ marginBottom: '0.25rem', fontSize: '0.625rem' }}>Last Meeting</p>
            <span style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>{details.last_meeting}</span>
          </div>
          <div>
            <p className="dm-kicker" style={{ marginBottom: '0.25rem', fontSize: '0.625rem' }}>Key Matchup</p>
            <span style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>{details.key_matchup}</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', paddingTop: '0.25rem' }}>
          <ActionButton variant="primary" disabled={disabled} onClick={onSimulate} data-testid="simulate-command-week">
            Simulate Match
          </ActionButton>
          <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span className="dm-kicker" style={{ fontSize: '0.625rem' }}>Speed</span>
            <select
              value={speed}
              onChange={e => setSpeed(e.target.value as 'Fast' | 'Normal' | 'Slow')}
              style={{
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '0.375rem 0.5rem',
                color: '#e2e8f0',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-display)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                cursor: 'pointer',
              }}
            >
              <option>Fast</option>
              <option>Normal</option>
              <option>Slow</option>
            </select>
          </label>
          {disabled && (
            <span style={{ fontSize: '0.75rem', color: '#f59e0b' }}>{disabledReason ?? 'Confirm the plan before simulating.'}</span>
          )}
        </div>
      </div>
    </div>
  );
}
