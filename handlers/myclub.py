from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select, func

from database.database import AsyncSessionLocal
from database.models import Club, ClubPlayer, Player, User,GameSetting


async def myclub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    message = update.effective_message

    async with AsyncSessionLocal() as session:
        # Récupération du club
        result = await session.execute(
            select(Club).where(Club.owner_id == user_id)
        )

        club = result.scalar_one_or_none()

        if club is None:
            await message.reply_text(
                "❌ You don't have a club yet.\n\n"
                "Use /createclub to create one."
            )
            return

        # Récupération du manager
        user = await session.get(User, user_id)

        # Nombre de joueurs
        result = await session.execute(
            select(func.count(ClubPlayer.id)).where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
        )
        
        player_count = result.scalar_one()
        result = await session.execute(
            select(GameSetting).where(
                GameSetting.key == "max_squad_size"
    )
)

        setting = result.scalar_one_or_none()

        max_squad_size = int(setting.value) if setting else 36


        # Overall moyen
        result = await session.execute(
            select(func.avg(Player.overall))
            .join(
                ClubPlayer,
                ClubPlayer.player_id == Player.id,
            )
            .where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
        )

        average_overall = result.scalar_one()

    average_overall = round(average_overall or 0, 1)

    caption = (
    "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
    "        𝗖𝗟𝗨𝗕 𝗖𝗘𝗡𝗧𝗘𝗥\n"
    "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
    f"🏟️ {club.name}\n"
    f"🌍 {club.country}\n"
    f"🏟️ {club.stadium_name}\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    f"👑 Manager: {user.first_name or user.username or 'Manager'}\n"
    f"💰 {user.coins:,} Coins\n"
    f"💎 {user.gems:,} Gems\n"
    f"👥 Squad ........ {player_count}/{max_squad_size}\n"
    f"⭐ Average OVR ... {average_overall}\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "⚔️ BUILD YOUR LEGACY\n"
    "🏆 DEFEND YOUR COLORS"
)

    if club.logo_file_id:
        await message.reply_photo(
            photo=club.logo_file_id,
            caption=caption,
        )
    else:
        await message.reply_text(caption)