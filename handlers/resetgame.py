from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import text

from config import OWNER_IDS
from database.database import engine


# ==========================================================
# RESET GAME
# ==========================================================

RESET_PREFIX = "resetgame"


# Static/catalog tables are intentionally preserved:
# players, leagues, competitions, competition structure,
# trophies, quiz questions and game settings.
#
# Everything below is player/club/progress data and is removed
# when the owner confirms a full game reset.
RESET_TABLES = [
    "match_player_stats",
    "match_events",
    "lineup_players",
    "lineups",
    "matches",
    "fixtures",
    "saved_lineup_players",
    "saved_lineups",
    "league_season_clubs",
    "competition_participants",
    "competition_rounds",
    "competition_seasons",
    "user_trophies",
    "awards",
    "notifications",
    "ranking_snapshots",
    "sanctions",
    "transfer_listings",
    "trades",
    "transactions",
    "purchases",
    "daily_rewards",
    "referrals",
    "club_players",
    "clubs",
    "users",
]


async def resetgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only command that asks for confirmation before resetting the game."""

    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if user.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ You are not authorized to reset the game."
        )
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚠️ YES, RESET EVERYTHING",
                    callback_data=f"{RESET_PREFIX}:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ CANCEL",
                    callback_data=f"{RESET_PREFIX}:cancel",
                )
            ],
        ]
    )

    await message.reply_text(
        (
            "⚠️ 𝐑𝐄𝐒𝐄𝐓 𝐆𝐀𝐌𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "This will delete ALL player/club progress:\n\n"
            "👤 Users\n"
            "⚽ Clubs & owned players\n"
            "📋 Saved lineups\n"
            "🏆 Season standings & competitions progress\n"
            "⚽ Matches & match statistics\n"
            "💰 Transfers, transactions & purchases\n"
            "🎁 Rewards, referrals & rankings\n"
            "🏅 Awards, trophies earned & notifications\n\n"
            "⚠️ This cannot be undone.\n"
            "Players/catalog, leagues, competitions, "
            "quiz questions and game settings are preserved."
        ),
        reply_markup=keyboard,
    )


async def resetgame_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    if query.from_user.id not in OWNER_IDS:
        try:
            await query.answer(
                "⛔ You are not authorized.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    try:
        await query.answer()
    except Exception:
        pass

    action = str(query.data).split(":", 1)[1]

    if action == "cancel":
        await query.edit_message_text(
            "❌ Reset cancelled. No data was deleted."
        )
        return

    if action != "confirm":
        await query.edit_message_text(
            "❌ Invalid reset action."
        )
        return

    try:
        async with engine.begin() as connection:
            # PostgreSQL: CASCADE handles all foreign-key dependencies.
            # RESTART IDENTITY resets integer sequences too.
            table_sql = ", ".join(
                f'"{table}"'
                for table in RESET_TABLES
            )

            await connection.execute(
                text(
                    f"TRUNCATE TABLE {table_sql} "
                    "RESTART IDENTITY CASCADE"
                )
            )

        # Pending Friendly challenges live in memory, not PostgreSQL.
        context.bot_data.pop(
            "pending_friendlies",
            None,
        )

        await query.edit_message_text(
            (
                "✅ 𝐆𝐀𝐌𝐄 𝐑𝐄𝐒𝐄𝐓 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🎮 Legendary Football is back to 0.\n\n"
                "👤 Users: reset\n"
                "⚽ Clubs: reset\n"
                "📋 Lineups: reset\n"
                "🏆 Progress: reset\n"
                "⚽ Match history: reset\n"
                "💰 Economy: reset\n\n"
                "📦 Players/catalog and permanent game "
                "configuration were preserved."
            )
        )

    except Exception as error:
        print(
            "❌ RESET GAME ERROR:",
            type(error).__name__,
            error,
        )

        await query.edit_message_text(
            (
                "❌ 𝐑𝐄𝐒𝐄𝐓 𝐅𝐀𝐈𝐋𝐄𝐃\n\n"
                f"{type(error).__name__}: {error}"
            )
        )


resetgame_handler = CommandHandler(
    "resetgame",
    resetgame,
)

resetgame_callback_handler = CallbackQueryHandler(
    resetgame_callback,
    pattern=r"^resetgame:(confirm|cancel)$",
)