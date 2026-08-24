import asyncio

from sqlalchemy import text

from database.database import AsyncSessionLocal


async def test_connection():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT current_database(), current_user"))
        database_name, username = result.one()

        print(f"Database: {database_name}")
        print(f"User: {username}")


if __name__ == "__main__":
    asyncio.run(test_connection())