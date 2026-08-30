"""
MANUWORLD — WORK

Commande /work :
- disponible toutes les 5 heures ;
- rémunération déterminée par le diplôme/niveau scolaire ;
- salaire en FCFA ;
- aucun travail avant le CEP.

Barème :
CEP          : 2 000 FCFA
BEPC         : 5 000 à 10 000 FCFA
Probatoire   : 10 000 à 21 000 FCFA
BACC         : 25 000 à 40 000 FCFA
Université   : 50 000 à 75 000 FCFA
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy import text
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from life_world.database import AsyncSessionLocal, get_life_character


WORK_COOLDOWN_SECONDS = 5 * 60 * 60

SALARY_RANGES = {
    "cep": (2000, 2000),
    "bepc": (5000, 10000),
    "probatoire": (10000, 21000),
    "bacc": (25000, 40000),
    "university": (50000, 75000),
}


def normalize_school_level(character: dict) -> str:
    level = str(
        character.get("school_level")
        or ""
    ).strip().lower()

    if level in SALARY_RANGES:
        return level

    diploma = str(
        character.get("current_diploma")
        or character.get("diploma_level")
        or ""
    ).strip().lower()

    if "univers" in level:
        return "university"
    if "bacc" in diploma or "baccalaur" in diploma:
        return "bacc"
    if "probatoire" in diploma:
        return "probatoire"
    if "bepc" in diploma:
        return "bepc"
    if "cep" in diploma:
        return "cep"

    education = str(
        character.get("education_level")
        or ""
    ).strip().lower()

    if "univers" in education or "supérieur" in education:
        return "university"
    if "terminal" in education:
        return "bacc"
    if "lycée" in education or "lycee" in education:
        return "probatoire"
    if "collège" in education or "college" in education:
        return "bepc"

    return ""


def format_money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ") + " FCFA"


async def ensure_work_column() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'life_characters'
                  AND column_name = 'last_work_at'
                """
            )
        )

        if result.first() is None:
            await session.execute(
                text(
                    """
                    ALTER TABLE life_characters
                    ADD COLUMN last_work_at TIMESTAMPTZ
                    """
                )
            )
            await session.commit()


async def work_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    character = await get_life_character(user.id)

    if character is None:
        await message.reply_text(
            "❌ Crée d'abord ton personnage MANUWORLD avec /life."
        )
        return

    await ensure_work_column()

    level = normalize_school_level(dict(character))
    if not level:
        await message.reply_text(
            "❌ Tu dois avoir obtenu au minimum le **CEP** avant de travailler.",
            parse_mode="Markdown",
        )
        return

    minimum, maximum = SALARY_RANGES[level]

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT last_work_at
                FROM life_characters
                WHERE id = :id
                FOR UPDATE
                """
            ),
            {"id": int(character["id"])},
        )

        row = result.mappings().first()
        last_work_at = row["last_work_at"] if row else None

        if last_work_at is not None:
            if last_work_at.tzinfo is None:
                last_work_at = last_work_at.replace(
                    tzinfo=timezone.utc
                )

            elapsed = (
                now - last_work_at
            ).total_seconds()

            if elapsed < WORK_COOLDOWN_SECONDS:
                remaining = int(
                    WORK_COOLDOWN_SECONDS - elapsed
                )

                hours = remaining // 3600
                minutes = (remaining % 3600) // 60

                await session.rollback()

                await message.reply_text(
                    "⏳ **TRAVAIL INDISPONIBLE**\n\n"
                    f"Tu as déjà travaillé récemment.\n"
                    f"⏱️ Prochain travail dans : "
                    f"**{hours}h {minutes:02d}min**"
                )
                return

        salary = random.randint(
            minimum,
            maximum,
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET balance = balance + :salary,
                    last_work_at = :last_work_at,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "salary": salary,
                "last_work_at": now,
                "id": int(character["id"]),
            },
        )

        balance_result = await session.execute(
            text(
                """
                SELECT balance
                FROM life_characters
                WHERE id = :id
                """
            ),
            {"id": int(character["id"])},
        )

        new_balance = balance_result.scalar_one()

        await session.commit()

    level_names = {
        "cep": "CEP",
        "bepc": "BEPC",
        "probatoire": "Probatoire",
        "bacc": "Baccalauréat",
        "university": "Université",
    }

    await message.reply_text(
        "💼 **TRAVAIL TERMINÉ**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎓 Niveau : **{level_names[level]}**\n"
        f"💰 Salaire : **+{format_money(salary)}**\n"
        f"💵 Nouveau solde : **{format_money(new_balance)}**\n\n"
        "⏳ Prochaine session disponible dans **5 heures**."
    )


work_handler = CommandHandler(
    "work",
    work_command,
)


__all__ = [
    "WORK_COOLDOWN_SECONDS",
    "SALARY_RANGES",
    "work_command",
    "work_handler",
]
