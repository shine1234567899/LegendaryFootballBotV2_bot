from database.database import AsyncSessionLocal
from database.models import Player
from sqlalchemy import select


async def create_yamal():
    async with AsyncSessionLocal() as session:
        # Do not create a duplicate if a Yamal record already exists.
        result = await session.execute(
            select(Player).where(
                Player.name.ilike("Yamal")
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            print(
                f"⚠️ Yamal existe déjà : "
                f"ID={existing.id} | "
                f"Name={existing.name} | "
                f"Position={existing.position} | "
                f"Overall={existing.overall}"
            )
            return

        player = Player(
            name="Yamal",
            country="Spain",
            position="ATT",
            age=18,
            overall=98,
            potential=98,
            value=70_000_000,
            image_file_id=None,
            starter_pool=True,
        )

        session.add(player)
        await session.commit()
        await session.refresh(player)

        print("✅ Yamal créé dans la base.")
        print(f"ID        : {player.id}")
        print(f"Name      : {player.name}")
        print(f"Country   : {player.country}")
        print(f"Position  : {player.position}")
        print(f"Overall   : {player.overall}")
        print(f"Potential : {player.potential}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_yamal())
