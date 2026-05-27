/**
 * Canonical player display formatters.
 *
 * Both the founding-draft picker (StartingRecruitmentStep) and the in-season
 * roster rows (PlayerCompactRow, PlayerTheaterRow) must show identical
 * strings for the same player. Funnel every name / role / OVR rendering
 * through these helpers so the two surfaces cannot drift again.
 *
 * Regression context: Codex playtest bug #3 — founding-draft picks did not
 * match the post-commit roster. See
 * tests/test_founding_roster_continuity.py.
 */
import type { Player } from '../../types';

/** Lightweight shape supported by the draft picker (subset of Player). */
export interface PlayerDisplayLike {
  name: string;
  role?: string;
  overall?: number;
  archetype?: string;
  public_archetype?: string;
  public_ovr_band?: readonly [number, number] | number[];
}

export function formatPlayerName(p: PlayerDisplayLike | Player): string {
  return p.name;
}

export function formatRole(p: PlayerDisplayLike | Player): string {
  // Roster payload uses `role`; prospect payload uses `public_archetype`.
  // Both are the canonical recruitment display label (e.g. "Sharpshooter").
  const candidate =
    (p as Player).role ??
    (p as PlayerDisplayLike).public_archetype ??
    (p as PlayerDisplayLike).archetype ??
    '';
  return candidate;
}

export function formatOverall(p: PlayerDisplayLike | Player): string {
  if (typeof (p as Player).overall === 'number') {
    return String((p as Player).overall);
  }
  const band = (p as PlayerDisplayLike).public_ovr_band;
  if (band && band.length === 2) {
    return band[0] === band[1] ? String(band[0]) : `${band[0]}–${band[1]}`;
  }
  return '?';
}
