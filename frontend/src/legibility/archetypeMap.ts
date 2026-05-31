import type { TermId } from './terms';

// Canonical PlayerArchetype enum value -> TermId. Keys are the raw enum values
// emitted by the backend as `archetype_key` (models.py PlayerArchetype); targets
// are the canonical `archetype.<enum>` terms seeded in terms.ts (V15 index
// decision #1). Enum-key payload consumers (e.g. Season Preview) import this map
// instead of defining their own. Screens that receive only a recruitment display
// string ("Sharpshooter", ...) — ProspectCard/Roster/PlayerDetailModal — cannot
// use this map without a backend enum-key payload field; see archetypeMap notes.
export const PLAYER_ARCHETYPE_TERM: Record<string, TermId> = {
  thrower: 'archetype.thrower',
  catcher: 'archetype.catcher',
  ball_hawk: 'archetype.ball_hawk',
  dodger_anchor: 'archetype.dodger_anchor',
  thrower_catcher: 'archetype.thrower_catcher',
  thrower_dodger: 'archetype.thrower_dodger',
  catcher_hawk: 'archetype.catcher_hawk',
  hawk_dodger: 'archetype.hawk_dodger',
};

export const CLUB_ARCHETYPE_TERM: Record<string, TermId> = {
  'Balanced Rebuild': 'program.archetype.balanced_rebuild',
  'Contender': 'program.archetype.contender',
  'Development Factory': 'program.archetype.development_factory',
  'Defensive Specialist': 'program.archetype.defensive_specialist',
  'Power Throwers': 'program.archetype.power_throwers',
  'Aging Veterans': 'program.archetype.aging_veterans',
};
