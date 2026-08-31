"""
MANUWORLD V3 — CORE
Shared, dependency-light utilities for all non-bank systems.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import text

from life_world.database import AsyncSessionLocal, get_life_character, get_life_character_by_username


def money(value: Any) -> str:
    try:
        n = int(value or 0)
    except (TypeError, ValueError):
        n = 0
    return f"{n:,}".replace(",", " ") + " FCFA"


def clamp(value: int | float, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def actor_by_telegram_id(telegram_id: int) -> dict[str, Any] | None:
    row = await get_life_character(int(telegram_id))
    return dict(row) if row else None


async def actor_by_username(username: str) -> dict[str, Any] | None:
    row = await get_life_character_by_username(str(username).lstrip("@").strip())
    return dict(row) if row else None


async def add_balance(
    character_id: int,
    amount: int,
    *,
    description: str = "MANUWORLD",
    transaction_type: str = "system",
) -> int:
    """Atomic balance change. Negative values debit the player."""
    amount = int(amount)
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT balance FROM life_characters
            WHERE id=:id
            FOR UPDATE
        """), {"id": int(character_id)})
        row = result.mappings().first()
        if not row:
            raise ValueError("Personnage introuvable.")
        balance = int(row["balance"] or 0)
        new_balance = balance + amount
        if new_balance < 0:
            raise ValueError("Solde insuffisant.")

        await session.execute(text("""
            UPDATE life_characters
            SET balance=:balance, updated_at=NOW()
            WHERE id=:id
        """), {"balance": new_balance, "id": int(character_id)})

        # life_transactions is the canonical transaction ledger in V3.
        await session.execute(text("""
            INSERT INTO life_transactions
                (character_id, transaction_type, amount, balance_after, description, reference)
            VALUES
                (:character_id, :transaction_type, :amount, :balance_after, :description, :reference)
        """), {
            "character_id": int(character_id),
            "transaction_type": transaction_type,
            "amount": amount,
            "balance_after": new_balance,
            "description": description,
            "reference": f"mwl:{transaction_type}",
        })
        await session.commit()
        return new_balance


async def award_event(
    character_id: int,
    *,
    title: str,
    description: str,
    money_change: int = 0,
    experience_reward: int = 0,
    event_type: str = "system",
) -> None:
    """Write a life event without making the caller know the event schema."""
    async with AsyncSessionLocal() as session:
        if money_change:
            result = await session.execute(text("""
                SELECT balance FROM life_characters
                WHERE id=:id
                FOR UPDATE
            """), {"id": int(character_id)})
            row = result.mappings().first()
            if row:
                balance = int(row["balance"] or 0)
                new_balance = max(0, balance + int(money_change))
                await session.execute(text("""
                    UPDATE life_characters
                    SET balance=:balance, updated_at=NOW()
                    WHERE id=:id
                """), {"balance": new_balance, "id": int(character_id)})

        await session.execute(text("""
            INSERT INTO life_events
                (character_id, event_type, title, description, experience_reward, money_change, event_data)
            VALUES
                (:character_id, :event_type, :title, :description, :experience_reward, :money_change, '{}'::jsonb)
        """), {
            "character_id": int(character_id),
            "event_type": event_type,
            "title": title,
            "description": description,
            "experience_reward": int(experience_reward),
            "money_change": int(money_change),
        })
        await session.commit()


async def ensure_v3_schema() -> None:
    """Idempotent schema for features shared across MANUWORLD."""
    async with AsyncSessionLocal() as session:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS mwl_daily_claims (
                character_id BIGINT PRIMARY KEY REFERENCES life_characters(id) ON DELETE CASCADE,
                last_claim_at TIMESTAMPTZ,
                streak INTEGER NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_achievements (
                id BIGSERIAL PRIMARY KEY,
                code VARCHAR(80) UNIQUE NOT NULL,
                title VARCHAR(160) NOT NULL,
                description TEXT NOT NULL,
                reward BIGINT NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_character_achievements (
                character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                achievement_id BIGINT NOT NULL REFERENCES mwl_achievements(id) ON DELETE CASCADE,
                unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY(character_id, achievement_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_audit_log (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT REFERENCES life_characters(id) ON DELETE SET NULL,
                action VARCHAR(80) NOT NULL,
                details JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_notifications (
                id BIGSERIAL PRIMARY KEY,
                character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                title VARCHAR(160) NOT NULL,
                body TEXT NOT NULL,
                read_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_political_parties (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                slogan VARCHAR(180) NOT NULL DEFAULT '',
                leader_character_id BIGINT REFERENCES life_characters(id) ON DELETE SET NULL,
                treasury BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_elections (
                id BIGSERIAL PRIMARY KEY,
                title VARCHAR(160) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'open',
                starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ends_at TIMESTAMPTZ,
                winner_character_id BIGINT REFERENCES life_characters(id) ON DELETE SET NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_candidates (
                election_id BIGINT NOT NULL REFERENCES mwl_elections(id) ON DELETE CASCADE,
                character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                party_id BIGINT REFERENCES mwl_political_parties(id) ON DELETE SET NULL,
                program TEXT NOT NULL DEFAULT '',
                votes INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(election_id, character_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_votes (
                election_id BIGINT NOT NULL REFERENCES mwl_elections(id) ON DELETE CASCADE,
                voter_character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                candidate_character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                voted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY(election_id, voter_character_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mwl_meetings (
                id BIGSERIAL PRIMARY KEY,
                organizer_character_id BIGINT NOT NULL REFERENCES life_characters(id) ON DELETE CASCADE,
                title VARCHAR(160) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                location VARCHAR(120) NOT NULL DEFAULT 'Hôtel de ville',
                starts_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
        ]
        for statement in statements:
            await session.execute(text(statement))

        achievements = [
            ("first_steps", "🌱 Premiers pas", "Obtenir sa première récompense quotidienne.", 500),
            ("entrepreneur", "🏢 Entrepreneur", "Créer une entreprise.", 2500),
            ("politician", "🏛️ Vie publique", "Se présenter à une élection.", 1500),
            ("healthy", "❤️ En forme", "Atteindre 90 de santé.", 1000),
            ("worker", "💼 Travailleur", "Effectuer une journée de travail.", 750),
        ]
        for code, title, description, reward in achievements:
            await session.execute(text("""
                INSERT INTO mwl_achievements(code,title,description,reward)
                VALUES(:code,:title,:description,:reward)
                ON CONFLICT(code) DO UPDATE SET
                    title=EXCLUDED.title,
                    description=EXCLUDED.description,
                    reward=EXCLUDED.reward
            """), {
                "code": code, "title": title,
                "description": description, "reward": reward,
            })
        await session.commit()
