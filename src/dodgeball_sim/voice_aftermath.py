from .rng import DeterministicRNG

def render_headline(result: str, context: str, rng: DeterministicRNG, **kwargs) -> str:
    templates = [
        "A decisive {result} for the squad.",
        "The team secures a hard-fought {result}.",
        "An {context} {result} that sends a message.",
        "They walk away with a {result} this week.",
        "The final whistle seals a {result}.",
        "A {result} that shifts the momentum.",
        "Another week, another {result}.",
        "The scoreboard reflects a {result}.",
        "Fans react to a shocking {result}.",
        "A {result} for the history books.",
        "They earned this {result} on the court.",
        "The post-match mood is defined by this {result}.",
        "A {result} that nobody saw coming.",
        "The expected {result} materializes.",
        "A gritty, unpolished {result}.",
        "The {result} speaks for itself.",
        "They ground out a {result}.",
        "A textbook {result} from start to finish.",
        "An emotional {result} for the locker room.",
        "A {result} that raises questions.",
        "They celebrate a critical {result}.",
        "A {result} built on pure effort.",
        "The {result} leaves the league buzzing.",
        "A {result} driven by late execution.",
        "The {result} confirms their status.",
        "A {result} that changes the narrative.",
        "They pull off a stunning {result}.",
        "A methodical {result} executed perfectly.",
        "A {result} that defines the season.",
        "The ultimate {result} to close the week."
    ]
    return rng.choice(templates).format(result=result, context=context)
