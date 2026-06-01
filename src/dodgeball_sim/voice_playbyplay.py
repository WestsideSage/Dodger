from .rng import DeterministicRNG

def render_play(event_type: str, actor: str, target: str, rng: DeterministicRNG, **kwargs) -> str:
    if event_type == "throw":
        templates = [
            "{actor} winds up and targets {target}.",
            "{actor} lets it fly at {target}.",
            "A fastball from {actor} directed at {target}.",
            "{actor} zeroes in on {target}.",
            "High velocity throw by {actor} toward {target}.",
            "{actor} steps into a throw at {target}.",
            "It's {actor} unloading on {target}.",
            "{actor} spots an opening and throws at {target}.",
            "{actor} sends a screamer towards {target}.",
            "A calculated strike from {actor} at {target}."
        ]
    elif event_type == "catch":
        templates = [
            "{actor} snatches it out of the air from {target}.",
            "Incredible hands by {actor} to catch {target}'s throw.",
            "{actor} secures the catch against {target}.",
            "A momentum-shifting catch by {actor} robbing {target}.",
            "{actor} reads {target} perfectly for the catch.",
            "Clean grab by {actor} on {target}'s attempt.",
            "{actor} pulls in the throw from {target}.",
            "A crucial catch from {actor} against {target}.",
            "{actor} stands tall and catches {target}'s heat.",
            "Beautiful catching form from {actor} against {target}."
        ]
    elif event_type == "dodge":
        templates = [
            "{target} elegantly dodges {actor}'s throw.",
            "{target} slips away from {actor}'s attempt.",
            "A quick sidestep by {target} avoids {actor}.",
            "{target} hits the deck to dodge {actor}.",
            "Great footwork from {target} dodging {actor}.",
            "{target} evades {actor}'s fastball.",
            "{actor} misses as {target} ducks away.",
            "{target} narrowly escapes {actor}'s throw.",
            "A nimble dodge by {target} against {actor}.",
            "{target} reads the release and dodges {actor}."
        ]
    else:
        templates = [
            "{actor} makes a move against {target}.",
            "{actor} engages {target}.",
            "Action between {actor} and {target}."
        ]

    return rng.choice(templates).format(actor=actor, target=target)


def render_targetless_play(
    resolution: str,
    actor: str,
    rng: DeterministicRNG,
    *,
    thrower_out: bool,
) -> str:
    """Faithful play-by-play for a throw event that has no target.

    A target-less throw is never a "miss against ``-``". It is one of three
    real outcomes, distinguished by whether the thrower was eliminated on
    their own throw (``thrower_out``) and the event ``resolution``:

    * ``thrower_out`` + ``clock_violation`` — an official throw-clock / burden
      violation: the burdened thrower failed to relinquish and is ruled out.
    * ``thrower_out`` (otherwise, rec ``miss``) — an illegal headshot: the
      throw rode up over the shoulders and the *thrower* is out as the penalty.
    * not ``thrower_out`` — the throw did not connect (an official ``miss``:
      the selected defender dodged, or the throw was off-target). The official
      translator drops the dodged defender's id, so we narrate a clean miss
      WITHOUT asserting the ball went "into open space" — a target WAS
      selected, so claiming an empty lane would be a new lie.

    Never emits a ``-`` placeholder target. The thrower name is the only
    actor named because the target id is genuinely unavailable on these plays.
    """
    if thrower_out:
        if resolution == "clock_violation":
            templates = [
                "{actor} can't beat the throw clock — a burden violation, and {actor} is out.",
                "The throw clock expires on {actor}; the stall is called and {actor} is out.",
            ]
        else:
            templates = [
                "{actor} sails one in high — an illegal headshot, and {actor} is out.",
                "{actor}'s throw rides up over the shoulders; the headshot foul puts {actor} out.",
            ]
    else:
        templates = [
            "{actor}'s throw misses.",
            "{actor}'s throw doesn't connect.",
            "{actor} comes up empty on the throw.",
        ]
    return rng.choice(templates).format(actor=actor)
