from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# Replace this with the owner ID from your config.py if it already exists.
try:
    from config import OWNER_ID
except ImportError:
    OWNER_ID = 8599799463


ANNOUNCEMENT_PENDING_KEY = "announcement_pending"


def _is_owner(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False

    try:
        return int(user.id) == int(OWNER_ID)
    except (TypeError, ValueError):
        return False


async def _send_announcement(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):
    chat_ids = context.application.bot_data.get(
        "known_group_ids",
        set(),
    )

    if not chat_ids:
        await update.effective_message.reply_text(
            "⚠️ No registered groups yet."
        )
        return

    sent = 0
    failed = 0

    for chat_id in list(chat_ids):
        try:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text=text,
            )
            sent += 1

        except Exception as error:
            failed += 1

            # A group may have removed the bot or become inaccessible.
            # Remove it from the in-memory registry so future announcements
            # don't keep retrying the same dead chat.
            error_name = type(error).__name__
            error_text = str(error)

            print(
                "⚠️ ANNOUNCEMENT FAILED:",
                chat_id,
                error_name,
                error_text,
            )

            if any(
                marker in error_text
                for marker in (
                    "Chat not found",
                    "Forbidden",
                    "bot was kicked",
                    "not enough rights",
                )
            ):
                chat_ids.discard(chat_id)

    try:
        await update.effective_message.reply_text(
            "📢 Announcement sent.\n\n"
            f"✅ Groups reached: {sent}\n"
            f"❌ Failed: {failed}"
        )
    except Exception as error:
        # Never let the confirmation message turn a successful broadcast
        # into an apparent command failure.
        print(
            "⚠️ ANNOUNCEMENT CONFIRMATION ERROR:",
            type(error).__name__,
            error,
        )


async def annonce_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not _is_owner(update):
        return

    message = update.effective_message

    if message is None:
        return

    # Preserve line breaks exactly as the owner typed them.
    raw_text = message.text or ""

    # Preserve all line breaks. Support both /annonce and /annonce@BotName.
    command_part, separator, remainder = raw_text.partition(" ")
    if not separator:
        text = ""
    else:
        text = remainder

    if text:
        await _send_announcement(
            update,
            context,
            text,
        )
        return

    context.application.bot_data[
        ANNOUNCEMENT_PENDING_KEY
    ] = update.effective_user.id

    await message.reply_text(
        "📢 𝐀𝐍𝐍𝐎𝐔𝐍𝐂𝐄𝐌𝐄𝐍𝐓\n\n"
        "Send the message you want to broadcast.\n"
        "It will be sent to every registered group."
    )


async def annonce_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    pending_owner = (
        context.application.bot_data.get(
            ANNOUNCEMENT_PENDING_KEY
        )
    )

    user = update.effective_user

    if (
        pending_owner is None
        or user is None
        or int(user.id) != int(pending_owner)
    ):
        return

    message = update.effective_message

    if message is None or not message.text:
        return

    # Do not strip, split, or join the message: Telegram's \n characters
    # are preserved exactly.
    announcement_text = message.text

    context.application.bot_data.pop(
        ANNOUNCEMENT_PENDING_KEY,
        None,
    )

    await _send_announcement(
        update,
        context,
        announcement_text,
    )


async def track_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Register every group/supergroup that sends an update to the bot.

    Telegram has no API that returns all groups a bot belongs to, so the
    bot must learn group IDs from updates. This tracker is intentionally
    broad and runs in a lower-priority handler group.
    """
    chat = update.effective_chat

    if chat is None:
        return

    if chat.type not in {"group", "supergroup"}:
        return

    ids = context.application.bot_data.setdefault(
        "known_group_ids",
        set(),
    )

    ids.add(int(chat.id))


annonce_handler = CommandHandler(
    "annonce",
    annonce_command,
)

annonce_message_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    annonce_text,
)

group_tracker_handler = MessageHandler(
    filters.ALL,
    track_group,
)