from sqlalchemy import inspect

from database.database import engine
from database.models import Base


async def main():
    async with engine.begin() as connection:
        tables = await connection.run_sync(
            lambda conn: inspect(conn).get_table_names()
        )

    print("Tables actuellement en PostgreSQL :")
    for table in tables:
        print(f" - {table}")

    print("\nTables déclarées dans V2 :")
    for table in Base.metadata.sorted_tables:
        print(f" - {table.name}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())