"""V26 The Crowd — media mini-events.

Occasional offseason choice beats whose effects land ONLY in fans, prestige, or
a one-season credibility bonus — NEVER match outcomes, standings, development, or
treasury (a HARD isolation invariant; see the fence test). Deterministic on the
``v26_media`` stream.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Optional, Tuple

_EVENT_KEY = "v26_media_event_json"
_CHOICE_KEY = "v26_media_choice"
_DONE_KEY = "v26_media_done_for"
_CREDIBILITY_BONUS_KEY = "v26_credibility_bonus"
MEDIA_EVENT_CHANCE = 0.55


@dataclass(frozen=True)
class MediaOption:
    key: str
    label: str
    fans: int
    prestige: int
    credibility: int
    receipt: str


@dataclass(frozen=True)
class MediaEvent:
    event_id: str
    prompt: str
    options: Tuple[MediaOption, ...]


_CATALOG: Tuple[MediaEvent, ...] = (
    MediaEvent("local_feature", "A local outlet wants a feature on the club. What's the angle?", (
        MediaOption(key="fans", label="Open the locker room — play to the fans",
                    fans=300, prestige=0, credibility=0, receipt="+300 fans from the feature"),
        MediaOption(key="prestige", label="A serious profile of the program's vision",
                    fans=0, prestige=4, credibility=0, receipt="+4 prestige from the profile"),
        MediaOption(key="recruits", label="Pitch your development pedigree to recruits",
                    fans=0, prestige=0, credibility=6, receipt="+6 credibility with recruits this season"),
    )),
    MediaEvent("star_interview", "Your star is offered a national interview. How do you handle it?", (
        MediaOption(key="embrace", label="Let him shine — the fans love it",
                    fans=400, prestige=1, credibility=0, receipt="+400 fans, +1 prestige"),
        MediaOption(key="team_first", label="Redirect to the team's story",
                    fans=100, prestige=3, credibility=0, receipt="+100 fans, +3 prestige"),
    )),
    MediaEvent("controversy", "A pundit questions your tactics. Your response?", (
        MediaOption(key="fire_back", label="Fire back publicly — the fans rally",
                    fans=350, prestige=-1, credibility=0, receipt="+350 fans, -1 prestige"),
        MediaOption(key="classy", label="Take the high road",
                    fans=0, prestige=3, credibility=2, receipt="+3 prestige, +2 credibility"),
    )),
)


def select_media_event(conn, season_id: str, root_seed: int) -> Optional[MediaEvent]:
    """Deterministically pick a media event for this offseason, or None."""
    from .rng import DeterministicRNG, derive_seed

    rng = DeterministicRNG(derive_seed(root_seed, "v26_media", season_id))
    if rng.unit() > MEDIA_EVENT_CHANCE:
        return None
    return rng.choice(_CATALOG)


def cache_media_event(conn, event: MediaEvent) -> None:
    from .persistence import set_state

    set_state(conn, _EVENT_KEY, json.dumps({
        "event_id": event.event_id,
        "prompt": event.prompt,
        "options": [asdict(o) for o in event.options],
    }))


def load_media_event(conn) -> Optional[dict]:
    from .persistence import get_state

    raw = get_state(conn, _EVENT_KEY)
    return json.loads(raw) if raw else None


def set_media_choice(conn, option_key: str) -> None:
    from .persistence import set_state

    set_state(conn, _CHOICE_KEY, option_key)
    conn.commit()


def media_credibility_bonus(conn) -> int:
    from .persistence import get_state

    try:
        return int(get_state(conn, _CREDIBILITY_BONUS_KEY) or 0)
    except (TypeError, ValueError):
        return 0


def apply_media_choice(conn, season_id: str) -> Optional[dict]:
    """Commit the user's media choice (default: the first option) — effects land
    ONLY in fans / prestige / a one-season credibility bonus. Idempotent."""
    from . import fan_ledger
    from .persistence import get_state, load_club_prestige, save_club_prestige, set_state

    if get_state(conn, _DONE_KEY) == season_id:
        raw = get_state(conn, "v26_media_result_json")
        return json.loads(raw) if raw else None
    event = load_media_event(conn)
    if not event:
        return None
    user = get_state(conn, "player_club_id")
    if not user:
        set_state(conn, _DONE_KEY, season_id)
        return None

    options = event["options"]
    chosen_key = get_state(conn, _CHOICE_KEY)
    option = next((o for o in options if o["key"] == chosen_key), options[0])

    if option["fans"]:
        fan_ledger.add_fans(conn, user, option["fans"], season_id, "media",
                            f"{option['receipt']} (media)")
    if option["prestige"]:
        save_club_prestige(conn, user, load_club_prestige(conn, user) + option["prestige"])
    # The credibility bonus is a single value the next season's recruiting reads.
    set_state(conn, _CREDIBILITY_BONUS_KEY, str(int(option["credibility"])))

    result = {"event_id": event["event_id"], "chosen": option["key"], "receipt": option["receipt"]}
    set_state(conn, "v26_media_result_json", json.dumps(result))
    set_state(conn, _DONE_KEY, season_id)
    conn.commit()
    return result


__all__ = [
    "MediaEvent",
    "MediaOption",
    "MEDIA_EVENT_CHANCE",
    "select_media_event",
    "cache_media_event",
    "load_media_event",
    "set_media_choice",
    "media_credibility_bonus",
    "apply_media_choice",
]
