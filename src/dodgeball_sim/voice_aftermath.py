from .rng import DeterministicRNG

# Generic fallback templates — used only when survivor counts are unavailable.
_WIN_TEMPLATES = [
    "A decisive Win for the squad.",
    "The team secures a hard-fought Win.",
    "An impressive Win that sends a message.",
    "They walk away with a Win this week.",
    "The final whistle seals a Win.",
    "A Win that shifts the momentum.",
    "The scoreboard reflects a Win.",
    "A gritty, unpolished Win.",
    "They ground out a Win.",
    "A methodical Win executed perfectly.",
]

_LOSS_TEMPLATES = [
    "A tough Loss the squad will want to forget.",
    "The team falls to a hard Loss.",
    "A costly Loss that raises questions.",
    "They drop this one — a Loss that stings.",
    "The final whistle seals a damaging Loss.",
    "A Loss that shifts the momentum the wrong way.",
    "The scoreboard reflects a difficult Loss.",
    "A grinding, painful Loss.",
    "They couldn't hold on — a Loss.",
    "A Loss built on missed opportunities.",
]

_DRAW_TEMPLATES = [
    "A hard-fought Draw — honors even.",
    "Neither side blinked: a Draw.",
    "The squad settles for a Draw.",
]

# Margin-aware templates. ``{score}`` is replaced with the player-perspective
# scoreline (own survivors first). Every Win/Loss template keeps the literal
# result word so downstream copy and tests stay stable.
_MARGIN_TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("Win", "shutout"): [
        "A {score} shutout Win — the squad never let them breathe.",
        "Total control in a {score} shutout Win.",
        "A {score} Win without conceding a single survivor.",
    ],
    ("Win", "dominant"): [
        "A commanding {score} Win for the squad.",
        "A {score} Win that was never in doubt.",
        "The squad dictates terms in a {score} Win.",
    ],
    ("Win", "solid"): [
        "A solid {score} Win on the court.",
        "The squad banks a {score} Win.",
        "A composed {score} Win this week.",
    ],
    ("Win", "narrow"): [
        "A nervy {score} Win, decided in the margins.",
        "The squad edges it {score} — a Win by inches.",
        "A {score} Win that came down to the final exchanges.",
    ],
    ("Loss", "shutout"): [
        "Shut out {score} — a Loss to bury quickly.",
        "A {score} shutout Loss the staff will not forget.",
        "Nothing landed: a {score} Loss without a survivor.",
    ],
    ("Loss", "heavy"): [
        "A heavy {score} Loss the staff will dissect.",
        "A {score} Loss that got away from the squad.",
        "Outclassed in a {score} Loss.",
    ],
    ("Loss", "clear"): [
        "A clear {score} Loss for the squad.",
        "The squad drops it {score} — a Loss with questions.",
        "A {score} Loss this week.",
    ],
    ("Loss", "narrow"): [
        "A {score} Loss by the finest of margins.",
        "So close: a {score} Loss decided late.",
        "The squad falls {score} — a Loss they nearly stole.",
    ],
    ("Draw", "draw"): [
        "A {score} Draw — honors even on the court.",
        "Neither side blinked: a {score} Draw.",
        "A hard {score} stalemate.",
    ],
}


def _margin_tier(result: str, mine: int, theirs: int) -> str:
    if result == "Win":
        if theirs == 0:
            return "shutout"
        if mine >= theirs * 2:
            return "dominant"
        if mine - theirs <= 1:
            return "narrow"
        return "solid"
    if result == "Loss":
        if mine == 0:
            return "shutout"
        if theirs >= mine * 2:
            return "heavy"
        if theirs - mine <= 1:
            return "narrow"
        return "clear"
    return "draw"


def render_headline(
    result: str,
    context: str,
    rng: DeterministicRNG,
    *,
    player_survivors: int | None = None,
    opponent_survivors: int | None = None,
    **kwargs,
) -> str:
    """Render the post-match banner headline.

    When ``player_survivors`` / ``opponent_survivors`` are supplied the headline
    references the actual scoreline and its margin character; otherwise a
    generic result template is returned.
    """
    if player_survivors is not None and opponent_survivors is not None:
        mine = int(player_survivors)
        theirs = int(opponent_survivors)
        normalized = result if result in ("Win", "Loss") else "Draw"
        tier = _margin_tier(normalized, mine, theirs)
        templates = _MARGIN_TEMPLATES.get((normalized, tier))
        if templates:
            return rng.choice(templates).format(score=f"{mine}-{theirs}")

    if result == "Win":
        return rng.choice(_WIN_TEMPLATES)
    if result == "Loss":
        return rng.choice(_LOSS_TEMPLATES)
    return rng.choice(_DRAW_TEMPLATES)
