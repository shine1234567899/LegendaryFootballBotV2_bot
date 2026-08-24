from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from handlers.command import count_command_usage

async def track_all_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None or not message.text:
        return

    try:
        await count_command_usage(user.id)
    except Exception as error:
        print(
            "⚠️ COMMAND COUNTER ERROR:",
            type(error).__name__,
            error,
        )

command_tracker_handler = MessageHandler(
    filters.COMMAND,
    track_all_commands,
    block=False,
)