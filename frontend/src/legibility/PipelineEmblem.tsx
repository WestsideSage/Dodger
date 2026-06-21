import styles from './PipelineEmblem.module.css';

export type PipelineTier = 1 | 2 | 3 | 4 | 5;

// Playtest 3 F-3: tier 5 was named "Elite", colliding with the POTENTIAL tier
// "Elite" (a talent ceiling ≥90). Pipeline tiers measure recruiting warmth,
// not talent — a tier-5 prospect can scout 24–54 OVR — so the ladder stays in
// metal/league vocabulary: Bronze → Silver → Gold → Premier → Platinum.
const TIER_NAME: Record<PipelineTier, string> = {
  5: 'Platinum',
  4: 'Premier',
  3: 'Gold',
  2: 'Silver',
  1: 'Bronze',
};

export function PipelineEmblem({ tier, size = 'md' }: { tier: PipelineTier; size?: 'sm' | 'md' }) {
  const name = TIER_NAME[tier];
  return (
    <span
      role="img"
      aria-label={`Pipeline Tier ${tier} (${name})`}
      title={`Pipeline Tier ${tier} — ${name}`}
      className={`${styles.emblem} ${styles[size]} ${styles[`t${tier}`]}`}
    >
      {tier}
    </span>
  );
}
