import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Player


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Player))
        players = result.scalars().all()

        print(f"Players: {len(players)}")


if __name__ == "__main__":
    asyncio.run(main())