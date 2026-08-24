from pathlib import Path
from telegram import InputFile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database.database import AsyncSessionLocal
from database.models import Club, ClubPlayer, Player


PLAYERS_PER_PAGE = 6
BASE_DIR = Path(__file__).resolve().parent.parent
SQUAD_BANNER = BASE_DIR / "assets" / "SQUAD.jpg"


async def build_squad_page(session, club_id: int, page: int):
    result = await session.execute(
        select(Player)
        .join(ClubPlayer, ClubPlayer.player_id == Player.id)
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
        )
        .order_by(Player.position, Player.overall.desc(), Player.name)
    )

    players = list(result.scalars().all())

    total_pages = max(
        1,
        (len(players) + PLAYERS_PER_PAGE - 1) // PLAYERS_PER_PAGE,
    )

    page = max(0, min(page, total_pages - 1))

    start = page * PLAYERS_PER_PAGE
    page_players = players[start:start + PLAYERS_PER_PAGE]

    lines = [
    "⚜️━━━━━━━━━━━━━━━━━━━━⚜️",
    "          𝗦𝗤𝗨𝗔𝗗",
    "⚜️━━━━━━━━━━━━━━━━━━━━⚜️",
    "",
    f"👥 Squad ........ {len(players)}/36",
    "",
]
    
    for index, player in enumerate(page_players, start=start + 1):
        lines.append(
            f"{index}. {player.name}\n"
            f"   {player.position} • OVR {player.overall} • "
            f"{player.country}"
        )

    lines.extend([
        "",
        f"Page {page + 1}/{total_pages}",
    ])

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"squad:{page - 1}",
            )
        )

    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"squad:{page + 1}",
            )
        )

    keyboard = [buttons] if buttons else []

    return "\n".join(lines), InlineKeyboardMarkup(keyboard)
    

async def squad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.owner_id == user_id)
        )

        club = result.scalar_one_or_none()

        if club is None:
            await update.message.reply_text(
                "❌ You don't have a club yet.\n\n"
                "Use /createclub first."
            )
            return

        text, keyboard = await build_squad_page(
            session,
            club.id,
            0,
        )

    if SQUAD_BANNER.exists():
     with SQUAD_BANNER.open("rb") as photo:
        await update.message.reply_photo(
            photo=InputFile(photo),
            caption=text,
            reply_markup=keyboard,
        )
    else:
     await update.message.reply_text(
        text,
        reply_markup=keyboard,
    )


async def squad_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        page = int(query.data.split(":")[1])
    except (AttributeError, IndexError, ValueError):
        return

    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.owner_id == user_id)
        )

        club = result.scalar_one_or_none()

        if club is None:
            await query.edit_message_text(
                "❌ You don't have a club."
            )
            return

        text, keyboard = await build_squad_page(
            session,
            club.id,
            page,
        )

    await query.edit_message_caption(
        caption=text,
        reply_markup=keyboard,
    )
async def player_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        player_id = int(query.data.split(":")[1])
    except (AttributeError, IndexError, ValueError):
        return

    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.owner_id == user_id)
        )

        club = result.scalar_one_or_none()

        if club is None:
            await query.answer(
                "You don't have a club.",
                show_alert=True,
            )
            return

        result = await session.execute(
            select(Player)
            .join(
                ClubPlayer,
                ClubPlayer.player_id == Player.id,
            )
            .where(
                Player.id == player_id,
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
        )

        player = result.scalar_one_or_none()

        if player is None:
            await query.answer(
                "This player is not in your squad.",
                show_alert=True,
            )
            return

    position_icon = {
        "GK": "🧤",
        "DEF": "🛡️",
        "MID": "⚙️",
        "ATT": "⚡",
    }.get(player.position, "⚽")

    text = (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "          𝗣𝗟𝗔𝗬𝗘𝗥\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        f"{position_icon} {player.name}\n\n"
        f"🌍 Country: {player.country}\n"
        f"📍 Position: {player.position}\n"
        f"⭐ Overall: {player.overall}\n"
        f"📈 Potential: {player.potential}\n"
        f"🎂 Age: {player.age}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏟️ {club.name}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 BACK TO SQUAD",
                callback_data="squad:0",
            )
        ]
    ])

    await query.edit_message_caption(
        caption=text,
        reply_markup=keyboard,
    )


squad_callback_handler = CallbackQueryHandler(
    squad_callback,
    pattern=r"^squad:\d+$",
)
player_callback_handler = CallbackQueryHandler(
    player_callback,
    pattern=r"^player:\d+$",
)