import type { CommandDashboardLane } from '../../../types';
import styles from './aftermathCards.module.css';

function buildStatLine(lanes: CommandDashboardLane[], exclude: string): string | null {
  const normalized = exclude.trim();
  for (const lane of lanes) {
    for (const item of lane.items) {
      if (item.trim() && item.trim() !== normalized) {
        return item;
      }
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

  const statLine = buildStatLine(evidenceLanes, turningPoint);
  const evidenceLabel = evidenceLanes.length > 0 ? `Based on ${evidenceLanes[0].title}` : null;

  return (
    <section className={styles.tacticalCard} data-testid="tactical-summary">
      <p className={styles.tacticalKicker}>TACTICAL READ</p>
      <p className={styles.tacticalText}>{turningPoint}</p>
      {statLine && <p className={styles.tacticalStat}>{statLine}</p>}
      {evidenceLabel && <p className={styles.tacticalFooter}>{evidenceLabel}</p>}
    </section>
  );
}
