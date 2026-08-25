from __future__ import annotations

import random
from sqlalchemy import select

from database.models import ClubPlayer, Player


POSITION_LIMITS = {
    "GK": 2,
    "DEF": 6,
    "MID": 6,
    "ATT": 4,
}

# Separate fictional starter-player pool.
# These players are created specifically for a club and are NOT taken
# from the CSV/imported Player pool.
FIRST_NAMES = [
    "Jean", "Samuel", "Kevin", "David", "Lucas", "Daniel", "Michael",
    "Alex", "Thomas", "Paul", "Chris", "Nathan", "Ryan", "Jordan",
    "Arthur", "Hugo", "Leo", "Noah", "Ethan", "Nathaniel",
    "Marc", "Eric", "William", "Gabriel", "Emmanuel", "Jonathan",
]

LAST_NAMES = [
    "Mbarga", "Nkoulou", "Moukouri", "Mvondo", "Etame", "Essomba",
    "Dupont", "Martin", "Bernard", "Robert", "Petit", "Durand",
    "Moreau", "Laurent", "Simon", "Michel", "Leroy", "Roux",
    "Fournier", "Girard", "Benoit", "Ngono", "Mballa", "Abanda",
    "Nana", "Tchana", "Ekotto", "Manga", "Fofana", "Diallo",
]


def _new_name(used_names: set[str]) -> str:
    # Keep trying random combinations first.
    for _ in range(200):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        if name.casefold() not in used_names:
            used_names.add(name.casefold())
            return name

    # Guaranteed fallback if the small name library gets saturated.
    while True:
        name = (
            f"{random.choice(FIRST_NAMES)} "
            f"{random.choice(LAST_NAMES)} "
            f"{random.randint(1000, 999999)}"
        )
        if name.casefold() not in used_names:
            used_names.add(name.casefold())
            return name


async def generate_starter_squad(session):
    """
    Generate a fresh fictional 18-player squad for a newly created club.

    IMPORTANT:
    - CSV/imported players are NEVER selected.
    - Existing players are NEVER assigned to the new club.
    - New Player rows are created for this club.
    - Every club gets its own 18 players.
    - No global starter-player pool is consumed.
    """

    # Get names already used in the database so generated names do not
    # accidentally duplicate an existing Player name.
    result = await session.execute(select(Player.name))
    used_names = {
        (name or "").strip().casefold()
        for name in result.scalars().all()
        if name
    }

    selected_players = []

    for position, amount in POSITION_LIMITS.items():
        for _ in range(amount):
            # Keep starter ratings modest so these are clearly fictional
            # starter players, separate from the FC26/CSV player pool.
            overall = random.randint(55, 68)
            potential = random.randint(max(overall, 60), 78)

            player = Player(
                name=_new_name(used_names),
                country="Unknown",
                position=position,
                age=random.randint(18, 30),
                overall=overall,
                potential=potential,
                value=max(100_000, overall * random.randint(15_000, 25_000)),
                image_file_id=None,
                starter_pool=True,
            )

            session.add(player)
            selected_players.append(player)

    # Flush so every generated Player has an ID before createclub.py
    # creates its ClubPlayer rows.
    await session.flush()

    random.shuffle(selected_players)
    return selected_players
