import asyncio
from sqlalchemy import select, func

from database.database import AsyncSessionLocal
from database.models import Player


async def main():
    async with AsyncSessionLocal() as session:

        total = await session.scalar(
            select(func.count(Player.id))
        )

        print(f"TOTAL PLAYERS: {total}")

        result = await session.execute(
            select(Player)
            .order_by(Player.id.desc())
            .limit(20)
        )

        players = result.scalars().all()

        for p in players:
            print(
                f"{p.id} | "
                f"{p.name} | "
                f"OVR={p.overall} | "
                f"starter_pool={p.starter_pool}"
            )


if __name__ == "__main__":
    asyncio.run(main())