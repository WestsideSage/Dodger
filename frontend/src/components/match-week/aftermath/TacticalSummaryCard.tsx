import type { CommandDashboardLane } from '../../../types';

export function TacticalSummaryCard({
  turningPoint,
  evidenceLanes = [],
}: {
  turningPoint: string;
  evidenceLanes?: CommandDashboardLane[];
}) {
  if (!turningPoint) return null;

  const evidenceLabel = evidenceLanes.length > 0
    ? `Based on ${evidenceLanes[0].title}`
    : null;

  return (
    <section
      className="dm-panel command-tactical-card"
      data-testid="tactical-summary"
    >
      <p className="dm-kicker" style={{ letterSpacing: '2px', marginBottom: '6px' }}>
        TACTICAL READ
      </p>
      <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5, margin: 0 }}>
        {turningPoint}
      </p>
      {evidenceLabel && (
        <p className="command-tactical-card-footer">
          {evidenceLabel}
        </p>
      )}
    </section>
  );
}
