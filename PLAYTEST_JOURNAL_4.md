# PLAYTEST JOURNAL 4 - V23 "The World"

Date: 2026-06-12
Build: V23 "The World" shipped block, local prod server on `localhost:8000`
Mode: player/auditor only. No source, tests, or docs changed.

Tooling note: Pare MCP was not available in this session, so I used the normal local shell/browser fallback required by `AGENTS.md`.

## Run 1 - The Founding Climb

I created `codex-pt4-founding-climb`, club name `Pioneer Works`, city `Redwood Junction`, coach `Mara Vale`, Recruiting Legend. The first New Game choice immediately did the right V23 work: Build from Scratch said I was founding at the bottom of the District League (D3), and Takeover said Premier is the top of a 28-club pyramid where the bottom two go down. That first screen was clear.

The wizard mostly kept that clarity. Staff hiring had a real budget read: $600k budget, $174k default payroll, $426k opening treasury, and the note that a mid-table District season pays about $280k. I hired a better staff group, moved payroll to $248k, and started with $352k. Founding draft also felt honest because it exposed ratings, ceiling, and growth arc instead of hiding the ball.

The first sag came at Season 1 preview. It explained 7 weeks, a Week 5 bye, top 4 of 7, and the playoff cut, but it did not repeat that I was in D3, at the bottom of a 28-club world, or what promotion meant. As a new player I could understand "make playoffs"; I could not yet feel "climb the pyramid" without going to Standings.

Week 1 made the weekly loop work. I scouted Old Quarter, saw an all-in rush read, changed my plan to hold back and go for catches, then won 8-3. The debrief and replay agreed: catches were 29-4 and the replay game plan showed my tactical choices. This was one of the best "receipts or it doesn't ship" moments of the run.

The Standings screen is where V23 really appears. District League was labeled D3, my row had the star, the stakes said champion promotes and next four enter promotion playoff, and the Pyramid panel let me inspect D1, D2, D3, and INT. From D3 I could see Premier's top two reach WORLDS and bottom two drop, and the International Circuit had its own Worlds path. This is the surface that makes the world feel alive.

Manual Season 1 results:

- W1 beat Old Quarter 8-3.
- W2 beat Harborside 7-3.
- W3 lost to Southbank 3-9.
- W4 beat Millfields 7-5.
- W5 bye.
- W6 beat Westvale 7-3.
- W7 drew Northgate 4-4.
- Regular season: 4-1-1, #2, +9 GP diff, 13 pts.

The bye exposed two copy/truth issues. The command banner said `Season 1 -- Week 06` while the page body said `W05 - BYE WEEK`. After locking, the sim panel said "Run the match when ready" even though there was no match.

Postseason framing worked emotionally but still undersold promotion. The semifinal said win and the final is one step away; the final said win the banner because there is no next week. I won the semifinal 10-4 and the final 15-2. The title felt good, but the final prompt did not explicitly say "win this and you are promoted"; that receipt arrived in the offseason instead.

The Season 1 offseason recap was excellent. It said:

- `PROMOTED - next season you play in the Challenger League.`
- Premier champion: Granite.
- Challenger champion: Meadowbrook.
- District champion: Pioneer.
- International champion: Stockholm.
- Promotions/relegations named both directions.
- Worlds: Stockholm beat Nairobi.
- Finances: +$320k league payout, +$140k playoff bonus, -$248k payroll, net +$212k, treasury $564k.
- Tier line: District payouts are the pyramid base scale.

Development was enormous: Aoife Sato went 56 to 84, Greta Eze 50 to 76, Minho Olsen 62 to 86, Luca Goodwin 65 to 84. It was exciting, but it explains why the climb turned into a sprint.

Signing Day had both strong and weak receipts. Niamh Ash signed with no rival bid and verified at 46 OVR. Mateo Kim signed after my offer 91 beat Old Quarter's 74 and verified at 44 OVR. However, Ivana Khalil disappeared between picks without a line telling me who signed her. The desk warns that this can happen, but the event still needs a named receipt. Later, the class report leaked archetype keys like `dodger_anchor` and `catcher_hawk`.

Season 2 verified the movement promise. Pioneer and Southbank moved into Challenger, exactly as the prior recap said. Season 2 was no longer competitive:

- W1 beat co-promoted Southbank 14-1.
- W2 showed +114 net starter OVR vs Riverton and ended 13-2.
- Finished regular season 6-0, +74.
- Won semifinal 22-0.
- Won final 21-3.
- Promoted to Premier.
- Treasury moved to $964k.

Season 3 and 4 were fast-forwarded. Pioneer immediately won Premier and Worlds twice:

- Season 3 Premier: 6-0, +76. Worlds: Pioneer beat Northwood.
- Season 4 Premier: 6-0, +90. Worlds: Pioneer beat Marseille.
- Treasury moved to $1.58M after S3 and $2.2M after S4.

Worlds history accumulated correctly in Dynasty Office -> League: Season 1 Stockholm, Season 2 Marseille, Season 3 Pioneer, Season 4 Pioneer. My Program history did not make my Worlds titles feel as visible as League history did, but the League archive did track them.

## Run 2 - The Takeover Under Threat

I created `codex-pt4-premier-threat` and took over Solstice Flare. The takeover intro correctly said Premier is the top of the 28-club pyramid, but the club picker only offered six Premier clubs. Ridgeline Vanguard was missing from the choice list. The same screen also said every club starts with a comparable six and that the choice is about identity, not difficulty. That clashes with the owner law that takeover should be under relegation threat.

Solstice started Season 1 in Premier, ranked #7 and in the DROP zone on Standings. That was clear once I opened Standings, but again the Season Preview only talked about 7 weeks, bye, and top 4 of 7.

Manual Premier start:

- W1 beat Northwood 7-5.
- W2 was a bye and reproduced the week/banner mismatch.
- W3 lost 6-7 to Aurora.

The W3 debrief was one of the best teaching moments in the run. Staff had advised Preserve Health because two starters had low stamina. I stayed Balanced. The game said the advice was not a guarantee, but in a one-point loss it was the clearest lever I held. That felt like AI playing alongside me, not through me.

Season 1 takeover fast-forward:

- Solstice finished regular season #1 at 5-1, +11.
- Ridgeline beat Solstice 12-3 in the semifinal, then beat Aurora 12-9 in the final.
- Worlds: Rhein beat Stockholm.
- Finances: +$612k league payout, +$72k playoff bonus, -$278k payroll, net +$406k, treasury $556k.

That bracket receipt was strong. It made "regular season #1 is not the same as champion" legible.

I then low-touched the save until relegation happened:

- Season 2: Solstice 4-2, #3, +8. Granite champion. Rhein Worlds champion.
- Season 3: Solstice 3-3, #5, -1, missed playoffs. Northwood champion. Rhein Worlds champion.
- Season 4: Solstice 2-3-1, #5, +3, missed playoffs. Ridgeline champion. Stockholm Worlds champion.
- Season 5: Solstice 1-3-2, #7, -17, relegated.

Season 5 recap did the important work:

- `RELEGATED - next season you play in the Challenger League.`
- Premier champion: Aurora.
- Relegated clubs: Ridgeline and Solstice.
- Worlds: Rhein beat Aurora.
- Finances: +$396k league payout, -$278k payroll, net +$118k, treasury $1.46M.

Post-relegation verification passed after I signed one free agent to field a legal six. Season 6 Standings put Solstice in Challenger League/D2, with Ridgeline also down. D2 stakes read: champion promotes, next four play a promotion playoff, bottom two relegate. The Pyramid panel starred D2. This was the cleanest "recap promise -> next season reality" receipt in the takeover run.

Signing Day also produced two useful receipts in this run:

- Trying to sign Rohan Nguyen got `SNIPED`: Stillwater offer 94 beat my 86, with my 40% interest and 0 recruiting actions named.
- Signing Daichi Patel as a free agent was uncontested, and the class report correctly said free-agent signings do not get contested-round cards.

The legal-roster gate also worked: with 5/12 players, skipping recruiting was blocked because at least six are needed to field a legal six. The UI was right; the only issue is that repeated blocked attempts generated browser console 409 errors.

## Run 3 - Adversarial Sweep

I cross-checked movement, standings, finances, and Worlds history across the two saves.

Confirmed good:

- Founding S1 recap promoted Pioneer to Challenger, and S2 Standings showed Pioneer in Challenger.
- Founding S2 recap promoted Pioneer to Premier, and S3 Standings showed Pioneer in Premier.
- Takeover S5 recap relegated Solstice to Challenger, and S6 Standings showed Solstice in Challenger.
- Worlds crowned a champion every completed season I checked.
- Dynasty Office -> League accumulated Worlds season by season.
- Fresh Chrome verification of Season 6 post-relegation had no console errors.

Contradiction/gap checks:

- I could inspect W1 replay immediately from the debrief, and it matched the debrief.
- I could not find archive replay buttons for old promotion finals or Worlds finals in Standings or Dynasty Office League history. The archive tells me who won Worlds, but does not let me click into the final replay from that history surface.
- All-Time Records still sometimes use generated IDs instead of human-facing names, for example `Rhein 3 - Season 5`, `Aurora 4 - Season 5`, `Ridgeline 5 - Season 4`.

## Findings Table

| ID | Severity | Surface | Exact repro | Contradiction or gap |
|---|---|---|---|---|
| PT4-01 | FRICTION | Season Preview | Start founding S1, promoted S2, Premier S3, or takeover seasons. Read the preview before Standings. | Preview explains weeks, bye, and top 4 of 7, but does not name current division/tier, 28-club pyramid, promotion/relegation, or Worlds stakes. The climb is legible only after opening Standings. |
| PT4-02 | TRUST-BREAK | Command Center bye week | Founding S1 W5 bye and takeover S1 W2 bye. | Header showed the next week (`Season 1 -- Week 06` or `Season 1 -- Week 03`) while the body correctly said W05/W02 bye. Two surfaces disagreed on the current week. |
| PT4-03 | FRICTION | Sim Lock on bye | Lock a bye week. | The lock panel says "Plan locked. Run the match when ready" and offers `Simulate Week` even though the page also says no match is scheduled. |
| PT4-04 | FRICTION | Postgame Standings Shift | Founding S1 W3 loss to Southbank. | Standings Shift named out-of-division/global clubs and rank jumps without explaining the global context, which was confusing from a D3 viewpoint. |
| PT4-05 | TRUST-BREAK | Prospect Pulse | Founding S1 W1 after scouting/contacting/visiting recruits. | Debrief said "No prospect movement this week" even though visible recruiting actions had changed prospect interest/state. |
| PT4-06 | TRUST-BREAK | Signing Day | Founding S1 Signing Day, after signing Niamh and Mateo. | Ivana Khalil disappeared between picks with no line saying who signed her. The mechanic is disclosed, but this specific disappearance lacked a receipt. |
| PT4-07 | POLISH | Signing Day / League Records | Founding S1 class report; Dynasty Office League records after several seasons. | Player-facing reports leak internal-ish names like `dodger_anchor`, `catcher_hawk`, `Rhein 3 - Season 5`, and `Aurora 4 - Season 5`. |
| PT4-08 | FRICTION | Takeover setup | New Game -> Take Over a Program. | Only six Premier clubs were offered; Ridgeline Vanguard was missing. Copy also says the choice is not a difficulty setting, which undercuts the intended "under threat" takeover premise. |
| PT4-09 | FRICTION | Fast-forward modal | Takeover S1 W4, choose "To the offseason" by clicking the visible text, then confirm. | The run stopped pre-playoffs instead of offseason. The modal copy is good, but the stop-point interaction did not behave like a normal text/radio click in my pass. |
| PT4-10 | FRICTION | Archive replay access | After completed seasons, inspect Standings, League Wire, and Dynasty Office -> League history. | High-stakes outcomes are archived, but I could not find a way to open the replay of an old promotion final or Worlds final from those archive surfaces. |
| PT4-11 | FRICTION | Browser console / Signing Day validation | In takeover S5, attempt to skip recruiting with only 5 rostered players. | The UI correctly blocks the action, but repeated blocked attempts logged repeated 409 console errors. Handled validation should ideally not look like noisy browser failures. |
| PT4-12 | DELIGHT | Offseason League Movement | Founding S1/S2, takeover S5. | Movement recap names champions, promotions, relegations, Worlds, and the user's own promotion/relegation banner. This is the strongest V23 receipt surface. |
| PT4-13 | DELIGHT | Manager Lesson | Takeover S1 W3 loss to Aurora. | The game told me staff advised Preserve Health, I ran Balanced, and in a 6-7 loss that was the clearest lever I held. This made AI advice feel like a co-traveler, not autopilot. |
| PT4-14 | DELIGHT | Standings Pyramid | D3 founding and D2/D1 later seasons. | The Pyramid panel with D1/D2/D3/INT tabs, DROP markers, and the user's star makes the wider world readable from any tier. |

## Balance Evidence (known-deferred)

Founding climb results:

| Season | Tier | Regular season | Postseason / Worlds | Treasury |
|---|---:|---|---|---:|
| S1 | D3 | 4-1-1, #2, +9 | District champion, promoted | $564k |
| S2 | D2 | 6-0, #1, +74 | Challenger champion, promoted | $964k |
| S3 | D1 | 6-0, #1, +76 | Premier champion, Worlds champion | $1.58M |
| S4 | D1 | 6-0, #1, +90 | Premier champion, Worlds champion | $2.2M |

Concrete balance notes:

- S2 W1 vs co-promoted Southbank was 14-1.
- S2 W2 showed +114 net starter OVR vs Riverton.
- S2 playoff scores were 22-0 and 21-3.
- S3/S4 Premier seasons were perfect with massive differentials.
- Founding development was explosive: Aoife 56 -> 84, Greta 50 -> 76, Minho 62 -> 86 after one season; Niamh 46 -> 82 after one season.
- Finances did not squeeze after the first title: $352k opening treasury became $2.2M by the end of S4.

Takeover threat results:

| Season | Tier | Solstice result | Movement / Worlds | Treasury |
|---|---:|---|---|---:|
| S1 | D1 | 5-1, #1, +11 | Lost semifinal 3-12; Rhein Worlds champ | $556k |
| S2 | D1 | 4-2, #3, +8 | Granite champion; Rhein Worlds champ | $890k |
| S3 | D1 | 3-3, #5, -1 | Missed playoffs; Rhein Worlds champ | $1.15M |
| S4 | D1 | 2-3-1, #5, +3 | Missed playoffs; Stockholm Worlds champ | $1.34M |
| S5 | D1 | 1-3-2, #7, -17 | Relegated; Rhein Worlds champ | $1.46M |
| S6 start | D2 | 0-0, #7 listed | Verified Challenger placement | $1.46M |

This is consistent with the known-deferred balance bucket: founding climb is much too fast, Premier finances get comfortable, and tier-shifted rosters create odd pressure curves. The takeover run did eventually produce relegation, but only after several seasons and after the roster aged down to 5 players.

## Verdict

A Teamfight Manager or CFB-dynasty player would probably keep playing through the first few hours because the core receipts are now real: pyramid standings, movement recap, Worlds history, scouting/tactic/debrief loops, and promotion/relegation carryover all mostly tell the truth.

The climb sags because the founding roster plus development economy overwhelms the world too quickly. My D3 founder became a Worlds champion in Season 3 and then repeated in Season 4 with no meaningful financial squeeze. The emotional idea of "The Climb" is strong, but the resistance curve currently collapses after the first season.

The biggest trust fixes I would want before calling V23 fully clean are: fix bye week header mismatch, make Season Preview carry division/world stakes, add missing Signing Day disappearance receipts, clean internal names from reports/records, and expose archive replays for promotion/Worlds finals.

## Saves Created

- `saves/codex-pt4-founding-climb.db`
- `saves/codex-pt4-premier-threat.db`
