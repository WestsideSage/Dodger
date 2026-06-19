# Floodlight Preservation Checklist (audit §2 → phase → test)

Source of truth: ../specs/2026-06-19-ui-redesign-audit.md §2 (97 behaviors).
Rule: a phase may not be marked done until every behavior assigned to it is green
by its listed test strategy. Test strategy ∈ {python-guard, vitest, e2e, manual-proof}.

## Phase 1 — App shell + SaveMenu
| # | Behavior (short) | Test strategy |
|---|---|---|
| 9 | Save-list record W-L-D only when wins defined; never fabricated 0-0 | vitest (SaveMenu row) |
| 10 | ruleset_selection pinned 'official_foam' at every create path | vitest + python-guard |
| 82 | Router trusts LIVE career state over post-sim next_state | vitest (App router) |
| 83 | Offseason vs in-season classification drives screen + header | vitest |
| 84 | Season/week/year fallback precedence; post-sim week priority | vitest |
| 85 | Incompatible saves hidden by default, non-loadable, labeled | vitest |
| 86 | Continue-career picks first non-incompatible non-debug save | vitest |
| 87 | Debug/test saves two-gate (?debug=true AND opt-in) | vitest |
| 88 | Active-tab persists to ?tab= only in game/offseason, validated | vitest |
| 89 | Save-state fetch failure falls back to menu, not broken shell | vitest |
| 91 | Launch-token guard: stale 403 refresh-retry vs business 403 verbatim | vitest (client.ts) |

## Phase 2 — Command loop + aftermath + replay
| # | Behavior (short) | Test strategy |
|---|---|---|
| 1–8 | V20 scoring-model family (formatScoreline/survivorDetail, wire, hero, strip, standings, bracket, recap) | vitest + python-guard |
| 11–18 | Playoff/draw/outcome truth (decided_by, draw label, verdict fallback, worlds_user, missed_playoffs) | vitest |
| 41–50 | Replay integrity (live-state eliminations, fresh-court, segment reveal, turning point, highlights map) | vitest + e2e |
| 90, 93–95 | Optimistic policy rollback; FALLBACK_BRIEFING; plan alignment; recent-results/stakes | vitest |

## Phases 3–8 — assigned by area (each phase's own plan finalizes per-item test strategy)
- Phase 3 Roster/lineup/player: #36, #51–#58
- Phase 4 Standings/league: #6, #7, #15, #16, #33, #34, #38, #96
- Phase 5 Dynasty/recruiting/history: #19–#28, #30, #59–#66, #97
- Phase 6 Ceremonies/offseason: #17, #18, #29, #31, #32, #35, #67–#75
- Phase 7 New-game wizard: #22, #76–#81
- Phase 8 Sweep (legibility primitives + responsive/a11y): #20, #21, #23–#27, #30, #37, #39, #40
