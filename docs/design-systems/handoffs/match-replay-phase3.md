# Match Replay Phase 3: Make the End State Satisfying

**Depends on:** Phase 2 complete (ReplayCourt, PlayerToken, ActionPath, refined PlayByPlayList exist)

**Design system reference:** `docs/design-systems/Match-Replay-Design-System.md`, sections 18–21

---

## Goal

Make finishing a match replay feel like payoff — a winner banner, match summary, player of the match, and a clear set of post-match actions. The replay should reward watching all the way through.

---

## What exists after Phase 2

- Full court with redesigned player tokens and action paths
- Play-by-play and key plays tabs in the info panel
- Event markers on the timeline
- Scoreboard shows "FINAL" when the match ends

**Current end-state gaps:**
- No winner announcement beyond "FINAL" on the scoreboard
- No match summary comparing team stats
- No player of the match highlight
- Key Plays tab doesn't auto-activate after match end
- No "Watch Again" / "Continue" action bar
- The replay just… stops

---

## What to build

### 1. `WinnerBanner`

**New file:** `frontend/src/components/match-replay/WinnerBanner.tsx`

A subtle banner that appears when the match ends.

**Props:**
```ts
{
  teamName: string;
  side: 'home' | 'away';
}
```

**Layout:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              NORTHWOOD IRONCLADS WIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Rules:**
- Full-width, appears between the scoreboard and the court area
- Team name in `font-display`, `text-2xl`, `uppercase`
- Subtle background tint using the winning team's color (warm/cool)
- Fade-in animation: `opacity: 0 → 1` over 400ms with `translateY(4px) → 0`
- Should NOT be a modal or block the court — the page remains usable

### 2. `MatchSummaryCard`

**New file:** `frontend/src/components/match-replay/MatchSummaryCard.tsx`

Side-by-side team stat comparison shown after match end.

**Props:**
```ts
{
  homeTeam: string;
  awayTeam: string;
  homeStats: TeamMatchStats;
  awayStats: TeamMatchStats;
  winnerSide: 'home' | 'away' | null;
}
```

**Type:**
```ts
type TeamMatchStats = {
  eliminations: number;
  catches: number;
  dodges: number;
  throws: number;
};
```

**Layout:**
```
MATCH SUMMARY

               Lunar    Northwood
Eliminations     2          6
Catches          6         11
Dodges           8         12
Throws          28         34
```

**Rules:**
- Two columns, team names at top
- Winner column gets subtle brightness, loser column is slightly muted
- Stats are derived by counting `proof_events` by resolution type per team
- Use `dm-kicker` for "MATCH SUMMARY" header
- Appears in the info panel as a new section when match is final

**Stat derivation from proof_events:**
```ts
function computeTeamStats(proofEvents: ReplayProofEvent[], clubId: string): TeamMatchStats {
  const offenseEvents = proofEvents.filter(e => e.offense_club_id === clubId);
  const defenseEvents = proofEvents.filter(e => e.defense_club_id === clubId);
  return {
    eliminations: offenseEvents.filter(e => e.resolution === 'hit').length,
    catches: defenseEvents.filter(e => e.resolution === 'caught').length,
    dodges: defenseEvents.filter(e => e.resolution === 'dodged').length,
    throws: offenseEvents.length,
  };
}
```

### 3. `PlayerOfTheMatch`

**New file:** `frontend/src/components/match-replay/PlayerOfTheMatch.tsx`

Highlights the top performer.

**Props:**
```ts
{
  playerName: string;
  teamName: string;
  statline: string;
  impactScore: number;
}
```

**Layout:**
```
PLAYER OF THE MATCH

Cade Kade
Northwood Ironclads

3 Eliminations · 2 Catches · 2 Dodges
Impact: 91
```

**Rules:**
- Player name is the strongest text (`text-xl`, `font-bold`)
- Team name is secondary
- Statline is compact, inline
- Impact score uses a `Badge` component

**Data source:** `MatchReplayResponse.report.top_performers[0]` — already available. The `TopPerformer` type has `player_name`, `team_name`, and stat fields.

### 4. Post-match mode logic

**Edit:** `frontend/src/components/MatchReplay.tsx`

When the match ends (final tick reached):

1. Set a `mode` state to `'postMatch'`
2. Show `WinnerBanner` between scoreboard and court
3. Switch info panel default tab to `'keyPlays'`
4. Append `MatchSummaryCard` and `PlayerOfTheMatch` to the info panel
5. Show the `ReplayFooterActions` bar

### 5. `ReplayFooterActions`

**New file:** `frontend/src/components/match-replay/ReplayFooterActions.tsx`

Action bar at the bottom of the replay.

**Props:**
```ts
{
  canContinue: boolean;
  onContinue: () => void;
  onWatchAgain: () => void;
}
```

**Layout:**
```
[Watch Again]                              [Continue →]
```

**Rules:**
- "Continue" is the primary action (orange, `variant="primary"`)
- "Watch Again" is secondary (outlined/muted), resets playback to tick 0
- "Continue" is disabled until the match is final
- Only one orange button on screen
- Action bar sits at the bottom of the content flow

### 6. Add Stats tab to ReplayInfoPanel

**Edit:** `frontend/src/components/match-replay/ReplayInfoPanel.tsx`

Add a third tab "Stats" that shows the `MatchSummaryCard` and `PlayerOfTheMatch` components. This tab is only available when the match is final.

Update tab list:
```ts
const tabs = mode === 'postMatch'
  ? ['playByPlay', 'keyPlays', 'stats']
  : ['playByPlay', 'keyPlays'];
```

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/match-replay/WinnerBanner.tsx` | Create |
| `frontend/src/components/match-replay/MatchSummaryCard.tsx` | Create |
| `frontend/src/components/match-replay/PlayerOfTheMatch.tsx` | Create |
| `frontend/src/components/match-replay/ReplayFooterActions.tsx` | Create |
| `frontend/src/components/match-replay/ReplayInfoPanel.tsx` | Edit — add Stats tab, post-match content |
| `frontend/src/components/MatchReplay.tsx` | Edit — add post-match mode logic, wire new components |

---

## What NOT to build

- Confetti or particle effects — per design system, not in scope
- Sound effects
- Full-screen victory modal — banner should be subtle
- Box Score as a separate page/route
- ShotMap — Phase 4
