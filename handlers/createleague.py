from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import League


# ==========================================================
# CREATE LEAGUE — OWNER ONLY
# ==========================================================


async def createleague(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Owner command.

    Usage:
        /createleague <name> <country> <max_clubs>

    Example:
        /createleague Premier_League England 20

    Creates a domestic Division 1 (tier 1).
    Additional divisions are created later with /adddivision.
    """

    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if user.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ This command is Owner only."
        )
        return

    if len(context.args) < 3:
        await message.reply_text(
            (
                "🏆 𝐂𝐑𝐄𝐀𝐓𝐄 𝐋𝐄𝐀𝐆𝐔𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n"
                "/createleague <name> <country> <max_clubs>\n\n"
                "Example:\n"
                "/createleague Premier_League England 20"
            )
        )
        return

    name = context.args[0].strip()
    country = context.args[1].strip()

    try:
        max_clubs = int(context.args[2])
    except ValueError:
        await message.reply_text(
            "❌ max_clubs must be a number."
        )
        return

    if not name or len(name) > 100:
        await message.reply_text(
            "❌ League name must contain 1–100 characters."
        )
        return

    if not country or len(country) > 100:
        await message.reply_text(
            "❌ Country must contain 1–100 characters."
        )
        return

    if max_clubs < 10:
        await message.reply_text(
            "❌ A league needs at least 10 clubs."
        )
        return

    if max_clubs % 2 != 0:
        await message.reply_text(
            "❌ max_clubs must be an even number."
        )
        return

    async with AsyncSessionLocal() as session:
        # League names must be unique.
        result = await session.execute(
            select(League).where(
                League.name == name
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            await message.reply_text(
                "❌ A league with this name already exists."
            )
            return

        league = League(
            name=name,
            country=country,
            tier=1,
            max_clubs=max_clubs,
            status="active",
            parent_league_id=None,
            promotion_target_id=None,
            relegation_target_id=None,
            promotion_slots=0,
            relegation_slots=0,
        )

        session.add(league)
        await session.commit()

        league_id = league.id

    await message.reply_text(
        (
            "✅ 𝐋𝐄𝐀𝐆𝐔𝐄 𝐂𝐑𝐄𝐀𝐓𝐄𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 {name}\n"
            f"🌍 Country : {country}\n"
            f"🥇 Division : 1\n"
            f"🆔 League ID : {league_id}\n"
            f"👥 Capacity : {max_clubs}\n\n"
            "You can now add lower divisions with:\n"
            f"/adddivision {league_id} Division_2 {max_clubs}"
        )
    )


createleague_handler = CommandHandler(
    "createleague",
    createleague,
)