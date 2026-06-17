# PLAYTEST JOURNAL 3 — The Orphanage Run (Hard-Mode Stress Test)

**Tester:** returning pro playtester, no knowledge of prior runs. Judging only what I see.
**Build:** local server `python -m dodgeball_sim`, port 8000, fresh browser session.
**Date:** 2026-06-11.

## Binding rules I am playing under
1. Draft the dregs — lowest-rated players at roster selection.
2. Prospects only, forever — never sign a veteran FA; every player from founding draft or prospect pipeline.
3. Churn mandatory — sign ≥1 prospect every offseason with a class slot + roster space.
4. Live on promises — keep 3-promise cap full, never break one by my own choice; track each promise's full life.
5. Use every lever on purpose — each Staff Focus ×2, each Dev Focus a full stretch, policy editor for a playoff-specific tweak, manual lineup AND auto-assign, scout every playable week, fast-forward ×2 (mid-season + into offseason) then audit.

Length: ≥8 seasons. Goals: (a) win a title; (b) win a 2nd title with a substantially different roster.

---

## DEVELOPMENT CLAIMS LEDGER
> Every future-claim the game makes about a player, then what actually happened.

| # | Season made | Player | Claim (verbatim/paraphrase) | Source screen | Outcome | Verdict |
|---|---|---|---|---|---|---|

## PROMISE LEDGER
| # | Season made | Player | Promise | Made-context | Resolution | Graded fairly? |
|---|---|---|---|---|---|---|
| P-1 | S1 W4 | Noor Perez | Early playing time → "appear in ≥6 matches this season" | Made unsigned; SIGNED S1 offseason; carried to S2 still 1/3 OPEN | keep by starting her ≥6× in S2 | carried fairly once signed |
| P-2 | S2 W1 | Rowan Cole (prospect) | Development priority → "run a focused dev plan ≥3 weeks AND keep them rostered" | Made unsigned | needs me to sign him S2→S3 + dev weeks | TBD |
| P-3 | S2 W1 | Zara Rodriguez (prospect) | We'll contend → "club reaches the playoffs this season" | Made unsigned | **still OPEN at S3 start** — did NOT break though I missed S2 playoffs | grading DEFERRED until signed |

**Promise grading verdict (S2→S3):** Credibility line: *"Promise record: 1 kept, 0 broken (+4 credibility)."* Only **P-1 (Noor) graded — KEPT, +4**, fairly (she played 6/6 matches as promised). **P-2 & P-3 stayed OPEN** despite S2 ending — so **prospect promises only grade once the prospect SIGNS; unsigned ones never break, they just linger.** This means: (a) the "this season" / "reach playoffs this season" wording is misleading (it really means the season they sign); (b) "never break a promise" is trivially satisfiable by simply not signing — a soft exploit. P-3 *should* have broken at S2 end by its literal text but didn't. **F-9 (promise grading, Med):** promise conditions reference "this season" but grading is silently deferred to the prospect's signing season; a literal reading of the card is wrong, and broken-on-schedule never happens for unsigned prospects.

**Promise-type keepability (for UNSIGNED prospects):** Early-playing-time & Development-priority both require the prospect be ROSTERED (impossible until next offseason → confusing while unsigned); only **We'll contend** (reach playoffs) is a pure team outcome and keepable for anyone. P-1 proved the "this season" condition silently re-anchors to the prospect's first season once signed — so the wording is misleading but the system doesn't auto-break on signing. Net F-4 severity: **Low-Med (confusing copy + opaque grade timing), not a hard break.**

**(promise/finding text below)**

### S1 W4–W7 (blitz) + bye
- W4 @ ? L 0–12 (catches 1–15), intent Balanced. W5 bye. W6 vs Solstice Flare L (catches **7**–24), intent Aggressive. W7 L 0–20 (catches **4**–27), intent Aggressive.
- **S1 regular season: 0-7-0, swept in all 7.** As designed for a dregs roster vs −100→−129 OVR fields.
- **Catch lever (revised conclusion):** Aggressive intent (opportunistic catch) reliably yields ~4–7 catch attempts (W2=6, W6=7, W7=4); Defensive(play-safe)=0 (W1), and W3 Control=0 was the outlier. **The catch-posture lever does control catch volume**; I simply get out-caught 2–6× by far better teams. Trace is honest.
- **F-2 (dev reset) CONFIRMED + refined:** dev-focus select resets to BALANCED at the start of each *match* week (verified value reads at W3 & W6 = "BALANCED" after prior weeks set to Youth). The W5 *bye* preserved the prior Youth value (lone exception). So a player must re-set the focus every match week; only the season-end (W7) value drives offseason growth. Trap-grade UX. I set Youth at W7 → S1 offseason should grow on Youth acceleration.
- **F-5 (cross-surface, Low):** During the bye, the page banner read "Season 1 -- Week 06" while the match card + directive read "Week 05 · Bye Week" (off-by-one). Repro: reach the bye week, compare banner vs match-week label.

**F-8 (Churn blocker, HIGH for this challenge, Med overall):** With a full 12/12 roster, the S2→S3 **Signing Day was auto-skipped** ("You didn't sign anyone — 0/3 slots used"); there is **no inline cut-to-sign option** at Signing Day. Good prospects (Cass Sato 69, Nia Mensah 69) went unsigned. To churn (sign a new prospect) you must proactively *release* a player from the roster BEFORE the offseason — the offseason flow itself never prompts it. This blocks the "second core replaces first" loop unless the player hunts for a release control. Dooms prospect-promises that require rostering (P-2). Repro: fill roster to 12/12 → reach Signing Day → it's a read-only "Update". *(Searched exhaustively: Roster screen, player card, Lineup Editor, Dynasty tabs — **there is NO release/cut/waive control anywhere in the UI** (33 buttons on Roster, zero match release/cut/waive/drop/trade). Churn is **retirement-gated only**. So at a full 12/12 roster the player literally cannot sign anyone for multiple seasons — the mandatory-churn / "second core" goal is blocked until natural attrition. Confirmed S2→S3 AND S3→S4 both auto-skipped signing. **Elevating F-8 to a top finding for any dynasty/rebuild playstyle.**)

**F-4 (Promise design, HIGH for the assignment, Med overall):** The prospect-promise UI offers "Early playing time → appears in ≥6 matches **this season**" for a prospect you have not signed and *cannot* sign until the offseason Signing Day (after this season ends). The promise opens as OPEN with a season condition that is impossible to satisfy, with no warning. Maxing the 3-promise cap with prospect promises therefore guarantees broken promises — directly at odds with a "never break a promise" playstyle. Repro: Dynasty Office → any unsigned prospect → Promise → Early playing time → see "≥6 matches this season" while they're not rostered. Tracking P-1's grading to confirm.

---

# ============================================================
# FINAL REPORT — The Orphanage Run, Seasons 1–8 (complete)
# ============================================================

## 1. THE DYNASTY STORY
**Club:** Hollow Creek Strays (founded from the 10 lowest-rated draftees, avg OVR 44.2; best-available 56s left on the board). Coach Del Marrow, "The Lifer."

| Season | Finish | Notes |
|---|---|---|
| S1 | **0-7-0, 7th/7** | Winless founding season. Swept every game (−100→−129 OVR underdog). |
| S2 | 0-5-1, 7th/7 | First non-loss (W7 draw). Gap shrank to −38. Signed Noor Perez (57) & Callum Saito (60) at S1 Signing Day. |
| S3 | 5th/7 | Even with the league (−6). Climbing. |
| S4 | **RUNNER-UP** | Made playoffs (#3 seed, 3-2-1). **Semifinal: beat Lunar Syndicate 12–7** (the team that swept me 0–14 in S1 — catch swing 29–15 my way via a policy-editor adjustment). **Final: lost 7–13 to Granite Specters.** The peak. |
| S5 | Semifinal exit | Lost 7–12 to Granite again. |
| S6 | 7th/7 | Missed playoffs — the relative-decline cliff begins. |
| S7 | 7th/7 | Static roster, league passes me. |
| S8 | 7th/7 | Same. Run ends. |

**Two cores?** No. There was only ever ONE core. The 10 founders + the two S1 signings (Perez, Saito) formed a 12-man roster that became **frozen and identical from S2 through S8** — every player hit their ceiling by S3 and then *nothing changed for five straight seasons* (dev beat showed "0 players changed OVR" in S4, S6, S7, S8). My founders started at 18–21 and ended at 26–29 **without a single decline or retirement**, and I could never sign or cut a soul (see F-8). The "second core that replaces the first" was mechanically impossible in this run.

**The turning points:** (1) The S1→S2 offseason, where Youth-acceleration turned 40-OVR scrubs into a 60-OVR squad in one summer. (2) The S4 Semifinal, where a deliberate Catch-posture + Opening-Rush policy edit inverted a historical 0–18 catch beating into a 29–15 win. (3) The S5→S6 transition, where the roster lock turned a Finalist into a permanent 7th-place team because the rest of the league kept improving and I couldn't.

## 2. THE CLAIMS LEDGER VERDICT
**Promises the game KEPT (with evidence):**
- **Displayed ceilings are real and reached.** Every founder hit *exactly* their displayed ceiling by S3 (70, or Slate 72), then never moved. Growth decayed cleanly +16→+6→+3 and landed on the cap with **zero miss/overshoot**. New signings likewise capped exactly (Noor 75=ceil75, Saito 74=ceil74). **CL-3: fully kept.**
- **Youth-acceleration dev focus** does what it says: every ≤22 player grew +15…+19 in S1. **CL-4: kept emphatically.**
- **Scouting staff focus** = +1 scout slot: verified LIVE (3→4). **CL-7: kept.**
- **Culture staff focus** = +25% interest gains: verified to the exact number (+12% no-Culture vs +15% Culture = 1.25×). **CL-8: kept.**
- **Policy-editor / catch-posture levers** are real and powerful, and the debrief honestly attributes outcomes (Aggressive/Go-for-catches drives catch volume 0→6–7; Defensive/Play-safe drives it to 0; the S4 semi win is traced to the +14 catch swing my adjustment produced).
- **Recruiting interest** is legible and traceable (Noor 52%→84% after visit+contact+promise, then signed uncontested; verified OVR on signing always fell inside the scouted range).

**Promises the game BROKE or muddied:**
- **"Highest ceiling on the sheet" steer is misleading (CL-2).** The Command Center repeatedly flagged Rowan Novak as the develop-target — he grew the **LEAST** of all 10 players (+15), because growth is headroom-driven and he was tied-top OVR. The copy uses "ceiling" for a youth/headroom momentum signal, and even as that it's wrong (two 18-yr-olds had more headroom).
- **Playing time does NOT matter for development (answers the key question).** Bench players with **0 minutes all season** grew *as much or more* than full-minute starters (S1: bench avg +18.25 vs starter +16). The "reps now shape the climb" framing is false — growth is headroom×youth(×dev focus), not minutes.
- **Training staff focus (+0.2 OVR/wk) is unverifiable (CL-6).** No itemized credit appears in any results surface (weekly aftermath or offseason dev beat). A disclosed number with no visible accounting.
- **Elite/Generational scarcity:** across all 8 incoming classes, **ZERO rookies ever projected at 70+ OVR** ("No rookies project at 70+ this year" every single year). I never once saw an Elite or Generational tag on a prospect or a roster. Either they're vanishingly rare (good for scarcity) or the talent ceiling of the whole league is ~75 — which would explain why no team ran away. Scarcity is "real" only in the trivial sense that elite talent appears to not exist at all in this league.
- **Veterans decline & retire believably — for rivals only.** Saw Yuki Rodriguez (2× champ) decline 71→58 and retire; rivals graduate regularly. But MY 18–21 founders never declined across 8 seasons (to age 26–29). Career-length labels read oddly ("3 seasons" for multi-season vets — F-10).

## 3. FINDINGS BY SEVERITY (with repro)
**HIGH**
- **F-8 — Full-roster signing lockout / no cut control.** At 12/12 the offseason Signing Day silently becomes a read-only "Update" (auto-skipped, 0/3 slots), and there is **no release/cut/waive control anywhere in the UI** (verified across Roster, player card, Lineup Editor, Dynasty tabs). Churn is gated entirely behind rival… er, your own retirements — which for a young core never come in time. This **breaks the central dynasty loop**: you get one contention window, then freeze and fall to last while the league develops past you (S4 Final → S6–S8 all 7th). For a rebuild/churn playstyle this is the single biggest problem. *Repro: fill roster to 12/12 → every subsequent Signing Day is skipped; search the UI for any way to release a player — there is none.*

**MEDIUM**
- **F-1 — Self-defeating Counter Read.** Vs an all-in *catching* team the game's own Counter Read recommends Defensive, which forces Catch Posture "Play safe" → **0 catches** → 0–14 sweep. It steers an underdog away from the one mechanic (catch-to-flip) that helps. *Repro: S1W1, accept the Defensive counter-read vs Lunar Syndicate.*
- **F-2 — Weekly settings silently reset to default.** Dev focus resets to "Balanced" and Staff focus resets to "Tactics" at the start of every match week (verified by reading the select values). Only the season-END setting drives offseason growth, so a player who sets a season-long plan in W1 gets Balanced growth unless they re-set it every week. No warning. *Repro: set Youth in W1, advance a week, read the dev-focus select = "BALANCED".*
- **F-4/F-9 — Prospect promise wording & deferred grading.** Promise cards say "…this season" / "reach the playoffs this season" while the prospect is unsigned and *cannot* play this season; grading is silently deferred until the prospect signs, so the literal card text is wrong and an unsigned promise never breaks on schedule (P-3 "We'll contend" survived a missed-playoff season). Makes "never break a promise" trivially gameable by never signing.
- **F-CL2 — Misleading "highest ceiling" develop steer** (see §2): points at the player who develops least.
- **Playing-time-irrelevance** (see §2): arguably a balance finding — bench scrubs develop like starters, undercutting any reason to manage minutes for growth.

**LOW**
- **F-3 — "Elite" overloaded.** Pipeline Tier 5 is labeled "Elite" (recruiting-interest tier) while a T5 prospect can have a known OVR of 24–54; same word "Elite" is also the top *potential* tier. Confusing.
- **F-5 — Bye-week banner off-by-one.** During the bye, the page banner reads "Week 06" while the match card/directive read "Week 05 · Bye Week."
- **F-6 — Front-loaded development.** One Youth offseason closes ~55–65% of headroom; squads rocket then plateau in ~3 years — compresses the dynasty arc (powerful but watch for staleness).
- **F-7 — Training staff-focus credit has no visible accounting** (see CL-6).
- **F-10 — Career-length label** on the Graduation card reads too small ("3 seasons" for established multi-season vets).

## 4. THE GRIND REPORT
- **Where it shined:** S1–S4. The climb from winless dregs to a championship game is genuinely compelling — every offseason Development beat is a payoff you look forward to, the policy-editor playoff adjustments feel smart and *work*, and the catch mechanic gives a real underdog path. The replay is astonishingly detailed (rule-cited play-by-play, 800+ calls/game) and every surface I cross-checked agreed (box ↔ debrief ↔ replay ↔ disclosed game plans).
- **Where it got boring/repetitive:** S5–S8. Once the roster capped at 70 and I couldn't refresh it, every season became identical: same 12 players, same auto-best-six, FF to a 7th-place finish, an offseason ceremony that now runs **10 beats** (Regular Season, Postseason, Awards, Records, **Hall of Fame**, Development [always "0 players changed"], Graduation, Incoming [always "0 at 70+"], Signing [always "skipped"], Schedule) — almost none of it actionable for me. **What I stopped reading:** the weekly pre-match desk, the Awards/Records/HoF beats, and the Incoming-Class beat (always 0 elite). **What I'd automate/cut:** make "Fast-forward to offseason" one click from the recap; collapse non-actionable offseason beats when nothing changed for the player; and stop re-prompting dev/staff focus every week (persist it).
- **The repetitive friction even in good seasons:** the dev-focus and staff-focus weekly reset (F-2) forces a 3-click Dynasty-Office detour every single week to keep a season-long plan, which is pure busywork given only the final week matters.

## 5. VERDICT
**Trustworthy?** On its core promise — development — **yes, emphatically.** Ceilings are real and hit to the integer, dev focuses do what they claim, staff-focus numbers verify to the exact percentage, and the match sim honestly attributes outcomes across perfectly-consistent surfaces. I tried hard to catch the numbers lying to each other and they didn't. That's rare and impressive.

**Interesting enough for a 20th season?** **Not as it stands** — and the single biggest thing standing in the way is **F-8 (no roster turnover mechanism).** A dynasty game lives or dies on the *loop*: build, contend, age, refresh, contend again. This game nails "build" and "contend" but has **no working "refresh"** — you can't cut, you can't sign over a full roster, and a young core never ages out, so a *successful* team gets frozen and is overtaken by a developing league, sliding to permanent last place. My run peaked in S4 and then had four seasons of nothing to do but watch. Fix the turnover loop (a release control + the ability to sign-over-cut at Signing Day, and/or earlier aging-decline so cores actually cycle), and add real elite/generational prospects so there's a talent target worth chasing across generations — then this becomes a game you'd genuinely play to season 20. The bones (development truth, the catch/policy mini-game, the honest sim) are excellent; the dynasty scaffolding around them is what's missing.

---

# SEASON LOG (raw running notes)

## League / mechanics learned (running notes)
- Season = 7-week regular season, top-4 of 7 to playoffs, one bye (mine W5). 7 teams.
- **Offseason growth uses the Dev Focus set at SEASON'S END only** (aftermath text: "Offseason growth follows the dev focus in effect at season's end"). So weekly dev-focus churn is cosmetic; only the last week's setting drives growth. → My "full season-stretch per focus" is fine but the binding moment is the final week.
- Weekly Intent (Balanced/Aggressive/Control/Defensive) auto-maps the 3 tactics cells: Defensive → Approach Patient / Catch "Play safe" / Rush "Hold back", and drops Risk. Tactics cells are individually editable (policy editor).
- Match-Day staff fixed: tactics Mara Ives 74, conditioning Nia Sol 69, medical Dr. Vale Chen 76.
- Replay is rule-cited play-by-play (USA Dodgeball rule numbers; 849 calls in game 1). Replay header discloses both clubs' actual GAME PLANS.

## Setup / Founding

**Club:** Hollow Creek Strays · City: Hollow Creek · Colors: Amber · Save: "Orphanage Run HM3"
**Coach:** Del Marrow — archetype **Former Player / The Lifer** ("faster player development, higher morale, stronger cohesion"). *(Logged as a claim to verify — see ledger CL-1.)*

**Ruleset seen on New Game card:** USA Dodgeball 2026.1 Foam. 6v6, 6 balls (3 each to start). Catch = thrower out + 1 teammate returns. Game point ONLY by wiping all 6. 3:00 No-Blocking line → sudden death. Shot clock if you hold 4/6 balls (attack within 5s). Many games inside a 24-min match window; most game points wins; draws are real.

**Roster-selection screen note:** copy promises "Each prospect shows their current OVR and archetype — the same values their roster row will show after you commit." → cross-check target for Week 1 roster (CL claim about surface consistency).

**Founding draft (the dregs — 10 lowest-rated of 25 offered; best-available left on board were Wren Mendoza 56 & Vale Kerrigan 56):**
| Player | OVR | Archetype (roles) |
|---|---|---|
| Luca Hawthorne | 40 | Possession Specialist (Catcher/Survivor) |
| Luca Slate | 42 | Two-Way Threat (Thrower/Catcher) |
| Ash Kline | 43 | Hit-and-Run (Survivor) |
| Rin Garcia | 44 | Net Specialist (Catcher) |
| Remy Ramirez | 45 | Skirmisher (Thrower/Survivor) |
| Avery Ash | 45 | Hit-and-Run (Survivor) |
| Rin Nakamura | 45 | Hit-and-Run (Survivor) |
| Mika Zane | 46 | Net Specialist (Catcher) |
| Rowan Novak | 46 | Hit-and-Run (Survivor) |
| Imani Petrov | 46 | Two-Way Threat (Thrower/Catcher) |

Avg OVR ≈ 44.2. Interpretation logged: "worst plausible team" = lowest-rated *pool*; took 10 not 6 so I have a bench for the mandated bench-vs-starter dev experiment + manual lineup lever. Throwers are thin (Slate, Ramirez, Petrov) — winning requires wipe-outs, so a thrower shortage is a real handicap, by design.

**Ledger seed — CL-1:** Coach "The Lifer" claims faster development. Will compare my offseason dev deltas against expectation/other focuses across the run.

### Roster baseline — Season 1 Week 1 (ceiling/potential snapshot, the spine of the experiment)
Roster screen: Lineup OVR 44; Archetype Mix Power 2 / Balanced 0 / Tactical 8; Potential Tiers Elite 0, High 0, Mid 1, Low 9, Raw 0; Age avg 19 (all 18–21).

| # | Player | OVR | Age | Tier | Stars | **Ceil** | Key ratings |
|---|---|---|---|---|---|---|---|
| 1 | Mika Zane | 46 | 20 | Low | ●●●○ | 70 | CAT52 DOD51 ACC50 IQ49 STA41 POW38 |
| 2 | Rowan Novak | 46 | 18 | Low | ●●●○ | 70 | STA53 IQ48 DOD46 CAT46 ACC45 POW39 |
| 3 | Imani Petrov | 46 | 20 | Low | ●●●○ | 70 | CAT51 ACC50 POW50 IQ50 STA41 DOD39 |
| 4 | Remy Ramirez | 45 | 20 | Low | ●●●○ | 70 | DOD52 POW50 ACC44 IQ42 STA40 CAT37 |
| 5 | Avery Ash | 45 | 18 | Low | ●●●○ | 70 | IQ54 DOD52 STA49 CAT44 POW41 ACC37 |
| 6 | Rin Nakamura | 45 | 18 | Low | ●●●○ | 70 | STA51 IQ50 ACC49 DOD46 CAT43 POW37 |
| 7 | Rin Garcia | 44 | 20 | Low | ●●●○ | 70 | DOD49 CAT47 POW47 STA42 IQ40 ACC36 |
| 8 | Ash Kline | 43 | 21 | Low | ●●●○ | 70 | DOD52 IQ50 STA46 ACC42 CAT39 POW37 |
| 9 | Luca Slate | 42 | 20 | **Mid** | ●●●○ | **72** | ACC46 POW46 STA41 DOD39 CAT38 IQ37 |
| 10 | Luca Hawthorne | 40 | 19 | Low | ●●●○ | 70 | CAT48 STA41 ACC38 DOD38 IQ37 POW35 |

**Observation A (potential individuation is nearly flat):** 9 of 10 players have an *identical* Ceil of exactly 70 and identical "Low / ●●●○". Only Slate differs (Mid / 72). Stars don't distinguish tier (Slate "Mid" still shows ●●●○). → Watch whether ceilings are genuinely per-player or just tier-bucketed constants. Logged.

**CL-2 (cross-surface, OPEN):** Command Center Week-1 "Watch" note: *"Rowan Novak carries the highest ceiling on the sheet — reps now shape the climb."* But Roster ceiling column: Novak = 70, while **Luca Slate = 72** (highest on the roster, but benched). If "the sheet" = the match lineup card, Novak ties 5 others at 70 (calling him "highest" among a 5-way tie is arbitrary); if "the sheet" = the roster, the claim is simply false (Slate 72 > 70). Either way the headline development steer points at the wrong/ambiguous player. **Severity: Low–Med, ambiguous copy.** Repro: New Game → Command Center W1 watch-line vs Roster ceil column.

### CLAIMS LEDGER — baseline rows
| # | Season | Player | Claim | Source | Outcome | Verdict |
|---|---|---|---|---|---|---|
| CL-1 | S1 | (team) | Coach Lifer → faster development | New Game coach card | TBD | open |
| CL-2 | S1 | Novak | "highest ceiling on the sheet" | CmdCenter watch | Slate=72>Novak=70 on roster | open/contradiction |
| CL-3 | S1 | all 10 | Ceilings 70 (×9) / 72 (Slate) | Roster | **S3: every founder hit EXACTLY their ceiling** (70, or 72 Slate). Decay +16→+6→+3. | **KEPT — ceilings real & reached, 0 miss** |
| CL-4 | S1 | all 10 | Youth accel boosts ≤22 growth | Aftermath | DELIVERED — all 10 (ages 18–21) grew +15…+19 | KEPT (emphatically) |
| CL-5 | S2 | team | Training dept head (Dante Rook 70) = "+6% offseason growth" (passive) | Staff tab | TBD | open |
| CL-6 | S2 | team | **Training Staff Focus** = +0.2 OVR offseason growth/week, cap 8wk (+1.6 max) | Program Settings | testing S2 (Training focus every wk) | open |
| CL-7 | S2 | n/a | Scouting Staff Focus = +1 Scout action (3→4) | Program Settings | **VERIFIED live: slots 3→4 on selecting Scouting** | KEPT |
| CL-8 | S2 | n/a | Culture Staff Focus = Contact/Visit interest gains +25% | Program Settings | **VERIFIED exactly: contact gain +12% (no Culture) vs +15% (Culture) = 1.25×** | KEPT |
| CL-9 | S2 | n/a | Tactics Staff Focus = +18 effective TIQ next match | Program Settings | TBD | open |
| CL-10 | S2 | n/a | Conditioning Staff Focus = stamina drag halved next match | Program Settings | TBD | open |

### S2 summary (0-5-1, no playoffs) + dev beat
- Band vs opponents shrank from S1's −100→−129 to **−38** (W2) — development closed most of the gap in one year. Results: L0–9-ish set losses early, then 2 GP vs champs (W3), 4 GP (W4), **draw 7–7 (W7)** — first non-loss. Still 0 wins → missed playoffs.
- **S2 Development (Youth yr2):** Noor 57→69(+12), Saito 60→69(+9), Hawthorne 59→67(+8), Slate 61→69(+8), Ramirez/Novak 61→68(+7), Kline/Garcia/A.Ash/Nakamura 61→67(+6), Zane/Petrov 62→68(+6). Growth smaller than S1 (headroom shrinking); same headroom-driven pattern. Squad now 67–69 OVR.
- **CL-6 (Training staff focus +0.2/wk) UNCONFIRMED:** no itemized training credit appears in the weekly aftermath OR the offseason dev beat. With only ~2 Training weeks this season (+0.4 total, below visible rounding) I can't isolate it. **F-7 (disclosure gap):** a disclosed numeric staff effect (+0.2 OVR/wk, cap 8) has no visible accounting anywhere in results — if it works, it's invisible; if it doesn't, you'd never know. Plan: dedicate a near-ceiling season to Training-every-week to isolate it.
- Champion S2 = **Northwood Ironclads** (≠ S1 Lunar) — league title rotates, not static/solved (good).

### S4 offseason — roster fully plateaued
- Dev beat: only **2 of 12 changed** — Noor 72→75 (=ceil 75), Saito 73→74 (=ceil 74); all 10 founders at ceiling grew **0**. **Entire roster now sits exactly at its displayed ceilings** (Noor 75, Saito 74, Slate 72, rest 70; avg ~71). CL-3 fully closed. No growth path remains without higher-ceiling players → blocked by F-8. **This is the dynasty's wall:** a maxed-70 roster reaches the Final but loses to a deeper #1 seed, and the player has no legal way to upgrade (can't sign at 12/12, can't cut). Goal (b) "substantially different second core" is effectively unreachable barring a cascade of retirements.

### S6 — the relative-decline cliff
- **Finished 7th of 7 — missed playoffs**, two seasons after reaching the Final. S6 dev beat: **0 players changed OVR** (my core is frozen at ceiling 70-75, not yet aging-declining at 24-27). So the collapse is **100% relative**: the league's younger cores developed past my hard-capped, un-refreshable roster. **F-8's deepest consequence:** "development is your way out" buys exactly ONE contention window (S4 here); without the ability to sign/cut, you can't sustain it and you fall back to last while standing still. This is the single most important dynasty finding of the run.

### S5 — title chase + aging observations
- S5: made playoffs again; **Semifinal vs Granite Specters = LOST 7–12** (re-applied Hold-back catch counter; not enough vs the dominant #1). Granite is a clear wall my capped roster can't clear.
- **Aging/decline (answers "do veterans decline & retire believably?"):** S5 Graduation beat retired **Yuki Rodriguez (former 2× champion, declined 71→58 OVR)**, Dray Slate (56), Tyne Hassan (51) — all rival players. So veterans DO visibly decline then retire. BUT career lengths display as **"3 seasons"** which reads oddly short for a sports career (possible mislabel of a longer tenure, or genuinely compressed careers). **None of my founders retired** — they're 23-26, still pinned at ceiling 70 (no decline yet at 5 seasons in). So aging is real for rivals; my own core's decline/retirement window hasn't opened by S5. **F-10 (Low): "N seasons" career counter on the Graduation card looks too small for the players shown (e.g., a multi-season league veteran listed at "3 seasons").** Watch my own core for decline in S6+.

### ★ FAST-FORWARD AUDIT (S3) — required lever #1
- **FF modal discloses (good transparency):** "auto-decides using your last saved weekly plan (intent, tactics, department orders) and **fields the canonical best-six lineup**. Pre-match desk and weekly ceremony not shown." 3 stop points: *to next bye*, *to pre-playoffs*, *to the offseason*.
- **AUDIT finding A (lineup override):** FF fields the "canonical best-six" — i.e. it **ignores a saved manual lineup**. My manually-fielded Noor (slot 6) would be replaced by the auto-best-six. Any "play player X" obligation can silently lapse under FF. (Here Noor had already kept P-1, so no live break — but the risk is real. Repro: save a sub-optimal manual starter, FF, check the played six.)
- **AUDIT finding B (dev focus not carried):** the carried plan is "intent, tactics, dept orders" — **dev focus is omitted**, so FF runs each week on the reset default (Balanced) and the season ends on Balanced regardless of what you'd set. (I set Strength at W2 then FF'd; confirming the S3 dev beat ran on Balanced below.) Combined with F-2 (weekly reset), **FF makes an intentional season-long dev focus impossible** unless you hand-play the final week.
- **AUDIT finding C (stop point vs missing playoffs):** chose "pre-playoffs" but, finishing **5th/7**, there were no playoff games for me so it rolled to the offseason. "Pre-playoffs" only leaves you a resume point if you actually qualify.
- **Result sanity:** S3 band was −6 OVR (even); FF produced a believable **5th-of-7** finish (up from 7th in S1–S2). Development climbing: 7th → 7th → 5th.
- **AUDIT finding B confirmed (masked):** S3 dev growth was +2…+4 and every founder landed exactly on ceiling. Because everyone capped, I can't distinguish Strength-vs-Balanced from the outcome — but the cap masks it, consistent with FF having run on default Balanced. Net: **once players reach ceiling, dev focus is irrelevant** (cap dominates). The dev-focus *choice* only matters while there's headroom (early seasons).
- **★ Dynasty inflection:** S3 offseason = founders ALL plateaued at 70 (Slate 72). To keep climbing (opp key threats are 71+), I must add higher-ceiling players — the "second core" is now *mechanically required*, not optional. But **F-8 blocks it**: roster is 12/12 and I found **no release/cut control** on the player card. Churn appears gated behind retirement only. This is the single biggest dynasty obstacle so far.

### ★ S4 PLAYOFFS — the breakthrough + policy-editor lever
- Development arc: finish 7th → 7th → 5th → **made playoffs (#3-ish seed, regular season 3-2-1)** in S4. From 0-7 dregs to playoff team in 4 seasons, purely via development.
- **Policy editor (required lever) used for a playoff-specific adjustment:** Semifinal vs Lunar Syndicate (key threat Dex Beck, 80 OVR catcher; tape shows all-in opening rush). Editor exposes radios: Approach / Target focus / Catch posture / Opening-Rush Commit / Rush Target, with a disclosed note ("an all-in rush's rushers catch worse on the counter"). I set **Commit: All-in → Hold back** (+ kept Catch "Go for catches") to punish their all-in rush with catches.
- **RESULT: WON 12–7. Catches 29–15 in MY favor (+14 swing)** — a complete inversion of S1's 0–18 sweep loss to the same club. The adjustment traced cleanly to catch dominance. **The policy editor + catch-posture levers are real and powerful, and the game honestly attributes the outcome.**
- **FINAL vs Granite Specters (#1 seed, −14): LOST 7–13 — runner-up.** Re-applied the Hold-back/Go-for-catches policy (it had reset to All-in for the new week — confirms weekly policy reset even in playoffs). Not enough vs the league's best with a ceiling-capped 70 roster. **S4 = runner-up; title (goal a) still pending.** The 70-cap roster can reach the Final but needs higher-ceiling blood to win it — which F-8 blocks.

**Staff Focus mechanic (found in Dynasty Office → Program Settings):** a *weekly* pick, "staff concentrates on one room this week," 5 options each with a disclosed number (logged CL-6…CL-10). Distinct from the Training *dept-head* passive (+6% dev, CL-5). This is the "each Staff Focus option ×2" lever. **S2 plan:** Training staff focus every week + Youth dev → measure offseason growth & look for an itemized training-credit bonus (CL-6).

### ★ S1→S2 OFFSEASON DEVELOPMENT BEAT (Youth acceleration; coach = Lifer) — centerpiece data
Format: OVR a→b (+overall). All 10 players, sorted by growth:
| Player | Role S1 | Minutes | OVR a→b | ΔOVR |
|---|---|---|---|---|
| Luca Hawthorne | **bench** | 0 | 40→59 | **+19** |
| Luca Slate | **bench** | 0 | 42→61 | **+19** |
| Ash Kline | **bench** | 0 | 43→61 | **+18** |
| Rin Garcia | **bench** | 0 | 44→61 | **+17** |
| Remy Ramirez | starter | full | 45→61 | +16 |
| Avery Ash | starter | full | 45→61 | +16 |
| Rin Nakamura | starter | full | 45→61 | +16 |
| Mika Zane | starter | full | 46→62 | +16 |
| Imani Petrov | starter | full | 46→62 | +16 |
| Rowan Novak | starter | full | 46→61 | **+15 (LEAST)** |

**ANSWER — "Does playing time matter for development?" → NO (S1 evidence).** The 4 bench players (literally 0 match minutes all season) grew **avg +18.25**; the 6 starters (full minutes) grew **avg +15.8**. Growth is **inverse to starting OVR (headroom-driven) + youth**, not minutes. Confound noted: my bench = my 4 lowest OVR, so headroom and bench-status coincide; a clean equal-OVR start-vs-bench test is needed (planned for S2+). But directionally, zero-minute players developed *at least as well* as full-minute players — minutes are not a positive driver.

**CL-2 RESOLVED — misleading steer.** The Command Center "Watch: Rowan Novak carries the highest ceiling on the sheet — reps now shape the climb" pointed at the player who **grew the least (+15)**. Novak's higher current OVR (46, tied-top) meant least headroom → least growth. The "reps shape the climb" framing also implies playing time matters, which the data contradicts. **Severity Med** (it actively misdirects a new manager's development attention).

**Development dynamics finding (F-6, design observation):** growth is **explosive and front-loaded** — one Youth-accel offseason closed ~55–65% of every player's headroom (40→59, 46→61). At this rate the dregs become a ~62-OVR squad immediately and will near the 70 ceiling within ~2 offseasons. Powerful delivery of "development is your way out," but watch for a fast plateau / compressed dynasty arc. Ceilings not shown numerically on this beat (only a "Ceiling" column label + OVR a→b); will re-read on Roster.
- Aging/Conditioning/Roster-Stabilization applied at this beat (players age +1).

### S1 Offseason ceremony (8 beats) + Signing Day
Beats: 1 Final table (7th/7), 2 Champion (Lunar Syndicate), 3 Awards (MVP Dray Slate 68 OVR, Harbor), 4 Records, 5 **Development** (above), 6 Incoming Class (**0 rookies project 70+** — weak class), 7 Signing Day, 8 Schedule Reveal (S2=2027, 6 matches Wk2–7).
- **Signings (churn satisfied):** Noor Perez (Skirmisher, scouted 46–76 → **verified OVR 57**, age 21) and Callum Saito (Two-Way, 41–71 → **verified 60**, age 19). Roster now 12/12. Verified-OVR-on-signing matches the scouted range honestly (57∈46–76, 60∈41–71).
- **Recruiting trace works:** Noor Perez interest 52%→**84%** after my visit+contact+promise; signed uncontested. Good, legible.
- **P-1 promise:** NO promise-grading beat in the ceremony. "Promise at stake" shown at Signing Day; signing Noor kept it OPEN into S2. So F-4's "impossible" concern softens IF you sign the prospect — the promise re-anchors and "this season" means her first season (S2). **Refined F-4:** the bug is the *wording* ("≥6 matches this season" shown while she's unsigned and can't play this season) + no in-ceremony confirmation; not a hard break if you sign. Will confirm P-1 still 1/3 open at S2 start and grade it at S2 end (must play Noor ≥6 of 6 matches).
- **Roster cap = 12.** S2 core: developed founders (59–62) + Perez 57 + Saito 60.

**CL-2 refinement:** Novak card = Potential **Low**, Ceiling 70, Headroom **+24**, Growth "▲ Growing", badge **"High Upside"** (tooltip: "24 OVR of headroom remaining at age 18 — genuine develop-target upside"). So the CC "highest ceiling" steer reads the *develop-target* signal (headroom×youth), not numeric ceiling. But it's still imprecise: Avery Ash (18, +25 headroom) and Rin Nakamura (18, +25) out-headroom Novak (+24) at the same age — so Novak is not strictly the best develop-target either. **Verdict so far: loose copy ("ceiling" used for a growth-momentum signal), not a data corruption. Severity Low.** Player card also exposes 2 hidden ratings (Throw Selection IQ, Catch Courage) not in the 6-stat row.

## SEASON 1 — Hollow Creek Strays (founding core)

### S1 W1 — @ Lunar Syndicate — **L 0–14** (sweep)
- **Decision:** heeded Counter Read → Intent **Defensive** (Approach Patient / Catch Play-safe / Rush Hold-back). Dev focus **Youth acceleration**. Auto-six fielded (Zane, Novak, Petrov, Ramirez, A.Ash, Nakamura). Scouted (5/5 playbook reads: they're Aggressive/all-in/target-stars/opportunistic-catch).
- **Expectation:** loss as −129 OVR underdog, but defense keeps it close.
- **Actual:** 0–14 sweep (14 games, each lost on a wipe-out). Primary Factor "Catch disparity": **catches 0–18**. My "Play safe" catch posture → literally **0 catch attempts converted**. Their Yuki Rodriguez 7C, Sasha Fern 34K. My best Mika Zane 13K / Imp 8.
- **Trace quality:** GOOD — debrief blamed catches, replay shows every catch is theirs, replay GAME PLANS disclosure = my exact locked plan. Debrief↔replay↔box all agree (14–0).
- **Finding F-1 (Balance/Advice, Med):** The game's own Counter Read recommended Defensive vs an all-in *catching* team; Defensive forces Catch Posture "Play safe" which yielded **0 catches** and a 0–14 sweep. Against a team that wins via catches, "play safe" = surrender the only mechanic (catch-to-flip) that helps an underdog. The advice is self-defeating here. (Caveat: −129 OVR gap means a blowout regardless; severity tempered. But 0/anything on catches from one posture flip is a very strong lever.) Repro: S1W1, take Counter Read's Defensive vs Lunar Syndicate.
- **CL-4 (dev claim, OPEN):** Aftermath: *"Youth acceleration boosts offseason growth for players 22 and under (and slows it for older players)."* All my players ≤21 → all should benefit. Verify at S1→S2 offseason deltas.
- Prospect sighting: **River Dubois** (fit 65, interest 37%) flagged in "next best improvement" — a courtable prospect already in the pipeline.

### S1 W2 — @ Aurora Sentinels — **L 0–15** (sweep)
- **Decision:** Intent **Aggressive** (to test the catch lever after W1's 0 catches). Auto-six again. Scouted (their playbook identical to Lunar's: Aggressive/all-in/opportunistic/target-stars/center — note: pre-tape playbook leans look uniform across opponents).
- **Catch-lever result:** catches **6–22** (vs W1's 0–18). Aggressive/opportunistic catch posture → my catch attempts rose 0→6. **The Catch Posture lever demonstrably controls catch volume** (good, traceable). Loss still a sweep on −119 OVR gap. Ayo Smirnov 33K/8C/Imp191; my best Mika Zane 10K/2C/Imp6.
- **F-2 (UX trap, Med):** Dev focus **silently reset to "Balanced"** in W2 — I set Youth acceleration in W1 and never touched it. Aftermath: "Balanced development is this week's development focus." Since offseason growth = the focus *at season's end*, a player who sets a season-long dev intent in W1 will unknowingly end on Balanced unless they re-set it every week (esp. the final week). The control does not persist and gives no warning. Repro: set Youth W1 → advance to W2 → dev focus shows/uses Balanced. **Mitigation for my run: I will re-set the season's target dev focus every week, and verify it on the final regular-season week.**
- Standings now live (other clubs: Harbor Tidebreakers, Granite Specters, Northwood Ironclads moving in the table).

### S1 W3 — @ Granite Specters — **L 0–14** (sweep)
- **Decision:** Intent **Control** (Approach Mixed/target Ball-holders, Catch Opportunistic). Re-set dev focus Youth acceleration (verified it had reset to Balanced — **F-2 confirmed via the select's value="BALANCED"**, true reset not mislabel).
- **Catch data, hypothesis weakened:** catches **0–19**, despite Control mapping catch to "Opportunistic." So 3-week catch series is 0 / 6 / 0 → catch volume looks dominated by the −100+ OVR gap and noise, NOT cleanly by posture. Downgrading the W2 "lever works" read to *uncertain*; need controlled data later.
- 0-3, rank #7 (last).

### Dynasty Office tour (S1 W4 prep) — recruiting + staff systems
- **Program Credibility:** Tier D · Regional, **45/100**. Rises with wins + youth development + prestige. Factors listed: 0W-3L; 2 weeks youth-dev; prestige 0.
- **Weekly recruiting Action Slots (reset weekly):** Scout 3 / Contact 5 / Visit 1. ("Scout narrows the OVR range; Contact + Visit build interest.") → folding prospect-scouting into the weekly loop.
- **Staff Room — 6 dept heads:** Conditioning Nia Sol 69, Culture Tessa Hart 68, Medical Dr. Vale Chen 76, Scouting Owen Pike 73, Tactics Mara Ives 74, **Training Dante Rook 70 with a "+6% dev" badge**.
  - **CL-5 (staff number, OPEN):** Training staff "+6% dev". Verify this shows up in offseason growth and that toggling/Training-focus seasons beat non-Training seasons.
- **Promises:** 0/3 open; checked at season's end; types = Early playing time / Development priority / We'll contend.
- **Prospect board (8), sorted by fit:** Noor Perez (Skirmisher, T5-Elite, fit66, int52%, OVR46–76), River Dubois (Poss-Spec, T2, fit64, int37%, 34–84 est), Callum Saito (Two-Way, T5, fit61, int52%, 41–71), Mara Hassan (Ball Hawk, T1, fit61, int37%), Mara Parr (Skirm, T3, fit48), Sloane Park (Two-Way, T2, fit47), Rin Zane (Two-Way, **T5-Elite but OVR 24–54**), Niko Hansen (Iron Anchor, T3, fit43).
- **F-3 (naming, Low):** Pipeline **Tier 5 "Elite"** labels *interest pipeline*, not talent — Rin Zane is "Elite" pipeline yet known OVR 24–54. A new player reasonably reads "Elite" as a talent tier. Mismatch with the Roster "Potential: Elite" tier wording (same word, different axis).
