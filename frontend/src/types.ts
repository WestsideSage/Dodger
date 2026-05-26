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
}

export interface RosterResponse {
    club_id: string;
    roster: Player[];
    default_lineup: string[];
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
}

export interface OneVOneFinaleMoment {
    kind: 'one_v_one_finale';
    match_id: string;
    tick: number;
    player_a_id: string;
    player_b_id: string;
    tick_started: number;
    display_text?: string;
}

export interface GassedCollapseMoment {
    kind: 'gassed_collapse';
    match_id: string;
    tick: number;
    player_id: string;
    team_id: string;
    fatigue_pct: number;
    display_text?: string;
}

export interface FloodThrowMoment {
    kind: 'flood_throw';
    match_id: string;
    tick: number;
    thrower_team_id: string;
    thrower_ids: string[];
    display_text?: string;
}

export interface ComebackMoment {
    kind: 'comeback';
    match_id: string;
    tick: number;
    team_id: string;
    deficit_at_low_point: number;
    catches_during_comeback: number;
    display_text?: string;
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
    events: ReplayEvent[];
    moment_events: MomentEvent[];
    proof_events: ReplayProofEvent[];
    key_play_indices: number[];
    official_state?: OfficialReplayState | null;
    report: {
        winner_name: string;
        match_mvp_player_id: string | null;
        match_mvp_name: string | null;
        top_performers: TopPerformer[];
        turning_point: string;
        evidence_lanes: CommandDashboardLane[];
    };
    broadcast_frame?: BroadcastFrame | null;
    playoff_frame?: PlayoffFrame | null;
    commentary_inserts?: CommentaryInsert[];
}

export interface StandingRow {
    club_id: string;
    club_name: string;
    wins: number;
    losses: number;
    draws: number;
    points: number;
    elimination_differential: number;
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
    playoff_spots: number;
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
  framing_line: string;
  broadcast_frame?: BroadcastFrame | null;
  adaptation_summary?: string | null;
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
}

export interface Aftermath {
    headline: string;
    match_card: {
        home_club_id: string;
        away_club_id: string;
        winner_club_id: string | null;
        home_survivors: number;
        away_survivors: number;
    } | null;
    player_growth_deltas: Array<{
        player_id: string;
        player_name: string;
        attribute: string;
        delta: number;
    }>;
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
    body: string[];
    verdict?: string;
    top_performers?: TopPerformer[];
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
}

export interface DevelopmentPlayer {
    name: string;
    ovr_before: number;
    ovr_after: number;
    delta: number;
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
    overall: number;
    age: number;
    hometown: string;
    archetype: string;
    kind: 'prospect' | 'free_agent';
}

export interface RecruitmentBeatPayload {
    player_signing: OffseasonSigning | null;
    other_signings: OffseasonSigning[];
    available_prospects: RecruitmentProspectChoice[];
}

export interface RatifiedRecordEntry {
    record_id?: string;
    record_type: string;
    holder_name: string;
    previous_value: number;
    new_value: number;
    detail: string;
    proof_source?: string;
}

export interface RecordsRatifiedBeatPayload {
    records: RatifiedRecordEntry[];
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
            promise_options: string[];
            active_promise: { promise_type: string; status: string } | null;
            interest_evidence: string[];
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
