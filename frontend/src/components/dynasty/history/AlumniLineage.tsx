import { EmptyState } from '../../../legibility/EmptyState';
import { POTENTIAL_TIERS } from '../../../domain/tiers';
import type { PotentialTier } from '../../../domain/tiers';
import styles from './AlumniLineage.module.css';

interface AlumnusEntry {
  id: string;
  name: string;
  seasons_played: number;
  career_elims: number;
  championships: number;
  ovr_final: number;
  potential_tier: string;
}

// Re-pointed to the canonical POTENTIAL_TIERS vocabulary (Elite/High/Mid/Low/Raw)
// from src/domain/tiers.ts. The old map keyed on Elite/High/Limited/Solid/Unknown,
// silently collapsing Mid/Low/Raw into the slate default (#26 de-collision).
const TIER_TONE: Record<PotentialTier, string> = {
  Elite: styles.toneElite,
  High: styles.toneHigh,
  Mid: styles.toneMid,
  Low: styles.toneLow,
  Raw: styles.toneRaw,
};

function tierToneClass(tier: string): string {
  return (POTENTIAL_TIERS as readonly string[]).includes(tier)
    ? TIER_TONE[tier as PotentialTier]
    : styles.toneUnknown;
}

export function AlumniLineage({ alumni }: { alumni: AlumnusEntry[] }) {
  if (alumni.length === 0) {
    return <EmptyState title="No Alumni Yet" body="No departed players have reached the archive yet." />;
  }

  return (
    <div className={styles.list}>
      {alumni.map((entry) => (
        <div key={entry.id} className={styles.row}>
          <div className={styles.main}>
            <strong className={styles.name}>{entry.name}</strong>
            <span className={styles.meta}>
              {entry.seasons_played} season{entry.seasons_played === 1 ? '' : 's'} - {entry.career_elims} career elims
            </span>
          </div>
          <div className={styles.side}>
            <span className={`${styles.tier} ${tierToneClass(entry.potential_tier)}`} data-tier={entry.potential_tier}>
              {entry.potential_tier}
            </span>
            <span className={styles.note}>
              {entry.championships} title{entry.championships === 1 ? '' : 's'} - Final OVR {entry.ovr_final}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
