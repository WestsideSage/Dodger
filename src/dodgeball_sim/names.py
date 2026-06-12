"""Shared name pools for every generated person in the league.

V22 Phase 1 (owner): "We need a much wider breadth of recruit names" — the
old pools (32 first names, 86 last names, with a separate 24×24 staff pool)
made every career a parade of Rins, Remys, Mikas and Ferns. One module now
feeds prospects, rookies and staff from wide, culturally broad pools.

Determinism contract: :func:`unique_full_name` consumes EXACTLY two RNG
draws per name, no matter how many collisions it has to skip. (The old
implementation shuffled the full first×last combo list per name — fixed
consumption too, but O(pool²) work per draw, which the wider pools can't
afford.) Collision resolution walks the combo space with a draw-derived
coprime stride, so it deterministically visits every combination at most
once without touching the RNG again.
"""
from __future__ import annotations

from math import gcd

from .rng import DeterministicRNG

# ~200 first names. The original 32 lead the tuple so long-running saves keep
# meeting familiar faces alongside the new breadth.
FIRST_NAMES: tuple[str, ...] = (
    # The original 32.
    "Rin", "Avery", "Kai", "River", "Mara", "Ezra", "Sloane", "Jules",
    "Remy", "Quinn", "Niko", "Sable", "Ash", "Lyra", "Zeph", "Cass",
    "Talia", "Noor", "Imani", "Briar", "Callum", "Elio", "Mika", "Nia",
    "Rowan", "Selah", "Tobin", "Vale", "Wren", "Zara", "Kellan", "Luca",
    # Anglophone / European.
    "Owen", "Declan", "Maeve", "Niamh", "Cillian", "Aoife", "Rhys", "Bronwyn",
    "Gareth", "Tegan", "Hamish", "Isla", "Ewan", "Fiona", "Alistair", "Greta",
    "Hugo", "Margot", "Etienne", "Camille", "Luc", "Amelie", "Mathis", "Elodie",
    "Stellan", "Freja", "Soren", "Ingrid", "Magnus", "Astrid", "Leif", "Sigrid",
    "Anders", "Maren", "Henrik", "Liv", "Otto", "Clara", "Emil", "Lotte",
    "Theo", "Imogen", "Felix", "Beatrix", "Jasper", "Cora", "Silas", "June",
    # Slavic / Eastern European.
    "Milan", "Zofia", "Tomas", "Ivana", "Bogdan", "Lena", "Andrei", "Katya",
    "Dmitri", "Oksana", "Pavel", "Mirela", "Stefan", "Anya", "Radek", "Vera",
    # Mediterranean / Latin American.
    "Mateo", "Lucia", "Thiago", "Valentina", "Rafael", "Camila", "Diego", "Ines",
    "Joaquin", "Marisol", "Esteban", "Pilar", "Andres", "Rocio", "Emilio", "Catalina",
    "Dante", "Bianca", "Marco", "Chiara", "Nico", "Alessia", "Paolo", "Serena",
    # East / Southeast Asian.
    "Haruto", "Yuna", "Ren", "Sakura", "Daichi", "Hana", "Kenji", "Aiko",
    "Jin", "Soo-Min", "Tae", "Ji-Woo", "Hyun", "Eun", "Minho", "Seo-Yeon",
    "Wei", "Mei", "Jun", "Xiu", "Bao", "Lan", "Cheng", "Ying",
    "Anh", "Linh", "Minh", "Thao", "Arun", "Dara", "Niran", "Mali",
    # South Asian.
    "Arjun", "Priya", "Rohan", "Anika", "Vikram", "Divya", "Kiran", "Meera",
    "Sanjay", "Lakshmi", "Dev", "Asha", "Ravi", "Sita", "Nikhil", "Tara",
    # Middle Eastern / North African.
    "Omar", "Layla", "Tariq", "Yasmin", "Karim", "Amira", "Sami", "Farah",
    "Idris", "Zainab", "Rashid", "Leila", "Hakim", "Nadia", "Faisal", "Soraya",
    # Sub-Saharan African.
    "Kwame", "Abena", "Kofi", "Ama", "Sekou", "Fatou", "Chinedu", "Ngozi",
    "Tunde", "Zuri", "Jabari", "Amara", "Baraka", "Nala", "Themba", "Ayana",
    # The Americas / Oceania / everywhere else.
    "Koa", "Leilani", "Tane", "Moana", "Aroha", "Manaia", "Keanu", "Alamea",
    "Dakota", "Cheyenne", "Phoenix", "Sierra", "Austin", "Savannah", "Memphis", "Aspen",
)

# ~300 last names. The original 86 lead the tuple.
LAST_NAMES: tuple[str, ...] = (
    # The original 86.
    "Voss", "Helix", "Turner", "Lark", "Orion", "Vega", "Keene", "Hart",
    "Rowe", "Slate", "Frost", "Drake", "Munn", "Cole", "Beck", "Thorn",
    "Bishop", "Vale", "Cross", "Mercer", "Rhodes", "Santos", "Ibarra", "Kline",
    "Novak", "Parr", "Sol", "Tanner", "West", "Yardley", "Zane", "Okafor",
    "Chavez", "Duval", "Nakamura", "Jensen", "Olsen", "Griffin", "Sterling", "Hawthorne",
    "Crosby", "Sinclair", "Garrison", "Fitzgerald", "Kerrigan", "O'Neill", "Rousseau", "Mendoza",
    "Petrov", "Saito", "Takahashi", "Chen", "Kim", "Park", "Patel", "Sharma",
    "Singh", "Das", "Ali", "Hassan", "Mensah", "Diallo", "Toure", "Kone",
    "Ivanov", "Smirnov", "Hansen", "Nielsen", "Johansen", "Moreau", "Dubois", "Leroy",
    "Garcia", "Martinez", "Rodriguez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez",
    "Torres", "Flores", "Sato", "Aura", "Zenith", "Apex", "Prism", "Bloom",
    "Knox", "Mace", "Ash", "Moss", "Fern", "Shore",
    # Anglophone.
    "Whitaker", "Holloway", "Pemberton", "Ashford", "Caldwell", "Donovan", "Ellsworth", "Fairbanks",
    "Galloway", "Harrington", "Kingsley", "Lockwood", "Marlowe", "Nightingale", "Ormond", "Prescott",
    "Quimby", "Ravenscroft", "Standish", "Thackeray", "Underhill", "Vickers", "Wadsworth", "Yeats",
    "Abernathy", "Blackwood", "Carmichael", "Drummond", "Eastwood", "Fenwick", "Goodwin", "Hutchins",
    # Celtic.
    "O'Brien", "MacAllister", "Gallagher", "Brennan", "Donnelly", "Flanagan", "Keegan", "Murphy",
    "Sullivan", "Doyle", "Llewellyn", "Pritchard", "Vaughan", "Griffiths", "MacLeod", "Buchanan",
    # French / Iberian / Italian.
    "Beaumont", "Chevalier", "Delacroix", "Fontaine", "Girard", "Lacroix", "Marchand", "Renard",
    "Severin", "Toussaint", "Aguilar", "Cabrera", "Delgado", "Escobar", "Fuentes", "Herrera",
    "Jimenez", "Maldonado", "Navarro", "Ortega", "Quintero", "Rojas", "Salazar", "Vargas",
    "Villanueva", "Zamora", "Bellini", "Caruso", "DeLuca", "Esposito", "Ferrara", "Gallo",
    "Lombardi", "Marino", "Pellegrini", "Ricci", "Romano", "Vitale",
    # Germanic / Nordic / Dutch.
    "Bauer", "Engel", "Fischer", "Hoffmann", "Keller", "Lehmann", "Richter", "Schneider",
    "Wagner", "Zimmermann", "Lindqvist", "Bergstrom", "Dahl", "Eriksson", "Holm", "Lund",
    "Nyberg", "Strand", "Soderberg", "Vinter", "Van Dijk", "De Vries", "Janssen", "Vermeer",
    # Slavic / Eastern European / Greek.
    "Kowalski", "Nowak", "Wisniewski", "Zielinski", "Horvath", "Kovacs", "Szabo", "Varga",
    "Dvorak", "Novotny", "Svoboda", "Popov", "Sokolov", "Volkov", "Kuznetsov", "Morozov",
    "Petrenko", "Shevchenko", "Bondar", "Papadopoulos", "Nikolaidis", "Economou", "Stavros", "Drakos",
    # East / Southeast Asian.
    "Tanaka", "Suzuki", "Watanabe", "Yamamoto", "Kobayashi", "Hayashi", "Shimizu", "Mori",
    "Fujita", "Ogawa", "Lee", "Choi", "Jung", "Kang", "Cho", "Yoon",
    "Lim", "Han", "Wang", "Li", "Zhang", "Liu", "Yang", "Huang",
    "Zhao", "Wu", "Zhou", "Xu", "Nguyen", "Tran", "Pham", "Hoang",
    "Vu", "Dang", "Santoso", "Wijaya", "Reyes", "Bautista", "Ocampo", "Villanara",
    # South Asian.
    "Gupta", "Mehta", "Iyer", "Nair", "Reddy", "Rao", "Chowdhury", "Banerjee",
    "Mukherjee", "Kapoor", "Malhotra", "Joshi", "Desai", "Trivedi", "Pillai", "Menon",
    # Middle Eastern / North African.
    "Al-Farsi", "Haddad", "Khalil", "Mansour", "Nasser", "Qureshi", "Rahimi", "Saleh",
    "Tahir", "Yousef", "Zaman", "Karimi", "Farahani", "Moradi", "Azizi", "Ebrahimi",
    # Sub-Saharan African.
    "Abara", "Adeyemi", "Afolabi", "Chukwu", "Eze", "Obi", "Okonkwo", "Onyeka",
    "Asante", "Boateng", "Owusu", "Agyeman", "Keita", "Sow", "Ndiaye", "Cisse",
    "Camara", "Traore", "Banda", "Chirwa", "Dube", "Khumalo", "Moyo", "Ncube",
    "Abebe", "Bekele", "Tesfaye", "Gebre", "Mwangi", "Otieno", "Wanjiku", "Kimani",
    # The Americas / Oceania.
    "Whitehorse", "Redcloud", "Swiftwind", "Tallbear", "Kahale", "Mahelona", "Kealoha", "Akana",
    "Ngata", "Parata", "Te Rangi", "Waititi", "Fonoti", "Tuilagi", "Faleolo", "Matagi",
)


def unique_full_name(
    *,
    rng: DeterministicRNG,
    used_names: set[str],
    used_last_names: set[str] | None = None,
    fallback_tag: str = "",
) -> str:
    """Draw a unique "First Last" name, consuming exactly two RNG draws.

    The two draws pick a starting combo index and a stride; the stride is
    nudged (without RNG) to the next value coprime with the combo-space size,
    so the walk visits every first×last combination exactly once. Collisions
    against ``used_names`` (and ``used_last_names`` when provided) skip ahead
    deterministically. Only a fully exhausted combo space falls back to a
    tagged name.
    """
    n_first = len(FIRST_NAMES)
    n_last = len(LAST_NAMES)
    total = n_first * n_last

    start = min(int(rng.unit() * total), total - 1)
    stride = min(int(rng.unit() * (total - 1)), total - 2) + 1
    while gcd(stride, total) != 1:
        stride += 1

    relaxed: str | None = None
    for step in range(total):
        idx = (start + step * stride) % total
        first = FIRST_NAMES[idx // n_last]
        last = LAST_NAMES[idx % n_last]
        name = f"{first} {last}"
        if name in used_names:
            continue
        if used_last_names is not None and last in used_last_names:
            # Remember the first name that was unique-but-for-the-surname rule,
            # mirroring the old picker's relaxed second pass.
            if relaxed is None:
                relaxed = name
            continue
        used_names.add(name)
        if used_last_names is not None:
            used_last_names.add(last)
        return name

    if relaxed is not None:
        used_names.add(relaxed)
        if used_last_names is not None:
            used_last_names.add(relaxed.split()[-1])
        return relaxed

    base = f"{FIRST_NAMES[start // n_last]} {LAST_NAMES[start % n_last]} {fallback_tag}".strip()
    used_names.add(base)
    return base


__all__ = ["FIRST_NAMES", "LAST_NAMES", "unique_full_name"]
