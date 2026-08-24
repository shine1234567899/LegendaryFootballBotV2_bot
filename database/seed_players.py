import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Player


PLAYERS = [
    # name, country, position, age, overall, potential, value
    ("Cristiano Ronaldo", "Portugal", "ST", 41, 90, 90, 15000000),
    ("Lionel Messi", "Argentina", "RW", 39, 89, 89, 12000000),
    ("Kylian Mbappé", "France", "ST", 27, 91, 95, 180000000),
    ("Erling Haaland", "Norway", "ST", 26, 91, 94, 180000000),
    ("Vinícius Júnior", "Brazil", "LW", 26, 90, 94, 170000000),
    ("Jude Bellingham", "England", "CM", 23, 90, 94, 160000000),
    ("Lamine Yamal", "Spain", "RW", 19, 89, 96, 160000000),
    ("Rodri", "Spain", "CDM", 30, 90, 90, 110000000),
    ("Harry Kane", "England", "ST", 33, 89, 89, 85000000),
    ("Mohamed Salah", "Egypt", "RW", 34, 89, 89, 70000000),
    ("Kevin De Bruyne", "Belgium", "CM", 35, 88, 88, 50000000),
    ("Robert Lewandowski", "Poland", "ST", 38, 88, 88, 40000000),
    ("Virgil van Dijk", "Netherlands", "CB", 35, 88, 88, 45000000),
    ("Thibaut Courtois", "Belgium", "GK", 34, 89, 89, 50000000),
    ("Alisson Becker", "Brazil", "GK", 33, 89, 90, 55000000),
    ("Achraf Hakimi", "Morocco", "RB", 27, 87, 90, 80000000),
    ("Bukayo Saka", "England", "RW", 25, 88, 92, 120000000),
    ("Pedri", "Spain", "CM", 23, 87, 92, 100000000),
    ("Federico Valverde", "Uruguay", "CM", 28, 88, 91, 110000000),
    ("Victor Osimhen", "Nigeria", "ST", 27, 87, 90, 90000000),
]


async def main():
    async with AsyncSessionLocal() as session:
        added = 0
        skipped = 0

        for data in PLAYERS:
            name = data[0]

            result = await session.execute(
                select(Player).where(Player.name == name)
            )

            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            player = Player(
                name=data[0],
                country=data[1],
                position=data[2],
                age=data[3],
                overall=data[4],
                potential=data[5],
                value=data[6],
            )

            session.add(player)
            added += 1

        await session.commit()

        print(f"✅ Players added: {added}")
        print(f"ℹ️ Players already existing: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())