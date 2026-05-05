from __future__ import annotations

import random
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, Optional

from .analysis import MatchAnalysis, analyze_match
from .court_renderer import CourtRenderer
from .engine import MatchEngine, MatchSetup
from .events import MatchEvent
from .narration import Lookup, build_lookup_from_setup
from .persistence import (
    StoredMatchSummary,
    connect,
    fetch_match,
    initialize_schema,
    load_all_meta_patches,
    load_club_trophies,
    load_hall_of_fame,
    load_league_records,
    load_news_headlines,
    list_recent_matches,
    match_setup_to_dict,
    record_match,
)
from .randomizer import generate_random_setup, randomize_setup
from .sample_data import sample_match_setup
from .setup_loader import format_matchup_summary, load_match_setup_from_path, match_setup_from_dict
from .ui_components import HeroAction, InfoList, MetricStrip, RatingBar, StatCard
from .ui_formatters import (
    format_analysis_report,
    format_event_details,
    format_event_row,
    matchup_preview,
    player_role,
    policy_rows,
    team_overall,
    team_snapshot,
)
from .ui_style import (
    DM_BORDER,
    DM_CREAM,
    DM_MUTED_CHARCOAL,
    DM_NIGHT,
    DM_OFF_WHITE_LINE,
    DM_PAPER,
    FONT_BODY,
    FONT_DISPLAY,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    apply_theme,
)

_DEFAULT_DB = Path("dodgeball_sim.db")
_DIFFICULTIES = ["rookie", "pro", "elite"]
_POLICY_KEYS = [
    "target_stars",
    "target_ball_holder",
    "risk_tolerance",
    "sync_throws",
    "rush_frequency",
    "rush_proximity",
    "tempo",
    "catch_bias",
]


class DodgeballApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.style = apply_theme(master)
        master.title("Dodgeball Manager")

        self.db_path_var = tk.StringVar(value=str(_DEFAULT_DB))
        self.setup_path_var = tk.StringVar(value="<sample>")
        self.seed_var = tk.StringVar(value="31415")
        self.difficulty_var = tk.StringVar(value="pro")
        self.events_var = tk.StringVar(value="18")
        self.status_var = tk.StringVar(value="Ready")
        self.roster_team_var = tk.StringVar()
        self.tactics_team_var = tk.StringVar()
        self.playback_state_var = tk.StringVar(value="Replay is idle.")
        self.event_count_var = tk.StringVar(value="0 events")

        self.conn: Optional[sqlite3.Connection] = None
        self.current_setup: Optional[MatchSetup] = None
        self.current_lookup: Optional[Lookup] = None
        self.current_events: list[MatchEvent] = []
        self.current_analysis: Optional[MatchAnalysis] = None
        self.current_summary: Optional[StoredMatchSummary] = None
        self.selected_event_index: Optional[int] = None
        self.autoplay_job: Optional[str] = None

        self.match_rows: list[StoredMatchSummary] = []
        self.roster_rating_bars: dict[str, RatingBar] = {}
        self.policy_bars: dict[str, ttk.Progressbar] = {}
        self.policy_value_vars: dict[str, tk.StringVar] = {}
        self.policy_effect_vars: dict[str, tk.StringVar] = {}
        self.sidebar_visible = True
        self.team_card_vars: dict[str, dict[str, tk.StringVar]] = {}

        self._build_ui()
        self._connect_db()
        self._load_setup(None, label="Loaded sample matchup")
        self._refresh_matches()

    def _build_ui(self) -> None:
        root = self.master
        root.geometry("1320x860")
        root.minsize(1080, 760)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)

        topbar = tk.Frame(root, bg=DM_NIGHT, padx=SPACE_3, pady=SPACE_2)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_columnconfigure(1, weight=1)
        ttk.Label(topbar, text="Dodgeball Manager", style="TopbarTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            topbar,
            text="Visible ratings. Visible context. Logged RNG. One canonical replay surface.",
            style="TopbarMuted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        header_actions = ttk.Frame(topbar)
        header_actions.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(header_actions, text="Controls", command=self._toggle_sidebar, style="Secondary.TButton").pack(side=tk.RIGHT)
        ttk.Button(header_actions, text="Quick Match", command=self._run_match, style="Accent.TButton").pack(side=tk.RIGHT, padx=(0, 8))

        hero = ttk.Frame(root, padding=(SPACE_3, SPACE_2, SPACE_3, SPACE_1))
        hero.grid(row=1, column=0, columnspan=2, sticky="ew")
        hero.columnconfigure(0, weight=1)
        ttk.Label(hero, textvariable=self.status_var, style="Muted.TLabel").grid(row=0, column=0, sticky="e")

        sidebar = ttk.Frame(root, padding=(SPACE_2, 0, SPACE_1, SPACE_2), width=330)
        sidebar.grid(row=2, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        self.sidebar = sidebar
        self._build_sidebar(sidebar)

        main = ttk.Notebook(root)
        main.grid(row=2, column=1, sticky="nsew", padx=(0, SPACE_2), pady=(0, SPACE_2))
        self.main_notebook = main

        self.hub_tab = ttk.Frame(main, padding=SPACE_2)
        self.roster_tab = ttk.Frame(main, padding=SPACE_2)
        self.tactics_tab = ttk.Frame(main, padding=SPACE_2)
        self.match_tab = ttk.Frame(main, padding=SPACE_2)
        self.intel_tab = ttk.Frame(main, padding=SPACE_2)

        main.add(self.hub_tab, text="Home")
        main.add(self.roster_tab, text="Roster Lab")
        main.add(self.tactics_tab, text="Coach Board")
        main.add(self.match_tab, text="Replay Arena")
        main.add(self.intel_tab, text="League Wire")

        self._build_hub_tab()
        self._build_roster_tab()
        self._build_tactics_tab()
        self._build_match_tab()
        self._build_intel_tab()
        self._toggle_sidebar()

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        config = ttk.LabelFrame(parent, text="Control Rail", style="Rail.TLabelframe", padding=SPACE_2)
        config.grid(row=0, column=0, sticky="new")
        config.columnconfigure(1, weight=1)

        ttk.Label(config, text="DB Path").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(config, textvariable=self.db_path_var).grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=(0, 6))
        ttk.Button(config, text="Browse", command=self._choose_db, style="Secondary.TButton").grid(row=0, column=2, pady=(0, 6))

        ttk.Label(config, text="Setup JSON").grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(config, textvariable=self.setup_path_var).grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(0, 6))
        ttk.Button(config, text="Load", command=self._choose_setup, style="Secondary.TButton").grid(row=1, column=2, pady=(0, 6))

        ttk.Label(config, text="Seed").grid(row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(config, textvariable=self.seed_var, width=12).grid(row=2, column=1, sticky="w", padx=(0, 6), pady=(0, 6))
        ttk.Button(config, text="Random Seed", command=self._random_seed, style="Secondary.TButton").grid(row=2, column=2, pady=(0, 6))

        ttk.Label(config, text="Difficulty").grid(row=3, column=0, sticky="w", pady=(0, 6))
        ttk.Combobox(config, textvariable=self.difficulty_var, values=_DIFFICULTIES, state="readonly", width=14).grid(
            row=3, column=1, sticky="w", padx=(0, 6), pady=(0, 6)
        )
        ttk.Label(config, text="Events to show").grid(row=4, column=0, sticky="w")
        ttk.Entry(config, textvariable=self.events_var, width=12).grid(row=4, column=1, sticky="w", padx=(0, 6))

        actions = ttk.Frame(config)
        actions.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(SPACE_2, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="Run Match", command=self._run_match, style="Accent.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(actions, text="Edit Matchup", command=self._open_setup_editor, style="Secondary.TButton").grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(actions, text="Use Sample", command=lambda: self._load_setup(None, label="Loaded sample matchup"), style="Secondary.TButton").grid(
            row=1, column=0, sticky="ew", padx=(0, 4), pady=(6, 0)
        )
        ttk.Button(actions, text="Jitter Ratings", command=self._jitter_setup, style="Secondary.TButton").grid(
            row=1, column=1, sticky="ew", padx=(4, 0), pady=(6, 0)
        )
        ttk.Button(actions, text="Fresh Teams", command=self._random_setup, style="Secondary.TButton").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )

        saved = ttk.LabelFrame(parent, text="Stored Replays", style="Rail.TLabelframe", padding=SPACE_2)
        saved.grid(row=1, column=0, sticky="nsew", pady=(SPACE_2, 0))
        parent.rowconfigure(1, weight=1)
        saved.rowconfigure(0, weight=1)
        saved.columnconfigure(0, weight=1)

        self.match_tree = ttk.Treeview(saved, columns=("id", "winner", "matchup", "tick"), show="headings", height=16)
        for key, heading, width in (
            ("id", "#", 48),
            ("winner", "Winner", 92),
            ("matchup", "Matchup", 180),
            ("tick", "Tick", 56),
        ):
            self.match_tree.heading(key, text=heading)
            self.match_tree.column(key, width=width, stretch=key == "matchup")
        self.match_tree.grid(row=0, column=0, sticky="nsew")
        self.match_tree.bind("<<TreeviewSelect>>", lambda _: self._sync_selected_match_summary())
        scroll = ttk.Scrollbar(saved, orient="vertical", command=self.match_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.match_tree.configure(yscrollcommand=scroll.set)

        saved_actions = ttk.Frame(saved)
        saved_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_1, 0))
        saved_actions.columnconfigure(0, weight=1)
        saved_actions.columnconfigure(1, weight=1)
        ttk.Button(saved_actions, text="View Match", command=self._view_selected, style="Secondary.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(saved_actions, text="Refresh", command=self._refresh_matches, style="Secondary.TButton").grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _build_hub_tab(self) -> None:
        tab = self.hub_tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(2, weight=1)

        hero = ttk.Frame(tab)
        hero.grid(row=0, column=0, columnspan=2, sticky="ew")
        hero.columnconfigure(0, weight=3)
        hero.columnconfigure(1, weight=2)

        hero_copy = ttk.Frame(hero, style="Surface.TFrame", padding=20)
        hero_copy.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        hero_copy.columnconfigure(0, weight=1)
        ttk.Label(hero_copy, text="Build a matchup. Run it. Read the truth.", style="Display.TLabel", wraplength=520, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            hero_copy,
            text="This is a dodgeball sim sandbox. Tune teams, hit Quick Match, and inspect the replay without hidden boosts or fake drama.",
            style="Muted.TLabel",
            wraplength=540,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 16))
        action_row = ttk.Frame(hero_copy)
        action_row.grid(row=2, column=0, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)
        action_row.columnconfigure(2, weight=1)
        HeroAction(action_row, "Quick Match", "Run the loaded matchup immediately.", "Play Now", self._run_match).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        HeroAction(action_row, "Team Lab", "Edit lineups, ratings, and chemistry.", "Edit Teams", self._open_setup_editor).grid(row=0, column=1, sticky="ew", padx=4)
        HeroAction(action_row, "Fresh Chaos", "Roll brand-new squads and see what happens.", "Randomize", self._random_setup).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        hero_preview = ttk.LabelFrame(hero, text="Tonight's Floor", style="Panel.TLabelframe", padding=SPACE_2)
        hero_preview.grid(row=0, column=1, sticky="nsew")
        hero_preview.columnconfigure(0, weight=1)
        hero_preview.rowconfigure(1, weight=1)
        self.preview_strip = MetricStrip(hero_preview, "Match Story", "-", "")
        self.preview_strip.grid(row=0, column=0, sticky="ew")
        self.hub_court_canvas = tk.Canvas(hero_preview, height=250, bg=DM_PAPER, highlightbackground=DM_BORDER, highlightthickness=1)
        self.hub_court_canvas.grid(row=1, column=0, sticky="nsew", pady=(SPACE_2, 0))
        self.hub_court_renderer = CourtRenderer(self.hub_court_canvas)

        cards = ttk.Frame(tab)
        cards.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_2, 0))
        for idx in range(4):
            cards.columnconfigure(idx, weight=1)
        self.card_overall = StatCard(cards, "Matchup Edge")
        self.card_record = StatCard(cards, "Recent Result")
        self.card_saved = StatCard(cards, "Saved Matches")
        self.card_focus = StatCard(cards, "Current Focus")
        self.card_overall.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.card_record.grid(row=0, column=1, sticky="ew", padx=8)
        self.card_saved.grid(row=0, column=2, sticky="ew", padx=8)
        self.card_focus.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        team_row = ttk.Frame(tab)
        team_row.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(SPACE_2, 0))
        team_row.columnconfigure(0, weight=1)
        team_row.columnconfigure(1, weight=1)
        team_row.rowconfigure(0, weight=1)
        self.team_card_vars = {}
        for idx, slot in enumerate(("team_a", "team_b")):
            card = ttk.LabelFrame(team_row, text="Lineup Spotlight", style="Panel.TLabelframe", padding=SPACE_2)
            card.grid(row=0, column=idx, sticky="nsew", padx=(0, 6) if idx == 0 else (6, 0))
            card.columnconfigure(0, weight=1)
            title = tk.StringVar(value="-")
            meta = tk.StringVar(value="-")
            stars = tk.StringVar(value="-")
            ttk.Label(card, textvariable=title, style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(card, textvariable=meta, style="Muted.TLabel", wraplength=300, justify="left").grid(row=1, column=0, sticky="w", pady=(4, 10))
            ttk.Label(card, textvariable=stars, style="Muted.TLabel", wraplength=300, justify="left").grid(row=2, column=0, sticky="w")
            self.team_card_vars[slot] = {"title": title, "meta": meta, "stars": stars}

        lower = ttk.Frame(tab)
        lower.grid(row=2, column=1, sticky="nsew", pady=(SPACE_2, 0))
        lower.columnconfigure(0, weight=1)
        lower.rowconfigure(1, weight=1)
        matchup = ttk.LabelFrame(lower, text="Season Context", style="Panel.TLabelframe", padding=SPACE_2)
        matchup.grid(row=0, column=0, sticky="ew")
        matchup.columnconfigure(0, weight=1)
        self.summary_text = self._make_text(matchup, height=8, wrap="word")
        self.summary_text.grid(row=0, column=0, sticky="ew")
        swing = ttk.LabelFrame(lower, text="Momentum", style="Panel.TLabelframe", padding=SPACE_2)
        swing.grid(row=1, column=0, sticky="nsew", pady=(SPACE_2, 0))
        swing.columnconfigure(0, weight=1)
        swing.rowconfigure(0, weight=1)
        self.momentum_canvas = tk.Canvas(swing, height=190, bg=DM_PAPER, highlightbackground=DM_BORDER, highlightthickness=1)
        self.momentum_canvas.grid(row=0, column=0, sticky="nsew")

    def _build_roster_tab(self) -> None:
        tab = self.roster_tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(2, weight=1)

        self.roster_snapshot = MetricStrip(tab, "Roster Lab", "-", "")
        self.roster_snapshot.grid(row=0, column=0, columnspan=2, sticky="ew")

        header = ttk.Frame(tab)
        header.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_2, 0))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Team", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        self.roster_team_box = ttk.Combobox(header, textvariable=self.roster_team_var, state="readonly", width=32)
        self.roster_team_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.roster_team_box.bind("<<ComboboxSelected>>", lambda _: self._refresh_roster_view())

        roster_panel = ttk.LabelFrame(tab, text="Roster Table", style="Panel.TLabelframe", padding=SPACE_2)
        roster_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(SPACE_2, 0))
        roster_panel.columnconfigure(0, weight=1)
        roster_panel.rowconfigure(0, weight=1)

        self.roster_tree = ttk.Treeview(
            roster_panel,
            columns=("name", "role", "ovr", "acc", "pow", "dod", "cat", "sta"),
            show="headings",
        )
        headings = [
            ("name", "Player", 180),
            ("role", "Role", 100),
            ("ovr", "OVR", 70),
            ("acc", "ACC", 60),
            ("pow", "POW", 60),
            ("dod", "DOD", 60),
            ("cat", "CAT", 60),
            ("sta", "STA", 60),
        ]
        for key, title, width in headings:
            self.roster_tree.heading(key, text=title)
            self.roster_tree.column(key, width=width, anchor="center", stretch=key == "name")
        self.roster_tree.grid(row=0, column=0, sticky="nsew")
        self.roster_tree.bind("<<TreeviewSelect>>", lambda _: self._refresh_player_inspector())
        roster_scroll = ttk.Scrollbar(roster_panel, orient="vertical", command=self.roster_tree.yview)
        roster_scroll.grid(row=0, column=1, sticky="ns")
        self.roster_tree.configure(yscrollcommand=roster_scroll.set)

        inspector = ttk.LabelFrame(tab, text="Player Inspector", style="Panel.TLabelframe", padding=SPACE_2)
        inspector.grid(row=2, column=1, sticky="nsew", pady=(SPACE_2, 0))
        inspector.columnconfigure(0, weight=1)
        ttk.Label(inspector, text="Selected player", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        self.player_name_var = tk.StringVar(value="No player selected")
        self.player_meta_var = tk.StringVar(value="")
        ttk.Label(inspector, textvariable=self.player_name_var, style="CardValue.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(inspector, textvariable=self.player_meta_var, style="Muted.TLabel", wraplength=360, justify="left").grid(row=2, column=0, sticky="w", pady=(0, 12))
        for idx, label in enumerate(("Accuracy", "Power", "Dodge", "Catch", "Stamina"), start=3):
            bar = RatingBar(inspector, label)
            bar.grid(row=idx, column=0, sticky="ew", pady=4)
            self.roster_rating_bars[label.lower()] = bar
        self.player_notes = self._make_text(inspector, height=8, wrap="word")
        self.player_notes.grid(row=8, column=0, sticky="nsew", pady=(12, 0))

    def _build_tactics_tab(self) -> None:
        tab = self.tactics_tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(2, weight=1)

        self.tactics_intro = MetricStrip(tab, "Coach Board", "-", "")
        self.tactics_intro.grid(row=0, column=0, columnspan=2, sticky="ew")

        header = ttk.Frame(tab)
        header.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_2, 0))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Team", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        self.tactics_team_box = ttk.Combobox(header, textvariable=self.tactics_team_var, state="readonly", width=32)
        self.tactics_team_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.tactics_team_box.bind("<<ComboboxSelected>>", lambda _: self._refresh_tactics_view())

        policy_panel = ttk.LabelFrame(tab, text="Coach Tendencies", style="Panel.TLabelframe", padding=SPACE_2)
        policy_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(SPACE_2, 0))
        policy_panel.columnconfigure(0, weight=1)
        for row, key in enumerate(_POLICY_KEYS):
            card = ttk.Frame(policy_panel, style="Surface.TFrame", padding=(12, 10))
            card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
            card.columnconfigure(1, weight=1)
            label_text = key.replace("_", " ").title()
            ttk.Label(card, text=label_text, style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
            value_var = tk.StringVar(value="-")
            effect_var = tk.StringVar(value="")
            bar = ttk.Progressbar(card, maximum=100, mode="determinate")
            bar.grid(row=0, column=1, sticky="ew", padx=(12, 8))
            ttk.Label(card, textvariable=value_var, style="Muted.TLabel").grid(row=0, column=2, sticky="e")
            ttk.Label(card, textvariable=effect_var, style="Muted.TLabel", wraplength=520, justify="left").grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
            self.policy_bars[key] = bar
            self.policy_value_vars[key] = value_var
            self.policy_effect_vars[key] = effect_var

        preview_panel = ttk.LabelFrame(tab, text="Playstyle Readout", style="Panel.TLabelframe", padding=SPACE_2)
        preview_panel.grid(row=2, column=1, sticky="nsew", pady=(SPACE_2, 0))
        preview_panel.columnconfigure(0, weight=1)
        preview_panel.rowconfigure(1, weight=1)
        self.tactics_snapshot = MetricStrip(preview_panel, "Preset Fit", "-", "")
        self.tactics_snapshot.grid(row=0, column=0, sticky="ew")
        self.tactics_summary = self._make_text(preview_panel, height=16, wrap="word")
        self.tactics_summary.grid(row=1, column=0, sticky="nsew", pady=(SPACE_2, 0))

    def _build_match_tab(self) -> None:
        tab = self.match_tab
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=1)

        controls = ttk.Frame(tab)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew")
        controls.columnconfigure(6, weight=1)
        ttk.Button(controls, text="Prev", command=self._prev_event, style="Secondary.TButton").grid(row=0, column=0, padx=(0, 6))
        ttk.Button(controls, text="Next", command=self._next_event, style="Secondary.TButton").grid(row=0, column=1, padx=(0, 6))
        self.play_button = ttk.Button(controls, text="Autoplay", command=self._toggle_autoplay, style="Accent.TButton")
        self.play_button.grid(row=0, column=2, padx=(0, 6))
        ttk.Button(controls, text="Jump Start", command=lambda: self._set_selected_event_index(0), style="Secondary.TButton").grid(
            row=0, column=3, padx=(0, 6)
        )
        ttk.Button(
            controls,
            text="Jump End",
            command=lambda: self._set_selected_event_index(len(self.current_events) - 1 if self.current_events else None),
            style="Secondary.TButton",
        ).grid(row=0, column=4, padx=(0, 6))
        ttk.Label(controls, textvariable=self.playback_state_var, style="Muted.TLabel").grid(row=0, column=5, sticky="w", padx=(8, 0))
        ttk.Label(controls, textvariable=self.event_count_var, style="Muted.TLabel").grid(row=0, column=6, sticky="e")

        court_panel = ttk.LabelFrame(tab, text="Top-Down Replay", style="Panel.TLabelframe", padding=SPACE_2)
        court_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")
        court_panel.columnconfigure(0, weight=1)
        court_panel.rowconfigure(0, weight=1)
        self.court_canvas = tk.Canvas(court_panel, height=400, bg=DM_PAPER, highlightbackground=DM_BORDER, highlightthickness=1)
        self.court_canvas.grid(row=0, column=0, sticky="nsew")
        self.court_renderer = CourtRenderer(self.court_canvas)

        log_panel = ttk.LabelFrame(tab, text="Event Log", style="Panel.TLabelframe", padding=SPACE_2)
        log_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
        log_panel.columnconfigure(0, weight=1)
        log_panel.rowconfigure(0, weight=1)
        self.event_tree = ttk.Treeview(log_panel, columns=("tick", "type", "actor", "target", "outcome"), show="headings")
        for key, title, width in (
            ("tick", "Tick", 56),
            ("type", "Type", 74),
            ("actor", "Actor", 150),
            ("target", "Target", 150),
            ("outcome", "Outcome", 92),
        ):
            self.event_tree.heading(key, text=title)
            self.event_tree.column(key, width=width, anchor="center", stretch=key in {"actor", "target"})
        self.event_tree.grid(row=0, column=0, sticky="nsew")
        self.event_tree.bind("<<TreeviewSelect>>", lambda _: self._on_event_select())
        event_scroll = ttk.Scrollbar(log_panel, orient="vertical", command=self.event_tree.yview)
        event_scroll.grid(row=0, column=1, sticky="ns")
        self.event_tree.configure(yscrollcommand=event_scroll.set)

        report_panel = ttk.LabelFrame(tab, text="Match Report", style="Panel.TLabelframe", padding=SPACE_2)
        report_panel.grid(row=2, column=1, sticky="nsew", pady=(10, 0))
        report_panel.columnconfigure(0, weight=1)
        report_panel.rowconfigure(1, weight=1)
        self.match_summary_strip = MetricStrip(report_panel, "Replay Focus", "-", "")
        self.match_summary_strip.grid(row=0, column=0, sticky="ew")
        self.report_text = self._make_text(report_panel, height=14, wrap="word")
        self.report_text.grid(row=1, column=0, sticky="nsew", pady=(SPACE_2, 0))

        detail_panel = ttk.LabelFrame(log_panel, text="Inspector Drawer", style="Panel.TLabelframe", padding=SPACE_2)
        detail_panel.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        detail_panel.columnconfigure(0, weight=1)
        self.event_detail_text = self._make_text(detail_panel, height=8, wrap="word")
        self.event_detail_text.grid(row=0, column=0, sticky="ew")

    def _build_intel_tab(self) -> None:
        tab = self.intel_tab
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=1)

        self.intel_snapshot = MetricStrip(tab, "League Wire", "-", "")
        self.intel_snapshot.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.headlines_list = InfoList(tab, "Headlines")
        self.headlines_list.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
        self.meta_list = InfoList(tab, "Meta Patches")
        self.meta_list.grid(row=1, column=1, sticky="nsew", pady=(10, 0))
        self.hall_list = InfoList(tab, "Hall of Fame")
        self.hall_list.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
        self.records_list = InfoList(tab, "Record Book & Trophies")
        self.records_list.grid(row=2, column=1, sticky="nsew", pady=(10, 0))

        controls = ttk.Frame(tab)
        controls.grid(row=3, column=0, columnspan=2, sticky="e", pady=(SPACE_2, 0))
        ttk.Button(controls, text="Refresh Intel", command=self._refresh_intel, style="Secondary.TButton").pack(side=tk.RIGHT)

    def _make_text(self, parent: tk.Misc, *, height: int, wrap: str) -> tk.Text:
        widget = tk.Text(
            parent,
            height=height,
            wrap=wrap,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
            background=DM_PAPER,
            foreground=DM_MUTED_CHARCOAL,
            insertbackground=DM_BORDER,
            font=FONT_BODY,
            highlightthickness=0,
        )
        widget.configure(state=tk.DISABLED)
        return widget

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)
        widget.see("1.0")

    def _toggle_sidebar(self) -> None:
        if self.sidebar_visible:
            self.sidebar.grid_remove()
            self.sidebar_visible = False
            self.status_var.set("Control rail hidden. Use Toggle Control Rail to restore it.")
        else:
            self.sidebar.grid()
            self.sidebar_visible = True
            self.status_var.set("Control rail visible.")

    def _choose_db(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db"), ("All", "*.*")])
        if path:
            self.db_path_var.set(path)
            self._connect_db()
            self._refresh_matches()

    def _choose_setup(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if path:
            self._load_setup(path, label=f"Loaded setup from {path}")

    def _random_seed(self) -> None:
        self.seed_var.set(str(random.randint(1000, 99999)))
        self.status_var.set("Assigned a fresh seed.")

    def _connect_db(self) -> None:
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        db_path = Path(self.db_path_var.get())
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = connect(db_path)
        initialize_schema(self.conn)
        self.status_var.set(f"Connected to {db_path}")

    def _load_setup(self, path: Optional[str], *, label: str) -> None:
        try:
            if path:
                setup = load_match_setup_from_path(path)
                self.setup_path_var.set(path)
            else:
                setup = sample_match_setup()
                self.setup_path_var.set("<sample>")
            self.current_setup = setup
            self.current_lookup = build_lookup_from_setup(setup)
            self.current_events = []
            self.current_analysis = None
            self.current_summary = None
            self.selected_event_index = None
            self._refresh_setup_views()
            self._populate_event_views()
            self.status_var.set(label)
        except Exception as exc:
            messagebox.showerror("Setup error", str(exc))

    def _apply_custom_setup(self, setup: MatchSetup) -> None:
        self.current_setup = setup
        self.current_lookup = build_lookup_from_setup(setup)
        self.setup_path_var.set("<custom>")
        self.current_events = []
        self.current_analysis = None
        self.current_summary = None
        self.selected_event_index = None
        self._refresh_setup_views()
        self._populate_event_views()
        self.status_var.set("Updated matchup from editor.")

    def _refresh_setup_views(self) -> None:
        if not self.current_setup:
            return
        self._set_text(self.summary_text, format_matchup_summary(self.current_setup))
        preview = matchup_preview(self.current_setup).splitlines()
        title = preview[0] if preview else "-"
        note = preview[1] if len(preview) > 1 else ""
        self.preview_strip.set(title, note)
        self.hub_court_renderer.render(self.current_setup, self.current_events, self.selected_event_index if self.current_events else None)
        self._draw_momentum(self.current_analysis)
        team_names = [self.current_setup.team_a.name, self.current_setup.team_b.name]
        self.roster_team_box.configure(values=team_names)
        self.tactics_team_box.configure(values=team_names)
        if self.roster_team_var.get() not in team_names:
            self.roster_team_var.set(team_names[0])
        if self.tactics_team_var.get() not in team_names:
            self.tactics_team_var.set(team_names[0])
        self._refresh_team_spotlights()
        self._refresh_roster_view()
        self._refresh_tactics_view()
        self._refresh_hub_cards()

    def _refresh_team_spotlights(self) -> None:
        if not self.current_setup:
            return
        teams = {"team_a": self.current_setup.team_a, "team_b": self.current_setup.team_b}
        for key, team in teams.items():
            top = sorted(team.players, key=lambda player: player.overall(), reverse=True)[:2]
            top_line = ", ".join(f"{player.name} ({player_role(player)})" for player in top) or "No players"
            self.team_card_vars[key]["title"].set(team.name)
            self.team_card_vars[key]["meta"].set(
                f"Overall {team_overall(team):.1f} | Chemistry {team.chemistry:.2f} | Tempo {self._policy_word(team.coach_policy.tempo)}"
            )
            self.team_card_vars[key]["stars"].set(f"Impact players: {top_line}")

    def _refresh_hub_cards(self) -> None:
        if not self.current_setup:
            return
        team_a = self.current_setup.team_a
        team_b = self.current_setup.team_b
        delta = team_overall(team_a) - team_overall(team_b)
        if delta > 0:
            edge_text = f"{team_a.name} +{delta:.1f}"
        elif delta < 0:
            edge_text = f"{team_b.name} +{abs(delta):.1f}"
        else:
            edge_text = "Even"
        self.card_overall.set(edge_text, "Average roster edge based on visible ratings.")
        if self.current_summary:
            winner = self.current_summary.winner_team_id or "Draw"
            self.card_record.set(winner, f"Seed {self.current_summary.seed} at {self.current_summary.difficulty}.")
        else:
            self.card_record.set("No result", "Run a match to populate the match report.")
        self.card_saved.set(str(len(self.match_rows)), "Recent stored replays available from the database.")
        self.card_focus.set(
            self.difficulty_var.get().title(),
            f"{team_a.name} vs {team_b.name} | inspect ratings, policy, and event log together.",
        )

    def _selected_team(self, selected_name: str) -> Optional[Any]:
        if not self.current_setup:
            return None
        teams = {self.current_setup.team_a.name: self.current_setup.team_a, self.current_setup.team_b.name: self.current_setup.team_b}
        return teams.get(selected_name)

    def _refresh_roster_view(self) -> None:
        team = self._selected_team(self.roster_team_var.get())
        self.roster_tree.delete(*self.roster_tree.get_children())
        if not team:
            return
        top = sorted(team.players, key=lambda player: player.overall(), reverse=True)[:3]
        top_line = ", ".join(f"{player.name} {player.overall():.1f}" for player in top)
        self.roster_snapshot.set(team.name, f"Overall {team_overall(team):.1f} | Top rotation: {top_line}")
        for player in team.players:
            ratings = player.ratings
            self.roster_tree.insert(
                "",
                tk.END,
                iid=player.id,
                values=(
                    player.name,
                    player_role(player),
                    f"{player.overall():.1f}",
                    f"{ratings.accuracy:.0f}",
                    f"{ratings.power:.0f}",
                    f"{ratings.dodge:.0f}",
                    f"{ratings.catch:.0f}",
                    f"{ratings.stamina:.0f}",
                ),
            )
        children = self.roster_tree.get_children()
        if children:
            self.roster_tree.selection_set(children[0])
            self._refresh_player_inspector()

    def _refresh_player_inspector(self) -> None:
        team = self._selected_team(self.roster_team_var.get())
        selection = self.roster_tree.selection()
        if not team or not selection:
            self.player_name_var.set("No player selected")
            self.player_meta_var.set("")
            self._set_text(self.player_notes, "")
            for bar in self.roster_rating_bars.values():
                bar.set(0)
            return
        player = next((item for item in team.players if item.id == selection[0]), None)
        if not player:
            return
        self.player_name_var.set(player.name)
        self.player_meta_var.set(
            f"{player_role(player)} | Age {player.age} | Overall {player.overall():.1f} | "
            f"Potential {player.traits.potential:.0f} | Pressure {player.traits.pressure:.0f}"
        )
        self.roster_rating_bars["accuracy"].set(player.ratings.accuracy)
        self.roster_rating_bars["power"].set(player.ratings.power)
        self.roster_rating_bars["dodge"].set(player.ratings.dodge)
        self.roster_rating_bars["catch"].set(player.ratings.catch)
        self.roster_rating_bars["stamina"].set(player.ratings.stamina)
        notes = [
            f"Role fit: {player_role(player)}",
            f"Consistency {player.traits.consistency:.0f} | Growth {player.traits.growth_curve:.0f}",
            f"Club ID: {player.club_id or team.id}",
            "Visible ratings only. Inspect this card against the event log when results feel surprising.",
        ]
        self._set_text(self.player_notes, "\n".join(notes))

    def _refresh_tactics_view(self) -> None:
        team = self._selected_team(self.tactics_team_var.get())
        if not team:
            return
        self.tactics_intro.set(
            team.name,
            f"Coach personality board. Tune sliders, then verify outcomes in replay instead of trusting vibes."
        )
        summary_lines = [team_snapshot(team), "", "Tendency Readout"]
        for label, value, effect in policy_rows(team.coach_policy):
            key = label.lower().replace(" ", "_")
            self.policy_bars[key]["value"] = value * 100.0
            self.policy_value_vars[key].set(f"{value:.2f}")
            self.policy_effect_vars[key].set(effect)
            summary_lines.append(f"  {label}: {effect}")
        summary_lines.extend(
            [
                "",
                "Preset Fit",
                f"  Best natural style: {self._suggest_preset(team)}",
                "  Warning: policy changes affect legibility only through logged probabilities and outcomes, not hidden buffs.",
            ]
        )
        self.tactics_snapshot.set(self._suggest_preset(team), f"{team.name} policy cluster based on visible sliders and roster fit.")
        self._set_text(self.tactics_summary, "\n".join(summary_lines))

    def _policy_word(self, value: float) -> str:
        if value >= 0.7:
            return "Fast"
        if value >= 0.45:
            return "Balanced"
        return "Patient"

    def _suggest_preset(self, team) -> str:
        policy = team.coach_policy.as_dict()
        if policy["risk_tolerance"] >= 0.65 and policy["tempo"] >= 0.55:
            return "Power-Arm Aggro"
        if policy["sync_throws"] >= 0.55:
            return "Swarm & Overload"
        if policy["target_stars"] >= 0.7:
            return "Sniper Control"
        if policy["rush_frequency"] <= 0.35:
            return "Catch-Heavy Attrition"
        return "Balanced Spreadsheet Enjoyer"

    def _run_match(self) -> None:
        if not self.current_setup:
            messagebox.showerror("No matchup", "Load or edit a matchup first.")
            return
        try:
            seed = int(self.seed_var.get())
        except ValueError:
            messagebox.showerror("Invalid seed", "Seed must be an integer.")
            return
        try:
            events_to_show = max(1, int(self.events_var.get()))
        except ValueError:
            events_to_show = 18
            self.events_var.set(str(events_to_show))
        difficulty = self.difficulty_var.get()
        if difficulty not in _DIFFICULTIES:
            messagebox.showerror("Invalid difficulty", f"Choose from {', '.join(_DIFFICULTIES)}")
            return

        setup = self.current_setup
        result = MatchEngine().run(setup, seed=seed, difficulty=difficulty)
        analysis = analyze_match(result.events, setup)
        match_id = record_match(self.conn, setup=setup, result=result, difficulty=difficulty)
        self.current_summary = StoredMatchSummary(
            match_id=match_id,
            seed=seed,
            winner_team_id=result.winner_team_id,
            difficulty=difficulty,
            team_a_id=setup.team_a.id,
            team_b_id=setup.team_b.id,
            config_version=result.config_version,
            final_tick=result.final_tick,
            created_at="",
        )
        self.current_events = list(result.events)
        self.current_analysis = analysis
        self.current_lookup = build_lookup_from_setup(setup)
        self._refresh_matches()
        self._refresh_setup_views()
        self._populate_event_views()
        self._update_match_report(events_to_show)
        self.main_notebook.select(self.match_tab)
        self.status_var.set(f"Recorded match #{match_id} with {len(result.events)} canonical events.")

    def _update_match_report(self, events_to_show: int) -> None:
        if not self.current_setup or not self.current_lookup or not self.current_summary:
            self._set_text(self.report_text, "Run a match to generate a report.")
            return
        lines = [
            _format_summary(self.current_summary),
            "",
            format_analysis_report(self.current_analysis, self.current_lookup) if self.current_analysis else "No analysis available.",
            "",
            "Opening sequence",
        ]
        for event in self.current_events[:events_to_show]:
            detail_lines = format_event_details(event, self.current_lookup).splitlines()
            if len(detail_lines) > 1:
                lines.append(f"  {detail_lines[1]}")
        winner = self.current_summary.winner_team_id or "draw"
        self.match_summary_strip.set(str(winner), f"{len(self.current_events)} logged events at {self.current_summary.difficulty} difficulty.")
        self._set_text(self.report_text, "\n".join(lines))

    def _populate_event_views(self) -> None:
        self._stop_autoplay()
        self.event_tree.delete(*self.event_tree.get_children())
        if not self.current_events or not self.current_lookup:
            self.event_count_var.set("0 events")
            self.playback_state_var.set("Replay is idle.")
            self._set_text(self.report_text, "Run a match or load a stored replay.")
            self._set_text(self.event_detail_text, "Select an event to inspect actors, probabilities, rolls, and state diff.")
            if self.current_setup:
                self.court_renderer.render(self.current_setup, [], None)
            return
        for index, event in enumerate(self.current_events):
            self.event_tree.insert("", tk.END, iid=str(index), values=format_event_row(event, self.current_lookup))
        self.event_count_var.set(f"{len(self.current_events)} events")
        self._set_selected_event_index(0)

    def _set_selected_event_index(self, index: Optional[int]) -> None:
        if index is None or not self.current_events:
            self.selected_event_index = None
            return
        index = max(0, min(index, len(self.current_events) - 1))
        self.selected_event_index = index
        self.event_tree.selection_set(str(index))
        self.event_tree.see(str(index))
        self._render_selected_event()

    def _on_event_select(self) -> None:
        selection = self.event_tree.selection()
        if not selection:
            return
        self.selected_event_index = int(selection[0])
        self._render_selected_event()

    def _render_selected_event(self) -> None:
        if self.selected_event_index is None or not self.current_lookup or not self.current_setup:
            return
        event = self.current_events[self.selected_event_index]
        self._set_text(self.event_detail_text, format_event_details(event, self.current_lookup))
        self.playback_state_var.set(f"Inspecting event {self.selected_event_index + 1}/{len(self.current_events)} at tick {event.tick}.")
        actor = self.current_lookup.player(event.actors.get("thrower", "")) or self.current_lookup.team(event.outcome.get("winner", "")) or event.event_type.upper()
        outcome = str(event.outcome.get("resolution") or event.outcome.get("winner") or event.event_type.upper()).upper()
        self.match_summary_strip.set(actor, f"{outcome} at tick {event.tick}. Replay remains derived from the canonical event log.")
        self.court_renderer.render(self.current_setup, self.current_events, self.selected_event_index)

    def _prev_event(self) -> None:
        if self.selected_event_index is None:
            self._set_selected_event_index(0)
            return
        self._set_selected_event_index(self.selected_event_index - 1)

    def _next_event(self) -> None:
        if self.selected_event_index is None:
            self._set_selected_event_index(0)
            return
        self._set_selected_event_index(self.selected_event_index + 1)

    def _toggle_autoplay(self) -> None:
        if self.autoplay_job:
            self._stop_autoplay()
            self.playback_state_var.set("Replay paused.")
            return
        if not self.current_events:
            return
        if self.selected_event_index is None:
            self._set_selected_event_index(0)
        self.play_button.configure(text="Pause")
        self._autoplay_step()

    def _autoplay_step(self) -> None:
        if not self.current_events:
            self._stop_autoplay()
            return
        if self.selected_event_index is None:
            self.selected_event_index = 0
        elif self.selected_event_index >= len(self.current_events) - 1:
            self._stop_autoplay()
            self.playback_state_var.set("Replay finished.")
            return
        else:
            self.selected_event_index += 1
        self._set_selected_event_index(self.selected_event_index)
        self.autoplay_job = self.master.after(900, self._autoplay_step)

    def _stop_autoplay(self) -> None:
        if self.autoplay_job:
            self.master.after_cancel(self.autoplay_job)
            self.autoplay_job = None
        self.play_button.configure(text="Autoplay")

    def _draw_momentum(self, analysis: MatchAnalysis | None) -> None:
        canvas = self.momentum_canvas
        canvas.delete("all")
        width = int(canvas.winfo_width() or canvas.cget("width"))
        height = int(canvas.winfo_height() or canvas.cget("height"))
        canvas.create_rectangle(0, 0, width, height, fill=DM_PAPER, outline="")
        if not analysis or not analysis.momentum:
            canvas.create_text(width / 2, height / 2, text="Run a match to reveal momentum swings.", fill=DM_MUTED_CHARCOAL, font=FONT_BODY)
            return
        max_tick = max(point.tick for point in analysis.momentum) or 1
        max_diff = max(abs(point.differential) for point in analysis.momentum) or 1
        coords: list[float] = []
        for point in analysis.momentum:
            x = 24 + (point.tick / max_tick) * (width - 48)
            y = (height / 2) - (point.differential / max_diff) * (height / 2 - 24)
            coords.extend([x, y])
        canvas.create_line(0, height / 2, width, height / 2, fill=DM_OFF_WHITE_LINE, dash=(4, 4), width=2)
        if len(coords) >= 4:
            canvas.create_line(*coords, smooth=True, width=3, fill=DM_BORDER)
        canvas.create_text(36, 18, text="Team A edge", fill=DM_MUTED_CHARCOAL, font=FONT_BODY)
        canvas.create_text(width - 44, height - 18, text="Team B edge", fill=DM_MUTED_CHARCOAL, font=FONT_BODY)

    def _jitter_setup(self) -> None:
        if not self.current_setup:
            return
        self.current_setup = randomize_setup(self.current_setup)
        self.current_lookup = build_lookup_from_setup(self.current_setup)
        self.current_events = []
        self.current_analysis = None
        self.current_summary = None
        self._refresh_setup_views()
        self._populate_event_views()
        self.status_var.set("Applied light rating jitter to the active setup.")

    def _random_setup(self) -> None:
        self.current_setup = generate_random_setup()
        self.current_lookup = build_lookup_from_setup(self.current_setup)
        self.setup_path_var.set("<random>")
        self.current_events = []
        self.current_analysis = None
        self.current_summary = None
        self._refresh_setup_views()
        self._populate_event_views()
        self.status_var.set("Generated fresh random teams.")

    def _open_setup_editor(self) -> None:
        if not self.current_setup:
            messagebox.showinfo("No matchup", "Load a matchup before editing.")
            return
        SetupEditor(self.master, self.current_setup, self._apply_custom_setup)

    def _refresh_matches(self) -> None:
        self.match_rows = list_recent_matches(self.conn, limit=20)
        self.match_tree.delete(*self.match_tree.get_children())
        for summary in self.match_rows:
            winner = summary.winner_team_id or "draw"
            matchup = f"{summary.team_a_id} vs {summary.team_b_id}"
            self.match_tree.insert("", tk.END, iid=str(summary.match_id), values=(summary.match_id, winner, matchup, summary.final_tick))
        self._refresh_intel()
        self._refresh_hub_cards()
        self.status_var.set(f"Loaded {len(self.match_rows)} stored matches.")

    def _sync_selected_match_summary(self) -> None:
        selection = self.match_tree.selection()
        if not selection:
            return
        match_id = int(selection[0])
        summary = next((row for row in self.match_rows if row.match_id == match_id), None)
        if summary:
            self.card_record.set(summary.winner_team_id or "Draw", f"Loaded replay #{summary.match_id} at tick {summary.final_tick}.")

    def _refresh_intel(self) -> None:
        headlines = load_news_headlines(self.conn)[:8]
        records = load_league_records(self.conn)[:6]
        hall = load_hall_of_fame(self.conn)[:5]
        patches = load_all_meta_patches(self.conn)[-4:]
        trophies = load_club_trophies(self.conn)[-6:]

        headline_items = [f"S{item['season_id']} W{item['week']} | {item['headline_text']}" for item in headlines] or ["No dynasty headlines yet."]
        meta_items = [f"{item['season_id']} | {item['name']} ({item['patch_id']})" for item in patches] or ["No saved patches yet."]
        hall_items = [
            f"{item['career_summary'].get('player_name', item['player_id'])} | legacy {item['career_summary'].get('legacy_score', 0):.1f}"
            for item in hall
        ] or ["No Hall of Fame inductees yet."]
        record_items = [f"{item['record_type']} | {item['record'].get('holder_name', item['holder_id'])} ({item['record_value']})" for item in records]
        record_items.extend([f"{item['season_id']} | {item['club_id']} won {item['trophy_type']}" for item in trophies])
        if not record_items:
            record_items = ["No league records or trophies saved yet."]

        self.headlines_list.set_items(headline_items)
        self.meta_list.set_items(meta_items)
        self.hall_list.set_items(hall_items)
        self.records_list.set_items(record_items)
        self.intel_snapshot.set(
            f"{len(headline_items)} feeds",
            f"{len(headlines)} headlines, {len(patches)} patches, {len(records)} records, {len(trophies)} trophies currently loaded.",
        )

    def _view_selected(self) -> None:
        selection = self.match_tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Select a saved match to view.")
            return
        match_id = int(selection[0])
        try:
            payload = fetch_match(self.conn, match_id)
        except KeyError:
            messagebox.showerror("Missing", f"Match {match_id} not found.")
            return
        try:
            events_to_show = max(1, int(self.events_var.get()))
        except ValueError:
            events_to_show = 18
        self.current_setup = match_setup_from_dict(payload["setup"])
        self.current_lookup = build_lookup_from_setup(self.current_setup)
        self.current_events = [MatchEvent(**event) for event in payload["events"]]
        self.current_analysis = analyze_match(self.current_events, self.current_setup)
        self.current_summary = StoredMatchSummary(
            match_id=payload["match_id"],
            seed=payload["seed"],
            winner_team_id=payload["winner_team_id"],
            difficulty=payload["difficulty"],
            team_a_id=payload["team_a_id"],
            team_b_id=payload["team_b_id"],
            config_version=payload["config_version"],
            final_tick=payload["final_tick"],
            created_at=payload["created_at"],
        )
        self.seed_var.set(str(payload["seed"]))
        self.difficulty_var.set(payload["difficulty"])
        self._refresh_setup_views()
        self._populate_event_views()
        self._update_match_report(events_to_show)
        self.main_notebook.select(self.match_tab)
        self.status_var.set(f"Loaded replay #{match_id} from the database.")


class SetupEditor(tk.Toplevel):
    def __init__(self, master: tk.Misc, setup: MatchSetup, on_save: Callable[[MatchSetup], None]):
        super().__init__(master)
        self.title("Edit Matchup")
        self.configure(bg=DM_CREAM)
        self.transient(master)
        self.resizable(True, True)
        self.payload = match_setup_to_dict(setup)
        self.on_save = on_save

        shell = ttk.Frame(self, padding=SPACE_2)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        ttk.Label(shell, text="Matchup Editor", style="HeroTitle.TLabel").grid(row=0, column=0, sticky="w")
        notebook = ttk.Notebook(shell)
        notebook.grid(row=1, column=0, sticky="nsew", pady=(SPACE_2, 0))

        self.team_panels: Dict[str, TeamPanel] = {}
        for key in ("team_a", "team_b"):
            panel = TeamPanel(notebook, self.payload[key])
            notebook.add(panel, text=self.payload[key]["name"])
            self.team_panels[key] = panel

        btn_row = ttk.Frame(shell)
        btn_row.grid(row=2, column=0, sticky="e", pady=(SPACE_2, 0))
        ttk.Button(btn_row, text="Save", command=self._save, style="Accent.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Cancel", command=self.destroy, style="Secondary.TButton").pack(side=tk.LEFT, padx=4)

    def _save(self) -> None:
        try:
            for panel in self.team_panels.values():
                panel.commit()
            new_setup = match_setup_from_dict(self.payload)
        except Exception as exc:
            messagebox.showerror("Invalid data", str(exc))
            return
        self.on_save(new_setup)
        self.destroy()


class TeamPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, team_payload: Dict[str, Any]):
        super().__init__(master, padding=SPACE_2)
        self.team = team_payload
        self.player_vars = {key: tk.StringVar() for key in ("id", "name", "accuracy", "power", "dodge", "catch", "stamina")}
        self.current_player_index: Optional[int] = None

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)

        info_frame = ttk.LabelFrame(self, text="Team Info", style="Panel.TLabelframe", padding=SPACE_2)
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        info_frame.columnconfigure(1, weight=1)
        ttk.Label(info_frame, text="Team ID").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, text=team_payload["id"]).grid(row=0, column=1, sticky="w")
        ttk.Label(info_frame, text="Team Name").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.team_name_var = tk.StringVar(value=team_payload.get("name", team_payload["id"]))
        ttk.Entry(info_frame, textvariable=self.team_name_var).grid(row=1, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(info_frame, text="Chemistry (0-1)").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.chemistry_var = tk.StringVar(value=str(team_payload.get("chemistry", 0.5)))
        ttk.Entry(info_frame, textvariable=self.chemistry_var).grid(row=2, column=1, sticky="ew", pady=(6, 0))

        policy_frame = ttk.LabelFrame(self, text="Coach Policy", style="Panel.TLabelframe", padding=SPACE_2)
        policy_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_2, 0))
        policy_frame.columnconfigure(1, weight=1)
        self.policy_vars: Dict[str, tk.StringVar] = {}
        for idx, key in enumerate(_POLICY_KEYS):
            ttk.Label(policy_frame, text=key.replace("_", " ").title()).grid(row=idx, column=0, sticky="w", pady=(0, 6))
            var = tk.StringVar(value=str(team_payload.get("coach_policy", {}).get(key, 0.5)))
            self.policy_vars[key] = var
            ttk.Entry(policy_frame, textvariable=var).grid(row=idx, column=1, sticky="ew", pady=(0, 6))

        players_frame = ttk.LabelFrame(self, text="Players", style="Panel.TLabelframe", padding=SPACE_2)
        players_frame.grid(row=2, column=0, sticky="nsew", pady=(SPACE_2, 0), padx=(0, 10))
        players_frame.rowconfigure(0, weight=1)
        players_frame.columnconfigure(0, weight=1)
        self.player_listbox = tk.Listbox(players_frame, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, borderwidth=0, highlightthickness=0, activestyle="none")
        self.player_listbox.grid(row=0, column=0, sticky="nsew")
        self.player_listbox.bind("<<ListboxSelect>>", self._on_player_select)
        player_scroll = ttk.Scrollbar(players_frame, command=self.player_listbox.yview)
        player_scroll.grid(row=0, column=1, sticky="ns")
        self.player_listbox.configure(yscrollcommand=player_scroll.set)
        btn_row = ttk.Frame(players_frame)
        btn_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_1, 0))
        ttk.Button(btn_row, text="Add Player", command=self._add_player, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Remove Player", command=self._remove_player, style="Secondary.TButton").pack(side=tk.LEFT)

        form_frame = ttk.LabelFrame(self, text="Player Details", style="Panel.TLabelframe", padding=SPACE_2)
        form_frame.grid(row=2, column=1, sticky="nsew", pady=(SPACE_2, 0))
        form_frame.columnconfigure(1, weight=1)
        for idx, key in enumerate(("id", "name", "accuracy", "power", "dodge", "catch", "stamina")):
            ttk.Label(form_frame, text=key.title()).grid(row=idx, column=0, sticky="w", pady=(0, 6))
            ttk.Entry(form_frame, textvariable=self.player_vars[key]).grid(row=idx, column=1, sticky="ew", pady=(0, 6))
        ttk.Button(form_frame, text="Apply Player Changes", command=self._save_player, style="Accent.TButton").grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(SPACE_1, 0)
        )

        self._refresh_players()

    def _refresh_players(self) -> None:
        players = self.team.get("players", [])
        self.player_listbox.delete(0, tk.END)
        for player in players:
            self.player_listbox.insert(tk.END, player.get("name", player.get("id")))
        if players:
            self.player_listbox.selection_set(0)
            self._load_player(0)
        else:
            self.current_player_index = None
            for var in self.player_vars.values():
                var.set("")

    def _on_player_select(self, _: tk.Event) -> None:
        selection = self.player_listbox.curselection()
        if selection:
            self._load_player(selection[0])

    def _load_player(self, index: int) -> None:
        players = self.team.get("players", [])
        if index < 0 or index >= len(players):
            return
        player = players[index]
        self.current_player_index = index
        self.player_vars["id"].set(player.get("id", ""))
        self.player_vars["name"].set(player.get("name", ""))
        ratings = player.get("ratings", {})
        for key in ("accuracy", "power", "dodge", "catch", "stamina"):
            self.player_vars[key].set(str(ratings.get(key, 60.0)))

    def _add_player(self) -> None:
        players = self.team.setdefault("players", [])
        new_index = len(players) + 1
        player_id = f"{self.team['id']}_p{new_index}"
        players.append(
            {
                "id": player_id,
                "name": f"Player {new_index}",
                "ratings": {stat: 60.0 for stat in ("accuracy", "power", "dodge", "catch", "stamina")},
                "traits": {"potential": 50.0, "growth_curve": 50.0, "consistency": 50.0, "pressure": 50.0},
            }
        )
        self._refresh_players()
        self.player_listbox.selection_clear(0, tk.END)
        self.player_listbox.selection_set(len(players) - 1)
        self._load_player(len(players) - 1)

    def _remove_player(self) -> None:
        selection = self.player_listbox.curselection()
        if not selection:
            messagebox.showinfo("Select player", "Select a player to remove.")
            return
        idx = selection[0]
        players = self.team.get("players", [])
        if len(players) <= 1:
            messagebox.showerror("Invalid", "Each team must keep at least one player.")
            return
        players.pop(idx)
        self._refresh_players()

    def _parse_float(self, value: str, label: str) -> float:
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be numeric.") from exc

    def _save_player(self) -> None:
        index = self.player_listbox.curselection()
        if not index:
            index = [self.current_player_index] if self.current_player_index is not None else []
        if not index:
            return
        idx = index[0]
        players = self.team.get("players", [])
        player = players[idx]
        player_id = self.player_vars["id"].get().strip()
        if not player_id:
            raise ValueError("Player ID cannot be empty.")
        player["id"] = player_id
        player["name"] = self.player_vars["name"].get().strip() or player_id
        ratings = player.get("ratings", {})
        for key in ("accuracy", "power", "dodge", "catch", "stamina"):
            ratings[key] = self._parse_float(self.player_vars[key].get(), key.title())
        player["ratings"] = ratings
        self._refresh_players()
        self.player_listbox.selection_clear(0, tk.END)
        self.player_listbox.selection_set(idx)
        self.current_player_index = idx

    def commit(self) -> None:
        if self.team.get("players"):
            self._save_player()
        if not self.team.get("players"):
            raise ValueError("Each team must have at least one player.")
        chemistry = self._parse_float(self.chemistry_var.get(), "Chemistry")
        self.team["chemistry"] = max(0.0, min(1.0, chemistry))
        name = self.team_name_var.get().strip()
        if name:
            self.team["name"] = name
        policy = self.team.setdefault("coach_policy", {})
        for key, var in self.policy_vars.items():
            value = self._parse_float(var.get(), key.replace("_", " ").title())
            policy[key] = max(0.0, min(1.0, value))


def _format_summary(summary: StoredMatchSummary) -> str:
    winner = summary.winner_team_id or "draw"
    return (
        f"#{summary.match_id:04d} seed={summary.seed} winner={winner} "
        f"{summary.team_a_id} vs {summary.team_b_id} "
        f"[{summary.difficulty} @ tick {summary.final_tick}]"
    )


def main() -> None:
    root = tk.Tk()
    DodgeballApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
