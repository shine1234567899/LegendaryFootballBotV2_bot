import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import GameSetting, League


GAME_SETTINGS = {
    "starting_coins": "100000000",
    "starting_gems": "500",
    "quiz_reward": "80000",
    "matches_per_day": "5",
    "default_league_size": "20",
    "default_promotion_slots": "2",
    "default_relegation_slots": "2",
    "max_squad_size": "36",
}


CHAMPIONSHIPS = {
    "England": [
        ("Premier League", 1),
        ("Championship", 2),
    ],
    "Spain": [
        ("La Liga", 1),
        ("Segunda División", 2),
    ],
    "Italy": [
        ("Serie A", 1),
        ("Serie B", 2),
    ],
    "France": [
        ("Ligue 1", 1),
        ("Ligue 2", 2),
    ],
    "Germany": [
        ("Bundesliga", 1),
        ("2. Bundesliga", 2),
    ],
}


async def seed_game_settings(session):
    for key, value in GAME_SETTINGS.items():
        result = await session.execute(
            select(GameSetting).where(GameSetting.key == key)
        )

        if result.scalar_one_or_none() is None:
            session.add(
                GameSetting(
                    key=key,
                    value=value,
                )
            )


async def seed_leagues(session):
    for country, divisions in CHAMPIONSHIPS.items():
        created = []

        for name, tier in divisions:
            result = await session.execute(
                select(League).where(League.name == name)
            )

            league = result.scalar_one_or_none()

            if league is None:
                league = League(
                    name=name,
                    country=country,
                    tier=tier,
                    max_clubs=20,
                    status="inactive",
                    promotion_slots=2,
                    relegation_slots=2,
                )

                session.add(league)
                await session.flush()

            created.append(league)

        # Liaison entre les divisions
        for index, league in enumerate(created):
            if index > 0:
                league.parent_league_id = created[index - 1].id

            if index < len(created) - 1:
                league.relegation_target_id = created[index + 1].id

            if index > 0:
                league.promotion_target_id = created[index - 1].id


async def main():
    async with AsyncSessionLocal() as session:
        try:
            await seed_game_settings(session)
            await seed_leagues(session)

            await session.commit()

            print("✅ Initial seed completed successfully.")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())