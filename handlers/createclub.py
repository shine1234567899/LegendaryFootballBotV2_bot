from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from sqlalchemy import select
from services.starter_squad import generate_starter_squad

from database.database import AsyncSessionLocal
from database.models import User, Club, Player, ClubPlayer
from handlers.manager_contracts import ensure_player_contract


CLUB_NAME, COUNTRY, STADIUM, LOGO, CONFIRM = range(5)


async def createclub_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):  
    if update.message is None or update.effective_user is None:
        return ConversationHandler.END

    user_id = update.effective_user.id
    if update.effective_chat is None:
     return ConversationHandler.END

    if update.effective_chat.type != "private":
     await update.message.reply_text(
        "❌ This command can only be used in a private chat with the bot.\n\n"
        "💬 Open the bot's private chat and use /createclub there."
    )
     return ConversationHandler.END

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.owner_id == user_id)
        )

        existing_club = result.scalar_one_or_none()

    if existing_club is not None:
        await update.message.reply_text(
            "❌ You already have a club.\n\n"
            f"🏟️ Your club: {existing_club.name}"
        )
        return ConversationHandler.END

    context.user_data.clear()

    await update.message.reply_text(
        "🏟️ CREATE YOUR CLUB\n\n"
        "Let's build your club step by step.\n\n"
        "1️⃣ What is the name of your club?"
    )

    return CLUB_NAME


async def club_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message is None:
        return CLUB_NAME

    name = update.message.text.strip()

    if len(name) < 3 or len(name) > 100:
        await update.message.reply_text(
            "❌ The club name must contain between 3 and 100 characters.\n\n"
            "Try again:"
        )
        return CLUB_NAME

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.name == name)
        )

        existing = result.scalar_one_or_none()

    if existing is not None:
        await update.message.reply_text(
            "❌ This club name is already taken.\n\n"
            "Choose another name:"
        )
        return CLUB_NAME

    context.user_data["club_name"] = name

    await update.message.reply_text(
        "🌍 2️⃣ Which country will your club belong to?\n\n"
        "Example: Cameroon"
    )

    return COUNTRY


async def club_country(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message is None:
        return COUNTRY

    country = update.message.text.strip()

    if len(country) < 2 or len(country) > 100:
        await update.message.reply_text(
            "❌ Invalid country name.\n\n"
            "Please try again:"
        )
        return COUNTRY

    context.user_data["country"] = country

    await update.message.reply_text(
        "🏟️ 3️⃣ What will your stadium be called?"
    )

    return STADIUM


async def club_stadium(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message is None:
        return STADIUM

    stadium = update.message.text.strip()

    if len(stadium) < 3 or len(stadium) > 100:
        await update.message.reply_text(
            "❌ The stadium name must contain between 3 and 100 characters.\n\n"
            "Try again:"
        )
        return STADIUM

    context.user_data["stadium"] = stadium

    await update.message.reply_text(
        "🖼️ 4️⃣ Send me your club logo.\n\n"
        "Send it as a Telegram photo."
    )

    return LOGO


async def club_logo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message is None:
        return LOGO

    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send the logo as a photo.\n\n"
            "Try again:"
        )
        return LOGO

    photo = update.message.photo[-1]

    context.user_data["logo_file_id"] = photo.file_id

    club_name_value = context.user_data["club_name"]
    country = context.user_data["country"]
    stadium = context.user_data["stadium"]

    await update.message.reply_photo(
        photo=photo.file_id,
        caption=(
            "🏟️ CLUB PREVIEW\n\n"
            f"⚽ Name: {club_name_value}\n"
            f"🌍 Country: {country}\n"
            f"🏟️ Stadium: {stadium}\n\n"
            "Do you want to create this club?\n\n"
            "Reply with:\n"
            "YES ✅\n"
            "or\n"
            "NO ❌"
        ),
    )

    return CONFIRM


async def confirm_club(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message is None or update.effective_user is None:
        return ConversationHandler.END

    answer = update.message.text.strip().lower()

    if answer not in {"yes", "no"}:
        await update.message.reply_text(
            "Please answer YES ✅ or NO ❌"
        )
        return CONFIRM

    if answer == "no":
        context.user_data.clear()

        await update.message.reply_text(
            "❌ Club creation cancelled.\n\n"
            "You can use /createclub whenever you want."
        )

        return ConversationHandler.END

    user_id = update.effective_user.id

    club_name_value = context.user_data["club_name"]
    country = context.user_data["country"]
    stadium = context.user_data["stadium"]
    logo_file_id = context.user_data["logo_file_id"]

    async with AsyncSessionLocal() as session:
        try:
            # Vérifie que le manager n'a pas déjà un club.
            result = await session.execute(
                select(Club).where(Club.owner_id == user_id)
            )

            if result.scalar_one_or_none() is not None:
                await update.message.reply_text(
                    "❌ You already have a club."
                )
                await session.rollback()
                return ConversationHandler.END

            # Vérifie le nom.
            result = await session.execute(
                select(Club).where(Club.name == club_name_value)
            )

            if result.scalar_one_or_none() is not None:
                await update.message.reply_text(
                    "❌ This club name is already taken."
                )
                await session.rollback()
                return ConversationHandler.END

            # Récupère 18 joueurs disponibles.
            try:
             players = await generate_starter_squad(session)
            except RuntimeError as exc:
             await update.message.reply_text(
                f"❌ Starter squad unavailable.\n\n{exc}"
                )
             await session.rollback()
             return ConversationHandler.END
            # Vérifie que le compte Telegram existe dans users.
            user = await session.get(User, user_id)

            if user is None:
                # Create the user row first so clubs.owner_id
                # satisfies the foreign-key constraint.
                user = User(
                    id=user_id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name,
                    coins=0,
                    gems=0,
                )
                session.add(user)
                await session.flush()

            # Création du club.
            club = Club(
                owner_id=user_id,
                league_id=None,
                name=club_name_value,
                logo_file_id=logo_file_id,
                stadium_name=stadium,
                country=country,
            )

            session.add(club)
            await session.flush()

            # Ajout des 18 joueurs + contrat automatique.
            for player in players:
                club_player = ClubPlayer(
                    club_id=club.id,
                    player_id=player.id,
                    is_current=True,
                )
                session.add(club_player)
                await session.flush()

                await ensure_player_contract(
                    session,
                    club.id,
                    player.id,
                )

            # Starter pack.
            user.coins = 50_000_000
            user.gems = 500

            await session.commit()

        except Exception:
            await session.rollback()
            raise

    context.user_data.clear()

    await update.message.reply_text(
        "🎉 CLUB CREATED SUCCESSFULLY!\n\n"
        f"⚽ {club_name_value}\n"
        f"🌍 {country}\n"
        f"🏟️ {stadium}\n\n"
        "🎁 STARTER PACK\n"
        "👥 18 players\n"
        "💰 50,000,000 Coins\n"
        "💎 500 Gems\n\n"
        "Welcome to Legendary Football! 🏆"
    )

    return ConversationHandler.END


async def cancel_createclub(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    if update.message:
        await update.message.reply_text(
            "❌ Club creation cancelled."
        )

    return ConversationHandler.END


createclub_handler = ConversationHandler(
    entry_points=[
        CommandHandler("createclub", createclub_start)
    ],
    states={
        CLUB_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                club_name,
            )
        ],
        COUNTRY: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                club_country,
            )
        ],
        STADIUM: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                club_stadium,
            )
        ],
        LOGO: [
            MessageHandler(
                filters.PHOTO,
                club_logo,
            )
        ],
        CONFIRM: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                confirm_club,
            )
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_createclub)
    ],
)