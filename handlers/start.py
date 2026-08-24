from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Update,
)
from telegram.ext import ContextTypes
from sqlalchemy import select, func

from database.database import AsyncSessionLocal
from database.models import User, Club, ClubPlayer, GameSetting
from services.localization import get_text

from music_manager import music_manager


BASE_DIR = Path(__file__).resolve().parent.parent
START_BANNER = BASE_DIR / "assets" / "start_banner.jpg"

# =========================================================
# WELCOME MUSIC
# =========================================================

async def send_welcome_music(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
):
    track = music_manager.pick()

    if track is None:
        print("🎵 No music found in music/.")
        return

    try:
        with track.open("rb") as audio:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                caption="🎵 Welcome to Legendary Football!",
            )
    except Exception as error:
        print(
            "🎵 WELCOME MUSIC ERROR:",
            type(error).__name__,
            error,
        )



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.message is None:
        return

    telegram_user = update.effective_user
    user_id = telegram_user.id

    async with AsyncSessionLocal() as session:
        # Récupérer ou créer l'utilisateur
        user = await session.get(User, user_id)

        if user is None:
            user = User(
                id=user_id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                language="en",
                coins=0,
                gems=0,
            )

            session.add(user)
            await session.commit()

        # Récupérer le club
        result = await session.execute(
            select(Club).where(
                Club.owner_id == user_id
            )
        )

        club = result.scalar_one_or_none()

        # Capacité maximale
        result = await session.execute(
            select(GameSetting).where(
                GameSetting.key == "max_squad_size"
            )
        )

        setting = result.scalar_one_or_none()
        max_squad_size = int(setting.value) if setting else 36

        # Nombre de joueurs
        player_count = 0

        if club is not None:
            result = await session.execute(
                select(func.count(ClubPlayer.id)).where(
                    ClubPlayer.club_id == club.id,
                    ClubPlayer.is_current.is_(True),
                )
            )

            player_count = result.scalar_one()

        language = user.language or "en"

    username = (
        telegram_user.first_name
        or telegram_user.username
        or "Manager"
    )

    # =========================================================
    # NO CLUB
    # =========================================================

    if club is None:
        caption = (
    "⚜️━━━━━━━━━━━━━━━━━━━━━━━━⚜️\n"
    "        𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗙𝗢𝗢𝗧𝗕𝗔𝗟𝗟\n"
    "⚜️━━━━━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
    f"          👑 𝗪𝗘𝗟𝗖𝗢𝗠𝗘\n"
    f"        𝗠𝗔𝗡𝗔𝗚𝗘𝗥 {username}\n\n"
    "The stadium awaits your command.\n"
    "Your decisions will shape your legacy.\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "⚔️ Build your empire.\n"
    "⚽ Shape your squad.\n"
    "🏆 Conquer the world.\n\n"
    "Your story begins with a single decision.\n\n"
    "        /createclub\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "        ⚜️ 𝗧𝗛𝗘 𝗟𝗘𝗚𝗘𝗡𝗗 𝗕𝗘𝗚𝗜𝗡𝗦 ⚜️"
)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📖 HELP",
                    callback_data="start_help",
                ),
                InlineKeyboardButton(
                    "🌍 LANGUAGE",
                    callback_data="start_language",
                ),
            ],
        ])

        if not START_BANNER.exists():
            await update.message.reply_text(
                caption,
                reply_markup=keyboard,
            )
            return

        with START_BANNER.open("rb") as photo:
            await update.message.reply_photo(
                photo=InputFile(photo),
                caption=caption,
                reply_markup=keyboard,
            )

        await send_welcome_music(
            context,
            update.effective_chat.id,
        )

        return

    # =========================================================
    # CLUB EXISTANT
    # =========================================================

    manager_name = (
        user.first_name
        or user.username
        or username
    )

    caption = (
    "⚜️━━━━━━━━━━━━━━━━━━━━━━━━⚜️\n"
    "        𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗙𝗢𝗢𝗧𝗕𝗔𝗟𝗟\n"
    "⚜️━━━━━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
    f"       👑 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗕𝗔𝗖𝗞\n"
    f"          {username}\n\n"
    "        ⚔️ 𝗠𝗔𝗡𝗔𝗚𝗘𝗥 𝗖𝗘𝗡𝗧𝗘𝗥\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    f"🏟️ {club.name}\n"
    f"🌍 {club.country}\n"
    f"🏟️ {club.stadium_name}\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    f"💰 {user.coins:,} Coins\n"
    f"💎 {user.gems:,} Gems\n"
    f"👥 Squad ............ {player_count}/{max_squad_size}\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "⚔️ Build your legacy.\n"
    "🏆 Defend your colors.\n"
    "👑 Become a legend.\n\n"
    "THE GAME WAITS FOR NO ONE.\n\n"
    "⚜️━━━━━━━━━━━━━━━━━━━━━━━━⚜️"
)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🏟️ MY CLUB",
                callback_data="start_myclub",
            ),
            InlineKeyboardButton(
                "👥 SQUAD",
                callback_data="start_squad",
            ),
        ],
        [
            InlineKeyboardButton(
                "💰 TRANSFERS",
                callback_data="start_transfers",
            )
        ],
        [
            InlineKeyboardButton(
                "📖 HELP",
                callback_data="start_help",
            ),
            InlineKeyboardButton(
                "🌍 LANGUAGE",
                callback_data="start_language",
            ),
        ],
    ])

    if club.logo_file_id:
        await update.message.reply_photo(
            photo=club.logo_file_id,
            caption=caption,
            reply_markup=keyboard,
        )
    elif START_BANNER.exists():
        with START_BANNER.open("rb") as photo:
            await update.message.reply_photo(
                photo=InputFile(photo),
                caption=caption,
                reply_markup=keyboard,
            )
    else:
        await update.message.reply_text(
            caption,
            reply_markup=keyboard,
        )

    await send_welcome_music(
        context,
        update.effective_chat.id,
    )