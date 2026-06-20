// Single source of truth for potential-tier vocabulary + ordering.
// Replaces the divergent Elite/High/Solid/Limited sort map in Roster.tsx.
export const POTENTIAL_TIERS = ['Elite', 'High', 'Mid', 'Low', 'Raw'] as const;
export type PotentialTier = (typeof POTENTIAL_TIERS)[number];

const RANK: Record<PotentialTier, number> = { Elite: 0, High: 1, Mid: 2, Low: 3, Raw: 4 };

/** Lower = better. Unknown tiers sort after all known ones, deterministically. */
export function potentialRank(tier: PotentialTier | string): number {
  return tier in RANK ? RANK[tier as PotentialTier] : POTENTIAL_TIERS.length;
}
