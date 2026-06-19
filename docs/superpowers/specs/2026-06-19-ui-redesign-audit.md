# Dodger Frontend Audit — Synthesis for Full UI Rewrite

This report consolidates 10 parallel per-area audits into a single non-regression contract and rebuild justification. It is the source of truth for the rewrite: Section 2 is what MUST stay green, Section 3 is why we are rebuilding, Section 5 is how to kill the bug classes at the root.

---

## 1. Complete Screen Inventory

### Area: App shell + navigation + save menu
| Screen | File | Reached via | Renders |
|---|---|---|---|
| Boot / Loading splash | frontend/src/App.tsx | Initial mount, screen==='loading' (App.tsx:90-100) | Centered .app-boot: kicker, brand, animated .court-pulse (role=status) |
| Save Menu (landing) | frontend/src/components/SaveMenu.tsx | App renders when screen==='menu' (App.tsx:102-104); nav 'Menu' button unloads+reloads | Landing card, 2-tab Load/New Game; save list rows; takeover form; build wizard entry |
| New-game build wizard (4 steps) | frontend/src/components/SaveMenu.tsx | 'Build from Scratch' -> setView('build_identity') (SaveMenu.tsx:715-744) | Delegates to Identity/Coach/StaffHiring/StartingRecruitment steps; shared build state |
| Main app shell (game/offseason) | frontend/src/App.tsx | screen==='game'\|'offseason' (App.tsx:131-308) | Collapsible left-nav rail + sticky broadcast-header + content swap by tab |
| Command Center tab | frontend/src/components/MatchWeek.tsx | activeTab==='command' (default; App.tsx:265-301) | MatchWeek with mode pre/post/offseason |
| Roster tab | frontend/src/components/Roster.tsx | activeTab==='roster' (App.tsx:303) | <Roster /> |
| Dynasty Office tab | frontend/src/components/DynastyOffice.tsx | activeTab==='dynasty' (App.tsx:302) | <DynastyOffice /> |
| Standings tab | frontend/src/components/LeagueContext.tsx | activeTab==='standings' (App.tsx:304) | <Standings /> |
| Match Replay overlay | frontend/src/components/MatchReplay.tsx | openCommandReplay -> commandReplay set (App.tsx:255-261) | Replay keyed by match_id; header swaps to MATCH DAY; tabs deactivate |

### Area: New game / onboarding (Build From Scratch wizard)
| Screen | File | Reached via | Renders |
|---|---|---|---|
| Step 1 — Program Identity | frontend/src/components/new-game/IdentityStep.tsx | view 'build_identity' (SaveMenu.tsx:960,721) | Save/Club/City inputs, color preset picker, live preview, collision banner |
| Step 2 — Head Coach | frontend/src/components/new-game/CoachStep.tsx | view 'build_coach' (SaveMenu.tsx:961) | Coach name + 3 archetype radio cards + summary |
| Step 3 — Hire Your Staff | frontend/src/components/new-game/StaffHiringStep.tsx | view 'build_staff' (SaveMenu.tsx:962) | Budget bar + scrollable dept candidate grid (radios); fetches own market |
| Step 4 — Recruit Roster | frontend/src/components/new-game/StartingRecruitmentStep.tsx | view 'build_roster' (SaveMenu.tsx:963) | Foundation coverage guide + scrollable prospect checkbox list; Commit (n/10) |

### Area: Command Center / pre-sim week
| Screen | File | Reached via | Renders |
|---|---|---|---|
| MatchWeek (mode router) | frontend/src/components/MatchWeek.tsx | Match Week tab; mode from career cursor | Switches pre-sim/post-sim/offseason; owns command-center fetch/mutations |
| PreSimDashboard | frontend/src/components/match-week/command-center/PreSimDashboard.tsx | pre-sim mode, default (testid 'weekly-command-center') | League Wire, Identity strip, Directive, Hero+MiniCourt, 3-col body (Plan/Opponent/Sim Lock), 3 modals |
| SeasonPreview | .../command-center/SeasonPreview.tsx | pre-sim when season_preview exists & not skipped | Division/climb context, officiating bulletin, season-shape timeline, stat tiles |
| PolicyEditor (modal) | .../command-center/PolicyEditor.tsx | testid 'open-policy-editor' | Radiogroup pill editor for 5 policy rows + rush sub-section |
| FastForwardDialog | .../command-center/PreSimDashboard.tsx | testid 'fast-forward-season' | Focus-trapped dialog; 3 stop points |
| Full Scouting File dialog | .../command-center/PreSimDashboard.tsx | testid 'open-scouting-file' | Cold-start facts + observed/prior intel notes |
| MatchCard (head-to-head) | .../command-center/MatchCard.tsx | Reusable comparison (imported elsewhere) | Slot OVR/STA gap bars, net edge, advantage tally |
| ProgramStatusStrip | frontend/src/components/match-week/ProgramStatusStrip.tsx | Mounted by match-week shell | Rank, points+diff (GP vs elim), W-L-D; fetches /api/standings |
| WeeklyChecklist | frontend/src/components/match-week/WeeklyChecklist.tsx | Pre-game panel (legacy/parallel to Sim Lock) | Lineup names, readiness, confirm gate, top staff rec |
| SimTransition | frontend/src/components/match-week/SimTransition.tsx | While isTransitioning | Full-screen Simulating spinner |

### Area: Match aftermath / result
| Screen | File | Reached via | Renders |
|---|---|---|---|
| Post-sim aftermath (orchestrator) | frontend/src/components/MatchWeek.tsx | mode='post-sim' after simulate/persistedResult | Staged reveal (0->4) of hero/banner/headline/score/analysis/fallout/replay/action |
| MatchScoreHero | .../aftermath/MatchScoreHero.tsx | revealStage>=1, match_card present | Scoreline (GP or survivors), count-up, winner/draw badge, set strip, draw footer |
| PrimaryFactorCard | .../aftermath/PrimaryFactorCard.tsx | revealStage>=1, primary_factor present | Canonical 'why': confidence badge, title, sentence, evidence chips |
| ManagerLessonCard | .../aftermath/ManagerLessonCard.tsx | revealStage>=1, manager_lesson present | CONTROLLABLE vs NOT ON YOU states |
| TacticalSummaryCard | .../aftermath/TacticalSummaryCard.tsx | revealStage>=2, not bye | Turning point + stat line + 'Based on <lane>' |
| KeyPlayersPanel | .../aftermath/KeyPlayersPanel.tsx | revealStage>=2, not bye | Top-3 performers, Your Club badge, Your Club's Best fallback |
| FalloutGrid | .../aftermath/FalloutGrid.tsx | revealStage>=3 | Who Grew / Standings Shift / Prospect Pulse with empty states |
| ReplayTimeline | .../aftermath/ReplayTimeline.tsx | revealStage>=3, not bye | Collapsible postgame report, beat list, moment beats, ComebackCard |
| NextBestImprovementPanel | .../aftermath/NextBestImprovementPanel.tsx | revealStage>=3, improvement non-empty | Loss-only ranked improvements + staleness disclaimer |
| PlayoffResolutionBanner | .../aftermath/PlayoffResolutionBanner.tsx | decided_by !== 'regulation' (MatchWeek.tsx:426) | OT/TIEBREAKER banner naming advance/eliminate |
| ChampionshipHero | .../aftermath/ChampionshipHero.tsx | championship present (MatchWeek.tsx:425) | Gold Champions hero |
| EliminationCeremony | .../aftermath/EliminationCeremony.tsx | revealStage>=4, elimination present | Send-off: stage, score, who carried, returning core, Continue |
| AftermathActionBar | .../aftermath/AftermathActionBar.tsx | revealStage>=4, not eliminated | Sticky bar: optional replay + advance (BANK/NEXT WEEK) |
| MatchCard (legacy/simple) | .../aftermath/MatchCard.tsx | NOT imported by MatchWeek — verify consumer | Simple VS scoreline via formatScoreline |
| StandingsShift / PlayerGrowthBlock / RecruitReactions | .../aftermath/{StandingsShift,PlayerGrowthBlock,RecruitReactions}.tsx | NOT imported by MatchWeek — likely dead | Standalone dm-panel versions of FalloutGrid data |
| Headline | .../aftermath/Headline.tsx | revealStage>=0 | War Room/Bye kicker, stage sub-label, headline + context |
| LateGameBanner / OneVOneBanner / ComebackCard | .../aftermath/{LateGameBanner,OneVOneBanner,ComebackCard}.tsx | Inside ReplayTimeline | Moment banners; ComebackCard self-suppresses |
| ReplaySpeedControl | .../aftermath/ReplaySpeedControl.tsx | NOT imported in aftermath — verify | 1x/2x/4x/instant pills |

### Area: Match replay / highlights
| Screen | File | Reached via | Renders |
|---|---|---|---|
| MatchReplay (full screen) | frontend/src/components/MatchReplay.tsx | commandReplay set (App.tsx:256) | Scoreboard, OfficialRulesPanel, ProofFrames, TurningPoint, DarkCourt, SETS strip, PossessionBar, transport, sidebar |
| DarkCourt | frontend/src/components/MatchReplay.tsx | Embedded in .mr-court-wrap | Memoized SVG court, trajectory, 12 player tokens |
| GameSegmentStrip (SETS) | frontend/src/components/MatchReplay.tsx | data.game_segments non-empty | Per-game chips + live-reveal hiding unreached games |
| PossessionBar | frontend/src/components/MatchReplay.tsx | Inside .mr-stage | 7-col grid of clickable per-event cells |
| OfficialRulesPanel | frontend/src/components/MatchReplay.tsx | Top of shell; null when no official_state | 4-col grid of full-time official state |
| CurrentEventCard | frontend/src/components/MatchReplay.tsx | Top of right sidebar | Active event actors/chips/summary |
| EventLog | frontend/src/components/MatchReplay.tsx | Right sidebar | Scrollable proof event list, auto-scroll active |
| MatchHighlights | frontend/src/features/replay/MatchHighlights.tsx | Sidebar, highlightBeats>0 | Highlight beat cards + Show-in-timeline + empty state |
| BroadcastFrameBlock | frontend/src/components/BroadcastFrameBlock.tsx | Inside ReplayProofFrames when broadcast_frame present | dm-panel: tags, hook, collapsible evidence |

### Area: Ceremonies / offseason
| Screen | File | Reached via | Renders |
|---|---|---|---|
| Offseason (beat router) | frontend/src/components/Offseason.tsx | Career enters offseason | Fetches beat, switches on key to 16 components; act() POSTs; Action-blocked status |
| ChampionReveal | .../ceremonies/ChampionReveal.tsx | beat.key==='champion' | Champion hero + lazy PlayoffBracket; own pips/action bar |
| RecapStandings | .../ceremonies/RecapStandings.tsx | beat.key==='recap' | Final table, missed-playoffs, finances, league movement |
| WorldsCrowning | .../ceremonies/WorldsCrowning.tsx | beat.key==='worlds_champion' | First title = staged reveal; later = quiet stage |
| AwardsNight | .../ceremonies/Ceremonies.tsx | beat.key==='awards' | MVP hero + supporting-award grid |
| Graduation | .../ceremonies/Ceremonies.tsx | beat.key==='retirements' | Retiring veteran farewell cards |
| SigningDay (Class Report) | .../ceremonies/Ceremonies.tsx | beat.key==='recruitment' && !can_recruit | Metric tiles, class glance, tab-filtered signing cards |
| NewSeasonEve | .../ceremonies/Ceremonies.tsx | beat.key==='schedule_reveal' | Schedule toggle + prediction; Start New Season |
| EventsBeat + EventCard + EventBracket | .../ceremonies/EventsBeat.tsx | beat.key==='events' | Competition calendar, champion/purse/seeding, brackets |
| MediaEvent | .../ceremonies/MediaEvent.tsx | beat.key==='media_event' | Press prompt, effect chips, committed receipt |
| DevelopmentResults | .../ceremonies/DevelopmentResults.tsx | beat.key==='development' | OVR delta rows, training credit receipt, checklist |
| RookieClassPreview | .../ceremonies/RookieClassPreview.tsx | beat.key==='rookie_class_preview' | Class upside, composition, archetype bars, storylines |
| RecordsRatified | .../ceremonies/StructuredOffseasonBeats.tsx | beat.key==='records_ratified' | Scope control, milestone cards w/ proof, empty states |
| HallOfFameInduction | .../ceremonies/StructuredOffseasonBeats.tsx | beat.key==='hof_induction' | Inductee plaques w/ proof toggle |
| RecruitmentChoice (Signing Day desk) | .../ceremonies/RecruitmentChoice.tsx | beat.key==='recruitment' && can_recruit | Prospect list (bands vs FA OVR), sign-over-cut, lock-class |
| TransferPeriod | .../ceremonies/TransferPeriod.tsx | beat.key==='transfer_period' | Treasury/wage header, expiring/buyout rows, settled results |
| CeremonyShell | .../ceremonies/CeremonyShell.tsx | Wrapper (not a beat) | Shared staged-reveal frame, pips, sticky action bar |

### Area: Dynasty office + history
| Screen | File | Reached via | Renders |
|---|---|---|---|
| Dynasty Office shell + subtab bar | frontend/src/components/DynastyOffice.tsx | Dynasty tab; ?subtab= | DoTabs (Recruit/History/Staff), treasury chip, settings, week note |
| Recruit subtab | frontend/src/components/DynastyOffice.tsx | DoTabs 'Recruit' (default) | CredibilityStrip, context, Promises, SlotMeter+StaffBrief, ScoutingNetwork, RecruitBoard |
| CredibilityStrip | .../dynasty/CredibilityStrip.tsx | Top of Recruit body | Grade hero, 0-100 track, evidence list |
| ProspectCard (+ locked variant) | .../dynasty/ProspectCard.tsx | RecruitBoard grid | Full prospect card; locked variant = name+hometown+reach only |
| RecruitingBadge | .../dynasty/RecruitingBadge.tsx | Inside ProspectCard | Status pill w/ pending state |
| Program Settings (Staff Focus) modal | frontend/src/components/DynastyOffice.tsx | DoTabs 'Program Settings' | Radiogroup of 5 weekly focus options |
| Staff subtab | frontend/src/components/DynastyOffice.tsx | DoTabs 'Staff' | Staff glance, facilities, staff cards, vacancies, pipeline hire |
| StaffMarketModal | .../dynasty/StaffMarketModal.tsx | No caller found — likely orphaned | Staff candidate dialog w/ Hire buttons |
| ScoutingNetworkPanel | frontend/src/components/DynastyOffice.tsx | Recruit subtab when present | Network level, upgrade gated on afford |
| FacilitiesUpgradePanel | frontend/src/components/DynastyOffice.tsx | Staff subtab when facilities present | Built vs Build buttons gated on afford |
| History subtab | .../dynasty/HistorySubTab.tsx | DoTabs 'History' | Switches MyProgramView / LeagueView |
| MyProgramView | .../dynasty/history/MyProgramView.tsx | History 'My Program'; reused in ProgramModal | Glance, timeline filter, Program Arc, Banner/Alumni shelf |
| LeagueView | .../dynasty/history/LeagueView.tsx | History 'League' | Glance, directory, worlds/dynasty/records/HoF/rivalries |
| ProgramModal | .../dynasty/history/ProgramModal.tsx | LeagueView directory click | Dialog wrapping MyProgramView(isSelf=false) |
| AlumniLineage | .../dynasty/history/AlumniLineage.tsx | MyProgramView 'Alumni' tab | Alumni rows + empty state |
| BannerShelf | .../dynasty/history/BannerShelf.tsx | MyProgramView 'Banners' tab | Title/award tiles + Next-banner (isSelf only) |
| MilestoneTree | .../dynasty/history/MilestoneTree.tsx | No caller — orphaned/deferred | SVG trunk + season dots + overlaid labels |

### Area: Roster + lineup + player detail
| Screen | File | Reached via | Renders |
|---|---|---|---|
| Roster (Team Roster) | frontend/src/components/Roster.tsx | tab 'roster' (App.tsx:303) | Glance strip + rl-table (ratings, potential, OVR sparkline, role) |
| PlayerDetailModal | frontend/src/components/PlayerDetailModal.tsx | Click roster row/name | Bio, potential, growth, ratings, release w/ confirm strip |
| LineupEditor | frontend/src/components/lineup/LineupEditor.tsx | 'Lineup Editor' button | 6 starter slots + bench list, auto-reorder, auto-assign, stale note |
| Sparkline | frontend/src/components/roster/Sparkline.tsx | Roster OVR cell (Detailed) | 60x20 SVG polyline of ovr_season_trend |
| PlayerCompactRow | frontend/src/components/roster/PlayerCompactRow.tsx | DEAD — no importer | Compact tr |
| PlayerTheaterRow | frontend/src/components/roster/PlayerTheaterRow.tsx | DEAD — no importer | Spacious tr |
| PotentialBadge | frontend/src/components/roster/PotentialBadge.tsx | Transitively dead (only PlayerTheaterRow) | Tier + stars + pips |

### Area: Standings + league context
| Screen | File | Reached via | Renders |
|---|---|---|---|
| Standings (League Office) | frontend/src/components/LeagueContext.tsx | tab 'standings' (App.tsx:304) | Glance, season table w/ cut line, sidebar (wire/tiebreaker/pyramid) |
| PlayoffBracket | frontend/src/components/standings/PlayoffBracket.tsx | bracket.active (LeagueContext.tsx:392) | Seeds + 3-col bracket, formatScoreline, YOU ADVANCED/ELIMINATED, OT/SEED chip |
| PyramidPanel (World Standings) | frontend/src/components/LeagueContext.tsx | divisions.length>1 (LeagueContext.tsx:667) | Division tablist, tables, DROP badge |
| RecentMatchesSidebar | frontend/src/components/standings/RecentMatchesSidebar.tsx | No reference — likely dead | dm-panel recent-match list |
| ProgramModal (club history) | frontend/src/components/dynasty/history/ProgramModal.tsx | Click standings/tiebreaker/pyramid row | Clicked club's history |

### Area: Legibility primitives + data layer
| Screen | File | Reached via | Renders |
|---|---|---|---|
| TermTip | frontend/src/legibility/TermTip.tsx | Inline wherever a domain term appears | Term button + tooltip w/ AFFECTS PLAY vs FLAVOR badge |
| ProofChip | frontend/src/legibility/ProofChip.tsx | Inline next to claims needing source | Cyan chip + receipt popover |
| KnownValue | frontend/src/legibility/KnownValue.tsx | Prospect/roster/scouting surfaces | known/estimated/hidden bordered value |
| CeilingGrade | frontend/src/legibility/CeilingGrade.tsx | Scouted prospect cards | HIGH_CEILING/SOLID/STANDARD pill; null on unknown |
| PipelineEmblem | frontend/src/legibility/PipelineEmblem.tsx | Prospect cards | Tier 1-5 Bronze..Platinum emblem |
| EmptyState | frontend/src/legibility/EmptyState.tsx | Any legitimately-empty list/section | Dashed card, role=status |

**Likely-dead / unverified consumers (confirm before porting):** aftermath/MatchCard.tsx, aftermath/{StandingsShift,PlayerGrowthBlock,RecruitReactions}.tsx, aftermath/ReplaySpeedControl.tsx, dynasty/StaffMarketModal.tsx, dynasty/history/MilestoneTree.tsx, standings/RecentMatchesSidebar.tsx, roster/{PlayerCompactRow,PlayerTheaterRow,PotentialBadge}.tsx.

---

## 2. Preserve-Behaviors Ledger (Non-Regression Contract)

Deduplicated across all areas. Every item here MUST stay green after the rewrite.

### A. The V20 scoring-model family (survivors vs game points) — THE headline trust contract
This single invariant recurs on **every** score-bearing surface and is the most-cited fix in memory (a 12-2 win once shown as "survivors 0-0").

1. **One shared scoreline decision via formatScoreline()/survivorDetail()** — official matches show home/away_game_points and label detail "game points"; legacy shows survivors. Never print a survivor count as the official result (a 0-0 foam draw can carry a 0-3 survivor box score). *Evidence:* matchResult.ts:34-48, :58-60; types.ts MatchReplayResponse.scoring_model + home/away_game_points (396-412).
2. **MatchScoreHero / MatchReplay scoreboard branch on scoring_model** (MatchScoreHero.tsx:146-153,63-66; MatchReplay.tsx:381-392).
3. **Pre-sim League Wire shows the game-point scoreline, not bare Win/Loss** (PreSimDashboard.tsx:454-460 — PT6 Command Center wire fix).
4. **Aftermath context line phrases verdict in the scoring model's scale** — sweep vs shutout, draw "on game points" only when official (MatchWeek.tsx:47-79).
5. **ProgramStatusStrip differential = game-point diff on official, elimination diff on legacy** (ProgramStatusStrip.tsx:13-14).
6. **Standings rank/diff column branches** — 'GP Diff' vs 'Survivor Diff', need-copy label branches (LeagueContext.tsx:328-336,367,487; PyramidPanel 296-298).
7. **PlayoffBracket scoreline via formatScoreline**, not raw home_survivors (PlayoffBracket.tsx:24-32).
8. **Recap differential column branches on diff_kind** ('GP ±' vs 'Elim ±') (RecapStandings.tsx:108,137-145).
9. **Save-list record shown W-L-D only when wins defined; never fabricated 0-0** (SaveMenu.tsx:441-445,519-526).
10. **ruleset_selection hard-pinned to 'official_foam' at every create path** so downstream scoring branches are correct (SaveMenu.tsx:231-233,259-261; new-game SaveMenu.tsx:260).

### B. Playoff / draw / outcome truth
11. **PlayoffResolutionBanner reads decided_by directly**, never derives from score; renders nothing on 'regulation' (PlayoffResolutionBanner.tsx:18,22-40; MatchWeek.tsx:426). The single most-cited playtest break (tied 0-0 semifinal silently advancing by seed).
12. **Draw is a real labeled outcome** — Draw badge + footer; in playoffs the footer must NOT promise a standings point (MatchScoreHero.tsx:161,176-235).
13. **Verdict is fallback only** — suppressed when primary_factor present, so one canonical 'why' (MatchWeek.tsx:522).
14. **Playoff-resolution banner only when NOT decided by regulation** (MatchWeek.tsx:426-428).
15. **Standings draw handling** — winner_name==='Draw' shows Draw, not a fabricated win; unparseable summaries fall back to raw, never dropped (LeagueContext.tsx:185,177-181).
16. **Player-outcome ribbon gated on played AND player-in-match AND winner identity** (PlayoffBracket.tsx:16-19,59,75-89).
17. **User's own Worlds run receipted on semifinal exit** (worlds_user) even when the global line names only the final (RecapStandings.tsx:253-262; types.ts pyramid.worlds_user 1176-1182).
18. **missed_playoffs banner only when backend confirms finish outside the cut** (RecapStandings.tsx:35-37,63-88).

### C. Faithfulness / fog-of-war / receipts
19. **Mechanical-vs-flavor badge** ('AFFECTS PLAY' vs 'FLAVOR') driven by terms.ts TermDef.kind — load-bearing copy, preserve mapping verbatim (TermTip.tsx:67-71; terms.ts 1-8 + per-term).
20. **Receipts/'why' rendered verbatim from backend evidence strings, never re-derived** (ProofChip.tsx:48; credibility.evidence[], motivations[].receipt, dealbreaker.receipt, interest_evidence, market_signal[].receipt).
21. **KnownValue three-state (known/estimated/hidden)** — estimate visually distinct from verified and from scout-to-reveal unknown (KnownValue.tsx:16-29).
22. **Founding-class prospects shown UNFOGGED on purpose** — same values the roster row shows post-commit (StartingRecruitmentStep.tsx:13-27,145-149).
23. **Prospect OVR is a scouted band vs verified FA OVR** (RecruitmentChoice.tsx:341-374; ProspectCard.tsx:328-333).
24. **Dealbreaker (★) hidden until scouted; veto shows WON'T VERBAL** (ProspectCard.tsx:364-381).
25. **Tactical-Diff distinguishes tape vs playbook vs unscouted**; intel meter never claims 'revealed from tape' when source is playbook; no "New intel" beside 0/5 reads (PreSimDashboard.tsx:900-1025).
26. **Vocabulary de-collision** across pipeline tiers (Bronze..Platinum), potential tiers (Elite/High/Mid/Low/Raw), scout ceiling grades — distinct word sets on purpose (PipelineEmblem.tsx:3-6; CeilingGrade.tsx:4-11).
27. **Ruleset display-name normalization never leaks impl keys** like OFFICIAL_FOAM (rulesetNames.ts:25-67).
28. **CeilingGrade copy never leaks exact tier/number; returns null on unknown grade** (CeilingGrade.tsx:35).
29. **Audience-tagged aftermath paragraphs read by tag, not prose prefix** (types.ts AftermathParagraph.audience 914-923).
30. **Proof-source provenance preserved on DOM** (data-broadcast-proof-source, data-player-outcome) — test + trust hooks; record:/career: prefixes stripped display-only (BroadcastFrameBlock.tsx:12-22).

### D. Empty-state / null truth
31. **Honest null-vs-zero: undefined/null payload = render nothing, not a fabricated default** (primary_factor, manager_lesson, narrative_beats, champion, ovr_season_trend null = no history). EmptyState is the dedicated truth surface.
32. **League Wire empty-state** — one honest static line, not a fabricated marquee; headlines-first merge order (PreSimDashboard.tsx:463-466,533-550; LeagueContext.tsx:170,372-375,579-584).
33. **Tiebreaker panel three states (hidden/soft/live)** gated on phase and whether any games played (LeagueContext.tsx:379-384,615-628).
34. **Phase-aware race/need copy** — regular-season math suppressed during playoffs/offseason (LeagueContext.tsx:346-367).
35. **Truthful empty states across fallout/standalone/history/league panels** ('Records updated — no rank changes', 'No prospect movement', records-book-empty vs my-club-empty-but-league-has) (FalloutGrid, KeyPlayersPanel, LeagueView, StructuredOffseasonBeats:116-141,227-244).
36. **OVR Sparkline only renders with >=2 points**, else honest NO-DATA fallback (Roster.tsx:440-449; Sparkline.tsx:2).
37. **Conditional rendering of replay surfaces** — OfficialRulesPanel/BroadcastFrameBlock/segments/CurrentEventCard return null when absent; ball states 'No ball state', rule calls 'None', burden 'No team on the clock' (MatchReplay.tsx:444,311,536,613).
38. **World Championship roll only when worlds data exists** (pyramid saves); runner_up clause only when present (LeagueView.tsx:132,145).

### E. Bye-week & no-fabricated-mechanic truth
39. **Bye-week primary action = ADVANCE BYE WEEK** — no opponent/match panels, no fatigue/recovery claims (no recovery system exists) (PreSimDashboard.tsx:361,439-450; MatchWeek.tsx:450-502,582).
40. **Champion/Worlds-defending stages never imply an NG+/ratchet/buff** — crowning is a moment (WorldsCrowning.tsx:8-10; ChampionReveal title_count only).

### F. Replay integrity
41. **Live court eliminations derived ONLY from current event score_state**, not unioned across prior events (MatchReplay.tsx:780-798).
42. **Survivor-delta suppressed across game boundaries** ('fresh court') (MatchReplay.tsx:580-600).
43. **GameSegmentStrip live-reveal** hides unreached games; running tally appends 'so far' mid-replay (MatchReplay.tsx:300-369,359-366).
44. **TurningPoint jump uses server turning_point_index**, falling back to first key play, not event 0 (MatchReplay.tsx:557-559,859,677).
45. **Highlight 'Show in timeline' maps source_event_index -> proof index via sequence_index**, guarding null (MatchReplay.tsx:864-868,980-989).
46. **Highlight package failure is non-fatal** — sets beats [], reel hides; cancellation guard (MatchReplay.tsx:689-701).
47. **Official engine enums humanized at boundary** without inventing absent state ('—' fallback) (MatchReplay.tsx:437-440).
48. **ComebackCard self-suppresses on shutout/zero-deficit AND only when winner_club_id===comeback.team_id** (ComebackCard.tsx:19-22; ReplayTimeline.tsx:158).
49. **Set-story strip reads per-game official score straight from persisted games** (MatchScoreHero.tsx:97-117).
50. **Replay top-performers/tactical evidence prefer authoritative replay payload**, fall back only when absent (MatchWeek.tsx:559-564).

### G. Roster / lineup integrity
51. **Server is source of truth for resolved lineup order** — saves splice server ordered_player_ids, never local array (Roster.tsx:519-526; LineupEditor.tsx:133,190).
52. **Auto-reorder OFF flip announced explicitly, only on first actual change** (LineupEditor.tsx:127-132,208-213).
53. **Persistent computed stale-lineup warning** (best benched OVR > weakest fielded) as durable note (LineupEditor.tsx:52-65,485-487).
54. **Release blocked (not hidden) at 6-floor with visible reason; confirm strip discloses free-agency + broken-promise** (Roster.tsx:490-495; PlayerDetailModal.tsx:207-227,271-272).
55. **Lineup save errors mapped to plain language, keyed to offending slot, role=alert** (LineupEditor.tsx:22-33,140-149,474-477).
56. **Conditional bio/growth narrative derived from real numbers; High-Upside ProofChip only with backed source** (PlayerDetailModal.tsx:110-117,133-145,163-171).
57. **Potential sort uses explicit tier-rank map w/ fallback, tie-break by OVR; starters-first for lineup sort** (Roster.tsx:239-252). *(Reconcile tier vocab — see risk catalogue.)*
58. **Role/archetype TermTip only for 8 known archetypes, plain badge otherwise; canonical formatters keep draft/roster parity** (Roster.tsx:14-23,457-464; playerDisplay.ts formatRole).

### H. Recruiting / offseason desk integrity
59. **Credibility grade read from payload, never re-derived** (CredibilityStrip.tsx:32-33).
60. **All-Time vs Latest-Season record label branches on hero.all_time presence** — never show a week-2 snapshot as all-time (MyProgramView.tsx:281-300).
61. **Promise resolution KEPT/VOIDED/BROKEN; void carries no manager blame** (DynastyOffice PromisesPanel 295-306).
62. **Roster-dependent promises say 'first season on your roster'; contender_path grades whether or not they sign** (DynastyOffice PROMISE_LABELS 236-249).
63. **Name-only/out-of-reach prospects render NO scoutable data and sink to bottom of every sort; excluded from At-Risk** (ProspectCard.tsx:151-194; DynastyOffice.tsx:995-1005,614-643,663).
64. **Optimistic recruiting status never regresses below server truth (monotonic precedence)** (ProspectCard.tsx:13-26,86-89,113).
65. **Refused recruiting actions unmistakable + refetch board** ('action not spent') (ProspectCard.tsx:111-124).
66. **Record/HoF rows use persisted holder display name, not humanized id** (LeagueView.tsx:198).
67. **signed_count is single source for 'how many YOU signed'; card list never fabricated to match** (Ceremonies.tsx:663-673,705-794).
68. **Class-report tiles labelled player-scope vs LEAGUE-scope** (Ceremonies.tsx:705-708).
69. **Veto-aware re-sign latch + disabled Re-sign** (TransferPeriod.tsx:124-128,161).
70. **Records milestone vs bookkeeping tiering + dethrone/new-holder flags; default scope + non-dead-end empty states** (StructuredOffseasonBeats.tsx:247-265,116-141).
71. **Integerized player-facing numbers (V21 zero-floats); training-credit .toFixed(1) the deliberate receipt exception** (StructuredOffseasonBeats.tsx:521; DevelopmentResults.tsx:65,183).
72. **Training-credit receipt with cap disclosure**, shown only when weeks>0 (DevelopmentResults.tsx:161-185).
73. **Sign-over-cut: release commits only if contested pick lands** (RecruitmentChoice.tsx:387-484,455-459,160-164).
74. **Skip/lock-class gated by backend roster-floor guard with visible reason** (RecruitmentChoice.tsx:50-51,572-587; Offseason.tsx:98-104).
75. **AwardsNight extra_stats vs season_stat fallback** (Ceremonies.tsx:183-211).

### I. Onboarding wizard integrity
76. **Save-name uniqueness validated up-front on Step 1 with visible banner** (IdentityStep.tsx:76-82,107-124).
77. **Seed continuity: fetch seed === root_seed POSTed** so preview equals generated career (SaveMenu.tsx:158,258).
78. **Staff step never soft-locks: defaults each dept to cheapest affordable; over-budget blocked** (StaffHiringStep.tsx:71-86,102-103,241-245).
79. **Empty {} staff_choices never sent; omitted when empty** (SaveMenu.tsx:256).
80. **Role-coverage tally counts coverage (hybrids multi-lane), imbalance advisory-only** (StartingRecruitmentStep.tsx:106-122,234).
81. **Roster selection bounded 6..10 with state-specific helper copy and hard 11th-cap refusal** (StartingRecruitmentStep.tsx:97-104,127-133,361).

### J. Routing / data-layer integrity
82. **Router trusts LIVE career state over post-sim next_state when advancing** (App.tsx:281-298) — fast-forward strands player otherwise.
83. **Offseason vs in-season classification drives screen + header meta** (App.tsx:14-18,246-250).
84. **Season/week/year fallback precedence; post-sim week takes priority; never invents data** (App.tsx:129,248-249,184).
85. **Incompatible saves hidden by default, non-loadable, labeled honestly** (SaveMenu.tsx:126-129,488-510,541,563-585).
86. **Continue-career hero picks first non-incompatible, non-debug save** (SaveMenu.tsx:138-140).
87. **Debug/test saves filtered unless ?debug=true AND opt-in (two-gate)** (SaveMenu.tsx:11-15,122-137).
88. **Active-tab persists to ?tab= only in game/offseason, validated against known tabs** (App.tsx:38-41,76-81).
89. **Save-state fetch failure falls back to menu, not broken shell** (App.tsx:68-73).
90. **Optimistic policy save with rollback on failure** (MatchWeek.tsx:208-232).
91. **Launch-token guard: stale-token 403 refresh-and-retry vs genuine business 403 surfaced verbatim** (api/client.ts:33-130).
92. **Response-field tolerance via nullish fallbacks** (default_lineup ?? [], lineup_auto_reorder ?? true, etc.) (Roster.tsx:229,495,517,426).
93. **FALLBACK_BRIEFING / matchup_details defaults render without re-deriving; confirm-lineup preview shows actual canonical six before clearing gate** (PreSimDashboard.tsx:26-36,342,345-351,1119-1167).
94. **Operational-Plan alignment reflects real state (pending orders OR conflict), no green-while-misaligned** (PreSimDashboard.tsx:509-517,778-797).
95. **Recent-results derived as ordered W/L from history slice; season subtitle deterministic flavor; stakesLine playoff semantics top-4 not top-3** (PreSimDashboard.tsx:371-375; presimNarrative.ts:5-26,38-110).
96. **Season label parsing centralized; sort numerically (avoid season_10<season_2 string trap)** (formatters.ts:26-39; MyProgramView seasonTick).
97. **isSelf gates self-only copy and 'Next banner' placeholder** (HistorySubTab.tsx:7; BannerShelf isSelf; ProgramModal forces isSelf=false).

---

## 3. Layout-Bug Catalogue (grouped by root cause, severity-ranked)

### Pattern 1 — Pervasive inline styles + hardcoded hex colors instead of tokens (ROOT CAUSE) — HIGH
This is the structural root of nearly every other bug and the inconsistent-spacing the user reported. It appears in essentially every component file.
- **App.tsx nav rail / header chrome** fully inline (collapsed width '3rem' overriding .left-nav 13rem; hamburger 2.25rem; box-shadow offsets) — App.tsx:134-178. *(high)*
- **SaveMenu** built almost entirely from inline-style objects (tabs, hero, rows, choice cards, takeover form); 'Faster Start' badge position:absolute top:-10px clips — SaveMenu.tsx:285-332,401-455,671-745. *(high)*
- **All 4 new-game steps** hardcoded inline + literal hex (#0f172a/#334155), ignore chosen club colors — IdentityStep.tsx:45 + CoachStep/StaffHiring/StartingRecruitment throughout. *(medium)*
- **PreSimDashboard dialogs / SeasonPreview / PolicyEditor / MatchWeek AftermathBody** entirely inline, no shared scale — SeasonPreview.tsx, PolicyEditor.tsx, MatchWeek.tsx. *(high)*
- **MatchCard (command-center)** has NO base CSS rule; whole card depends on inline magic numbers + percentage grid '1fr 36% 1fr' — MatchCard.tsx. *(high)*
- **All aftermath components** hardcode hex + inline px/rem — PrimaryFactorCard, ManagerLessonCard, EliminationCeremony, ChampionshipHero, PlayoffResolutionBanner, banners, Headline, MatchWeek bye/AftermathBody blocks. *(medium)*
- **MatchHighlights / BroadcastFrameBlock** entirely inline, bypass index.css design system — MatchHighlights.tsx:12-77; BroadcastFrameBlock.tsx:24-134. *(medium)*
- **All ceremony components** hardcoded hex + ad-hoc gap values 0.3-2rem — Ceremonies.tsx and siblings. *(medium)*
- **PlayoffBracket / standings MatchCard / PyramidPanel** inline hex + magic font sizes bypass --dm-* tokens — PlayoffBracket.tsx:40-117; LeagueContext.tsx:246-307. *(medium)*
- **Every legibility primitive** inline-styled, DUPLICATING tokens already in index.css; EmptyState ignores the existing .dm-empty-state class — legibility/*. *(high)*
- **Roster modals/primitives** (PlayerDetailModal, LineupEditor, ui.tsx) inline with hardcoded literals — PlayerDetailModal.tsx:75-85; LineupEditor.tsx:276-285; ui.tsx:39-55,178-194. *(high)*
- **index.css itself duplicates color tokens twice** (--color-dm-* and --dm-*) and is an 8744-line / 260KB monolith with overlapping families (.command-empty-state + .dm-empty-state; many .dm-action variants) — no single canonical token source. *(medium)*

### Pattern 2 — Missing min-width:0 / text-overflow on flex/grid items (overflow & clipping) — HIGH
Long names/labels cannot shrink or ellipsize and force container overflow.
- **Legibility popovers/rows** no min-width:0, no ellipsis (KnownValue, TermTip header, ProofChip) — KnownValue.tsx:18-31; TermTip.tsx:57-72. *(medium)*
- **CeilingGrade** whiteSpace:nowrap with no max-width — CeilingGrade.tsx:51-54. *(medium)*
- **Command-center MatchCard** name spans have title but no ellipsis/min-width:0; long names push grid — MatchCard.tsx:159-171,203-217. *(high)*
- **Standings PlayoffBracket** team-name ellipsis without min-width:0 on the flex item — refuses to shrink — PlayoffBracket.tsx:49. *(high)*
- **Tactical-Diff rows** fixed '8rem 1fr 1fr' + per-cell nowrap meta, no min-width:0 — PreSimDashboard.tsx:955-1016. *(medium)*
- **EliminationCeremony** score row + contributor rows, no flex-wrap/min-width:0, 2.4rem numbers flank 'vs <opponent>' — EliminationCeremony.tsx:53-65,89-97. *(high/medium)*
- **KeyPlayers** name+badge+club row no ellipsis — KeyPlayersPanel.tsx:101-123. *(medium)*
- **PrimaryFactor/ManagerLesson** header rows no min-width:0; chip text no max-width — PrimaryFactorCard.tsx:25-43; ManagerLessonCard.tsx:45-63. *(low)*
- **Roster** player-name span no ellipsis; sort-indicator chip nowrap crowds header — index.css:6028; Roster.tsx:281-310. *(medium)*
- **LineupEditor** slot/bench name spans no min-width:0, OVR collides — LineupEditor.tsx:413-420,446-449. *(medium)*
- **OfficialRulesPanel** long GAME PLANS / burden strings, no wrapping/ellipsis in narrow cells — index.css:6787-6812. *(medium)*
- **ProgramStatusStrip** rank/points/W-L-D blocks no min-width:0, won't stack — ProgramStatusStrip.tsx:21-63. *(medium)*
- **TransferPeriod / ProspectCard / Dynasty rows** long chips (veto, suitor, hometown) no truncation, wrap unpredictably and shove action buttons — TransferPeriod.tsx; ProspectCard.tsx:225-282; LeagueView.tsx:255-267. *(medium/low)*
- **RecapStandings** club_name 1fr cell no ellipsis inside overflow:hidden panel — clipped — RecapStandings.tsx. *(high)*
- **Save-name + inline badge** inside same truncating ellipsis container — badge clips — SaveMenu.tsx:473-504. *(medium)*
- **New-game prospect name** whiteSpace:nowrap but no textOverflow — forces row wider, pushes OVR block to clip — StartingRecruitmentStep.tsx:284. *(medium)*

### Pattern 3 — Hardcoded fixed widths / magic-pixel grid columns that don't shrink or collapse — HIGH
- **PossessionBar fixed 7-column grid** for 200+ event streams — cells go microscopic / strip grows huge, no horizontal scroll — index.css:6945. *(high)*
- **do-hist-glance hard 5-col + do-staff-glance hard 4-col**, NO responsive collapse — index.css:7109-7120,7333-7344. *(high)*
- **rl-ratings min-width:280px + 3×minmax(80px)** forces table to horizontal scroll off-screen — index.css:6033. *(high)*
- **do-board-grid minmax(300px,1fr)** overflows containers <330px — index.css:6301-6305. *(low)*
- **Bracket columns min-width:13rem** (PlayoffBracket both command + standings, EventBracket) — two columns exceed phone width, only flex-wraps never collapses — PlayoffBracket.tsx:67; EventBracket.tsx; index.css:4811-4825,4824. *(high)*
- **cc-gates repeat(5, minmax(0,1fr))** forces 5 gates + 0.5rem labels into one row — index.css:5751. *(medium)*
- **Ruleset key-rules label column flex:'0 0 9.5rem' whiteSpace:nowrap** crowds description — SaveMenu.tsx:621-639. *(medium)*
- **RecapStandings table tracks '2rem 1fr 6rem 3.5rem 4rem'** fixed numeric tracks won't shrink inside overflow:hidden — RecapStandings.tsx. *(high)*
- **AwardsNight supporting grid repeat(min(n,3),1fr)** no collapse/min-width:0; MVP name 2.1rem + paddingRight:8rem reserve collides with absolute badge — Ceremonies.tsx. *(high)*
- **RookieClassPreview** label track '0 0 7rem' clips long archetype names — RookieClassPreview.tsx. *(medium)*
- **ui.tsx KeyValueRow gridTemplateColumns 'minmax(96px,0.8fr) minmax(0,1fr)'** propagated everywhere — ui.tsx. *(medium)*
- **StaffMarketModal width:'600px'** (not min(vw,..)) overflows <640px — inconsistent with SettingsModal min(92vw,34rem) — StaffMarketModal.tsx:34. *(medium)*
- **mr-shell sidebar min 320px**; **cc-body 1.35/1/0.95fr** mid-width squeeze — index.css:6737,6623. *(medium)*
- **Fixed two-column modal grids** (PlayerDetailModal '1fr 1fr', LineupEditor 'minmax(0,1.05fr) minmax(0,0.95fr)') don't collapse — PlayerDetailModal.tsx:75-85; LineupEditor.tsx:276-285. *(high)*
- **New-game Foundation chips flex:'1 1 0' minWidth:100px** wrap unevenly; budget bar fixed 0.78rem no min-width — StartingRecruitmentStep.tsx:184; StaffHiringStep.tsx:119. *(medium/low)*

### Pattern 4 — Nested fixed-height scroll regions (off-screen footers / conflicting scrollbars) — HIGH
- **StaffHiringStep maxHeight 380px** inside constrained card pushes Next off-screen — StaffHiringStep.tsx:164. *(high)*
- **StartingRecruitmentStep maxHeight 360px** same — StartingRecruitmentStep.tsx:249. *(high)*
- **RecruitmentChoice maxHeight 420px/220px** + tall desk hides content — RecruitmentChoice.tsx. *(medium)*
- **LineupEditor maxHeight 24rem inner + body overflowY:auto** nested scroll — LineupEditor.tsx:413-420. *(medium)*
- **mr-sidebar-wrap calc(100vh - 180px) + min-height 600px** — guessed offset can exceed short viewports, page scrolls — index.css:7002-7003. *(high)*
- **ReplayTimeline** JS-decided scroll, nested overflow without min-width:0 clips beats — ReplayTimeline.tsx:105,141-156. *(low)*
- **Dialog overlay (ui.tsx) padding:2rem, caller-supplied panel no max-height/overflow** — tall modals clip off-screen — ui.tsx:538-571. *(medium)*

### Pattern 5 — Fixed positioning / sticky without safe-area or collision handling — MEDIUM
- **Legibility popovers position:absolute left:0, no flip/clamp, no portal** — clipped by ancestor overflow + render off the right edge — TermTip.tsx:43-55; ProofChip.tsx:33-49. *(high)*
- **broadcast-header sticky** meta string + skewed ::before, no flex-shrink/ellipsis — index.css:432-460; App.tsx:246-250. *(medium)*
- **AftermathActionBar sticky bottom:0** no safe-area padding, buttons no min-width:0 (desktop) — AftermathActionBar.tsx:22-39. *(medium)*
- **CeremonyShell action bar sticky bottom:1rem**, primary min-width:210px overflows narrow; overlaps tall stage — index.css:2369,2403. *(medium)*
- **RatingBar tooltip width:15rem absolute** overflows near right margin — ui.tsx:320-345. *(medium)*
- **left-nav sticky height:100vh**, uppercase labels no ellipsis overflow 13rem; no intermediate breakpoint 720-1180px — index.css:372-428. *(medium)*

### Pattern 6 — SVG fixed viewBox / magic-coordinate arrays assuming exactly 6 players — MEDIUM/LOW
- **DarkCourt** viewBox 0 0 600 320, PLAYER_R=14, formation assumes 6/side; F.LASTNAME text no wrap/ellipsis overflows token — MatchReplay.tsx:23-25,35-55,137. *(medium)*
- **MiniCourt** viewBox 0 0 360 180, HOME_POS/AWAY_POS magic arrays tied to 6 players; full names never fit — PreSimDashboard.tsx:56-140. *(low)*
- **MilestoneTree** all magic px (TRUNK_X=90, ROW_HEIGHT=80, svgWidth=460), absolute HTML labels overlaid, clips in narrow container — MilestoneTree.tsx:40-45,184-247. *(medium)*
- **Sparkline fixed 60x20**; fallback bar width=overall% looks like a trend but is a static gauge (misleading) — Sparkline.tsx:7-8; Roster.tsx:443-448. *(low)*
- **app-shell / landing-shell magic-px gradient court markings** (circle 260/340px, calc(50% ± 261px)) don't scale — index.css:7572-7587,7783-7803. *(low)*

### Pattern 7 — Sub-legible tiny fonts (0.5–0.68rem) for load-bearing labels — MEDIUM
Pervasive: cc-gate .lbl 0.5rem, cc-objective tags, MatchCard 8px, KeyPlayers 0.55-0.6rem, KnownValue 0.55rem, ProofChip 0.62rem, CeilingGrade 0.58rem, TermTip badge 0.5rem, EmptyState 0.68rem, ProspectCard 0.55rem, PlayoffBracket 0.5-0.62rem. Below comfortable legibility, don't scale with user font settings, clip in tight rows. — index.css:5751,5769; legibility/*; MatchCard.tsx; ProspectCard.tsx. *(medium)*

### Pattern 8 — Inconsistent / duplicated modal & action-bar shells — MEDIUM
- **3 command-center modals share .command-policy-overlay but FastForwardDialog is hand-rolled** (duplicate focus-trap) vs shared Dialog; undefined sizing props — PreSimDashboard.tsx:168-308,1258-1403. *(medium)*
- **ChampionReveal / RecapStandings reimplement progress pips + action bar inline** instead of CeremonyShell; non-sticky vs sticky inconsistency — RecapStandings.tsx; ChampionReveal.tsx. *(low)*
- **WeeklyChecklist vs PreSimDashboard Sim Lock** overlapping confirm-plan responsibility (parallel surfaces). *(structural)*

### Pattern 9 — Brittle magic-value lookups / scale mismatches (correctness-adjacent) — LOW/MEDIUM
- **Headline accent->RGB 3-way hardcoded lookup**, silent orange fallback — Headline.tsx:23. *(low)*
- **Confidence pip scale mismatch: Roster 4-pip vs PotentialBadge 5-pip**; unbounded filled count widens cell — Roster.tsx:425; PotentialBadge.tsx:12. *(medium)*
- **Potential-sort tier map keys (Elite/High/Solid/Limited) differ from rendered tiers (Elite/High/Mid/Low/Raw)** — Mid/Low/Raw all fall to ?? 4 bucket, silently lumped — Roster.tsx:239-252 vs PotentialBlock:146. Must reconcile to one tier vocabulary. *(medium)*
- **DiffBar calc(50% - x%) inside cell with no width cap** — bar stretches unpredictably — LeagueContext.tsx:76-94. *(low)*
- **AgeCurve/RatingMini percentage heights depend entirely on external CSS box dimensions** — fragile inline↔CSS coupling — Roster.tsx:188,215. *(low)*

### Pattern 10 — Missing responsive overrides on otherwise-tokenized grids — HIGH
- **.ls-side fixed 2-col, NO override at 720/1180px** — wire+tiebreaker jammed on phones — index.css:6394. *(high)*
- **League Wire ticker single horizontal-scroll strip**, headline text never wraps, effectively off-screen — LeagueContext.tsx:586-600; index.css:6666-6677. *(high)*
- **.ls-table-title white-space:nowrap** can't wrap long division names — index.css:6480. *(medium)*
- **Glance cells 3rem/2.2rem fonts only drop to 1-col at 720px** — crowd at 720-1180px — index.css:6415-6452. *(medium)*

---

## 4. API Surface (frontend dependencies)

**Base / data layer (api/client.ts, hooks):**
- apiGet<T>(url) / apiPost<T>(url, body) — fetch wrappers with X-Dodgeball-Launch-Token injection + stale-token refresh-and-retry
- GET /api/launch-token (mint/refresh)
- useApiResource(url) — generic GET hook; useVoiceRegister(tier) -> GET /api/voice-register/{tier}

**Career / status:** GET /api/save-state · GET /api/status · POST /api/saves/unload

**Saves:** GET /api/saves · GET /api/saves/clubs · POST /api/saves/load · POST /api/saves/delete · POST /api/saves/new · POST /api/saves/build-from-scratch · GET /api/saves/starting-staff?seed= · GET /api/saves/starting-prospects?seed= *(latter two are direct fetch() in the wizard steps, NOT via client.ts — fold into client.ts in rewrite)*

**Command center:** GET /api/command-center · POST /api/command-center/plan · POST /api/tactics · POST /api/command-center/season-preview/skip · POST /api/command-center/scout · POST /api/command-center/confirm-lineup · POST /api/command-center/simulate · POST /api/command-center/fast-forward

**Lineup:** POST /api/lineup · POST /api/lineup/auto-reorder · POST /api/lineup/auto-assign

**Matches:** GET /api/matches/{id}/replay · GET /api/matches/{id}/highlights

**Roster:** GET /api/roster · POST /api/roster/release

**Standings / playoffs:** GET /api/standings · GET /api/playoffs/bracket

**Dynasty:** GET /api/dynasty-office · POST /api/recruiting/scout|contact|visit|focus/{id} · POST /api/recruiting/network/upgrade · POST /api/dynasty-office/staff/hire · POST /api/dynasty-office/facilities/upgrade · POST /api/dynasty-office/bench-role *(defined, not called)* · POST /api/dynasty-office/promises

**History:** GET /api/history/my-program?club_id= · GET /api/history/league

**Offseason:** GET /api/offseason/beat · POST /api/offseason/advance · POST /api/offseason/recruit · POST /api/offseason/begin-season · POST /api/offseason/transfer · POST /api/offseason/media

---

## 5. Recommendations for the Rewrite (kill each bug class at the root)

The audit shows the codebase has good faithfulness logic trapped inside an un-systematized presentation layer. Keep all of Section 2's logic; replace the rendering substrate.

### 5.1 One canonical design-token system (kills Pattern 1, 7, and root of all spacing drift)
- Establish a single token source: collapse the duplicated --color-dm-* and --dm-* blocks in index.css into one set. No component may use a literal hex or raw px again.
- Define a spacing scale, a type scale (minimum readable floor — retire all 0.5-0.68rem load-bearing labels), a radius scale, and a color/role palette.
- Migrate every inline `style={{...}}` to token-driven classes or a styling system. This alone removes the highest-count bug across app-shell, wizard, command-center, aftermath, replay, ceremonies, dynasty, standings, roster, and legibility primitives.

### 5.2 A shared layout primitive set (kills Pattern 2, 3, 10)
- `<Truncate>` / a `.truncate` utility that bakes in `min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap` — apply to every name/label cell. This single primitive eliminates the dozens of "long name overflows because the flex item won't shrink" findings.
- A responsive `<Grid>` with auto-collapse breakpoints (replace every hard `repeat(N, ...)` and fixed-px column). Glance strips (do-hist/do-staff), bracket columns (13rem), rl-ratings (280px), tables, and ls-side must collapse, not overflow.
- A scrollable-container primitive that owns its own height relative to the viewport (no guessed `calc(100vh - 180px)` / `min-height:600px`) and never nests a fixed-height scroll inside another scroll — fixes the off-screen-footer family in both wizard steps, RecruitmentChoice, LineupEditor, and the replay sidebar.

### 5.3 A single Modal/Popover primitive with collision handling (kills Pattern 4-overlay, 5, 8)
- One Dialog component: focus-trap, max-height + internal scroll, safe-area padding, `min(vw, rem)` width. Delete the hand-rolled FastForwardDialog and StaffMarketModal's 600px; route all modals through it.
- One Popover that renders in a portal with edge-flip/clamp logic — fixes TermTip/ProofChip rendering off-screen and being clipped by ancestor overflow (critical for a legibility app).
- One sticky ActionBar primitive (safe-area aware, buttons that stack) — unify AftermathActionBar, CeremonyShell, and the inline ChampionReveal/RecapStandings bars.

### 5.4 Centralize the faithfulness logic so it cannot drift (protects Section 2)
- Keep `formatScoreline()`/`survivorDetail()`/`rulesetNames.ts`/`formatters.ts`/`playerDisplay.ts` as the ONLY sources for scorelines, ruleset names, season parsing, and role labels. No surface may read home_survivors/home_game_points or season_id directly.
- Reconcile the tier vocabularies (potential Elite/High/Mid/Low/Raw vs sort map Elite/High/Solid/Limited vs pipeline metals vs ceiling grades) into one documented enum set with one rank map — fixes the silent-lump sort bug while preserving the deliberate de-collision (#26).
- Preserve all proof-source/data-testid/data-player-outcome attributes as a tested contract; carry them through the new component API.

### 5.5 Responsive SVG primitives (kills Pattern 6)
- Make DarkCourt/MiniCourt/MilestoneTree/Sparkline accept a fluid viewBox and a player-count parameter instead of magic 6-player coordinate arrays; ellipsize/abbreviate SVG text via a measured-fit helper. Replace the misleading Sparkline OVR-gauge fallback with the honest NO-DATA empty state already mandated by #36.

### 5.6 Delete dead components before porting
Confirm-and-remove the orphans (Section 1 list): aftermath/MatchCard, StandingsShift/PlayerGrowthBlock/RecruitReactions, ReplaySpeedControl, StaffMarketModal, MilestoneTree, RecentMatchesSidebar, PlayerCompactRow/PlayerTheaterRow/PotentialBadge. They only reintroduce the inline-style overflow patterns if revived.

### 5.7 Fold direct fetch() calls into the client layer
The wizard's starting-staff/starting-prospects use raw fetch() bypassing client.ts (and thus the launch-token guard #91). Route them through apiGet so token refresh + error semantics are uniform.

### 5.8 Establish a frontend verification harness for non-regression
There is no FE test runner; the trust contract in Section 2 is currently guarded only by Python guards on rendered strings and data-testids. Before reskinning, lock the V20 family, draw/playoff-resolution, fog-of-war, and empty-state behaviors behind component/integration tests keyed on the existing data-testid/data-* hooks so the rewrite can prove it kept them green.
