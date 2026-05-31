# Playtest Synthesis — Seed for Multi-Phase Planning (2026-05-29)

## What this document is (and is not)

This is a **synthesis of findings**, assembled to *begin* a planning session — it is **not** a plan and **not** an implementation spec. The next prompt should read this, then run a planning phase (likely multi-phase, since several items are screen redesigns rather than point fixes). Do **not** treat any grouping or ordering below as a committed sequence; they are clustering hints only.

Sources combined here:
- Agent browser playtest of a fresh "Build from Scratch" club across Seasons 1–3 (Granite Boulders).
- Agent code/DB verification of disputed items.
- Maurice's raw observations (marked **[Owner]**).

## Verification legend

- ✅ **Verified** — reproduced directly (UI + code/DB where relevant).
- 🟡 **Reported** — observed once or owner-reported; not yet independently reproduced/root-caused.
- ⚙️ **Design question** — needs a product decision before it can be specced.

---

## 0. Build / workflow gotcha (read first)

The dev server can run **stale code** even after backend fixes land. During this session `preview_start` silently **reused a lingering server process** (old roster-cap value) across stop/start cycles, which produced two *false* "regression" findings. Before trusting any backend behavior in a playtest: confirm the bound process is fresh (`Get-NetTCPConnection -LocalPort 8000`, `Stop-Process` the old PID, restart). This matters for planning because **verification steps in any future plan must guard against stale-server false negatives.**

---

## 1. Confirmed WORKING — do not re-open in planning

These were suspected broken earlier but verified correct on current code. Planning should not spend effort here except where *legibility* is called out separately (see §3).

- ✅ **Development growth is potential-scaled.** Attribute deltas differ by tier (Elite Ezra +3 DOD/+3 IQ per season; Low Mika ~+1). Across S2→S3 only 7/10 players gained composite OVR — near-ceiling players plateaued (headroom model working). *Note: the composite-OVR "+1" hides real attribute gains — that is a presentation gap, not a logic gap (see §3).*
- ✅ **Recruiting signs players.** Drove a target 51%→100% interest over 2 weeks; on a fresh server the Recruitment Desk picker renders ("3 signings remain, Roster 10/12") and signing moved roster 10→11/12. The earlier "never signs" was the stale-server artifact above.
- ✅ **Tactics/catch-posture persist across weeks** (earlier "resets weekly" was a harness click artifact).
- ✅ **Strengths to preserve:** Match Replay court+event-log+possession timeline; Roster Lab ratings/potential/role legibility; league teams have visible strategic identities; offseason ceremony scaffolding (champion bracket, stat-driven awards).

---

## 2. Open issues — CORRECTNESS / LOGIC (likely smaller, but high trust-impact)

These break the "decisions are rewarded / the sim is fair" promise. Mostly logic, not redesign.

| # | Issue | Source | Notes for planning |
|---|-------|--------|--------------------|
| 2.1 | **Auto-lineup benches the best players, every season.** Created club fields the weakest 6; top players (incl. best catcher) sit. Reset recurs each new season, silently undoing a manual fix. | ✅ Agent (S1+S2) | Highest trust-impact item. Fix auto-selection to best-by-role/OVR; consider persisting the user's manual lineup across seasons. Reproduced cause→effect: bad lineup = shutout losses; fixed lineup = 6-0/4-0 wins. |
| 2.2 | **"+NNN NET OVR (FAVORITE)" tag is false.** Shown as heavy favorite every week while finishing dead last (0-4, survivor diff -11). Likely sums full 10-man roster vs opponent rather than fielded 6 v 6. | ✅ Agent | Pairs with 2.1 — the edge calc should use the actual fielded lineup. ⚙️ also decide what the tag should *mean*. |
| 2.3 | **Readiness permanently 5/5.** Every week starts at 5/5 before the player does anything, so the gate is meaningless. | 🟡 [Owner] | Decide what "readiness" should represent (gates that start unmet and are earned by scouting/planning/health?). ⚙️ semantics decision, then logic. |
| 2.4 | **Operational Plan is a single button + all-green.** Only one actionable control; all 4 indicators show green even when the plan is flagged "misaligned." | 🟡 [Owner] | Contradictory signal (green while misaligned). Overlaps with Policy Editor redesign (§4) and readiness (2.3). |
| 2.5 | **Match Replay scores by survivors, not match score.** Believed implemented; not present. | 🟡 [Owner] | Confirm intended scoring model; reconcile replay header + aftermath with official match scoring (see docs/reviews/2026-05-27-official-match-scoring-integration.md). |
| 2.6 | **Float leak in Next Best Improvement** ("51.0 OVR"). | 🟡 [Owner] | Small: format/round OVR to int at the boundary. Check for sibling float/raw-key leaks (prior note: `hawk_dodger` raw key leaked in Season Preview / Next Best Improvement). |
| 2.7 | **New-save name collision fails Commit silently** — only tiny red text on Step 3, though the name is entered on Step 1. | ✅ Agent | Small onboarding fix: validate uniqueness on Step 1; block Commit with a visible banner. |

---

## 3. Open issues — GROWTH LEGIBILITY (logic is fine; presentation is the gap)

Distinct theme worth its own planning lens: **player growth genuinely happens but is invisible.** Owner: *"Overall still not showing growth changes."* This is real — but the cause is presentation, not the engine.

- Player Card shows potential as a **tier word only** ("Elite"), no numeric ceiling / no projected growth.
- Offseason Development beat shows **composite +1 OVR**, hiding the differentiated attribute gains underneath.
- Net effect: a player cannot *see* that their Elite prospect is developing faster than a Low one, so dev decisions feel decorative even though they aren't.

Planning implication: a "make growth visible" pass spanning Player Card + Development beat + possibly Roster Lab (show ceiling, attribute deltas, season-over-season trend).

---

## 4. Open issues — SCREEN REDESIGNS (likely larger; the multi-phase driver)

These are **[Owner]**-reported "underdesigned / needs audit" screens. They are why this is a multi-phase effort. Each needs a design pass, not just a tweak.

- **4.1 Class Report** — underdesigned; currently a centered text blob ("Class report" paragraph). 🟡
- **4.2 Season Preview** — underdesigned. 🟡 (Agent note: content is *informative* — teaches goal/bye/watch-area — but visually plain.)
- **4.3 Bye Week aftermath** — underdesigned. 🟡
- **4.4 Match Aftermath audit** — streamline information; some cards feel important, others "silent." Needs an information-hierarchy audit (what's primary vs secondary). 🟡 Agent corroboration: the **PRIMARY FACTOR labeling mismatches margin** — 0-4 losses and 6-0 wins both labeled "inconclusive/close/variance." Fold this into the aftermath audit.
- **4.5 Rookie Class Preview** — underdesigned. 🟡
- **4.6 War Room** — wants more flair, especially for playoffs (it *is* the playoffs). 🟡
- **4.7 Policy Editor** — visual upgrade; each option is currently shown **three times** per category (pill name + right-of-box value + description). De-duplicate and restyle. 🟡 Overlaps with Operational Plan (2.4).
- **4.8 Records Ratified audit** — see §5 (has a design question attached).

---

## 5. Open issues — RECORDS RATIFIED (audit + design question)

- **5.1 Audit (🟡 [Owner]):** Too many low-impact records; broken records should *feel* impactful. Also unclear whether the screen shows **your club's** players or **all clubs** — needs an explicit scope/filter.
- **5.2 ⚙️ Design question — records for a brand-new club:** With a fresh club there are no prior records to break. **Owner's proposed answer:** seed an initial record set *dynamically from your own club's history* — the retiree from your club with the highest value in each category becomes that category's leader, giving a self-generated baseline that future players can chase. Planning should treat this as the working proposal to design against (confirm + spec).

---

## 6. Open issues — WORKFLOW / FEATURE

- **6.1 Multi-week simulation (🟡 [Owner], strong value).** Currently every week requires Lock + Simulate clicks. Add fast-forward controls so playtesting and focused iteration are dramatically faster. Minimum proposed targets: **Sim to Playoffs, Sim to Offseason, Sim to Next Season.** Direct agent corroboration: this single feature would have saved a large share of this session's clicks; it's a force-multiplier for testing every other item above.

---

## 7. Cross-cutting themes (for the planner to weigh)

1. **Two distinct workstreams are tangled:** (a) correctness/logic fixes (§2) and (b) screen redesigns (§4). They can largely proceed independently, but a few items straddle both — Operational Plan (2.4), Policy Editor (4.7), and the Match Aftermath audit (4.4 + PRIMARY FACTOR labeling). Decide whether to fix logic first then restyle, or co-design.
2. **The "fielded lineup" is a root dependency.** 2.1 (auto-lineup) and 2.2 (favorite tag) share a root: the game reasons about the roster, not the actual starting 6. Resolving the lineup model unblocks both and likely improves result fairness broadly.
3. **Legibility vs mechanics.** Several "feels broken" items (growth §3, readiness 2.3, operational plan 2.4) are really *the UI not surfacing real state*. Worth a dedicated "make the simulation legible" lens so engine-correct systems stop reading as decorative.
4. **Decisions needed before specs** (⚙️): readiness semantics (2.3), favorite-tag meaning (2.2), replay scoring model (2.5), new-club records seeding (5.2). These gate their respective designs and should be answered early in planning.

## 8. Rough size signal (planning triage aid only — not a sequence)

- **Small / contained:** 2.6 float, 2.7 save-name, 4.7 policy de-dup (visual), parts of 4.4 (labeling).
- **Medium / logic:** 2.1 auto-lineup, 2.2 favorite calc, 2.3 readiness, 2.4 operational plan, 2.5 replay scoring, §3 growth-legibility surfacing.
- **Large / design-led:** 4.1–4.6 redesigns, 4.8/5 records audit + seeding, 6.1 multi-week sim.

---

*Prepared as the input to a planning session. Next step: planning, not implementation.*
