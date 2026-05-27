Wave 0 — Foundations (1 day)
0.1 Vocab unify

Files: frontend/src/components/match-week/command-center/PreSimDashboard.tsx:15-23, backend CoachPolicy keys.
Pick one set: Balanced | Aggressive | Control | Defensive. Map at API boundary only.
Accept: grep shows no UI string "Win Now" / "Preserve Health" / "Prepare For Playoffs".
0.2 Platform key hint

File: PreSimDashboard.tsx:698.
Detect navigator.platform. Render "Ctrl+Enter" on win.
Wire actual handler (currently no listener). Accept: keypress locks/sims.
0.3 Kill dead button

File: PreSimDashboard.tsx:723-727 League Table button → route to standings, or remove.
Accept: no onClick={() => undefined} in repo.
Wave 1 — Replay readability (CRITICAL, ~3 days)
1.1 Persistent score header

File: frontend/src/components/MatchReplay.tsx (DarkCourt wrapper).
Sticky strip top of court: HOME name | score · set · clock · AWAY name | score. Drives off existing replay event stream.
Accept: at any pause, viewer reads current score in <1s. Tested on 320px width.
1.2 Action captions

File: MatchReplay.tsx:51-67 resolution helpers + new caption component.
On each throw: floating chip near target — "F.LASTNAME caught by R.GRAVES" / "OUT — hit". Persist 800ms.
Accept: colorblind sim (grayscale) still readable.
1.3 Late-game banner re-use

File: frontend/src/components/match-week/aftermath/LateGameBanner.tsx.
Drop into replay when score gap ≤1 in last set. Reuse, don't rebuild.
Accept: triggers on close games only.
Wave 2 — Why-lost verdict (CRITICAL, ~3 days)
2.1 Verdict payload

Backend: src/dodgeball_sim/voice_verdict.py already exists. Extend to emit causal tags: intent_mismatch | fatigue_burn | foul_storm | role_counter | outclassed | upset_win.
Accept: every MatchResult carries ≥1 tag w/ evidence ints (foul count, stamina min, threat OVR delta).
2.2 Verdict panel

File: frontend/src/components/match-week/aftermath/ — new VerdictPanel.tsx, slot above FalloutGrid.
Renders top tag as sentence + remedy ("Try Control vs Tactical next time").
Accept: copy maps 1:1 to backend tags. No "vibes" lines.
2.3 Tag → next-week nudge

File: PreSimDashboard.tsx scoutRead logic (~262-271).
If last loss tagged intent_mismatch w/ same opponent archetype, surface in Counter Read.
Accept: replays of prior L visible as evidence in pre-sim.
Wave 3 — Command Center cleanup (HIGH, ~4 days)
3.1 De-duplicate Plan vs Scout panels

File: PreSimDashboard.tsx:481-490 and :572-587.
Plan panel: your posture + projected effect deltas only.
Scout panel: opponent threat + counter recommendation only.
Remove repeated cc-align-callout.
Accept: no string appears in both panels.
3.2 Real conflict matrix

File: PreSimDashboard.tsx:247-251.
Replace single hasApproachConflict w/ table: rows = intents, cols = threat roles, cells = match %.
Show match score + top reason in callout.
Accept: every intent×role combo produces non-default message.
3.3 Projected-effect chips on policy cells

File: PreSimDashboard.tsx:491-519 (cc-policy grid).
Each cell shows 1-2 deltas: "+12% throws · +18% foul risk".
Source: backend tactics module returns previewed multipliers.
Accept: changing dev focus updates body text live.
3.4 Real readiness gates

File: PreSimDashboard.tsx:228-234.
Replace scout: ready: true constant. Add gates: injury reviewed, sub set, rival-week scouted, fatigue triage done.
Accept: a fresh week starts at ≤3/5 most weeks.
3.5 Hero hierarchy

File: PreSimDashboard.tsx:357-382 identity strip.
Demote Program+Season to one crumb line above hero. Promote Week+Opponent to hero only.
Accept: hero passes 5-second "where am I, who's next" test.
Wave 4 — Mobile survival (CRITICAL, ~2 days)
4.1 Stack panels <900px

File: frontend/src/styles/*.css (cc-body grid rules — find via grep cc-body).
Vertical stack: Plan → Scout → Lock. Sim button sticky bottom.
Accept: 360px viewport, no horizontal scroll, no overlap.
4.2 Identity strip collapse

6 cells → 3 cells (Week · Opponent · Status). Rest behind tap.
Accept: 360px, no wrap.
4.3 Kill title= for truncation

Files: PreSimDashboard.tsx:360, threat card, hero stats.
Replace w/ ellipsis + tap-to-expand modal/popover.
Accept: long club names readable on touch.
4.4 Readiness chips inline detail

File: PreSimDashboard.tsx:618-628.
2nd line under chip showing detail (currently in title).
Accept: mobile user sees gate reason w/o hover.
Wave 5 — Threat + court honesty (HIGH, ~2 days)
5.1 Threat card history line

File: PreSimDashboard.tsx:452-459.
Add "Last vs you: 4 elim, 0 caught · L 3-5".
Source: backend match history filtered by opponent.
Accept: shows "—" only on first meeting, never on rematch.
5.2 MiniCourt — drive from real lineup

File: PreSimDashboard.tsx:62-146.
Replace fixed HOME_POS/AWAY_POS with positions from lineup formation. If schematic kept, relabel "Schematic only".
Accept: swapping lineup order changes court.
5.3 Symmetric advantage state

File: PreSimDashboard.tsx:452 (is-disadvantage class).
Add is-advantage cyan variant when your top OVR > threat OVR.
Accept: both states visually distinct.
Wave 6 — Roster decision clarity (MED, ~2 days)
6.1 Style bucket vs role reconciliation

File: frontend/src/components/Roster.tsx:50-58 (styleBucket).
Either align by recomputing role from same source, or show both badges side by side with explanation.
Accept: tactics math + UI badge always agree.
6.2 Potential tier as dots

File: Roster.tsx:29-35 (potentialGlyph).
Replace glyph with 1-5 filled dot scale plus tier text.
Accept: tier readable w/o legend.
Wave 7 — Standings stakes (HIGH, ~2 days)
7.1 Seed delta inline

File: frontend/src/components/standings/* + sidebar.
For user team: "Win → seed #3 (vs Riverside). Loss → seed #6 (vs Storm)."
Source: backend playoff projector.
Accept: every week renders both branches.
7.2 Magic number

Same area. Show clinch/elim numbers when applicable.
Accept: appears wk 12+ only when math meaningful.
Wave 8 — Ceremony pacing + dynasty payoff (MED, ~3 days)
8.1 Ceremony stagger

File: frontend/src/components/ceremonies/CeremonyShell.tsx + Ceremonies.tsx.
Per stage: reveal name → click → reveal stats/quote. Add 600ms idle copy between beats.
Accept: awards night ≥3 click-reveals, not one scroll.
8.2 Per-award beats

File: Ceremonies.tsx:38- AwardsNight.
Split supporting awards into own ceremony beats, not one render.
Accept: each award has its own stage with reveal.
8.3 Dynasty narrative hooks

File: frontend/src/components/dynasty/history/*.
Compute & surface: longest active streak, records set this season, alumni-now-in-HOF.
Accept: history tab leads w/ a narrative line, not a grid.
Wave 9 — Polish (LOW, ~1 day)
9.1 Last-meeting formatter: parse details.last_meeting → "L 3-5 · Wk 7 last season" w/ color.
9.2 Dev focus → lift out of policy cell into header row.
9.3 "Auto-saved" → timestamp + last action.
9.4 League Wire button → real route.
Sequencing
Wave 0 → (Wave 1 || Wave 4) → Wave 2 → Wave 3 → Wave 5 → Wave 6 → Wave 7 → Wave 8 → Wave 9
Wave 1 and Wave 4 parallel — different files. Wave 2 needs backend change so start backend day 1 of its slot.

Verification per wave
Each wave done when:

New copy + states screenshot at 360/768/1280px.
Replay/match e2e: simulate 5-week season, verify verdict + readiness gates fire honestly.
Mobile manual pass on real phone or devtools 360px.
Total est: ~22 dev days serial, ~14 days w/ parallelization.