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
