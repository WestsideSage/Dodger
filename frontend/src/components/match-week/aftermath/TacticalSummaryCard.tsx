import type { CommandDashboardLane } from '../../../types';

export function TacticalSummaryCard({
  turningPoint,
  evidenceLanes = [],
}: {
  turningPoint: string;
  evidenceLanes?: CommandDashboardLane[];
}) {
  const fallback = evidenceLanes.find((lane) => lane.summary)?.summary;

  return (
    <section className="dm-panel command-tactical-card" data-testid="tactical-summary">
      <p className="dm-kicker">Tactical Read</p>
      <p>{turningPoint || fallback || 'The staff report is still assembling the tactical read for this match.'}</p>
    </section>
  );
}
