from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .persistence import load_rivalry_records
from .playoffs import playoff_stage_label
from .voice_register import tier1


@dataclass(frozen=True)
class BroadcastTag:
    label: str
    tone: str
    proof_source: str


@dataclass(frozen=True)
class BroadcastHook:
    text: str
    proof_source: str


@dataclass(frozen=True)
class BroadcastFrame:
    stakes_tag: BroadcastTag | None
    rivalry_tag: BroadcastTag | None
    archetype_tag: BroadcastTag | None
    historical_hook: BroadcastHook | None
    voice_slot: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlayoffFrame:
    label: str
    title: str
    proof_source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CommentaryInsert:
    text: str
    source_event_id: int | str
    source_record_id: str
    source_event_index: int
    proof_source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_broadcast_frame(
    *,
    season_id: str,
    match_id: str | None,
    week: int,
    player_club_id: str,
    opponent_club_id: str,
    rivalry_summary: Mapping[str, Any] | None,
    last_meeting: Mapping[str, Any] | None,
    trajectory_row: Mapping[str, Any] | None,
) -> BroadcastFrame:
    stage_label = playoff_stage_label(season_id, match_id or "")
    stakes_tag, voice_slot = _stakes_tag(stage_label, week, match_id)
    rivalry_tag = _rivalry_tag(player_club_id, opponent_club_id, rivalry_summary)
    archetype_tag = _archetype_tag(trajectory_row)
    historical_hook = _historical_hook(
        player_club_id=player_club_id,
        opponent_club_id=opponent_club_id,
        rivalry_summary=rivalry_summary,
        last_meeting=last_meeting,
        stage_label=stage_label,
    )
    return BroadcastFrame(
        stakes_tag=stakes_tag,
        rivalry_tag=rivalry_tag,
        archetype_tag=archetype_tag,
        historical_hook=historical_hook,
        voice_slot=voice_slot,
    )


def build_playoff_frame(*, season_id: str, match_id: str) -> PlayoffFrame | None:
    stage_label = playoff_stage_label(season_id, match_id)
    if stage_label == "Playoff Final":
        return PlayoffFrame(
            label=stage_label,
            title=tier1("broadcast.playoff_final.title"),
            proof_source=f"match:{match_id}",
        )
    if stage_label == "Playoff Semifinal":
        return PlayoffFrame(
            label=stage_label,
            title=tier1("broadcast.playoff_semifinal.title"),
            proof_source=f"match:{match_id}",
        )
    return None


def build_commentary_inserts(
    events: Sequence[Mapping[str, Any]],
    *,
    record_items: Sequence[Mapping[str, Any]],
    name_map: Mapping[str, str],
    cap: int = 3,
) -> list[CommentaryInsert]:
    player_records = {
        str(item.get("record_type", "")): item
        for item in record_items
        if item.get("holder_type") == "player"
    }
    inserts: list[CommentaryInsert] = []
    used_record_types: set[str] = set()
    for index, event in enumerate(events):
        if len(inserts) >= cap:
            break
        if event.get("event_type") != "throw":
            continue
        resolution = str((event.get("outcome") or {}).get("resolution", ""))
        actors = event.get("actors") or {}
        thrower_id = str(actors.get("thrower", ""))
        target_id = str(actors.get("target", ""))
        event_id = event.get("event_id")

        note = _record_insert_for_event(
            resolution=resolution,
            thrower_id=thrower_id,
            target_id=target_id,
            event_id=event_id,
            event_index=index,
            player_records=player_records,
            used_record_types=used_record_types,
            name_map=name_map,
        )
        if note is None:
            continue
        used_record_types.add(note.source_record_id)
        inserts.append(note)
    return inserts


def load_matchup_broadcast_frame(
    conn,
    *,
    season_id: str,
    player_club_id: str,
    opponent_club_id: str,
    match_id: str | None,
    week: int,
    trajectory_row: Mapping[str, Any] | None = None,
) -> BroadcastFrame:
    rivalry_summary = load_rivalry_summary(conn, player_club_id, opponent_club_id)
    last_meeting = load_last_meeting(
        conn,
        season_id=season_id,
        player_club_id=player_club_id,
        opponent_club_id=opponent_club_id,
        exclude_match_id=match_id,
    )
    return build_broadcast_frame(
        season_id=season_id,
        match_id=match_id,
        week=week,
        player_club_id=player_club_id,
        opponent_club_id=opponent_club_id,
        rivalry_summary=rivalry_summary,
        last_meeting=last_meeting,
        trajectory_row=trajectory_row,
    )


def load_rivalry_summary(conn, club_a_id: str, club_b_id: str) -> dict[str, Any] | None:
    key = frozenset((club_a_id, club_b_id))
    for item in load_rivalry_records(conn):
        if frozenset((item["club_a_id"], item["club_b_id"])) == key:
            return item
    return None


def load_last_meeting(
    conn,
    *,
    season_id: str,
    player_club_id: str,
    opponent_club_id: str,
    exclude_match_id: str | None = None,
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT match_id, week, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
          AND (
            (home_club_id = ? AND away_club_id = ?)
            OR (home_club_id = ? AND away_club_id = ?)
          )
        ORDER BY week DESC, match_id DESC
        """,
        (season_id, player_club_id, opponent_club_id, opponent_club_id, player_club_id),
    ).fetchall()
    for row in rows:
        if exclude_match_id and row["match_id"] == exclude_match_id:
            continue
        return dict(row)
    return None


def _stakes_tag(
    stage_label: str,
    week: int,
    match_id: str | None,
) -> tuple[BroadcastTag, str]:
    if stage_label == "Playoff Final":
        return (
            BroadcastTag("Playoff Final", "title", f"match:{match_id or 'playoff_final'}"),
            "broadcast.playoff_final",
        )
    if stage_label == "Playoff Semifinal":
        return (
            BroadcastTag("Playoff Semifinal", "playoff", f"match:{match_id or 'playoff_semifinal'}"),
            "broadcast.playoff_semifinal",
        )
    if week <= 1:
        return (
            BroadcastTag("Week 1 Opener", "opening", f"week:{week}"),
            "broadcast.week_opener",
        )
    return (
        BroadcastTag("Regular Season", "regular", f"week:{week}"),
        "broadcast.regular_season",
    )


def _rivalry_tag(
    player_club_id: str,
    opponent_club_id: str,
    rivalry_summary: Mapping[str, Any] | None,
) -> BroadcastTag | None:
    if rivalry_summary is None:
        return None
    rivalry = rivalry_summary.get("rivalry") or {}
    score = float(rivalry.get("rivalry_score", 0.0) or 0.0)
    meetings = int(rivalry.get("total_meetings", 0) or 0)
    playoff_meetings = int(rivalry.get("playoff_meetings", 0) or 0)
    championship_meetings = int(rivalry.get("championship_meetings", 0) or 0)
    if championship_meetings > 0 or score >= 55.0 or (meetings >= 4 and playoff_meetings > 0):
        return BroadcastTag(
            label=tier1("broadcast.rivalry_tag"),
            tone="rivalry",
            proof_source=f"rivalry:{player_club_id}:{opponent_club_id}",
        )
    return None


def _archetype_tag(trajectory_row: Mapping[str, Any] | None) -> BroadcastTag | None:
    if trajectory_row is None:
        return None
    label = str(
        trajectory_row.get("program_archetype")
        or trajectory_row.get("trajectory")
        or trajectory_row.get("label")
        or ""
    ).strip()
    if not label:
        return None
    return BroadcastTag(
        label=label.replace("_", " ").title(),
        tone="trajectory",
        proof_source=f"trajectory:{trajectory_row.get('row_id', label)}",
    )


def _historical_hook(
    *,
    player_club_id: str,
    opponent_club_id: str,
    rivalry_summary: Mapping[str, Any] | None,
    last_meeting: Mapping[str, Any] | None,
    stage_label: str,
) -> BroadcastHook | None:
    if rivalry_summary is not None:
        rivalry = rivalry_summary.get("rivalry") or {}
        championship_meetings = int(rivalry.get("championship_meetings", 0) or 0)
        playoff_meetings = int(rivalry.get("playoff_meetings", 0) or 0)
        meetings = int(rivalry.get("total_meetings", 0) or 0)
        if championship_meetings > 0:
            return BroadcastHook(
                text=(
                    f"These clubs already own {championship_meetings} championship "
                    f"meeting{'s' if championship_meetings != 1 else ''}."
                ),
                proof_source=f"rivalry:{player_club_id}:{opponent_club_id}",
            )
        if playoff_meetings > 0 and stage_label != "Regular Season":
            return BroadcastHook(
                text=(
                    f"They have already crossed in {playoff_meetings} playoff "
                    f"meeting{'s' if playoff_meetings != 1 else ''}."
                ),
                proof_source=f"rivalry:{player_club_id}:{opponent_club_id}",
            )
        if meetings >= 3:
            return BroadcastHook(
                text=f"This is meeting {meetings + 1} in a series that keeps getting hotter.",
                proof_source=f"rivalry:{player_club_id}:{opponent_club_id}",
            )
    if last_meeting is not None:
        result = _meeting_result(player_club_id, opponent_club_id, last_meeting)
        home_survivors = int(last_meeting.get("home_survivors", 0))
        away_survivors = int(last_meeting.get("away_survivors", 0))
        if last_meeting.get("home_club_id") == player_club_id:
            player_score, opp_score = home_survivors, away_survivors
        else:
            player_score, opp_score = away_survivors, home_survivors
        return BroadcastHook(
            text=(
                f"Last time out: Week {int(last_meeting.get('week', 0))} "
                f"{result} {player_score}-{opp_score}."
            ),
            proof_source=f"match:{last_meeting.get('match_id', 'last_meeting')}",
        )
    return None


def _meeting_result(
    player_club_id: str,
    opponent_club_id: str,
    meeting: Mapping[str, Any],
) -> str:
    winner = meeting.get("winner_club_id")
    if winner == player_club_id:
        return "Win"
    if winner == opponent_club_id:
        return "Loss"
    return "Draw"


def _record_insert_for_event(
    *,
    resolution: str,
    thrower_id: str,
    target_id: str,
    event_id: Any,
    event_index: int,
    player_records: Mapping[str, Mapping[str, Any]],
    used_record_types: set[str],
    name_map: Mapping[str, str],
) -> CommentaryInsert | None:
    def player_name(player_id: str) -> str:
        return name_map.get(player_id, player_id)

    elimination_record = player_records.get("most_career_eliminations")
    if (
        elimination_record
        and elimination_record.get("holder_id") == thrower_id
        and resolution in {"hit", "failed_catch"}
        and "most_career_eliminations" not in used_record_types
    ):
        return CommentaryInsert(
            text=tier1("broadcast.commentary.record_eliminations", player=player_name(thrower_id)),
            source_event_id=event_id,
            source_record_id="most_career_eliminations",
            source_event_index=event_index,
            proof_source=f"event:{event_id}|record:most_career_eliminations",
        )

    catches_record = player_records.get("most_career_catches")
    if (
        catches_record
        and catches_record.get("holder_id") == target_id
        and resolution == "catch"
        and "most_career_catches" not in used_record_types
    ):
        return CommentaryInsert(
            text=tier1("broadcast.commentary.record_catches", player=player_name(target_id)),
            source_event_id=event_id,
            source_record_id="most_career_catches",
            source_event_index=event_index,
            proof_source=f"event:{event_id}|record:most_career_catches",
        )

    dodges_record = player_records.get("most_career_dodges")
    if (
        dodges_record
        and dodges_record.get("holder_id") == target_id
        and resolution == "dodged"
        and "most_career_dodges" not in used_record_types
    ):
        return CommentaryInsert(
            text=tier1("broadcast.commentary.record_dodges", player=player_name(target_id)),
            source_event_id=event_id,
            source_record_id="most_career_dodges",
            source_event_index=event_index,
            proof_source=f"event:{event_id}|record:most_career_dodges",
        )
    return None


__all__ = [
    "BroadcastFrame",
    "BroadcastHook",
    "BroadcastTag",
    "CommentaryInsert",
    "PlayoffFrame",
    "build_broadcast_frame",
    "build_commentary_inserts",
    "build_playoff_frame",
    "load_last_meeting",
    "load_matchup_broadcast_frame",
    "load_rivalry_summary",
]
