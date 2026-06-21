// Single source for the #63 "name-only prospects excluded from At-Risk and
// sunk to the bottom of every sort" predicate. Mirrors the inline logic that
// previously lived in DynastyOffice.tsx (At-Risk count + sort comparators).
type ProspectLike = { fully_visible?: boolean; fit_score?: number };

/** A prospect is At-Risk only if he is fully visible AND his fit is below 65. */
export function isAtRisk(p: ProspectLike): boolean {
  return p.fully_visible !== false && (p.fit_score ?? 0) < 65;
}

/** 0 for visible prospects, 1 for beyond-network (locked) — locked sinks last. */
export function lockedSinkKey(p: ProspectLike): number {
  return p.fully_visible === false ? 1 : 0;
}
