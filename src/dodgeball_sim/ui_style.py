from __future__ import annotations

import tkinter as tk
from tkinter import ttk

SPACE_1 = 8
SPACE_2 = 16
SPACE_3 = 24

DM_CREAM = "#F4F1EA"
DM_PAPER = "#FFF9EC"
DM_CHARCOAL = "#242428"
DM_MUTED_CHARCOAL = "#3A3A40"
DM_BRICK = "#B75A3A"
DM_BURNT_ORANGE = "#C66A32"
DM_MUSTARD = "#D6A23A"
DM_TEAL = "#6FA6A0"
DM_SAGE = "#8FA87E"
DM_GYM_BLUE = "#6C8FB3"
DM_RED = "#C94E3F"
DM_OFF_WHITE_LINE = "#EEE3D0"
DM_BORDER = "#2F2F35"
DM_BENCH = "#D8CCB9"
DM_NIGHT = "#214E5F"
DM_PANEL_TINT = "#F9F4E8"

FONT_TITLE = ("Bahnschrift SemiBold", 24)
FONT_SECTION = ("Segoe UI Semibold", 11)
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BADGE = ("Segoe UI Semibold", 9)
FONT_DISPLAY = ("Bahnschrift SemiBold", 34)
FONT_MONO = ("Consolas", 10)
FONT_SUBTITLE = ("Segoe UI", 12)
FONT_BUTTON = ("Segoe UI Semibold", 10)


def apply_theme(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=DM_CREAM)
    root.option_add("*Font", FONT_BODY)

    style.configure(".", background=DM_CREAM, foreground=DM_CHARCOAL)
    style.configure("TFrame", background=DM_CREAM)
    style.configure("Surface.TFrame", background=DM_PAPER, borderwidth=0)
    style.configure("Tint.TFrame", background=DM_PANEL_TINT)
    style.configure("SectionHeader.TLabel", background=DM_CREAM, foreground=DM_MUTED_CHARCOAL, font=FONT_SECTION)
    style.configure("RailHeader.TLabel", background=DM_CREAM, foreground=DM_MUTED_CHARCOAL, font=("Segoe UI Semibold", 10))
    style.configure("HeroTitle.TLabel", background=DM_CREAM, foreground=DM_CHARCOAL, font=FONT_TITLE)
    style.configure("Display.TLabel", background=DM_CREAM, foreground=DM_CHARCOAL, font=FONT_DISPLAY)
    style.configure("TopbarTitle.TLabel", background=DM_NIGHT, foreground=DM_PAPER, font=("Bahnschrift SemiBold", 26))
    style.configure("TopbarMuted.TLabel", background=DM_NIGHT, foreground=DM_OFF_WHITE_LINE, font=FONT_BODY)
    style.configure("Muted.TLabel", background=DM_CREAM, foreground=DM_MUTED_CHARCOAL)
    style.configure("CardValue.TLabel", background=DM_PAPER, foreground=DM_CHARCOAL, font=("Segoe UI Semibold", 15))
    style.configure("CardCaption.TLabel", background=DM_PAPER, foreground=DM_MUTED_CHARCOAL, font=FONT_SMALL)
    style.configure("Panel.TLabelframe", background=DM_PAPER, bordercolor=DM_BORDER, relief="solid", borderwidth=1)
    style.configure("Panel.TLabelframe.Label", background=DM_PAPER, foreground=DM_CHARCOAL, font=FONT_SECTION)
    style.configure("Rail.TLabelframe", background=DM_PANEL_TINT, bordercolor=DM_BORDER, relief="solid", borderwidth=1)
    style.configure("Rail.TLabelframe.Label", background=DM_PANEL_TINT, foreground=DM_MUTED_CHARCOAL, font=("Segoe UI Semibold", 10))
    style.configure(
        "Accent.TButton",
        background=DM_BURNT_ORANGE,
        foreground=DM_PAPER,
        bordercolor=DM_BORDER,
        focuscolor=DM_OFF_WHITE_LINE,
        padding=(10, 6),
    )
    style.map("Accent.TButton", background=[("active", DM_BRICK), ("pressed", DM_BRICK)])
    style.configure(
        "Secondary.TButton",
        background=DM_PAPER,
        foreground=DM_CHARCOAL,
        bordercolor=DM_BORDER,
        focuscolor=DM_OFF_WHITE_LINE,
        padding=(10, 6),
    )
    style.map("Secondary.TButton", background=[("active", DM_OFF_WHITE_LINE), ("pressed", DM_OFF_WHITE_LINE)])
    # Action/Quiet are spec-named aliases for Accent/Secondary
    style.configure(
        "Action.TButton",
        background=DM_BURNT_ORANGE,
        foreground=DM_PAPER,
        bordercolor=DM_BORDER,
        focuscolor=DM_OFF_WHITE_LINE,
        padding=(14, 8),
        font=FONT_BUTTON,
    )
    style.map("Action.TButton", background=[("active", DM_BRICK), ("pressed", DM_BRICK)])
    style.configure(
        "Quiet.TButton",
        background=DM_PAPER,
        foreground=DM_CHARCOAL,
        bordercolor=DM_BORDER,
        focuscolor=DM_OFF_WHITE_LINE,
        padding=(12, 7),
        font=FONT_BUTTON,
    )
    style.map("Quiet.TButton", background=[("active", DM_OFF_WHITE_LINE), ("pressed", DM_OFF_WHITE_LINE)])
    style.configure(
        "Subtitle.TLabel",
        background=DM_CREAM,
        foreground=DM_MUTED_CHARCOAL,
        font=FONT_SUBTITLE,
    )
    style.configure("TEntry", fieldbackground=DM_PAPER, foreground=DM_CHARCOAL, bordercolor=DM_BORDER)
    style.configure("TCombobox", fieldbackground=DM_PAPER, foreground=DM_CHARCOAL, bordercolor=DM_BORDER)
    style.configure("TNotebook", background=DM_CREAM, borderwidth=0)
    style.configure("TNotebook.Tab", background=DM_OFF_WHITE_LINE, foreground=DM_MUTED_CHARCOAL, padding=(16, 10), borderwidth=1)
    style.map("TNotebook.Tab", background=[("selected", DM_PAPER), ("active", DM_PANEL_TINT)], foreground=[("selected", DM_CHARCOAL)])
    style.configure("Treeview", background=DM_PAPER, fieldbackground=DM_PAPER, foreground=DM_CHARCOAL, bordercolor=DM_BORDER, rowheight=28)
    style.configure("Treeview.Heading", background=DM_OFF_WHITE_LINE, foreground=DM_CHARCOAL, relief="flat", font=FONT_SECTION)
    style.map("Treeview", background=[("selected", DM_TEAL)], foreground=[("selected", DM_CHARCOAL)])
    style.configure("Horizontal.TProgressbar", troughcolor=DM_OFF_WHITE_LINE, background=DM_SAGE, bordercolor=DM_BORDER, lightcolor=DM_SAGE, darkcolor=DM_SAGE)
    style.configure("Vertical.TScrollbar", background=DM_OFF_WHITE_LINE, troughcolor=DM_PAPER, bordercolor=DM_BORDER)
    return style


__all__ = [
    "DM_BENCH",
    "DM_BORDER",
    "DM_BRICK",
    "DM_BURNT_ORANGE",
    "DM_CHARCOAL",
    "DM_CREAM",
    "DM_GYM_BLUE",
    "DM_MUSTARD",
    "DM_MUTED_CHARCOAL",
    "DM_OFF_WHITE_LINE",
    "DM_PAPER",
    "DM_RED",
    "DM_SAGE",
    "DM_TEAL",
    "FONT_BADGE",
    "FONT_BODY",
    "FONT_BUTTON",
    "FONT_DISPLAY",
    "FONT_MONO",
    "FONT_SECTION",
    "FONT_SMALL",
    "FONT_SUBTITLE",
    "FONT_TITLE",
    "SPACE_1",
    "SPACE_2",
    "SPACE_3",
    "apply_theme",
]
