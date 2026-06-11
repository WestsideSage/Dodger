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
    why: 'Rec-league matches only: fewer wasted/headshot throws. Official-rules matches do not model it in-play; it still shapes archetype identity and development.',
    kind: 'mechanical',
  },
  'attr.catch_courage': {
    label: 'Catch Courage',
    plain: 'Willingness to attempt catches on hard incoming throws.',
    why: 'Rec-league matches only: more catch attempts (more resurrections, more risk). Official-rules matches read the Catch rating and posture instead; it still shapes identity and development.',
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
  // TRUTH (V16 Contested Offseason): Signing Day prospect picks resolve
  // through a contested round (recruitment.conduct_recruitment_round) where
  // your offer = base + interest x weight against real rival bids. Interest,
  // Pipeline and Credibility are therefore MECHANICAL (they feed that offer
  // chain). Fit stays a flavor reading: it summarizes mechanical inputs
  // (scouted range + credibility) but is not itself consumed anywhere.
  // V19b: promises are MECHANICAL — evaluated at season's end against real
  // match/plan/playoff records, and the kept/broken record feeds program
  // credibility (kept +4 each, broken -6 each, capped ±15), which sets
  // prospect interest, which strengthens your contested Signing Day offer.
  'recruit.promise': {
    label: 'Promises',
    plain: 'A real commitment to a prospect or player, checked at season\'s end.',
    why: 'Each promise is graded against what actually happened (matches played, dev weeks run, playoffs made). Playing-time and development promises to an unsigned prospect wait for their first season on your roster; "We\'ll contend" grades this season whether or not they sign. Kept promises build credibility; broken ones cost more — and credibility feeds every prospect\'s interest in you.',
    kind: 'mechanical',
  },
  'recruit.fit': {
    label: 'Fit',
    plain: 'How well this prospect matches your program right now (0-100).',
    why: 'A shortlist aid blending the scouted range with your credibility — a reading, not a lever. Your signing odds come from Interest, not Fit.',
    kind: 'flavor',
  },
  'recruit.interest': {
    label: 'Interest',
    plain: 'How interested the prospect is in your program (%).',
    why: 'Rises with contact/visits and credibility — and it strengthens your Signing Day offer in the contested round. Courted prospects are measurably harder for rival clubs to snipe.',
    kind: 'mechanical',
  },
  'recruit.ovr_range': {
    label: 'OVR Range',
    plain: 'The estimated band for this prospect’s true overall.',
    why: 'Scouting narrows the band — the verified OVR is revealed only at signing.',
    kind: 'mechanical',
  },
  'recruit.pipeline': {
    label: 'Pipeline',
    plain: 'A recruiting region/tier your program has a relationship with.',
    why: 'A higher tier starts the prospect warmer (higher base interest), which feeds straight into your contested Signing Day offer.',
    kind: 'mechanical',
  },
  'program.credibility': {
    label: 'Program Credibility',
    plain: 'The recruiting-facing reputation that sets which prospects are interested.',
    why: 'Rises with wins and youth focus; sets the interest baseline every prospect starts from, which feeds your contested Signing Day offer.',
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
  // V20 §7.3: the differential that actually ranks official careers.
  'standings.gp_diff': {
    label: 'Game-Point Differential',
    plain: 'Game points scored minus conceded across the season.',
    why: 'The live tiebreaker behind table points: officials rank on points, then total game points scored, then this.',
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
  // --- Lineup ---
  // HONESTY (2026-06-09 audit; WT-20; V19a 2026-06-10): role fit is now a
  // REAL engine effect in both rulesets — a starter whose archetype fits
  // their seat (slots 1-4 carry archetype preferences) plays +3 on every
  // action stat (lineup.role_fit_bonuses). Bonus-only: a mismatched seat
  // costs the foregone bonus, never a hidden penalty. Slot ORDER also keeps
  // its WT-20 effect: rush Target orders who secures the opening balls /
  // sprints (officials and rec).
  'lineup.slot_order': {
    label: 'Slot Order',
    plain: 'The sequence of your six starters from Captain (slot 1) through Utility (slot 6).',
    why: 'Role fit is mechanical: a starter whose archetype fits their seat (slots 1-4) plays +3 on every action stat — bonus-only, a mismatch just forgoes it. Order also sets the opening rush: your first slots secure the designated balls when Rush Target is "Nearest" (other Target options re-order by power/overall). Swap a bench player in by clicking a slot, then a bench card.',
    kind: 'mechanical',
  },
  // --- Staff focus (V19b: the department-order fiction became one real
  // weekly decision — the staff concentrates on ONE room, each a disclosed
  // mechanical effect; "medical" was REMOVED because injuries are not
  // modeled and a decision with nothing to decide is a fiction). ---
  'dept.tactics': {
    label: 'Tactics Focus',
    plain: 'A film week: your throwers play the next match smarter.',
    why: 'Next match, every thrower gains +18 effective Tactical IQ — better target reads, better release timing, throws that beat the catch window.',
    kind: 'mechanical',
  },
  'dept.training': {
    label: 'Training Focus',
    plain: 'A practice block that banks toward the offseason.',
    why: 'Each training week adds +0.2 OVR of offseason growth for the whole squad (cap 8 weeks a season), headroom-capped per player.',
    kind: 'mechanical',
  },
  'dept.conditioning': {
    label: 'Conditioning Focus',
    plain: 'A recovery week: legs stay fresher in the next match.',
    why: 'Next match, the fatigue drag on every action stat is halved — late-match performance holds up.',
    kind: 'mechanical',
  },
  'dept.scouting': {
    label: 'Scouting Focus',
    plain: 'Extra scout hours on the recruit board this week.',
    why: 'One extra Scout action this week (3 → 4) for narrowing prospect bands.',
    kind: 'mechanical',
  },
  'dept.culture': {
    label: 'Culture Focus',
    plain: 'A locker-room week that makes your program easier to say yes to.',
    why: 'Contact and Visit interest gains land 25% stronger this week — interest feeds your contested Signing Day offer.',
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
  'archetype.ball_hawk': {
    label: 'Ball Hawk',
    plain: 'Evasive survivor who collects loose balls and attempts opportunistic catches.',
    why: 'Stays alive to accumulate throw chances; successful catches can shift momentum late in a round.',
    kind: 'mechanical',
  },
} as const satisfies Record<string, TermDef>;

export type TermId = keyof typeof TERMS;

export function getTerm(id: TermId): TermDef {
  return TERMS[id];
}
