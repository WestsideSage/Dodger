from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Dict, Iterable, Sequence

from .events import MatchEvent
from .models import MatchSetup
from .ui_style import (
    DM_BENCH,
    DM_BORDER,
    DM_BRICK,
    DM_CHARCOAL,
    DM_CREAM,
    DM_GYM_BLUE,
    DM_MUSTARD,
    DM_OFF_WHITE_LINE,
    DM_PAPER,
    DM_RED,
    DM_TEAL,
)


@dataclass(frozen=True)
class PlayerToken:
    player_id: str
    team_id: str
    x: float
    y: float
    fill: str


class CourtRenderer:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas

    def render(
        self,
        setup: MatchSetup,
        events: Sequence[MatchEvent],
        event_index: int | None,
        *,
        team_colors: Dict[str, str] | None = None,
    ) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width = max(640, int(canvas.winfo_width() or canvas.cget("width")))
        height = max(320, int(canvas.winfo_height() or canvas.cget("height")))
        canvas.create_rectangle(0, 0, width, height, fill=DM_PAPER, outline="")
        court = (20, 28, width - 20, height - 36)
        canvas.create_rectangle(*court, fill=DM_CREAM, outline=DM_BORDER, width=2)
        mid_x = (court[0] + court[2]) / 2
        canvas.create_rectangle(court[0], court[1], mid_x, court[3], fill="#F0ECE1", outline="")
        canvas.create_rectangle(mid_x, court[1], court[2], court[3], fill="#ECE8DE", outline="")
        canvas.create_rectangle(*court, outline=DM_BORDER, width=2)
        canvas.create_line(mid_x, court[1], mid_x, court[3], fill=DM_BORDER, dash=(6, 4), width=2)
        canvas.create_line(court[0] + 90, court[1], court[0] + 90, court[3], fill=DM_OFF_WHITE_LINE, width=2)
        canvas.create_line(court[2] - 90, court[1], court[2] - 90, court[3], fill=DM_OFF_WHITE_LINE, width=2)
        color_a = (team_colors or {}).get(setup.team_a.id, DM_TEAL)
        color_b = (team_colors or {}).get(setup.team_b.id, DM_GYM_BLUE)
        canvas.create_rectangle(court[0], court[1], court[0] + 8, court[3], fill=color_a, outline="")
        canvas.create_rectangle(court[2] - 8, court[1], court[2], court[3], fill=color_b, outline="")
        canvas.create_text(court[0] + 78, court[1] + 16, text=setup.team_a.name, fill=color_a, font=("Segoe UI Semibold", 11))
        canvas.create_text(court[2] - 78, court[1] + 16, text=setup.team_b.name, fill=color_b, font=("Segoe UI Semibold", 11))
        canvas.create_text(court[0] + 12, 12, anchor="w", text="Replay reads the engine log", fill=DM_CHARCOAL, font=("Segoe UI Semibold", 10))

        tokens = self._build_tokens(setup, court, {setup.team_a.id: color_a, setup.team_b.id: color_b})
        eliminated = self._eliminated_players(events[: max(event_index or 0, 0) + 1] if event_index is not None else ())
        event = events[event_index] if event_index is not None and 0 <= event_index < len(events) else None

        for token in tokens.values():
            is_out = token.player_id in eliminated
            self._draw_player(token, is_out)

        if event and event.event_type == "throw":
            thrower = tokens.get(event.actors.get("thrower"))
            target = tokens.get(event.actors.get("target"))
            if thrower and target:
                resolution = str(event.outcome.get("resolution", "live"))
                line_color = DM_BRICK
                if resolution == "catch":
                    line_color = DM_MUSTARD
                elif resolution == "dodged":
                    line_color = DM_GYM_BLUE
                elif resolution in ("hit", "failed_catch"):
                    line_color = DM_RED
                canvas.create_line(thrower.x, thrower.y, target.x, target.y, fill=line_color, width=4, arrow=tk.LAST)
                canvas.create_oval(thrower.x - 23, thrower.y - 23, thrower.x + 23, thrower.y + 23, outline=DM_MUSTARD, width=3)
                canvas.create_oval(target.x - 27, target.y - 27, target.x + 27, target.y + 27, outline=line_color, width=4)
                mid_x = (thrower.x + target.x) / 2
                mid_y = (thrower.y + target.y) / 2
                canvas.create_oval(mid_x - 7, mid_y - 7, mid_x + 7, mid_y + 7, fill=line_color, outline=DM_BORDER, width=1)
                if event.state_diff.get("player_out"):
                    out_id = event.state_diff["player_out"].get("player_id", "")
                    out_token = tokens.get(out_id)
                    if out_token:
                        canvas.create_line(out_token.x - 22, out_token.y - 22, out_token.x + 22, out_token.y + 22, fill=DM_RED, width=4)
                        canvas.create_line(out_token.x + 22, out_token.y - 22, out_token.x - 22, out_token.y + 22, fill=DM_RED, width=4)
                canvas.create_text(
                    width / 2,
                    height - 12,
                    text=f"{event.outcome.get('resolution', 'live').upper()} | tick {event.tick}",
                    fill=line_color,
                    font=("Segoe UI Semibold", 11),
                )
        elif event and event.event_type == "match_end":
            winner = event.outcome.get("winner") or "-"
            canvas.create_rectangle(court[0] + 110, court[1] + 72, court[2] - 110, court[3] - 72, fill=DM_PAPER, outline=DM_BORDER, width=2)
            canvas.create_text(width / 2, height / 2 - 14, text="FINAL", fill=DM_CHARCOAL, font=("Bahnschrift SemiBold", 28))
            canvas.create_text(width / 2, height / 2 + 24, text=str(winner), fill=DM_BRICK, font=("Segoe UI Semibold", 16))
        else:
            canvas.create_text(width / 2, height - 12, text="Select an event to inspect the court state.", fill=DM_CHARCOAL, font=("Segoe UI", 10))

    def _build_tokens(
        self,
        setup: MatchSetup,
        court: tuple[int, int, int, int],
        colors: Dict[str, str],
    ) -> Dict[str, PlayerToken]:
        left_x = court[0] + 120
        right_x = court[2] - 120
        tokens: Dict[str, PlayerToken] = {}
        for team, x in ((setup.team_a, left_x), (setup.team_b, right_x)):
            rows = self._y_positions(len(team.players), court[1] + 40, court[3] - 40)
            fill = colors.get(team.id, DM_TEAL if team is setup.team_a else DM_GYM_BLUE)
            for player, y in zip(team.players, rows):
                tokens[player.id] = PlayerToken(player_id=player.id, team_id=team.id, x=x, y=y, fill=fill)
        return tokens

    def _y_positions(self, count: int, top: int, bottom: int) -> list[float]:
        if count <= 1:
            return [(top + bottom) / 2]
        gap = (bottom - top) / (count - 1)
        return [top + gap * index for index in range(count)]

    def _eliminated_players(self, events: Iterable[MatchEvent]) -> set[str]:
        eliminated: set[str] = set()
        for event in events:
            player_out = event.state_diff.get("player_out") or event.outcome.get("player_out")
            if isinstance(player_out, dict):
                player_id = player_out.get("player_id")
                if player_id:
                    eliminated.add(player_id)
            elif player_out:
                eliminated.add(str(player_out))
        return eliminated

    def _draw_player(self, token: PlayerToken, is_out: bool) -> None:
        fill = DM_BENCH if is_out else token.fill
        outline = DM_RED if is_out else DM_BORDER
        radius = 16
        self.canvas.create_oval(token.x - radius, token.y - radius, token.x + radius, token.y + radius, fill=fill, outline=outline, width=2)
        initials = "".join(part[0] for part in token.player_id.split("_")[:2]).upper()
        self.canvas.create_text(token.x, token.y, text=initials[:2], fill=DM_PAPER if not is_out else DM_CHARCOAL, font=("Segoe UI Semibold", 9))


__all__ = ["CourtRenderer"]
