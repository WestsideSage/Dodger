import type { CommandDashboardLane } from '../../../types';

export function TacticalSummaryCard({
  turningPoint,
  evidenceLanes = [],
}: {
  turningPoint: string;
  evidenceLanes?: CommandDashboardLane[];
}) {
  const fallback = evidenceLanes.find((lane) => lane.summary)?.summary;
  const body = turningPoint || fallback || 'The staff report is still assembling the tactical read for this match.';

  return (
    <section
      className="dm-panel command-tactical-card"
      data-testid="tactical-summary"
      style={{
        borderLeft: '3px solid rgba(249,115,22,0.5)',
        background: 'rgba(249,115,22,0.04)',
      }}
    >
      <p
        className="dm-kicker"
        style={{ color: '#f97316', letterSpacing: '2px', marginBottom: '6px' }}
      >
        TACTICAL READ
      </p>
      <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5, margin: 0 }}>
        {body}
      </p>
    </section>
  );
}
