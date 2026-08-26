from __future__ import annotations

import asyncio

from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, TelegramError
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import OWNER_IDS


# Same approach as V1:
# the registry lives in application.bot_data and needs no migration.
GROUPS_KEY = "known_group_ids"


def _get_group_registry(context: ContextTypes.DEFAULT_TYPE) -> set[int]:
    groups = context.application.bot_data.setdefault(GROUPS_KEY, set())

    # Protect against an old version having stored a list.
    if not isinstance(groups, set):
        groups = set(groups)
        context.application.bot_data[GROUPS_KEY] = groups

    return groups


async def track_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Register every group/supergroup that sends an update."""
    chat = update.effective_chat

    if chat is None:
        return

    if chat.type not in {"group", "supergroup"}:
        return

    groups = _get_group_registry(context)
    groups.add(int(chat.id))


async def annonce_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Owner-only announcement broadcast, compatible with the V1 approach."""
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if user.id not in OWNER_IDS:
        return

    if not context.args:
        await message.reply_text(
            "📢 Usage:\n"
            "/annonce Your message here"
        )
        return

    text = " ".join(context.args).strip()

    if not text:
        await message.reply_text(
            "❌ The announcement cannot be empty."
        )
        return

    groups = _get_group_registry(context)

    if not groups:
        await message.reply_text(
            "⚠️ No groups are registered yet.\n"
            "Send a message in a group where the bot is present, "
            "then try again."
        )
        return

    sent = 0
    removed = 0
    failed = 0

    for chat_id in list(groups):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
            )
            sent += 1

        except Forbidden:
            # Bot was removed/blocked or has no access anymore.
            groups.discard(chat_id)
            removed += 1

        except BadRequest as exc:
            error_text = str(exc).lower()

            if (
                "chat not found" in error_text
                or "bot was kicked" in error_text
                or "not enough rights" in error_text
                or "have no rights" in error_text
            ):
                groups.discard(chat_id)
                removed += 1
            else:
                failed += 1
                print(
                    f"⚠️ ANNOUNCEMENT BadRequest for {chat_id}: {exc}"
                )

        except NetworkError as exc:
            # Temporary Telegram/network issue: keep the group registered.
            failed += 1
            print(
                f"⚠️ ANNOUNCEMENT NetworkError for {chat_id}: {exc}"
            )

        except TelegramError as exc:
            failed += 1
            print(
                f"⚠️ ANNOUNCEMENT TelegramError for {chat_id}: {exc}"
            )

        except Exception as exc:
            failed += 1
            print(
                f"⚠️ ANNOUNCEMENT unexpected error for {chat_id}: {exc}"
            )

        # Avoid hammering Telegram when there are many groups.
        await asyncio.sleep(0.05)

    await message.reply_text(
        "📢 Announcement finished.\n\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"🗑 Removed: {removed}\n"
        f"📊 Registered groups: {len(groups)}"
    )


annonce_handler = CommandHandler(
    "annonce",
    annonce_command,
)

# Register this low-priority tracker in main.py:
# application.add_handler(
#     MessageHandler(
#         filters.ChatType.GROUPS,
#         track_group,
#     ),
#     group=-11,
# )
#
# The tracker intentionally does not use a database or Alembic migration.
group_tracker_handler = MessageHandler(
    filters.ChatType.GROUPS,
    track_group,
)
