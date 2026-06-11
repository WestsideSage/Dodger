export type RecruitingStatus =
    | 'UNSCOUTED'
    | 'SCOUTED'
    | 'CONTACTED'
    | 'VISITED'
    | 'INTERESTED'
    | 'LOCKED_OUT';

export interface PlayerRatings {
    accuracy: number;
    power: number;
    dodge: number;
    catch: number;
    stamina: number;
    tactical_iq: number;
    catch_courage?: number;
    throw_selection_iq?: number;
    conditioning_curve?: number;
}

export interface PlayerTraits {
    potential: number;
    growth_curve: number;
    consistency: number;
    pressure: number;
}

export interface Player {
    id: string;
    name: string;
    ratings: PlayerRatings;
    traits: Omit<PlayerTraits, 'potential'>;
    age: number;
    club_id: string | null;
    newcomer: boolean;
    archetype: string;
    overall: number;
    role: string;
    potential_tier: string;
    scouting_confidence: number;
    weekly_ovr_history: number[];
    // Phase 5 — Growth legibility: Player Card fields
    potential_ceiling: number;
    headroom: number;
    projected_growth: 'growing' | 'plateauing' | 'declining';
    /** null = no season-over-season history yet (honest empty-state) */
    ovr_season_trend: number[] | null;
    /** Strongest base attribute (e.g. "Accuracy"), derived from ratings. */
    bio_strongest_attr: string;
    /** Second-strongest base attribute (e.g. "Power"), derived from ratings. */
    bio_secondary_attr: string;
}

export interface RosterResponse {
    club_id: string;
    roster: Player[];
    default_lineup: string[];
    /** V19 Task 8: ON = the offseason re-seats the fielded six automatically;
     *  OFF = hands-on (a manual lineup save flips this off implicitly). */
    lineup_auto_reorder?: boolean;
}

export type Approach = 'aggressive' | 'patient' | 'mixed';
export type TargetFocus = 'their_stars' | 'ball_holders' | 'spread';
export type CatchPosture = 'go_for_catches' | 'play_safe' | 'opportunistic';
export type OpeningRushCommit = 'all_in' | 'balanced' | 'hold_back';
export type OpeningRushTarget = 'nearest' | 'strongest_side' | 'center';

export interface CoachPolicy {
    approach: Approach;
    target_focus: TargetFocus;
    catch_posture: CatchPosture;
    rush_commit: OpeningRushCommit;
    rush_target: OpeningRushTarget;
}

export interface StatusResponse {
    status: string;
    state: {
        state: string;
        season_number: number;
        week: number;
        offseason_beat_index: number;
        match_id: string | null;
    };
    context: {
        season_id: string;
        player_club_id: string;
        player_club_name: string | null;
        season_year: number | null;
    };
}

export interface SimResponse {
    status: string;
    message?: string;
    simulated_count?: number;
    stop_reason?: string;
    match_id?: string | null;
    next_state?: string | null;
}

export interface MatchStartContext {
    config_version: string;
    difficulty: string;
    meta_patch: Record<string, unknown> | null;
    team_policies: Record<string, CoachPolicy>;
}

export interface MatchEndContext {
    reason: string;
    moment_events?: MomentEvent[];
}

export interface ThrowContext {
    tick: number;
    thrower_selection: Record<string, unknown>;
    target_selection: Record<string, unknown>;
    difficulty: string;
    policy_snapshot: CoachPolicy;
    chemistry_delta: number;
    meta_patch: Record<string, unknown> | null;
    rush_context: Record<string, unknown>;
    sync_context: { is_synced: boolean; sync_modifier: number };
    calc: Record<string, unknown>;
    fatigue: Record<string, unknown>;
    pressure_active: boolean;
    pressure_reason?: string;
    pressure_modifier?: number;
    catch_decision?: Record<string, unknown> | null;
}

export type ReplayEventContext = MatchStartContext | MatchEndContext | ThrowContext;

export interface DramaticCatchMoment {
    kind: 'dramatic_catch';
    match_id: string;
    tick: number;
    catcher_id: string;
    catcher_team_id: string;
    thrower_id: string;
    thrower_team_id: string;
    returning_player_id: string;
    active_count_a: number;
    active_count_b: number;
    display_text?: string;
    // Official multi-game matches: which game (1-based) the moment happened
    // in; the tick is a per-game engine tick. Null/absent for rec matches.
    game_number?: number | null;
    // Server-resolved position in proof_events where this moment belongs.
    // Null when the persisted stream predates game/tick anchoring metadata.
    anchor_index?: number | null;
}

export interface LateGameEscapeMoment {
    kind: 'late_game_escape';
    match_id: string;
    tick: number;
    survivor_id: string;
    survivor_team_id: string;
    attacker_team_id: string;
    attacker_count: number;
    display_text?: string;
    // Official multi-game matches: which game (1-based) the moment happened
    // in; the tick is a per-game engine tick. Null/absent for rec matches.
    game_number?: number | null;
    // Server-resolved position in proof_events where this moment belongs.
    // Null when the persisted stream predates game/tick anchoring metadata.
    anchor_index?: number | null;
}

export interface OneVOneFinaleMoment {
    kind: 'one_v_one_finale';
    match_id: string;
    tick: number;
    player_a_id: string;
    player_b_id: string;
    tick_started: number;
    display_text?: string;
    // Official multi-game matches: which game (1-based) the moment happened
    // in; the tick is a per-game engine tick. Null/absent for rec matches.
    game_number?: number | null;
    // Server-resolved position in proof_events where this moment belongs.
    // Null when the persisted stream predates game/tick anchoring metadata.
    anchor_index?: number | null;
}

export interface GassedCollapseMoment {
    kind: 'gassed_collapse';
    match_id: string;
    tick: number;
    player_id: string;
    team_id: string;
    fatigue_pct: number;
    display_text?: string;
    // Official multi-game matches: which game (1-based) the moment happened
    // in; the tick is a per-game engine tick. Null/absent for rec matches.
    game_number?: number | null;
    // Server-resolved position in proof_events where this moment belongs.
    // Null when the persisted stream predates game/tick anchoring metadata.
    anchor_index?: number | null;
}

export interface FloodThrowMoment {
    kind: 'flood_throw';
    match_id: string;
    tick: number;
    thrower_team_id: string;
    thrower_ids: string[];
    display_text?: string;
    // Official multi-game matches: which game (1-based) the moment happened
    // in; the tick is a per-game engine tick. Null/absent for rec matches.
    game_number?: number | null;
    // Server-resolved position in proof_events where this moment belongs.
    // Null when the persisted stream predates game/tick anchoring metadata.
    anchor_index?: number | null;
}

export interface ComebackMoment {
    kind: 'comeback';
    match_id: string;
    tick: number;
    team_id: string;
    deficit_at_low_point: number;
    catches_during_comeback: number;
    display_text?: string;
    // Official multi-game matches: which game (1-based) the moment happened
    // in; the tick is a per-game engine tick. Null/absent for rec matches.
    game_number?: number | null;
    // Server-resolved position in proof_events where this moment belongs.
    // Null when the persisted stream predates game/tick anchoring metadata.
    anchor_index?: number | null;
}

export type MomentEvent =
  | DramaticCatchMoment
  | LateGameEscapeMoment
  | OneVOneFinaleMoment
  | GassedCollapseMoment
  | FloodThrowMoment
  | ComebackMoment;

export interface ReplayEvent {
    index: number;
    tick: number;
    event_type: 'match_start' | 'match_end' | 'throw' | 'stall_reset';
    phase: string;
    actors: Record<string, string | null>;
    context: ReplayEventContext;
    probabilities: Record<string, number>;
    rolls: Record<string, number>;
    outcome: Record<string, string | number | null>;
    state_diff: Record<string, unknown>;
    label: string;
    detail: string;
}

export interface ProofContextSection {
    items: string[];
    thrower_fatigue?: number;
    target_fatigue?: number;
}

export interface ScoreState {
    home_living: number;
    away_living: number;
    home_eliminated_player_ids: string[];
    away_eliminated_player_ids: string[];
}

export interface ReplayProofEvent {
    sequence_index: number;
    tick: number;
    // Official matches: 1-based game this throw belongs to and the per-game
    // engine tick (both null for rec/legacy streams).
    game_number?: number | null;
    engine_tick?: number | null;
    // The queued teammate a valid catch brought back, when the play had one.
    returned_player_id?: string | null;
    returned_player_name?: string | null;
    thrower_id: string;
    thrower_name: string;
    target_id: string;
    target_name: string;
    offense_club_id: string;
    defense_club_id: string;
    resolution: string;
    is_key_play: boolean;
    proof_tags: string[];
    summary: string;
    detail: string;
    odds: Record<string, number>;
    rolls: Record<string, number>;
    fatigue: ProofContextSection;
    decision_context: ProofContextSection;
    tactic_context: ProofContextSection;
    liability_context: ProofContextSection;
    score_state: ScoreState;
}

export interface TopPerformer {
    player_id: string;
    player_name: string;
    club_name?: string;
    score: number;
    eliminations_by_throw: number;
    catches_made: number;
    dodges_successful: number;
}

export interface OfficialClockView {
    limit_seconds: number;
    elapsed_seconds: number;
}

export interface OfficialGameScoreView {
    team_a_id: string;
    team_b_id: string;
    team_a_games: number;
    team_b_games: number;
    team_a_ties: number;
    team_b_ties: number;
    no_point_games: number;
}

export interface OfficialBurdenView {
    team_id: string | null;
    basis: string;
    clock_status: string;
    seconds_remaining: number;
    play_n_count: number;
}

export interface OfficialBallView {
    ball_id: string;
    state: string;
    side?: string | null;
    controller_player_id?: string | null;
}

export interface OfficialTeamStateView {
    team_id: string;
    active_ids: string[];
    queued_ids: string[];
    entering_id?: string | null;
    unavailable_ids: string[];
}

export interface OfficialRuleCallView {
    rule_label: string;
    summary: string;
    timestamp_seconds: number;
}

export interface OfficialReplayState {
    ruleset: string;
    rulebook_version: string;
    official_payload_version: string;
    match_clock?: OfficialClockView | null;
    game_clock?: OfficialClockView | null;
    game_score?: OfficialGameScoreView | null;
    mode: string;
    burden?: OfficialBurdenView | null;
    balls: OfficialBallView[];
    teams: OfficialTeamStateView[];
    player_statuses: Record<string, string>;
    rule_calls: OfficialRuleCallView[];
}

export interface MatchReplayResponse {
    match_id: string;
    season_id: string;
    week: number;
    home_club_id: string;
    home_club_name: string;
    away_club_id: string;
    away_club_name: string;
    winner_club_id: string | null;
    winner_name: string;
    home_survivors: number;
    away_survivors: number;
    config_version?: string | null;  // V11: "official:..." when run under official ruleset
    scoring_model?: string;
    home_game_points?: number;
    away_game_points?: number;
    home_games_won?: number;
    away_games_won?: number;
    tied_games?: number;
    no_point_games?: number;
    events: ReplayEvent[];
    moment_events: MomentEvent[];
    proof_events: ReplayProofEvent[];
    key_play_indices: number[];
    // Per-game story of an official match (set results in order, running
    // points, proof-index ranges). Null for legacy/rec matches.
    game_segments?: ReplayGameSegment[] | null;
    // V20 intent context: the locked match policies each club actually
    // played under (club_id -> policy dict). Null for legacy/rec matches.
    team_policies?: Record<string, Record<string, string>> | null;
    official_state?: OfficialReplayState | null;
    report: {
        winner_name: string;
        match_mvp_player_id: string | null;
        match_mvp_name: string | null;
        top_performers: TopPerformer[];
        turning_point: string;
        // Proof-timeline index of the same event the turning_point text
        // describes, so "jump to" lands on exactly that play.
        turning_point_index?: number | null;
        evidence_lanes: CommandDashboardLane[];
    };
    broadcast_frame?: BroadcastFrame | null;
    playoff_frame?: PlayoffFrame | null;
    commentary_inserts?: CommentaryInsert[];
}

export interface ReplayGameSegment {
    game_number: number;
    winner_club_id: string | null;
    result_type: string; // "elimination" | "no_point" | "tie" | "cloth_active_count"
    home_points: number;
    away_points: number;
    home_running_points: number;
    away_running_points: number;
    home_final_actives: number;
    away_final_actives: number;
    first_proof_index?: number | null;
    last_proof_index?: number | null;
}

export interface StandingRow {
    club_id: string;
    club_name: string;
    wins: number;
    losses: number;
    draws: number;
    points: number;
    elimination_differential: number;
    // V20 §7.3: the differential that actually ranks official careers
    // (the survivor diff is a legacy/rec stat — noise on officials).
    game_point_differential?: number;
    total_game_points_scored?: number;
    is_user_club: boolean;
    latest_approach?: string | null;
    program_archetype?: string;
    program_trajectory_label?: string;
}

export interface StandingsResponse {
    season_id: string;
    standings: StandingRow[];
    recent_matches?: RecentMatchSummary[];
    total_weeks: number;
    current_week: number;
    user_games_remaining?: number;
    playoff_spots: number;
    is_offseason?: boolean;
    // V20 §7.3: which differential ranks this career.
    is_official_career?: boolean;
}

export interface RecentMatchSummary {
    match_id: string;
    week: number;
    summary: string;
    winner_name: string;
}

export interface ScheduleRow {
    match_id: string;
    week: number;
    home_club_id: string;
    home_club_name: string;
    away_club_id: string;
    away_club_name: string;
    status: string;
    is_user_match: boolean;
    stage: string;
}

export interface PlayoffSeed {
    seed: number;
    club_id: string;
    club_name: string;
    wins: number;
    losses: number;
    draws: number;
    is_player_club: boolean;
}

export interface PlayoffBracketMatch {
    match_id: string;
    home_club_id: string;
    home_club_name: string;
    away_club_id: string;
    away_club_name: string;
    home_survivors: number | null;
    away_survivors: number | null;
    winner_club_id: string | null;
    status: string;
    // Foam/official matches score by game points, not survivors; present so the
    // bracket can render the meaningful scoreline instead of a survivors 0-0.
    scoring_model?: string | null;
    home_game_points?: number | null;
    away_game_points?: number | null;
    // Task 1 (2026-05-27 playtest-fixes): tiebreaker surfacing. NULL on
    // regulation wins / unplayed matches; "overtime" or "seed_tiebreaker"
    // when the resolver had to step in.
    decided_by?: 'overtime' | 'seed_tiebreaker' | 'regulation' | null;
    narrative_note?: string | null;
}

export interface PlayoffBracketRound {
    round: string;
    matches: PlayoffBracketMatch[];
}

export interface PlayoffBracketResponse {
    active: boolean;
    season_id?: string;
    format?: string;
    status?: string;
    seeds?: PlayoffSeed[];
    rounds?: PlayoffBracketRound[];
    champion_club_id?: string | null;
    champion_club_name?: string | null;
    player_club_id?: string | null;
}

export interface ScheduleResponse {
    season_id: string;
    schedule: ScheduleRow[];
}

export interface NewsItem {
    tag: string;
    text: string;
    match_id: string | null;
    player_id: string | null;
}

export interface NewsResponse {
    season_id: string;
    items: NewsItem[];
}

export interface MatchupDetails {
  opponent_record: string;
  last_meeting: string;
  key_matchup: string;
  key_threat?: KeyThreat | null;
  framing_line: string;
  broadcast_frame?: BroadcastFrame | null;
  adaptation_summary?: string | null;
  staff_impact?: StaffImpact[];
  tactical_diff?: TacticalDiff;
}

export interface KeyThreat {
  name: string;
  archetype: string;
  ovr: number;
}

export interface ReadinessGate {
  id: string;
  label: string;
  short_label: string;
  detail: string;
  ready: boolean;
}

export interface WeekBriefing {
  readiness: {
    gates: ReadinessGate[];
    total: number;
    ready_count: number;
    is_ready_to_lock: boolean;
    items_remaining: number;
    next_issue: string;
  };
  edge: {
    net_starter_ovr: number;
    standing: 'favorite' | 'even' | 'underdog';
    headline?: string;
    advisory_detail?: string;
    advisory?: boolean;
  };
  fatigue: {
    at_risk_count: number;
    min_stamina: number | null;
  };
  form: {
    recent_record: string;
    rank: number | null;
    regular_season_record: string;
    games_remaining: number;
  };
  threat: KeyThreat | null;
  match_context: {
    is_home: boolean;
    playoff_stage: string | null;
  };
  league_leader: string | null;
  staff_recommendation: {
    action: 'keep' | 'change';
    recommended_intent: string | null;
    reason: string;
  };
  recommendation: {
    verdict: 'aligned' | 'adjust';
    advised_intent: string | null;
    reason: string;
    advisory: boolean;
  };
}

export interface RecruitingActionResult {
  action: 'scout' | 'contact' | 'visit';
  headline: string;
  interest_before: number;
  interest_after: number;
  ovr_band_before: number[];
  ovr_band_after: number[];
  next_step: string;
}

export interface RecruitingActionResponse {
  status: string;
  result: RecruitingActionResult;
}

export interface StaffImpact {
  department: string;
  name: string;
  rating_primary: number;
  effect: string;
}

export interface TacticalDiffRow {
  axis: string;
  label: string;
  player_value: string;
  opponent_value: string | null;
  opponent_known: boolean;
  // WT-30: present only on axes revealed after scouting. 'tape' = an observed
  // tendency (frequency over completed games); 'playbook' (V19b) = the
  // opponent archetype's base policy — real week-1 intel before tape exists.
  // Never the hidden upcoming plan.
  opponent_source?: 'tape' | 'playbook';
  confidence?: number | null;
  confidence_label?: 'strong' | 'leans' | 'mixed' | 'playbook lean';
  sample?: number;
}

export interface TacticalDiffIntel {
  source: string;
  text: string;
}

export interface ColdStartPositionGroup {
  label: string;
  count: number;
  avg_ovr: number;
}

export interface TacticalDiffColdStart {
  program_archetype?: string | null;
  roster_shape?: { throwers: number; defenders: number; total: number } | null;
  // BUG #10 enrichment: strongest/weakest archetype family by visible OVR, and
  // the opponent's already-player-facing W-L-D record. Both derivable; never
  // sourced from the opponent's hidden upcoming plan.
  position_groups?: {
    strongest: ColdStartPositionGroup;
    weakest: ColdStartPositionGroup;
    single_family: boolean;
  } | null;
  recent_form?: string | null;
  threat?: { name: string; archetype: string; ovr: number } | null;
}

export interface TacticalDiff {
  player_plan: TacticalDiffRow[];
  opponent_intel: TacticalDiffIntel[];
  opponent_unscouted: boolean;
  // WT-30 scout state.
  scouted?: boolean;
  intel_revealed?: boolean;
  tape_axes_revealed?: number;
  cold_start?: TacticalDiffColdStart | null;
  note: string;
}

export interface BroadcastTag {
  label: string;
  tone: string;
  proof_source: string;
}

export interface BroadcastHook {
  text: string;
  proof_source: string;
}

export interface BroadcastFrame {
  stakes_tag?: BroadcastTag | null;
  rivalry_tag?: BroadcastTag | null;
  archetype_tag?: BroadcastTag | null;
  historical_hook?: BroadcastHook | null;
  voice_slot: string;
}

export interface PlayoffFrame {
  label: string;
  title: string;
  proof_source: string;
}

export interface CommentaryInsert {
  text: string;
  source_event_id: string | number;
  source_record_id: string;
  source_event_index: number;
  proof_source: string;
}

export interface HighlightBeat {
  kind: string;
  title: string;
  body: string;
  tick: number;
  source_event_id: string | number;
  source_event_index: number;
  proof_source: string;
}

export interface MatchHighlightsResponse {
  match_id: string;
  beats: HighlightBeat[];
}

export interface LineupPlayer {
    id: string;
    name: string;
    overall: number;
    age?: number;
    potential?: number;
    stamina?: number;
}

export interface CommandCenterPlan {
    season_id: string;
    week: number;
    player_club_id: string;
    is_bye?: boolean;
    intent: string;
    available_intents: string[];
    opponent: {
        club_id: string | null;
        name: string;
    };
    department_heads: Array<{
        department: string;
        name: string;
        rating_primary: number;
        rating_secondary: number;
        voice: string;
    }>;
    department_orders: Record<string, string>;
    recommendations: Array<{
        department: string;
        voice: string;
        text: string;
    }>;
    warnings: string[];
    lineup: {
        player_ids: string[];
        players: LineupPlayer[];
        summary: string;
    };
    opponent_lineup?: {
        players: LineupPlayer[];
    };
    tactics: CoachPolicy;
    history_count: number;
    matchup_details?: MatchupDetails;
    briefing?: WeekBriefing;
}

export interface CommandDashboardLane {
    title: string;
    summary: string;
    items: string[];
}

export interface CommandDashboard {
    season_id: string;
    week: number;
    match_id: string;
    stage?: string;
    opponent_name: string;
    result: string;
    lanes: CommandDashboardLane[];
}

export interface CommandHistoryRecord {
    history_id: number;
    season_id: string;
    week: number;
    club_id: string;
    match_id: string | null;
    opponent_club_id: string | null;
    intent: string;
    plan: CommandCenterPlan;
    dashboard: CommandDashboard;
    created_at: string;
}

export interface CommandCenterResponse {
    season_id: string;
    week: number;
    player_club_id: string;
    player_club_name: string;
    current_objective: string;
    plan: CommandCenterPlan;
    latest_dashboard: CommandDashboard | null;
    history: CommandHistoryRecord[];
    season_preview?: SeasonPreview | null;
    // Career ruleset ("official_foam" | "official_no_sting" | "official_cloth"
    // | null/absent for legacy generic). Lets plan-editing surfaces disclose
    // announced-only knobs (official engine does not enforce opening rush — WT-20).
    ruleset_selection?: string | null;
}

export interface SeasonPreview {
    regular_season_weeks: number;
    bye_week: number | null;
    bye_text: string;
    playoff_cut: number;
    total_clubs: number;
    top_goal: string;
    strength: { archetype: string; archetype_key: string; avg_overall: number } | null;
    weakness: { archetype: string; archetype_key: string; avg_overall: number } | null;
    skipped: boolean;
}

// A post-match body paragraph carries its own audience, assigned by the
// backend that authors the copy. "result" = what happened on court,
// "you" = the player's own plan, "them" = the opponent's posture. Surfaces
// read this tag instead of prefix-matching the prose.
export interface AftermathParagraph {
    text: string;
    audience: 'you' | 'them' | 'result';
}

export interface Aftermath {
    headline: string;
    match_card: {
        home_club_id: string;
        away_club_id: string;
        winner_club_id: string | null;
        home_survivors: number;
        away_survivors: number;
        scoring_model?: string;
        home_game_points?: number;
        away_game_points?: number;
        // Official matches: per-game set results in playing order, so the
        // aftermath can show how the game points accumulated.
        games?: Array<{
            game_number: number;
            winner_club_id: string | null;
            home_points: number;
            away_points: number;
            result_type: string;
        }>;
    } | null;
    player_growth_deltas: Array<{
        player_id: string;
        player_name: string;
        attribute: string;
        delta: number;
    }>;
    development_feedback?: {
        focus: string;
        focus_label: string;
        summary: string;
        progress: string;
        players: string[];
    };
    bye_recovery?: {
        summary: string;
        players: string[];
    };
    standings_shift: Array<{
        club_id: string;
        club_name: string;
        old_rank: number;
        new_rank: number;
    }>;
    recruit_reactions: Array<{
        prospect_id: string;
        prospect_name: string;
        interest_delta: string;
        evidence: string;
    }>;
    body: AftermathParagraph[];
    verdict?: string;
    top_performers?: TopPerformer[];
    // V14 Task 1: deterministic, proof-backed Primary Factor explaining the
    // result. Absent on bye weeks / payloads where derivation failed —
    // components must treat undefined as "render nothing".
    primary_factor?: {
        code: string;
        title: string;
        sentence: string;
        confidence: 'high' | 'medium' | 'low';
        evidence_chips: string[];
    };
    // WT-32: an ADJACENT "Manager Lesson" surfaced ONLY when the Primary Factor
    // is inconclusive (a genuine coin-flip loss). It answers "what could *I*
    // have changed?" from controllable prep — or, when nothing controllable
    // applied, honestly says so (`controllable: false`). It NEVER replaces or
    // reranks the event-derived primary_factor. Absent on conclusive results,
    // wins/draws, and bye weeks — components treat undefined as "render nothing".
    manager_lesson?: {
        code: string;
        title: string;
        sentence: string;
        controllable: boolean;
        evidence_chips: string[];
    };
    // Task 3 (2026-05-28 playtest-fixes): derived narrative facts about
    // the resolved match. Frontend copy generators (e.g. ComebackCard)
    // gate themselves on these fields so a shutout never renders
    // "clawed it back" text. Absent on bye weeks and on payloads where
    // derivation failed — components must treat undefined as "render
    // nothing narrative".
    narrative_beats?: {
        was_shutout: boolean;
        largest_deficit: number;
        lead_changes: number;
        selected_plan_label: string;
        actual_plan_executed: string;
    };
    // Task 1 (2026-05-27 playtest-fixes): present only for playoff matches
    // that needed a tiebreaker (overtime / seed). The banner renders
    // ``narrative_note`` verbatim; ``decided_by`` selects the chip text.
    playoff_resolution?: {
        decided_by: 'overtime' | 'seed_tiebreaker' | 'regulation';
        narrative_note: string;
        winner_club_id: string;
        loser_club_id: string;
        stage: string;
        player_outcome: 'advanced' | 'eliminated' | null;
    };
    // Task 9 (2026-05-28 playtest-fixes): present only when the player
    // lost a playoff match (their season ended). Drives the one-screen
    // EliminationCeremony shown before the regular-season recap.
    elimination?: {
        stage: string;
        opponent_name: string;
        player_score: number;
        opponent_score: number;
        decided_by: 'overtime' | 'seed_tiebreaker' | 'regulation';
        cause: string;
        contributors: Array<{ player_name: string; score: number }>;
        returning: string[];
    };
    // Task 10 (2026-05-28 playtest-fixes): present only when the player
    // won the title-clinching final. Drives the celebration hero shown
    // first on the aftermath screen, before the standard debrief.
    championship?: {
        champion_name: string;
        opponent_name: string;
        player_score: number;
        opponent_score: number;
        decided_by: 'overtime' | 'seed_tiebreaker' | 'regulation';
    };
    // Task 11 (2026-05-28 playtest-fixes): present only on a loss. Up to
    // three actionable next steps ranked from existing engine values.
    improvement_panel?: Array<{
        category: 'position_group' | 'condition' | 'recruit';
        title: string;
        detail: string;
    }>;
}

export interface OffseasonAward {
    player_name: string;
    club_name: string;
    award_type: string;
    award_name: string;
    season_stat: number;
    season_stat_label: string;
    career_stat: number;
    ovr: number;
    extra_stats?: {
        throw_elims: number;
        catches: number;
        times_eliminated: number;
        matches: number;
    } | null;
}

export interface OffseasonRetiree {
    name: string;
    ovr_final: number;
    career_elims: number;
    championships: number;
    seasons_played: number;
    potential_tier: string;
}

export interface OffseasonSigning {
    name: string;
    ovr: number;
    age?: number;
    role?: string;
    club_name?: string;
}

export interface OffseasonFixture {
    week: number;
    home: string;
    away: string;
    is_player_match: boolean;
}

// --- Per-beat payload interfaces ---

export interface AwardsBeatPayload {
    awards: OffseasonAward[];
}

export interface RetirementsBeatPayload {
    retirees: OffseasonRetiree[];
}

export interface ChampionBeatPayload {
    // `champion` is absent when the season ended without a champion (backend returns `{}`)
    champion?: { club_name: string; wins: number; losses: number; draws: number; title_count: number };
}

export interface RecapBeatPayload {
    standings: Array<{
        rank: number;
        club_name: string;
        wins: number;
        losses: number;
        draws: number;
        points: number;
        diff: number;
        is_player_club: boolean;
    }>;
    /**
     * Work item #3: present only when the user's club finished OUTSIDE the
     * playoff cut. `finish` is the 1-based seeding position, `cutoff` the number
     * of playoff berths, `total` the league size. Absent when the club qualified.
     */
    missed_playoffs?: {
        finish: number;
        cutoff: number;
        total: number;
    };
}

export interface DevelopmentPlayer {
    name: string;
    ovr_before: number;
    ovr_after: number;
    delta: number;
    notes?: string[];
    // Phase 5 — Growth legibility: per-attribute deltas and ceiling
    attr_deltas?: Record<string, number>;
    potential_ceiling?: number | null;
}

export interface DevelopmentBeatPayload {
    players: DevelopmentPlayer[];
}

export interface RookieClassPreviewBeatPayload {
    class_size: number;
    top_prospects: number;
    free_agents: number;
    archetypes: Array<{ name: string; count: number }>;
    storylines: string[];
}

export interface RecruitmentProspectChoice {
    prospect_id: string;
    name: string;
    /** Verified OVR — present for free agents only (league veterans with
        public history). Prospects carry public_ovr_band instead (V16). */
    overall?: number;
    age: number;
    hometown: string;
    archetype: string;
    kind: 'prospect' | 'free_agent';
    pipeline_tier?: number;
    fit_score?: number;
    /** Scouted public OVR band [low, high] — prospects only. */
    public_ovr_band?: number[];
    scouted?: boolean;
    contacted?: boolean;
    visited?: boolean;
    /** Courtship interest (%): strengthens the contested Signing Day offer. */
    interest?: number;
}

/** Resolution of a Signing Day pick through the contested round (V16). */
export interface SigningOutcome {
    kind: 'signed' | 'sniped' | 'free_agent_signed';
    prospect_id: string;
    prospect_name: string;
    explanation: string;
    winning_club_id?: string;
    winning_club_name?: string;
    winning_offer?: number;
    your_offer?: number;
    your_interest?: number;
    actions_taken?: number;
    rival_club_name?: string | null;
    rival_offer?: number | null;
    /** Pre-signing scouted band, for the post-signing reveal line. */
    scouted_band?: number[];
    /** "Scouted L–H → verified OVR N." — present on contested wins. */
    reveal?: string;
}

export interface SigningCard {
    player_id: string;
    name: string;
    ovr: number;
    role: string;
    club_id: string;
    club_name: string;
    user_interaction: {
        scouted: boolean;
        contacted: boolean;
        visited: boolean;
        locked_out: boolean;
    };
    outcome_kind: 'my_signing' | 'rival_signing' | 'surprise';
    reason: string;
    round_number: number;
}

export interface RecruitmentBeatPayload {
    player_signing: OffseasonSigning | null;
    other_signings: OffseasonSigning[];
    signings?: SigningCard[];
    available_prospects: RecruitmentProspectChoice[];
    signed_count: number;
    signing_limit: number;
    remaining_signings: number;
    roster_size: number;
    roster_limit: number;
}

export interface RatifiedRecordEntry {
    record_id?: string;
    record_type: string;
    holder_name: string;
    previous_value: number;
    new_value: number;
    detail: string;
    proof_source?: string;
    // Phase 7: club scope filter fields
    holder_club_id?: string;
    is_my_club?: boolean;
    /** False when the same holder extended their own record (bookkeeping);
        true for first-time records and dethronings. Missing on payloads
        ratified before this field existed — treat as true. */
    is_new_holder?: boolean;
    previous_holder_name?: string;
    /** V21 middle tier: set when a same-holder extension crossed a
        round-number boundary ("Passed 100 career eliminations"). */
    milestone_label?: string;
}

export interface RecordsRatifiedBeatPayload {
    records: RatifiedRecordEntry[];
    /** Phase 7: true when no seasons have been ratified yet (fresh league). */
    records_book_empty?: boolean;
}

export interface HallOfFameInductee {
    player_id?: string;
    player_name: string;
    legacy_score: number;
    threshold: number;
    reasons: string[];
    seasons_played: number;
    championships: number;
    awards_won: number;
    total_eliminations: number;
    proof_source?: string;
}

export interface HofInductionBeatPayload {
    inductees: HallOfFameInductee[];
}

export interface ScheduleRevealBeatPayload {
    fixtures: OffseasonFixture[];
    season_label: string;
    prediction: string;
}

// Beats that carry data only in `body` text have empty payloads
export type EmptyBeatPayload = Record<string, never>;

// Base fields shared by every beat variant
interface OffseasonBeatBase {
    beat_index: number;
    total_beats: number;
    title: string;
    body: string;
    state: string;
    can_advance: boolean;
    can_recruit: boolean;
    can_begin_season: boolean;
    signed_player_id: string;
    signed_player?: { id: string; name: string; overall: number; age: number } | null;
    /** Rides on the POST /api/offseason/recruit response (the beat replaces
        state wholesale, so the contested outcome must travel with it). */
    signing_outcome?: SigningOutcome | null;
}

// Discriminated union — `key` is the discriminant
export type OffseasonBeat =
    | (OffseasonBeatBase & { key: 'champion'; payload: ChampionBeatPayload })
    | (OffseasonBeatBase & { key: 'recap'; payload: RecapBeatPayload })
    | (OffseasonBeatBase & { key: 'awards'; payload: AwardsBeatPayload })
    | (OffseasonBeatBase & { key: 'records_ratified'; payload: RecordsRatifiedBeatPayload })
    | (OffseasonBeatBase & { key: 'hof_induction'; payload: HofInductionBeatPayload })
    | (OffseasonBeatBase & { key: 'development'; payload: DevelopmentBeatPayload })
    | (OffseasonBeatBase & { key: 'retirements'; payload: RetirementsBeatPayload })
    | (OffseasonBeatBase & { key: 'rookie_class_preview'; payload: RookieClassPreviewBeatPayload })
    | (OffseasonBeatBase & { key: 'recruitment'; payload: RecruitmentBeatPayload })
    | (OffseasonBeatBase & { key: 'schedule_reveal'; payload: ScheduleRevealBeatPayload });

export interface CommandCenterSimResponse {
    status: string;
    message: string;
    plan: CommandCenterPlan;
    dashboard: CommandDashboard;
    next_state: string | null;
    aftermath?: Aftermath;
}

export type FastForwardStopPoint = 'next_bye' | 'pre_playoffs' | 'offseason';

export interface FastForwardResponse {
    status: string;
    message: string;
    weeks_simulated: number;
    stop_reason: string;
    next_state: string | null;
    week_summaries: Array<{ week: number | null; opponent_name: string | null; result: string | null }>;
    final_dashboard?: CommandDashboard | null;
    final_aftermath?: Aftermath | null;
    requested_stop_point?: FastForwardStopPoint | null;
    resolved_stop_point?: FastForwardStopPoint | null;
}

export interface DynastyOfficeResponse {
    season_id: string;
    week: number;
    player_club_id: string;
    player_club_name: string;
    recruiting: {
        credibility: {
            score: number;
            grade: string;
            evidence: string[];
        };
        budget: {
            scout: [number, number];
            contact: [number, number];
            visit: [number, number];
        };
        active_promises: Array<{
            player_id: string;
            promise_type: string;
            status: string;
            evidence: string;
            result: 'fulfilled' | 'broken' | null;
            result_season_id: string | null;
        }>;
        prospects: Array<{
            player_id: string;
            name: string;
            hometown: string;
            public_archetype: string;
            public_ovr_band: number[];
            fit_score: number;
            interest?: number;
            pipeline_tier: number;
            promise_options: string[];
            active_promise: { promise_type: string; status: string } | null;
            interest_evidence: string[];
            scouted?: boolean;
            contacted?: boolean;
            visited?: boolean;
            recruiting_status?: RecruitingStatus;
        }>;
        rules: {
            max_active_promises: number;
            promise_options: string[];
            honesty: string;
        };
    };
    league_memory: {
        records: { items: Array<Record<string, string | number | null>> };
        awards: { items: Array<Record<string, string | number | null>> };
        rivalries: { items: Array<Record<string, string | number | null>> };
        recent_matches: Array<{
            match_id: string;
            week: number;
            summary: string;
            winner_name: string;
        }>;
    };
    staff_market: {
        current_staff: Array<{
            department: string;
            name: string;
            rating_primary: number;
            rating_secondary: number;
            voice: string;
            effect_summary: string;
            training_modifier_pct?: number;
        }>;
        active_facilities: string[];
        candidates: Array<{
            candidate_id: string;
            department: string;
            name: string;
            rating_primary: number;
            rating_secondary: number;
            voice: string;
            effect_lanes: string[];
        }>;
        recent_actions: Array<{
            candidate_id: string;
            department: string;
            name: string;
            effect_lanes: string[];
        }>;
        rules: {
            honesty: string;
        };
    };
}

export interface SaveInfo {
    name: string;
    path: string;
    club_id: string | null;
    club_name: string | null;
    season_id: string | null;
    week: number | null;
    incompatible?: boolean;
    last_modified?: number;
    season_number?: number;
    wins?: number;
    losses?: number;
    draws?: number;
}

export interface SaveListResponse {
    saves: SaveInfo[];
    active_path: string | null;
}

export interface SaveStateResponse {
    loaded: boolean;
    active_path: string | null;
    meta: SaveInfo | null;
}

export interface ClubOption {
    club_id: string;
    name: string;
    tagline: string;
    colors: string;
}
