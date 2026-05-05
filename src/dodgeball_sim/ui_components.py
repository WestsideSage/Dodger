from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .ui_style import DM_BORDER, DM_MUTED_CHARCOAL, DM_OFF_WHITE_LINE, DM_PAPER, FONT_BADGE, FONT_BODY, FONT_SUBTITLE


class StatCard(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, value: str = "-", caption: str = ""):
        super().__init__(master, style="Surface.TFrame", padding=12)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title.upper(), style="CardCaption.TLabel").grid(row=0, column=0, sticky="w")
        self.value_var = tk.StringVar(value=value)
        self.caption_var = tk.StringVar(value=caption)
        ttk.Label(self, textvariable=self.value_var, style="CardValue.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 2))
        ttk.Label(self, textvariable=self.caption_var, style="CardCaption.TLabel", wraplength=220, justify="left").grid(row=2, column=0, sticky="w")

    def set(self, value: str, caption: str = "") -> None:
        self.value_var.set(value)
        self.caption_var.set(caption)


class InfoList(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str):
        super().__init__(master, style="Surface.TFrame", padding=12)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title, style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        self.listbox = tk.Listbox(
            self,
            bg=DM_PAPER,
            fg=DM_MUTED_CHARCOAL,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            font=FONT_BODY,
        )
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.rowconfigure(1, weight=1)

    def set_items(self, items: list[str]) -> None:
        self.listbox.delete(0, tk.END)
        for item in items:
            self.listbox.insert(tk.END, item)


class MetricStrip(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, value: str = "-", note: str = ""):
        super().__init__(master, style="Surface.TFrame", padding=(12, 10))
        self.columnconfigure(1, weight=1)
        ttk.Label(self, text=title.upper(), style="CardCaption.TLabel").grid(row=0, column=0, sticky="w")
        self.value_var = tk.StringVar(value=value)
        self.note_var = tk.StringVar(value=note)
        ttk.Label(self, textvariable=self.value_var, style="CardValue.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(self, textvariable=self.note_var, style="Muted.TLabel", wraplength=280, justify="left").grid(row=1, column=1, sticky="w", padx=(12, 0))

    def set(self, value: str, note: str) -> None:
        self.value_var.set(value)
        self.note_var.set(note)


class HeroAction(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, note: str, button_text: str, command):
        super().__init__(master, style="Surface.TFrame", padding=14)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title.upper(), style="CardCaption.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self, text=note, style="Muted.TLabel", wraplength=240, justify="left").grid(row=1, column=0, sticky="w", pady=(6, 10))
        ttk.Button(self, text=button_text, command=command, style="Accent.TButton").grid(row=2, column=0, sticky="ew")


class RatingBar(ttk.Frame):
    def __init__(self, master: tk.Misc, label: str):
        super().__init__(master, style="Surface.TFrame")
        self.columnconfigure(1, weight=1)
        tk.Label(self, text=label, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.value_var = tk.StringVar(value="0")
        tk.Label(self, textvariable=self.value_var, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(row=0, column=2, sticky="e", padx=(8, 0))
        self.progress = ttk.Progressbar(self, maximum=100, mode="determinate")
        self.progress.grid(row=0, column=1, sticky="ew")

    def set(self, value: float) -> None:
        self.progress["value"] = max(0.0, min(100.0, value))
        self.value_var.set(f"{value:.0f}")


_UNCERTAINTY_BAR_HALO_WIDTHS = {
    "UNKNOWN": 100,
    "GLIMPSED": 30,
    "KNOWN": 12,
    "VERIFIED": 0,
}


def uncertainty_bar_halo_width_for_tier(tier: str) -> int:
    """Map a scouting tier to the total visible uncertainty width."""
    return _UNCERTAINTY_BAR_HALO_WIDTHS.get(tier, 100)


class UncertaintyBar(ttk.Frame):
    """Small ratings bar with tier-driven uncertainty halo."""

    def __init__(self, master: tk.Misc, label: str = ""):
        super().__init__(master, style="Surface.TFrame")
        self.columnconfigure(1, weight=1)
        if label:
            tk.Label(self, text=label, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(
                row=0, column=0, sticky="w", padx=(0, 8)
            )
        self._canvas = tk.Canvas(self, height=18, bg=DM_PAPER, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=1, sticky="ew")
        self.value_var = tk.StringVar(value="?")
        tk.Label(self, textvariable=self.value_var, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(
            row=0, column=2, sticky="e", padx=(8, 0)
        )

    def set(self, midpoint: float, tier: str) -> None:
        self._canvas.delete("all")
        width = max(1, int(self._canvas.winfo_width()))
        halo_total = uncertainty_bar_halo_width_for_tier(tier)

        def x(ovr: float) -> int:
            return int(round((ovr / 100.0) * width))

        midpoint = max(0.0, min(100.0, midpoint))
        if tier == "VERIFIED":
            xpos = x(midpoint)
            self._canvas.create_line(xpos, 4, xpos, 14, fill=DM_BORDER, width=2)
            self.value_var.set(f"{midpoint:.0f}")
            return

        low = max(0.0, midpoint - halo_total / 2)
        high = min(100.0, midpoint + halo_total / 2)
        self._canvas.create_rectangle(x(low), 6, x(high), 12, fill=DM_OFF_WHITE_LINE, outline="")
        self._canvas.create_oval(x(midpoint) - 4, 5, x(midpoint) + 4, 13, fill=DM_BORDER, outline="")
        self.value_var.set(f"{int(low)}-{int(high)}")


class PageHeader(ttk.Frame):
    """Reusable page-level header with title and optional subtitle."""

    def __init__(self, master: tk.Misc, title: str, subtitle: str = "") -> None:
        super().__init__(master, style="TFrame")
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title, style="Display.TLabel").grid(row=0, column=0, sticky="w")
        if subtitle:
            ttk.Label(
                self,
                text=subtitle,
                style="Subtitle.TLabel",
                wraplength=760,
                justify="left",
            ).grid(row=1, column=0, sticky="w", pady=(4, 0))


def make_badge(master: tk.Misc, text: str) -> tk.Label:
    return tk.Label(
        master,
        text=text,
        bg=DM_OFF_WHITE_LINE,
        fg=DM_BORDER,
        font=FONT_BADGE,
        padx=8,
        pady=3,
        relief="solid",
        bd=1,
    )


__all__ = [
    "HeroAction",
    "InfoList",
    "MetricStrip",
    "PageHeader",
    "RatingBar",
    "StatCard",
    "UncertaintyBar",
    "make_badge",
    "uncertainty_bar_halo_width_for_tier",
]
