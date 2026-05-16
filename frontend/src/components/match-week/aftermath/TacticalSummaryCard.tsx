import type { CommandDashboardLane } from '../../../types';

function buildStatLine(lanes: CommandDashboardLane[]): string | null {
  for (const lane of lanes) {
    if (lane.items.length > 0) {
      return lane.items[0];
    }
  }
  if (lanes.length > 0) return `Focus: ${lanes[0].title}`;
  return null;
}

export function TacticalSummaryCard({
  turningPoint,
  evidenceLanes = [],
}: {
  turningPoint: string;
  evidenceLanes?: CommandDashboardLane[];
}) {
  if (!turningPoint) return null;

  const statLine = buildStatLine(evidenceLanes);
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
      <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.55, margin: 0 }}>
        {turningPoint}
      </p>
      {statLine && (
        <p
          style={{
            marginTop: '0.75rem',
            marginBottom: 0,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.65rem',
            color: '#64748b',
            lineHeight: 1.45,
            borderLeft: '2px solid #1e293b',
            paddingLeft: '0.6rem',
          }}
        >
          {statLine}
        </p>
      )}
      {evidenceLabel && (
        <p className="command-tactical-card-footer">
          {evidenceLabel}
        </p>
      )}
    </section>
  );
}
