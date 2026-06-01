// Canonical player-facing ruleset / scoring-model display names — the single
// source of truth, mirroring the backend `archetype_display_name` pattern.
//
// No surface may invent its own label: implementation-register keys like
// `USAD FOAM` / `OFFICIAL_FOAM` must never reach the player (WT-5). Two forms:
//   - `full`  for selectors and headers  ("USA Dodgeball 2026.1 — Foam")
//   - `short` for compact chips / scoreboards ("Foam Division")
//
// Accepts the match `scoring_model` values ("foam" / "cloth" / "no_sting" /
// "legacy"), the career `ruleset_selection` keys ("official_foam" /
// "official_no_sting" / "official_cloth" / "generic"), AND the engine ruleset
// PROFILE names ("foam-open" / "cloth-open" / "no-sting-open" and their
// "-mixed" / "-women" variants surfaced in the official replay panel),
// normalising them all onto one canonical name. WT-5, WT-18 (selector copy),
// the scoreline, the replay scoreboard, and the official-rules panel consume
// this.

export type RulesetNameForm = 'full' | 'short';

interface RulesetName {
  full: string;
  short: string;
}

const RULESET_NAMES: Record<string, RulesetName> = {
  foam: { full: 'USA Dodgeball 2026.1 — Foam', short: 'Foam Division' },
  cloth: { full: 'USA Dodgeball 2026.1 — Cloth', short: 'Cloth Division' },
  no_sting: { full: 'USA Dodgeball 2026.1 — No-Sting', short: 'No-Sting Division' },
  legacy: { full: 'Legacy survivor scoring', short: 'Legacy' },
};

// Career `ruleset_selection` keys (and null/generic) normalise onto the
// scoring-model names above.
const KEY_ALIASES: Record<string, string> = {
  official_foam: 'foam',
  official_cloth: 'cloth',
  official_no_sting: 'no_sting',
  generic: 'legacy',
  '': 'legacy',
};

export function rulesetDisplayName(
  key: string | null | undefined,
  form: RulesetNameForm = 'full',
): string {
  const raw = (key ?? '').toLowerCase();
  const canonical = KEY_ALIASES[raw] ?? raw;
  const entry = RULESET_NAMES[canonical];
  if (entry) {
    return entry[form];
  }
  // Engine profile-name family (e.g. "foam-open", "cloth-open-mixed",
  // "no-sting-open"): normalise by material substring so an implementation
  // profile key still reads like a name rather than leaking (WT-5). Check
  // cloth/no-sting before foam (none is a substring of another, but explicit).
  let material: string | null = null;
  if (raw.includes('cloth')) material = 'cloth';
  else if (raw.includes('no-sting') || raw.includes('no_sting') || raw.includes('nosting')) material = 'no_sting';
  else if (raw.includes('foam')) material = 'foam';
  if (material) {
    return RULESET_NAMES[material][form];
  }
  // Unknown key: never leak the raw key in upper-case. Title-case it as a
  // last resort so a new ruleset still reads like a name, not a constant.
  const cleaned = raw.replace(/[_-]/g, ' ').trim();
  return cleaned ? cleaned.replace(/\b\w/g, (c) => c.toUpperCase()) : 'Legacy survivor scoring';
}
