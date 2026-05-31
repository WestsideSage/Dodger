export type TermKind = 'mechanical' | 'flavor';

export interface TermDef {
  label: string;
  plain: string;
  why: string;
  kind: TermKind;
}

export const TERMS = {
  'archetype.sharpshooter': {
    label: 'Sharpshooter',
    plain: 'Aggressive attacker who prioritizes high-accuracy throws to eliminate opponents.',
    why: 'Higher throw volume and accuracy — your primary source of eliminations.',
    kind: 'mechanical',
  },
  'archetype.net_specialist': {
    label: 'Net Specialist',
    plain: 'Catch-focused defender who turns incoming throws into resurrections.',
    why: 'Catches out the thrower AND brings a teammate back — high swing on each attempt.',
    kind: 'mechanical',
  },

  'archetype.iron_anchor': {
    label: 'Iron Anchor',
    plain: 'Evasive survivor who is hard to eliminate and stays alive deep into rallies.',
    why: 'Late-rally staying power; buys time for teammates to catch or reset.',
    kind: 'mechanical',
  },
  'archetype.two_way_threat': {
    label: 'Two-Way Threat',
    plain: 'Hybrid who throws with authority and attempts catches on incoming balls.',
    why: 'No single defensive answer — opponents cannot key on one vulnerability.',
    kind: 'mechanical',
  },
  'archetype.skirmisher': {
    label: 'Skirmisher',
    plain: 'Mobile attacker who throws quickly and retreats to avoid return fire.',
    why: 'Generates elimination attempts without committing to a long throw exchange.',
    kind: 'mechanical',
  },
  'archetype.possession_specialist': {
    label: 'Possession Specialist',
    plain: 'Catch-and-control player who prioritizes holding the ball over throwing.',
    why: 'Starves the opponent of ammo; forces them to take lower-percentage risks.',
    kind: 'mechanical',
  },
  'archetype.hit_and_run': {
    label: 'Hit-and-Run',
    plain: 'Fast attacker who strikes and repositions before opponents can respond.',
    why: 'Disrupts defensive positioning without exposing themselves to counterattacks.',
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
  // --- Lineup (mechanical: slot order drives role-label assignment) ---
  'lineup.slot_order': {
    label: 'Slot Order',
    plain: 'The sequence of your six starters from Captain (slot 1) through Utility (slot 6).',
    why: 'Each slot carries a role label that summarizes the position. Reorder to put the right archetype in the right slot — swap a bench player in by clicking a slot, then a bench card.',
    kind: 'mechanical',
  },
  // --- Department orders (mechanical: each drives a weekly staff focus) ---
  'dept.tactics': {
    label: 'Tactics',
    plain: 'Your staff\'s game-planning focus this week — opponent prep, containment, or tempo.',
    why: 'Tactical orders bias how your team approaches the next match. Mechanical.',
    kind: 'mechanical',
  },
  'dept.training': {
    label: 'Training',
    plain: 'What your training staff emphasizes in practice — fundamentals, throws, or catches.',
    why: 'Training focus shapes which attributes your players develop toward. Mechanical.',
    kind: 'mechanical',
  },
  'dept.conditioning': {
    label: 'Conditioning',
    plain: 'How hard you push the squad physically — recovery emphasis vs. stamina push.',
    why: 'Conditioning order trades short-term edge for long-term freshness. Mechanical.',
    kind: 'mechanical',
  },
  'dept.medical': {
    label: 'Medical',
    plain: 'How aggressively your medical staff manages player minutes and injury risk.',
    why: 'Affects whether injured or tired players are rested or pushed. Mechanical.',
    kind: 'mechanical',
  },
  'dept.scouting': {
    label: 'Scouting',
    plain: 'What your scouts focus on — next opponent, the prospect board, or playoff rivals.',
    why: 'Scouting focus narrows which information you get each week. Mechanical.',
    kind: 'mechanical',
  },
  'dept.culture': {
    label: 'Culture',
    plain: 'The locker-room emphasis this week — youth confidence, veteran leadership, accountability.',
    why: 'Culture orders influence morale and long-term player identity. Mechanical.',
    kind: 'mechanical',
  },
  // --- Staff roles (Phase 3b) ---
  'staff.training': {
    label: 'Training Staff',
    plain: 'Runs offseason player-development sessions and tracks rep quality.',
    why: 'Higher rating boosts each player\'s offseason OVR growth by up to 15% — the only staff role with a live mechanical hook.',
    kind: 'mechanical',
  },
  'staff.tactics': {
    label: 'Tactics Staff',
    plain: 'Prepares matchup-specific game plans and reviews replay evidence.',
    why: 'Advisory only — surfaces tactical recommendations in the command center; no hidden stat effect.',
    kind: 'flavor',
  },
  'staff.conditioning': {
    label: 'Conditioning Staff',
    plain: 'Monitors fatigue risk and designs recovery schedules.',
    why: 'Advisory only — flags overuse and recovery recommendations; no hidden stat effect.',
    kind: 'flavor',
  },
  'staff.medical': {
    label: 'Medical Staff',
    plain: 'Tracks player availability and warns on overuse risk.',
    why: 'Advisory only — availability warnings; no hidden stat effect.',
    kind: 'flavor',
  },
  'staff.scouting': {
    label: 'Scouting Staff',
    plain: 'Explains fit scores and clarifies the prospect board.',
    why: 'Advisory only — improves recruit board readability; no hidden fit-score modifier.',
    kind: 'flavor',
  },
  'staff.culture': {
    label: 'Culture Staff',
    plain: 'Frames promise risk and monitors command-plan stability.',
    why: 'Advisory only — surfaces promise-risk framing in the office; no hidden morale stat.',
    kind: 'flavor',
  },
  'archetype.thrower': {
    label: 'Thrower',
    plain: 'Aggressive eliminator via throws.',
    why: 'Primary source of offensive eliminations; high throw volume.',
    kind: 'mechanical',
  },
  'archetype.hawk_dodger': {
    label: 'Ball Hawk / Dodger',
    plain: 'Hybrid evasion: catches and dodges.',
    why: 'Stays alive and gathers balls without being easily eliminated.',
    kind: 'mechanical',
  },
  'archetype.catcher': {
    label: 'Catcher',
    plain: 'Catch-focused player who converts incoming throws into teammate resurrections.',
    why: 'Every successful catch eliminates the thrower AND brings a teammate back — the highest swing play in dodgeball.',
    kind: 'mechanical',
  },
  'archetype.ball_hawk': {
    label: 'Ball Hawk',
    plain: 'Evasive survivor who collects loose balls and attempts opportunistic catches.',
    why: 'Stays alive to accumulate throw chances; successful catches can shift momentum late in a round.',
    kind: 'mechanical',
  },
  'archetype.dodger_anchor': {
    label: 'Dodger Anchor',
    plain: 'Evasion-first specialist designed to be the last player standing.',
    why: 'Hard to eliminate — opponents waste throws chasing this player; forces late-round panic decisions.',
    kind: 'mechanical',
  },
  'archetype.thrower_catcher': {
    label: 'Thrower / Catcher',
    plain: 'Hybrid who attacks with throws and is willing to attempt catches on incoming throws.',
    why: 'Doubles threat: eliminates via throws AND can swing a round with a catch; higher variance than a pure specialist.',
    kind: 'mechanical',
  },
  'archetype.thrower_dodger': {
    label: 'Thrower / Dodger',
    plain: 'Hybrid who attacks with throws and uses mobility to survive.',
    why: 'Throw volume with lower exposure than a pure Thrower — stays in the game longer to keep throwing.',
    kind: 'mechanical',
  },
  'archetype.catcher_hawk': {
    label: 'Catcher / Ball Hawk',
    plain: 'Hybrid focused on catching incoming throws and collecting loose balls.',
    why: 'Resurrection machine: turns defensive play into offensive momentum through repeated catch attempts.',
    kind: 'mechanical',
  },
} as const satisfies Record<string, TermDef>;

export type TermId = keyof typeof TERMS;

export function getTerm(id: TermId): TermDef {
  return TERMS[id];
}
