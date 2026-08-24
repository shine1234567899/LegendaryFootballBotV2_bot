from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import League


# ==========================================================
# ADD DIVISION — OWNER ONLY
# ==========================================================

async def adddivision(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Owner command:
        /adddivision <league_id> <division_name> [max_clubs]

    Example:
        /adddivision 1 League 2
        /adddivision 1 Ligue 2 20

    Creates a child division under an existing first division.
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

    if len(context.args) < 2:
        await message.reply_text(
            (
                "⚙️ 𝐀𝐃𝐃 𝐃𝐈𝐕𝐈𝐒𝐈𝐎𝐍\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n"
                "/adddivision <league_id> <name> [max_clubs]\n\n"
                "Example:\n"
                "/adddivision 1 League 2 20"
            )
        )
        return

    try:
        parent_id = int(context.args[0])
    except ValueError:
        await message.reply_text(
            "❌ Invalid league ID."
        )
        return

    name = context.args[1].strip()

    if len(name) < 1 or len(name) > 100:
        await message.reply_text(
            "❌ Division name must contain 1–100 characters."
        )
        return

    max_clubs = 20

    if len(context.args) >= 3:
        try:
            max_clubs = int(context.args[2])
        except ValueError:
            await message.reply_text(
                "❌ max_clubs must be a number."
            )
            return

        if max_clubs < 2:
            await message.reply_text(
                "❌ A division needs at least 2 clubs."
            )
            return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(League).where(League.id == parent_id)
        )
        parent = result.scalar_one_or_none()

        if parent is None:
            await message.reply_text(
                "❌ Parent league not found."
            )
            return

        # A division is always one tier below its parent.
        division_tier = parent.tier + 1

        # Prevent duplicate names.
        result = await session.execute(
            select(League).where(League.name == name)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            await message.reply_text(
                "❌ A league/division with this name already exists."
            )
            return

        division = League(
            name=name,
            country=parent.country,
            tier=division_tier,
            max_clubs=max_clubs,
            status="inactive",
            parent_league_id=parent.id,
            promotion_target_id=parent.id,
            promotion_slots=parent.relegation_slots,
            relegation_slots=parent.relegation_slots,
        )

        session.add(division)
        await session.flush()

        # The parent first division sends relegated clubs here.
        # If it already has a relegation target, we don't overwrite it.
        if parent.relegation_target_id is None:
            parent.relegation_target_id = division.id

        # Keep the first division as the promotion target of the new division.
        division.promotion_target_id = parent.id

        await session.commit()

        division_id = division.id
        division_tier_value = division.tier
        parent_name = parent.name

    await message.reply_text(
        (
            "✅ 𝐃𝐈𝐕𝐈𝐒𝐈𝐎𝐍 𝐂𝐑𝐄𝐀𝐓𝐄𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 Parent league : {parent_name}\n"
            f"🥈 Division : {name}\n"
            f"🆔 Division ID : {division_id}\n"
            f"📊 Tier : {division_tier_value}\n"
            f"👥 Capacity : {max_clubs}\n\n"
            "⬆️ Promotion target connected.\n"
            "⬇️ Relegation target connected."
        )
    )


adddivision_handler = CommandHandler(
    "adddivision",
    adddivision,
)