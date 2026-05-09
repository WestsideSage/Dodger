export interface PlayerRatings {
    accuracy: number;
    power: number;
    dodge: number;
    catch: number;
    stamina: number;
    tactical_iq: number;
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

export interface CoachPolicy {
    target_stars: number;
    target_ball_holder: number;
    risk_tolerance: number;
    sync_throws: number;
    rush_frequency: number;
    rush_proximity: number;
    tempo: number;
    catch_bias: number;
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

export interface ReplayEvent {
    index: number;
    tick: number;
    event_type: string;
    phase: string;
    actors: Record<string, string>;
    context: Record<string, unknown>;
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
    score: number;
    eliminations_by_throw: number;
    catches_made: number;
    dodges_successful: number;
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
    events: ReplayEvent[];
    proof_events: ReplayProofEvent[];
    key_play_indices: number[];
    report: {
        winner_name: string;
        match_mvp_player_id: string | null;
        match_mvp_name: string | null;
        top_performers: TopPerformer[];
        turning_point: string;
        evidence_lanes: CommandDashboardLane[];
    };
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
}

export interface StandingsResponse {
    season_id: string;
    standings: StandingRow[];
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
}

export interface CommandCenterPlan {
    season_id: string;
    week: number;
    player_club_id: string;
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
        players: Array<{
            id: string;
            name: string;
            overall: number;
            age?: number;
            potential?: number;
            stamina?: number;
        }>;
        summary: string;
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
}

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
