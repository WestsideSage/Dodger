import type { TermId } from './terms';

// PlayerArchetype enum value -> TermId. Keys are the raw enum values emitted by
// the backend as `archetype_key` (models.py PlayerArchetype); targets are the
// unified flavor-name terms in terms.ts (Sharpshooter, Net Specialist, ...), the
// single archetype display set across the app. Enum-key payload consumers (e.g.
// Season Preview) import this map. Display-string screens (ProspectCard/Roster/
// PlayerDetailModal) key the same flavor terms by the display string directly.
export const PLAYER_ARCHETYPE_TERM: Record<string, TermId> = {
  thrower: 'archetype.sharpshooter',
  catcher: 'archetype.net_specialist',
  ball_hawk: 'archetype.ball_hawk',
  dodger_anchor: 'archetype.iron_anchor',
  thrower_catcher: 'archetype.two_way_threat',
  thrower_dodger: 'archetype.skirmisher',
  catcher_hawk: 'archetype.possession_specialist',
  hawk_dodger: 'archetype.hit_and_run',
};

export const CLUB_ARCHETYPE_TERM: Record<string, TermId> = {
  'Balanced Rebuild': 'program.archetype.balanced_rebuild',
  'Contender': 'program.archetype.contender',
  'Development Factory': 'program.archetype.development_factory',
  'Defensive Specialist': 'program.archetype.defensive_specialist',
  'Power Throwers': 'program.archetype.power_throwers',
  'Aging Veterans': 'program.archetype.aging_veterans',
};
