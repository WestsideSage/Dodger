from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable, Tuple

from .analysis import MatchAnalysis, analyze_match
from .engine import MatchEngine
from .events import MatchEvent
from .models import MatchSetup
from .narration import build_lookup_from_setup, narrate_event
from .persistence import (
    StoredMatchSummary,
    connect,
    fetch_match,
    initialize_schema,
    list_recent_matches,
    record_match,
)
from .sample_data import describe_sample_matchup, sample_match_setup
from .setup_loader import (
    format_matchup_summary,
    load_match_setup_from_path,
    match_setup_from_dict,
)

_DEFAULT_DB = Path("dodgeball_sim.db")


def _run_and_record(
    conn: sqlite3.Connection,
    *,
    setup: MatchSetup,
    seed: int,
    difficulty: str,
) -> Tuple[int, StoredMatchSummary, MatchAnalysis, Tuple[MatchEvent, ...]]:
    engine = MatchEngine()
    result = engine.run(setup, seed=seed, difficulty=difficulty)
    match_id = record_match(conn, setup=setup, result=result, difficulty=difficulty)
    summary = StoredMatchSummary(
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
    analysis = analyze_match(result.events, setup)
    return match_id, summary, analysis, tuple(result.events)


def _format_summary(summary: StoredMatchSummary) -> str:
    winner = summary.winner_team_id or "draw"
    return (
        f"#{summary.match_id:04d} seed={summary.seed} winner={winner} "
        f"{summary.team_a_id} vs {summary.team_b_id} "
        f"[{summary.difficulty} @ tick {summary.final_tick}]"
    )


def _print_recent(conn: sqlite3.Connection) -> None:
    summaries = list_recent_matches(conn, limit=5)
    if not summaries:
        print("No matches recorded yet.")
        return
    print("Recent matches:")
    for summary in summaries:
        print("  -", _format_summary(summary))


def _show_match(conn: sqlite3.Connection, match_id: int, *, events_to_show: int) -> None:
    try:
        payload = fetch_match(conn, match_id)
    except KeyError:
        print(f"Match {match_id} not found")
        return
    setup = match_setup_from_dict(payload["setup"])
    lookup = build_lookup_from_setup(setup)
    events = [MatchEvent(**evt) for evt in payload["events"]]
    analysis = analyze_match(events, setup)
    summary = StoredMatchSummary(
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

    print(format_matchup_summary(setup))
    print(_format_summary(summary))
    _print_analysis_highlights(analysis, lookup)
    print("First events:")
    for event in events[:events_to_show]:
        print(f"  {narrate_event(event, lookup)}")


def _interactive_loop(
    conn: sqlite3.Connection,
    *,
    setup: MatchSetup,
    description: str,
    difficulty: str,
    default_seed: int,
    events_to_show: int,
) -> None:
    next_seed = default_seed
    lookup = build_lookup_from_setup(setup)
    while True:
        print("\n=== Dodgeball Manager Prototype ===")
        print(description)
        print("Options: [r]un match (optionally 'r <seed>'), [l]ist recent, [v]iew match <id>, [q]uit")
        choice = input("Enter choice: ").strip()
        if not choice:
            continue
        cmd = choice.lower().split()
        action = cmd[0]
        if action == "q":
            print("Exiting.")
            return
        if action == "l":
            _print_recent(conn)
            continue
        if action == "r":
            if len(cmd) > 1 and cmd[1].isdigit():
                run_seed = int(cmd[1])
            else:
                run_seed = next_seed
                next_seed += 1
            match_id, summary, analysis, events = _run_and_record(
                conn,
                setup=setup,
                seed=run_seed,
                difficulty=difficulty,
            )
            print(f"Saved match #{match_id} with seed {run_seed} and difficulty {difficulty}.")
            print(format_matchup_summary(setup))
            print(_format_summary(summary))
            _print_analysis_highlights(analysis, lookup)
            print("First events:")
            for event in events[:events_to_show]:
                print(f"  {narrate_event(event, lookup)}")
            continue
        if action == "v":
            if len(cmd) < 2 or not cmd[1].isdigit():
                print("Usage: v <match_id>")
                continue
            _show_match(conn, int(cmd[1]), events_to_show=events_to_show)
            continue
        print("Unknown option. Use r/l/v/q.")


def _print_analysis_highlights(analysis: MatchAnalysis, lookup) -> None:
    if analysis.hero:
        hero = analysis.hero
        print(f"  HERO: {lookup.player(hero.player_id)} kept {lookup.team(hero.team_id)} alive!")
    if analysis.momentum:
        max_point = max(analysis.momentum, key=lambda p: abs(p.differential))
        if max_point.differential == 0:
            print("  Momentum: perfectly balanced duel.")
        else:
            direction = "team A" if max_point.differential > 0 else "team B"
            print(
                f"  Momentum: biggest swing {abs(max_point.differential)} for {direction} around tick {max_point.tick}."
            )


def _resolve_setup(path: str | None) -> Tuple[MatchSetup, str]:
    if path:
        setup = load_match_setup_from_path(path)
        return setup, f"Loaded from {path}:\n{format_matchup_summary(setup)}"
    setup = sample_match_setup()
    return setup, f"Sample matchup:\n{describe_sample_matchup()}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Dodgeball Manager prototype CLI")
    parser.add_argument("--db", default=str(_DEFAULT_DB), help="Path to SQLite DB (default dodgeball_sim.db)")
    parser.add_argument("--dynasty", action="store_true", help="Start dynasty mode (season league management)")
    parser.add_argument("--seed", type=int, default=31415, help="Base seed (auto mode increments when omitted)")
    parser.add_argument(
        "--difficulty",
        choices=["rookie", "pro", "elite"],
        default="pro",
        help="Difficulty profile (affects coach decision quality)",
    )
    parser.add_argument("--setup", help="Path to JSON match setup (defaults to sample matchup)")
    parser.add_argument(
        "--events",
        type=int,
        default=5,
        help="Number of events to show when viewing a saved match",
    )
    parser.add_argument("--auto", action="store_true", help="Run once (non-interactive) and print summary")
    parser.add_argument("--show", type=int, metavar="MATCH_ID", help="Print details for an existing match and exit")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    conn = connect(args.db)
    initialize_schema(conn)

    if args.dynasty:
        from .dynasty_cli import dynasty_main
        dynasty_main(conn, difficulty=args.difficulty)
        return

    setup, description = _resolve_setup(args.setup)

    if args.show is not None:
        _show_match(conn, args.show, events_to_show=args.events)
        return

    if args.auto:
        match_id, summary, analysis, events = _run_and_record(
            conn,
            setup=setup,
            seed=args.seed,
            difficulty=args.difficulty,
        )
        lookup = build_lookup_from_setup(setup)
        print(format_matchup_summary(setup))
        print(_format_summary(summary))
        _print_analysis_highlights(analysis, lookup)
        print("First events:")
        for event in events[:args.events]:
            print(f"  {narrate_event(event, lookup)}")
        print(f"Stored as match #{match_id} in {args.db}")
        return

    _interactive_loop(
        conn,
        setup=setup,
        description=description,
        difficulty=args.difficulty,
        default_seed=args.seed,
        events_to_show=args.events,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
