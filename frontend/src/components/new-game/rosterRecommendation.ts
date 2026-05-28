/**
 * Recommended composition for the founding-draft roster.
 *
 * Grounding (do not invent these numbers — they come from the engine):
 *
 *   - The match engine plays 6 starters per side (`STARTERS_COUNT = 6`
 *     in `src/dodgeball_sim/lineup.py`).
 *   - The court has 4 archetype-preferred slots (`COURT_SLOT_PREFERENCES`
 *     in `src/dodgeball_sim/lineup.py:19-24`):
 *
 *       slot 0: {DODGER_ANCHOR, CATCHER}
 *       slot 1: {DODGER_ANCHOR, BALL_HAWK}
 *       slot 2: {THROWER,       BALL_HAWK}
 *       slot 3: {THROWER,       CATCHER}
 *
 *     Each of the four "pure" core archetypes covers exactly two slots.
 *     A roster needs at least one of each pure core archetype to fill
 *     every preferred slot without triggering `check_lineup_liabilities`
 *     warnings (`src/dodgeball_sim/lineup.py:49`).
 *   - Display labels come from `_RECRUITMENT_DISPLAY_NAMES` in
 *     `src/dodgeball_sim/recruitment.py:93-102`.
 *
 * Therefore the recommended minimum for a 6-pick founding roster is:
 *
 *       1 Sharpshooter (THROWER)
 *       1 Net Specialist (CATCHER)
 *       1 Ball Hawk
 *       1 Iron Anchor
 *
 * Picks 5-10 are flex: any archetype, including hybrids
 * (Two-Way Threat, Skirmisher, Possession Specialist, Hit-and-Run),
 * which decompose into the pure cores via `_HYBRID_DECOMPOSITION`
 * (`src/dodgeball_sim/lineup.py:26-31`) and can cover any slot their
 * components cover.
 *
 * The recommendation is advisory only. The user can submit any
 * composition between 6 and 10 picks — imbalance produces a warning,
 * not a block.
 */

export interface ProspectLike {
  public_archetype?: string;
  archetype?: string;
}

/** Pure core archetypes — each covers two court slots. */
export const CORE_ARCHETYPES = [
  'Sharpshooter',
  'Net Specialist',
  'Ball Hawk',
  'Iron Anchor',
] as const;

export type CoreArchetype = (typeof CORE_ARCHETYPES)[number];

/** Hybrid archetypes (decompose into two cores). Listed for tally bucket. */
export const HYBRID_ARCHETYPES = [
  'Two-Way Threat',
  'Skirmisher',
  'Possession Specialist',
  'Hit-and-Run',
] as const;

/**
 * Recommended minimum count per pure core archetype for a founding roster.
 * Derived from court slot coverage: each pure core covers two of the four
 * preferred slots, so one of each clears all liability warnings.
 */
export const RECOMMENDED_COMPOSITION: Record<CoreArchetype, number> = {
  Sharpshooter: 1,
  'Net Specialist': 1,
  'Ball Hawk': 1,
  'Iron Anchor': 1,
};

function archetypeOf(p: ProspectLike): string {
  return p.public_archetype ?? p.archetype ?? '';
}

/** Count picks per displayed archetype label. */
export function summarizePicks(picks: ProspectLike[]): Record<string, number> {
  const tally: Record<string, number> = {};
  for (const pick of picks) {
    const key = archetypeOf(pick);
    if (!key) continue;
    tally[key] = (tally[key] ?? 0) + 1;
  }
  return tally;
}

export interface CompositionRow {
  role: CoreArchetype;
  recommended: number;
  actual: number;
  delta: number;
}

/** Diff for rendering: one row per core archetype. */
export function diffComposition(picks: ProspectLike[]): CompositionRow[] {
  const tally = summarizePicks(picks);
  return CORE_ARCHETYPES.map(role => {
    const actual = tally[role] ?? 0;
    const recommended = RECOMMENDED_COMPOSITION[role];
    return { role, recommended, actual, delta: actual - recommended };
  });
}

/**
 * Count picks whose archetype is not one of the pure cores
 * (hybrids + any unrecognized label). Useful for the "Flex" row.
 */
export function countFlex(picks: ProspectLike[]): number {
  const coreSet = new Set<string>(CORE_ARCHETYPES);
  return picks.reduce(
    (n, p) => (coreSet.has(archetypeOf(p)) ? n : n + 1),
    0,
  );
}

/** Returns true if the composition meets every recommended minimum. */
export function isBalanced(picks: ProspectLike[]): boolean {
  return diffComposition(picks).every(row => row.actual >= row.recommended);
}

/**
 * Human-readable warning when composition falls short of recommendation.
 * Returns null when balanced.
 */
export function imbalanceWarning(picks: ProspectLike[]): string | null {
  const missing = diffComposition(picks).filter(row => row.actual < row.recommended);
  if (missing.length === 0) return null;
  const labels = missing.map(row => row.role).join(', ');
  return `Your roster is light on ${labels}. You can proceed anyway — hybrids and bench depth may still cover those slots.`;
}
