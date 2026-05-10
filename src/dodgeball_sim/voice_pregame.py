from .rng import DeterministicRNG

def render_matchup_framing(home: str, away: str, rng: DeterministicRNG, **kwargs) -> str:
    templates = [
        "A classic showdown awaits as {home} hosts {away}.",
        "The stage is set in {home}'s arena to welcome {away}.",
        "{home} looks to defend their home court against a hungry {away} squad.",
        "{away} rolls into town looking to upset {home}.",
        "Can {away} steal a win on the road against {home}?",
        "Tension builds as {home} prepares to face {away}.",
        "It all comes down to execution when {home} meets {away}.",
        "{home} and {away} clash in a highly anticipated matchup.",
        "{away} faces a tough test in {home}'s territory.",
        "The crowd is buzzing for {home} vs {away}.",
        "Expect fireworks when {home} takes on {away}.",
        "{home} holds court advantage against {away}.",
        "{away} will need a flawless game plan against {home}.",
        "The rivalry writes another chapter: {home} vs {away}.",
        "All eyes are on {home} as they battle {away}.",
        "{away}'s offense meets {home}'s defense tonight.",
        "A true test of resilience for {away} playing at {home}.",
        "{home} is ready to make a statement against {away}.",
        "It's a battle of attrition between {home} and {away}.",
        "Can {home} execute their game plan against {away}?",
        "{away} steps into the hostile environment of {home}.",
        "Match week brings {away} to {home}'s doorstep.",
        "{home} aims to control the pace against {away}.",
        "Will {away}'s aggressive style overwhelm {home}?",
        "A pivotal conference clash: {home} vs {away}.",
        "{home} must protect the ball against {away}.",
        "Every possession matters when {home} plays {away}.",
        "{away} is looking to shock the crowd at {home}.",
        "{home}'s faithful are ready for the showdown with {away}.",
        "The whistle approaches for {home} and {away}.",
        "Strategic masterclass expected between {home} and {away}."
    ]
    return rng.choice(templates).format(home=home, away=away)
