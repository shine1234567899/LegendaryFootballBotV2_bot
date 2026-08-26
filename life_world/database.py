from sqlalchemy import text
from database.database import AsyncSessionLocal

async def ensure_life_tables():
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
        CREATE TABLE IF NOT EXISTS life_characters (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT NOT NULL UNIQUE,
            first_name VARCHAR(80) NOT NULL,
            nationality VARCHAR(80) NOT NULL,
            gender VARCHAR(20) NOT NULL,
            residence_country VARCHAR(80) NOT NULL,
            birth_date DATE NOT NULL,
            life_id VARCHAR(32) NOT NULL UNIQUE,
            balance BIGINT NOT NULL DEFAULT 0,
            balance_bank BIGINT NOT NULL DEFAULT 0,
            family_name VARCHAR(80),
            family_id BIGINT,
            education_level VARCHAR(80) NOT NULL DEFAULT 'École primaire',
            diploma_level VARCHAR(80),
            identity_card BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """))
        await session.commit()

async def get_life_character(telegram_id):
    async with AsyncSessionLocal() as session:
        r=await session.execute(text(
            "SELECT * FROM life_characters WHERE telegram_id=:id LIMIT 1"
        ),{"id":telegram_id})
        return r.mappings().first()

async def create_life_character(**data):
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
        INSERT INTO life_characters
        (telegram_id,first_name,nationality,gender,residence_country,birth_date,life_id)
        VALUES (:telegram_id,:first_name,:nationality,:gender,:residence_country,:birth_date,:life_id)
        """),data)
        await session.commit()
