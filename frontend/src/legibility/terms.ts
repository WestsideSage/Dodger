export type TermKind = 'mechanical' | 'flavor';

export interface TermDef {
  label: string;
  plain: string;
  why: string;
  kind: TermKind;
}

export const TERMS = {
  'archetype.thrower': {
    label: 'Sharpshooter',
    plain: 'Aggressive attacker who looks to eliminate opponents with throws.',
    why: 'Higher throw volume and accuracy — a primary source of eliminations.',
    kind: 'mechanical',
  },
  'archetype.catcher': {
    label: 'Net Specialist',
    plain: 'Catch-focused defender who turns incoming throws into resurrections.',
    why: 'A catch outs the thrower AND brings a teammate back — high swing.',
    kind: 'mechanical',
  },
  'archetype.ball_hawk': {
    label: 'Ball Hawk',
    plain: 'Aggressive catcher who hunts risky catches off live throws.',
    why: 'Generates catches (resurrections) but can over-commit and get out.',
    kind: 'mechanical',
  },
  'archetype.dodger_anchor': {
    label: 'Iron Anchor',
    plain: 'Evasive survivor who anchors the floor and avoids elimination.',
    why: 'Stays alive late, when survivor counts decide foam games.',
    kind: 'mechanical',
  },
  'archetype.thrower_catcher': {
    label: 'Two-Way Threat',
    plain: 'Balanced hybrid who both throws to eliminate and catches to resurrect.',
    why: 'Flexible lineup glue with no glaring liability to target.',
    kind: 'mechanical',
  },
  'archetype.thrower_dodger': {
    label: 'Skirmisher',
    plain: 'Mobile attacker who throws and evades rather than catching.',
    why: 'Pressures opponents while staying hard to eliminate.',
    kind: 'mechanical',
  },
  'archetype.catcher_hawk': {
    label: 'Possession Specialist',
    plain: 'Catch-first player who controls tempo and wins the catch battle.',
    why: 'Tilts the catch swing — often the deciding factor at large OVR gaps.',
    kind: 'mechanical',
  },
  'archetype.hawk_dodger': {
    label: 'Hit-and-Run',
    plain: 'Evasive opportunist who picks catches and slips elimination.',
    why: 'Survives and steals swing catches without holding ground.',
    kind: 'mechanical',
  },
  'coach.balanced': {
    label: 'Balanced',
    plain: 'No strong tactical lean; adapts to the matchup.',
    why: 'Safe default — fewer exploitable tendencies, fewer sharp edges.',
    kind: 'mechanical',
  },
  'program.archetype.balanced_rebuild': {
    label: 'Balanced Rebuild',
    plain: 'A well-rounded club without a dominant strength yet.',
    why: 'No obvious matchup edge to exploit or fear — read it as average.',
    kind: 'flavor',
  },
  'program.archetype.contender': {
    label: 'Contender',
    plain: 'A high-overall roster built to win now.',
    why: 'Expect a strong starting six — a genuinely tough matchup.',
    kind: 'flavor',
  },
  'program.archetype.development_factory': {
    label: 'Development Factory',
    plain: 'A young, high-potential roster that may rest starters in soft weeks.',
    why: 'Beatable now, dangerous later; they sometimes field developing players.',
    kind: 'flavor',
  },
  'program.archetype.defensive_specialist': {
    label: 'Defensive Specialist',
    plain: 'A club skewed toward dodging and catching over throwing.',
    why: 'Hard to eliminate and catch-heavy — the catch swing favors them.',
    kind: 'flavor',
  },
  'program.archetype.power_throwers': {
    label: 'Power Throwers',
    plain: 'A club skewed toward accuracy and power over defense.',
    why: 'Throw-heavy pressure; thinner on catches and survival.',
    kind: 'flavor',
  },
  'program.archetype.aging_veterans': {
    label: 'Aging Veterans',
    plain: 'An older roster past its physical peak.',
    why: 'Experienced but declining — upside is limited going forward.',
    kind: 'flavor',
  },
  'attr.throw_selection_iq': {
    label: 'Throw Selection IQ',
    plain: 'How well a player picks good throws vs. low-percentage ones.',
    why: 'Higher IQ means fewer wasted/headshot throws and fewer flood-throw mistakes.',
    kind: 'mechanical',
  },
  'attr.catch_courage': {
    label: 'Catch Courage',
    plain: 'Willingness to attempt catches on hard incoming throws.',
    why: 'More catch attempts = more resurrections, but missed attempts cost eliminations.',
    kind: 'mechanical',
  },
  'growth.ceiling': {
    label: 'Ceiling',
    plain: 'The highest OVR this player is projected to reach.',
    why: 'Headroom above current OVR is how much they can still grow.',
    kind: 'mechanical',
  },
  'growth.headroom': {
    label: 'Headroom',
    plain: 'Ceiling minus current OVR — remaining growth room.',
    why: 'High headroom + young age = a genuine high-upside develop target.',
    kind: 'mechanical',
  },
  'recruit.fit': {
    label: 'Fit',
    plain: 'How well this prospect matches your program right now (0-100).',
    why: 'Higher fit closes more easily; it is NOT the same as their OVR.',
    kind: 'mechanical',
  },
  'recruit.interest': {
    label: 'Interest',
    plain: 'How interested the prospect is in your program (%).',
    why: 'Rises with contact/visits and credibility; courted prospects are easier to sign.',
    kind: 'mechanical',
  },
  'recruit.ovr_range': {
    label: 'OVR Range',
    plain: 'The estimated band for this prospect’s true overall.',
    why: 'Scouting narrows the band — you learn how good they really are.',
    kind: 'mechanical',
  },
  'recruit.pipeline': {
    label: 'Pipeline',
    plain: 'A recruiting region/tier your program has a relationship with.',
    why: 'Stronger pipeline tier means warmer prospects and easier closes.',
    kind: 'mechanical',
  },
  'program.credibility': {
    label: 'Program Credibility',
    plain: 'The recruiting-facing reputation that sets which prospects are interested.',
    why: 'Rises with wins and dev; gates the tier of recruits you can attract.',
    kind: 'mechanical',
  },
  'program.prestige': {
    label: 'Club Prestige',
    plain: 'A separate long-term score earned from titles and facilities.',
    why: 'Feeds into credibility over time; 0 on a brand-new club is normal.',
    kind: 'mechanical',
  },
  'standings.diff': {
    label: 'Differential',
    plain: 'Eliminations for minus against across the season.',
    why: 'A tiebreaker and a rough strength signal beyond W-L-D.',
    kind: 'mechanical',
  },
  'standings.playoff_line': {
    label: 'Playoff Line',
    plain: 'The cutoff seed that makes the postseason (top N).',
    why: 'Clubs above the line are in; below are out — your weekly target.',
    kind: 'mechanical',
  },
  'identity.intent': {
    label: 'Program Identity',
    plain: 'Your program’s historical strategic lean (e.g. Balanced).',
    why: 'A flavor summary of how you’ve managed — not a hidden stat bonus.',
    kind: 'flavor',
  },
} as const satisfies Record<string, TermDef>;

export type TermId = keyof typeof TERMS;

export function getTerm(id: TermId): TermDef {
  return TERMS[id];
}
