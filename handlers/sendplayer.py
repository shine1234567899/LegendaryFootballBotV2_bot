from __future__ import annotations
from pathlib import Path
from telegram import Update
from telegram.ext import ConversationHandler, MessageHandler, ContextTypes, filters
from sqlalchemy import select
from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import User, Club, Player, ClubPlayer

IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "sendplayer.jpg"
USERNAME, NAME, COUNTRY, POSITION, AGE, OVERALL, POTENTIAL, VALUE, IMAGE = range(9)

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS

async def get_user(session, username):
    username = username.strip().lstrip("@")
    if not username:
        return None
    return await session.scalar(select(User).where(User.username.ilike(username)))

async def get_club(session, owner_id):
    return await session.scalar(select(Club).where(Club.owner_id == owner_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return ConversationHandler.END
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ This command is Owner only.")
        return ConversationHandler.END
    context.user_data.pop("sendplayer", None)
    await update.message.reply_text(
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "        𝗦𝗘𝗡𝗗 𝗣𝗟𝗔𝗬𝗘𝗥\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        "👤 Enter the manager's username:"
    )
    return USERNAME

async def username(update, context):
    async with AsyncSessionLocal() as session:
        user = await get_user(session, update.message.text)
        if not user:
            await update.message.reply_text("❌ User not found. Enter another username:")
            return USERNAME
        club = await get_club(session, user.id)
        if not club:
            await update.message.reply_text("❌ This user has no club yet. Enter another username:")
            return USERNAME
    context.user_data["sendplayer"] = {
        "target_user_id": user.id, "target_club_id": club.id,
        "target_name": f"@{user.username}" if user.username else (user.first_name or f"User #{user.id}"),
        "club_name": club.name,
    }
    await update.message.reply_text("👤 Enter the player's name:")
    return NAME

async def name(update, context):
    value = update.message.text.strip()
    if not value:
        await update.message.reply_text("❌ Player name cannot be empty.")
        return NAME
    context.user_data["sendplayer"]["name"] = value
    await update.message.reply_text("🌍 Enter the player's country:")
    return COUNTRY

async def country(update, context):
    value = update.message.text.strip()
    if not value:
        await update.message.reply_text("❌ Country cannot be empty.")
        return COUNTRY
    context.user_data["sendplayer"]["country"] = value
    await update.message.reply_text("📍 Enter the player's position:\n\nGK / DEF / MID / ATT")
    return POSITION

async def position(update, context):
    value = update.message.text.strip().upper()
    if value not in {"GK", "DEF", "MID", "ATT"}:
        await update.message.reply_text("❌ Invalid position. Use GK, DEF, MID or ATT.")
        return POSITION
    context.user_data["sendplayer"]["position"] = value
    await update.message.reply_text("🎂 Enter the player's age:")
    return AGE

async def age(update, context):
    try:
        value = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Age must be a number.")
        return AGE
    if not 1 <= value <= 50:
        await update.message.reply_text("❌ Enter an age between 1 and 50.")
        return AGE
    context.user_data["sendplayer"]["age"] = value
    await update.message.reply_text("⭐ Enter the player's Overall:")
    return OVERALL

async def overall(update, context):
    try:
        value = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Overall must be a number.")
        return OVERALL
    if not 1 <= value <= 130:
        await update.message.reply_text("❌ Overall must be between 1 and 130.")
        return OVERALL
    context.user_data["sendplayer"]["overall"] = value
    await update.message.reply_text("📈 Enter the player's Potential:")
    return POTENTIAL

async def potential(update, context):
    try:
        value = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Potential must be a number.")
        return POTENTIAL
    if not 1 <= value <= 130:
        await update.message.reply_text("❌ Potential must be between 1 and 130.")
        return POTENTIAL
    context.user_data["sendplayer"]["potential"] = value
    await update.message.reply_text("💰 Enter the player's value in Coins:")
    return VALUE

async def value(update, context):
    try:
        value = int(update.message.text.strip().replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ Value must be a number.")
        return VALUE
    if value <= 0:
        await update.message.reply_text("❌ Value must be greater than 0.")
        return VALUE
    context.user_data["sendplayer"]["value"] = value
    await update.message.reply_text("🖼️ Send the player's photo now, or type /skip.")
    return IMAGE

async def finish(update, context):
    data = context.user_data.get("sendplayer")
    if not data:
        await update.message.reply_text("❌ Player data was lost. Use /sendplayer again.")
        return ConversationHandler.END
    async with AsyncSessionLocal() as session:
        club = await session.scalar(select(Club).where(Club.id == data["target_club_id"]))
        if not club:
            await update.message.reply_text("❌ Target club no longer exists.")
            return ConversationHandler.END
        existing = await session.scalar(select(Player).where(Player.name.ilike(data["name"])))
        if existing:
            await update.message.reply_text("❌ A player with this exact name already exists.")
            return NAME
        player = Player(
            name=data["name"], country=data["country"], position=data["position"],
            age=data["age"], overall=data["overall"], potential=data["potential"],
            value=data["value"], image_file_id=data.get("image_file_id"),
            starter_pool=True,
        )
        session.add(player)
        await session.flush()
        session.add(ClubPlayer(club_id=club.id, player_id=player.id, is_current=True))
        await session.commit()
    context.user_data.pop("sendplayer", None)
    await update.message.reply_text(
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "       ✅ 𝗣𝗟𝗔𝗬𝗘𝗥 𝗦𝗘𝗡𝗧\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        f"👤 Manager : {data['target_name']}\n🏟️ Club : {data['club_name']}\n\n"
        f"⚽ Player : {data['name']}\n🌍 Country : {data['country']}\n"
        f"📍 Position : {data['position']}\n🎂 Age : {data['age']}\n"
        f"⭐ Overall : {data['overall']}\n📈 Potential : {data['potential']}\n"
        f"💰 Value : {data['value']:,} Coins\n\n"
        "✅ Player created and added to the squad.\n"
        "✅ Player is usable and trainable."
    )
    return ConversationHandler.END

async def image(update, context):
    if not update.message or not update.message.photo:
        await update.message.reply_text("❌ Send a photo or use /skip.")
        return IMAGE
    context.user_data["sendplayer"]["image_file_id"] = update.message.photo[-1].file_id
    return await finish(update, context)

async def skip(update, context):
    context.user_data["sendplayer"]["image_file_id"] = None
    return await finish(update, context)

sendplayer_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(r"^/sendplayer$"), start)],
    states={
        USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
        COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
        POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, position)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
        OVERALL: [MessageHandler(filters.TEXT & ~filters.COMMAND, overall)],
        POTENTIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, potential)],
        VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, value)],
        IMAGE: [
            MessageHandler(filters.PHOTO, image),
            MessageHandler(filters.Regex(r"^/skip$"), skip),
        ],
    },
    fallbacks=[],
)
