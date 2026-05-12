import type { CommandCenterPlan } from '../../types';
import { ActionButton } from '../ui';

export function WeeklyChecklist({
  plan,
  onAcceptPlan,
  planConfirmed,
}: {
  plan: CommandCenterPlan;
  onAcceptPlan: () => void;
  planConfirmed: boolean;
}) {
  const warnings: string[] = plan?.warnings ?? [];
  const recommendations: Array<{ department: string; text: string }> = plan?.recommendations ?? [];
  const lineupSummary: string | undefined = plan?.lineup?.summary;
  const starterNames: string[] = (plan?.lineup?.players ?? []).slice(0, 6).map(player => player.name);

  return (
    <div className="dm-panel" style={{ flex: 6 }}>
      <div className="dm-panel-header">
        <p className="dm-kicker">Pre-Game</p>
        <h3 className="dm-panel-title">Weekly Checklist</h3>
      </div>

      <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>

        {/* Lineup status */}
        <div>
          <p className="dm-kicker" style={{ marginBottom: '0.375rem' }}>Lineup</p>
          {starterNames.length > 0 ? (
            <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
              {starterNames.join(' · ')}
            </p>
          ) : lineupSummary ? (
            <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0 }}>{lineupSummary}</p>
          ) : null}
        </div>

        {/* Readiness / warnings */}
        <div>
          <p className="dm-kicker" style={{ marginBottom: '0.375rem' }}>Readiness</p>
          {warnings.length === 0 ? (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
              <span style={{ color: '#10b981', flexShrink: 0, fontSize: '0.875rem' }}>✓</span>
              <span style={{ fontSize: '0.8125rem', color: '#10b981' }}>
                Lineup and tactics are aligned. Squad is ready for match day.
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              {warnings.map((w, i) => (
                <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                  <span style={{ color: '#f59e0b', flexShrink: 0, fontSize: '0.875rem' }}>!</span>
                  <span style={{ fontSize: '0.8125rem', color: '#cbd5e1', lineHeight: 1.4 }}>{w}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <p className="dm-kicker" style={{ marginBottom: '0.375rem' }}>Plan Status</p>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
            <span style={{ color: planConfirmed ? '#10b981' : '#f59e0b', flexShrink: 0, fontSize: '0.875rem' }}>
              {planConfirmed ? 'OK' : '!'}
            </span>
            <span style={{ fontSize: '0.8125rem', color: planConfirmed ? '#10b981' : '#cbd5e1', lineHeight: 1.4 }}>
              {planConfirmed
                ? 'Staff plan is confirmed. Risk notes stay visible but do not block match day.'
                : 'Confirm the staff plan to unlock match simulation.'}
            </span>
          </div>
        </div>

        {/* Top staff recommendation */}
        {recommendations.length > 0 && (
          <div style={{ borderTop: '1px solid #1e293b', paddingTop: '0.75rem' }}>
            <p className="dm-kicker" style={{ marginBottom: '0.375rem', fontSize: '0.625rem' }}>
              {recommendations[0].department} Dept.
            </p>
            <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0, lineHeight: 1.4 }}>
              {recommendations[0].text}
            </p>
          </div>
        )}

        <div style={{ borderTop: '1px solid #1e293b', paddingTop: '0.75rem' }}>
          <ActionButton variant={planConfirmed ? 'ghost' : 'accent'} onClick={onAcceptPlan}>
            {planConfirmed ? 'Plan Confirmed' : 'Confirm Plan'}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
