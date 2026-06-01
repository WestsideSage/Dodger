# Teardown Report — Frontend Performance and Responsiveness

## Verdict
Frontend responsiveness looks **uneven but not broadly broken**. Normal roster, standings, and Command Center surfaces are likely fine on desktop-scale data, and `npm run lint` / `npm run build` pass. The riskiest areas are replay playback and history-style long lists, where the frontend renders full event/log payloads and recomputes state during interaction. Pare MCP was not available in this session, so I used normal local inspection.

## Highest-signal findings

### 1. Full replay playback can become the main interaction bottleneck
- Severity: High
- Evidence: Backend returns full `events` and `proof_events` in [replay_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/replay_service.py:287>). `MatchReplay` renders full `proof_events` into the possession strip and event log in [MatchReplay.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:646>) and [MatchReplay.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:677>). `EventLog` maps every event row in [MatchReplay.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:430>). Each playback tick rebuilds eliminated state by scanning from event `0` through `eventIndex` in [MatchReplay.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:550>).
- Why it matters: autoplay advances every 1200ms, so long official matches can turn into repeated O(n) state reconstruction plus a full active-row update across the whole log.
- Reproduction / inspection path: Open a long full replay, start playback, profile `MatchReplay`, `EventLog`, and `DarkCourt`.
- Suggested fix direction: Precompute per-event view state once, or read eliminated IDs from each proof event’s `score_state`. Keep the full raw log available, but render a bounded current window plus key-play jumps.
- Regression gate: Add a replay fixture with a high `proof_events.length`, then assert playback stays under an agreed commit/render budget in browser profiling.

### 2. PolicyEditor saves on every discrete option change
- Severity: Medium
- Evidence: `PolicyEditor` calls `onChange` directly for arrow-key and click changes in [PolicyEditor.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/command-center/PolicyEditor.tsx:44>) and [PolicyEditor.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/command-center/PolicyEditor.tsx:80>). That flows to `savePolicy`, which posts `commandApi.savePlan` and replaces Command Center data in [MatchWeek.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchWeek.tsx:198>).
- Why it matters: fast option exploration can create multiple API writes and rerender the full Command Center panel, especially because `PreSimDashboard` is a large component.
- Reproduction / inspection path: Open Command Center, open Policy Editor, rapidly arrow through plan options while watching network and React commits.
- Suggested fix direction: Keep local draft state inside the editor and save on Apply, or debounce with visible saving state and request cancellation/last-write-wins.
- Regression gate: Interaction test verifies one save per committed policy edit, not one save per intermediate arrow/click.

### 3. Tab switching refetches route data instead of reusing recently loaded state
- Severity: Medium
- Evidence: `App` conditionally mounts only the active tab in [App.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/App.tsx:261>). `useApiResource` fetches on mount with no cache in [useApiResource.ts](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/hooks/useApiResource.ts:9>). `Standings` fetches both `/api/standings` and `/api/playoffs/bracket` in [LeagueContext.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/LeagueContext.tsx:195>). `DynastyOffice` fetches `/api/dynasty-office` and also `/api/command-center` on mount in [DynastyOffice.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/DynastyOffice.tsx:668>) and [DynastyOffice.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/DynastyOffice.tsx:683>).
- Why it matters: on desktop this will mostly feel like brief tab latency, but it becomes noticeable when bouncing between Command Center, standings, and dynasty/history views.
- Reproduction / inspection path: Switch Command Center -> Standings -> Dynasty Office -> Standings with network panel open.
- Suggested fix direction: Add a small app-level resource cache with explicit invalidation after week simulation, staff hire, recruiting action, lineup save, or offseason advance.
- Regression gate: Browser test counts network requests during repeated tab switches and verifies fresh data after mutating actions.

### 4. Long dynasty/history views are unbounded render surfaces
- Severity: Medium
- Evidence: `MyProgramView` builds and renders every visible timeline entry in [MyProgramView.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/history/MyProgramView.tsx:250>) and [MyProgramView.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/history/MyProgramView.tsx:337>). `LeagueView` maps full records and HOF arrays in [LeagueView.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/history/LeagueView.tsx:156>) and [LeagueView.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/history/LeagueView.tsx:184>).
- Why it matters: this is probably fine early, but multi-season saves can make Records/HOF/Timeline the first non-replay list to feel heavy.
- Reproduction / inspection path: Load a mature save with many seasons, open Dynasty Office -> History -> League and Program.
- Suggested fix direction: Add season filters or “latest first / show more” pagination before virtualization.
- Regression gate: Fixture with large timeline/records/HOF payload; assert initial render remains responsive and only the first bounded page is mounted.

### 5. Some delayed feedback timers are not cleaned up on unmount
- Severity: Low
- Evidence: `ProspectCard` sets feedback clear timers without cleanup in [ProspectCard.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/ProspectCard.tsx:98>) and [ProspectCard.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/dynasty/ProspectCard.tsx:106>). `LineupEditor` does the same for slot-error clearing in [LineupEditor.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/lineup/LineupEditor.tsx:102>).
- Why it matters: not a current slowdown, but it is a cleanup footgun if the user changes tabs/closes modals immediately after actions.
- Reproduction / inspection path: Trigger recruiting/lineup feedback, immediately close or navigate away.
- Suggested fix direction: Store timeout IDs in refs and clear on unmount.
- Regression gate: Component test unmounts after action and verifies no state update after unmount.

## Performance Hotspots

| Component | Interaction/path | Suspected or measured cost | Evidence | Measurement recommendation | Fix direction |
|---|---|---|---|---|---|
| `MatchReplay` | Full replay autoplay and event jumping | Suspected high cost on long logs | Full event log render plus O(n) eliminated scan per active event | React Profiler on long official replay | Precompute event state, bounded visible log |
| `PolicyEditor` + `MatchWeek` | Rapid policy changes | Suspected API/write churn | Direct `onChange` -> `savePlan` per option | Count network calls while arrowing options | Draft/apply or debounced last-write save |
| `Standings` / `DynastyOffice` | Repeated tab switching | Confirmed refetch pattern, cost unmeasured | `useApiResource` fetch-on-mount, conditional tab mount | Network count across tab bounce | Shared cache + mutation invalidation |
| `MyProgramView` / `LeagueView` | Mature save history browsing | Suspected long-list cost | Maps full timeline, records, HOF arrays | Load large synthetic dynasty save | Paging/show-more filters |
| CSS nav/reveal | Nav collapse, reveal sequences | Low suspected layout cost | nav width transition in [App.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/App.tsx:132>), reveal uses transform in [index.css](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/index.css:1789>) | Chrome performance trace during nav/reveal | Only adjust if trace shows layout spikes |

## Do-not-optimize-yet list
- Do not blanket `memo`, `useMemo`, or `useCallback` every component.
- Do not virtualize roster, standings, playoff bracket, or policy rows yet; current data sizes do not justify it.
- Do not spend performance budget on mobile-specific layout changes; desktop is the product target.
- Do not split bundles before there is route-level load evidence. Current build: JS `493.12 kB` uncompressed / `135.27 kB` gzip; CSS `178.75 kB` / `29.65 kB` gzip.
- Do not remove reveal animation broadly. Most relevant reveal CSS uses opacity/transform, which is the right direction.

## Confirmed strengths
- Build and lint are green: `npm run lint` passed; `npm run build` passed after allowing normal TypeScript build-info writes.
- `ReplayTimeline` is collapsed by default, limiting aftermath cost until opened in [ReplayTimeline.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/match-week/aftermath/ReplayTimeline.tsx:89>).
- Major reveal timers clean up correctly in `MatchWeek`, `MatchReplay`, and `CeremonyShell`: [MatchWeek.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchWeek.tsx:310>), [MatchReplay.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/MatchReplay.tsx:570>), [CeremonyShell.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/ceremonies/CeremonyShell.tsx:28>).
- `Roster` already memoizes its sorted roster projection in [Roster.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/Roster.tsx:232>).
- `useVoiceRegister` has a module-level cache, avoiding repeated voice-register fetches in [useVoiceRegister.ts](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/hooks/useVoiceRegister.ts:6>).

## Open questions
- What is the real upper bound of `proof_events.length` in official multi-set matches after recent balance changes?
- How large do records/HOF/program timelines become in a realistic 20+ season save?
- Are tab refetch delays visible against the real backend on Maurice’s machine, or only theoretically wasteful?

## Suggested next prompt
Implement a targeted replay responsiveness pass: profile one long official replay, precompute per-event replay view state, bound the visible event log without hiding key-play navigation, and add a regression fixture that proves playback remains smooth on a large proof log.