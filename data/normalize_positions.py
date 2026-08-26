from sqlalchemy import update
from database.database import AsyncSessionLocal
from database.models import Player

async def normalize_strikers_to_attackers():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(Player)
            .where(Player.position == "ST")
            .values(position="ATT")
        )
        await session.commit()
        return result.rowcount or 0
