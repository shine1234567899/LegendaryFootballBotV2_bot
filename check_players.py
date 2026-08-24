import asyncio
from urllib.parse import urlsplit

from sqlalchemy import select, func

from config import DATABASE_URL
from database.database import AsyncSessionLocal, ASYNC_DATABASE_URL
from database.models import Player


async def main():
    print("DATABASE HOST :", urlsplit(DATABASE_URL).hostname)
    print("ASYNC HOST    :", urlsplit(ASYNC_DATABASE_URL).hostname)
    print()

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

        for p in result.scalars().all():
            print(
                f"{p.id} | {p.name} | "
                f"OVR={p.overall} | "
                f"starter_pool={p.starter_pool}"
            )


if __name__ == "__main__":
    asyncio.run(main())