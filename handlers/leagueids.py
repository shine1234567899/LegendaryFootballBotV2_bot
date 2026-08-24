from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import League


async def leagueids(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(League).order_by(League.id.asc())
        )

        leagues = result.scalars().all()

    if not leagues:
        await message.reply_text(
            "❌ No leagues found."
        )
        return

    lines = [
        "🏆 𝐋𝐄𝐀𝐆𝐔𝐄 𝐈𝐃𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for league in leagues:
        lines.append(
            f"🏟️ {league.name}\n"
            f"🆔 League ID : `{league.id}`\n"
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


leagueids_handler = CommandHandler(
    "leagueids",
    leagueids,
)