# Dodgeball Manager V3 Chaos Report

Codename: Glassbreak

Audit date: 2026-04-29

## Project Trajectory

### WHERE WE WERE

V1 established Manager Mode save/resume, season lifecycle, and the career state cursor. V2 added scouting, recruitment, Build-a-Club, playoffs, and the ten-beat offseason ceremony, which increased the number of persisted lifecycle surfaces. Earlier chaos coverage already identified one serious recruitment integrity hole: a prospect could be signed by more than one club. V3 then rebuilt roster truth, replay presentation, and pacing controls while keeping the deterministic engine and SQLite boundary intact.

### WHERE WE ARE

The V3 core is resilient against normal and many abnormal interruptions. Fresh career initialization and offseason initialization survived forced process kills with `PRAGMA integrity_check = ok`. SQL injection-style club names, extreme Build-a-Club strings, extreme tactics values, empty rosters, and malicious scout strategy values did not corrupt SQLite or break the full test suite. The application is still not fully bulletproof: direct domain calls can duplicate a prospect across multiple clubs, corrupt JSON payloads crash load paths, and forged cursor state can place the GUI in impossible lifecycle positions.

### WHERE WE ARE GOING

V4 should treat save/load recovery and domain invariants as release-critical foundations. The next release needs single-owner player acquisition, explicit save-validation/error recovery for JSON blobs, and lifecycle guardrails around loaded cursor state before adding more web parity, recruitment depth, or manager automation.

## Critical Failure Points

### CF-1: Duplicate prospect signing still creates two roster owners

Status: FAIL

Reproduction:

1. Create a fresh manager DB with `initialize_manager_career(conn, "aurora", 777)`.
2. Load a season 1 prospect from `load_prospect_pool(conn, 1)`.
3. Call `sign_prospect_to_club(conn, prospect, "aurora", 1)`.
4. Call `sign_prospect_to_club(conn, prospect, "lunar", 1)`.
5. Load all rosters and search for the prospect id.

Observed:

- `prospect_1_000` appeared once in `aurora` and once in `lunar`.
- `prospect_pool.is_signed` was set, but `sign_prospect_to_club()` does not enforce it.
- SQLite integrity remained `ok`, so this is a semantic corruption rather than a physical DB corruption.

Impact:

One player can be owned by multiple clubs, which can poison lineup truth, player stats, recruitment history, and future UI displays. This should be fixed before V4 expands recruitment or web mutation paths.

### CF-2: Corrupt persisted JSON crashes save-load paths

Status: FAIL under damaged save-file conditions

Reproduction:

1. Create a fresh manager career.
2. Replace `dynasty_state.career_state_cursor` with malformed JSON such as `{not-json`.
3. Call `load_career_state_cursor(conn)`.
4. Replace `club_rosters.players_json` with malformed JSON such as `[bad-json`.
5. Call `load_club_roster(conn, "aurora")`.

Observed:

- Cursor load raises `JSONDecodeError`.
- Roster load raises `JSONDecodeError`.
- SQLite integrity remains `ok`.

Impact:

A partially edited, externally damaged, or truncated JSON value makes the save unreadable through normal load paths. V4 should add save validation and a recoverable error path instead of crashing the client.

### CF-3: Forged offseason cursor can route the GUI into an impossible beat

Status: FAIL under tampered cursor state

Reproduction:

1. Create a fresh manager career.
2. Persist `CareerStateCursor(state=SEASON_COMPLETE_OFFSEASON_BEAT, season_number=1, week=0, offseason_beat_index=999)`.
3. Load the cursor.
4. Route to season-complete UI.

Observed:

- The pure `build_offseason_ceremony_beat()` clamps out-of-range beat indices.
- `show_season_complete()` indexes `OFFSEASON_CEREMONY_BEATS[self.cursor.offseason_beat_index]` before that clamp, so a forged save can hard-crash with an out-of-range index.

Impact:

Normal UI flow should not produce this state, but save files are not defensively normalized at load time. V4 should clamp or reject loaded cursor payloads before routing.

## State Corruptions

- Physical SQLite corruption after forced process kill: PASS. Repeated kill tests during career initialization and offseason initialization left readable databases with `PRAGMA integrity_check = ok`.
- Semantic recruitment corruption: FAIL. Duplicate signing leaves one prospect in multiple club rosters.
- JSON payload corruption: FAIL. Malformed JSON does not corrupt SQLite but makes affected save surfaces unreadable.
- Standings/offseason idempotence under interruption: PASS WITH WARNING. Offseason writes remained readable after kill tests; however, several offseason helper functions commit internally, so partial-but-readable offseason state is possible.
- Root seed type drift: WARNING. Build-a-Club accepted `root_seed="MALICIOUS_STRING"` and stored it. Some paths tolerate string seeds through hashing, but paths that later cast with `int(get_state(...))` can crash if the stored value is non-numeric.

## Edge Case Checklist

| Scenario | Result | Notes |
| --- | --- | --- |
| Rename existing `dodgeball_manager.db` before test | PASS | File was not present, so no rename was possible. `dodgeball_sim.db` was copied to `dodgeball_sim.chaos-backup.db` per repo guidance. |
| Force kill during career initialization | PASS | Disposable DB remained readable with integrity `ok`. |
| Force kill during offseason initialization | PASS | Disposable DB remained readable with integrity `ok`. |
| SQL injection-style Build-a-Club names | PASS WITH WARNING | Parameterized writes preserved tables; 5,024-character name stored successfully. No length cap. |
| Non-integer root seed | WARNING | Stored successfully as text; later integer-cast paths are at risk. |
| Extreme tactics values | PASS | Values persisted through `CoachPolicy.as_dict()` normalized to 0..1. |
| Empty engine rosters | PASS WITH WARNING | Engine ended immediately with no winner and no crash. This is stable but produces a degenerate match. |
| Empty user roster in scheduled match | PASS WITH WARNING | Match completed immediately with the non-empty opponent as winner. |
| Duplicate prospect signing | FAIL | Same prospect can exist on two rosters. |
| All scouts assigned to same invalid target | PASS WITH WARNING | No crash or SQL injection; invalid assignment strings persisted and scouting tick wrote no events. |
| Malicious scout mode/priority strings | PASS WITH WARNING | Stored without crash, but there is no validation/normalization. |
| Direct invalid career transition | PASS | `advance()` blocked `season_active_pre_match -> next_season_ready`. |
| Forged impossible career cursor | FAIL WITH TAMPERED SAVE | Load accepts impossible beat index; UI route can crash. |
| Full regression test gate | PASS | `python -m pytest -q`: 318 passed, one pytest cache access warning. |

## Test Evidence

- Probe databases: `output/chaos-v3-probes/`
- Full suite: `python -m pytest -q`
- Result: 318 passed
- Warning: pytest could not write cache under `.pytest_cache` because of local access permissions.

## Stability Verdict

V3 is stable enough to serve as the technical foundation for V4, but it is not bulletproof. The core engine, lifecycle happy path, SQLite durability, and V3 pacing/roster tests are sound. The V4 sprint should include a small pre-feature hardening task for duplicate signing, cursor normalization, root seed validation, and recoverable corrupt-save handling before expanding recruitment or web mutation surfaces.
