import random

from sqlalchemy import select

from database.models import ClubPlayer, Player


# Nombre de joueurs par poste
POSITION_LIMITS = {
    "GK": 2,
    "DEF": 6,
    "MID": 6,
    "ATT": 4,
}


async def generate_starter_squad(session):
    selected_players = []

    for position, amount in POSITION_LIMITS.items():
        result = await session.execute(
            select(Player)
            .where(
                Player.position == position,
                ~Player.id.in_(
                    select(ClubPlayer.player_id)
                    .where(ClubPlayer.is_current.is_(True))
                ),
            )
        )

        available_players = list(result.scalars().all())

        if len(available_players) < amount:
            raise RuntimeError(
                f"Not enough available {position} players. "
                f"Required: {amount}, available: {len(available_players)}"
            )

        selected_players.extend(
            random.sample(available_players, amount)
        )

    random.shuffle(selected_players)

    return selected_players