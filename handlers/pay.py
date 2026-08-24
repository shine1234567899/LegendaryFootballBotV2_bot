from __future__ import annotations

from decimal import Decimal, InvalidOperation

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User


# ==========================================================
# PAY
# ==========================================================
#
# /pay @username amount
#
# Transfers game coins from the current user to another user.
#
# Example:
#   /pay @shine 5000000
#
# Rules:
#   - amount must be positive
#   - sender cannot pay himself
#   - sender must have enough coins
#   - recipient must already exist
#   - confirmation button is required
#
# Coins only. Gems and player ownership are untouched.
# ==========================================================


PAY_CONFIRM_PREFIX = "pay:confirm"
PAY_CANCEL_PREFIX = "pay:cancel"


def _format_amount(amount: int) -> str:
    return f"{amount:,}"


def _confirm_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ CONFIRM",
                    callback_data=f"{PAY_CONFIRM_PREFIX}:pending",
                ),
                InlineKeyboardButton(
                    "❌ CANCEL",
                    callback_data=f"{PAY_CANCEL_PREFIX}:pending",
                ),
            ]
        ]
    )


def _parse_amount(raw: str) -> int | None:
    cleaned = (
        raw.replace(",", "")
        .replace("_", "")
        .strip()
    )

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None

    if value <= 0 or value != value.to_integral_value():
        return None

    return int(value)


async def _get_user_by_id(
    session,
    user_id: int,
):
    result = await session.execute(
        select(User).where(
            User.id == user_id
        )
    )
    return result.scalar_one_or_none()


async def _get_user_by_username(
    session,
    username: str,
):
    username = username.strip().lstrip("@")

    if not username:
        return None

    result = await session.execute(
        select(User).where(
            User.username.ilike(username)
        )
    )
    return result.scalar_one_or_none()


async def pay(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if len(context.args) != 2:
        await message.reply_text(
            (
                "💸 𝐏𝐀𝐘\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n"
                "/pay @username amount\n\n"
                "Example:\n"
                "/pay @manager 5000000"
            )
        )
        return

    recipient_input = context.args[0]
    amount = _parse_amount(context.args[1])

    if amount is None:
        await message.reply_text(
            "❌ Invalid amount."
        )
        return

    async with AsyncSessionLocal() as session:
        sender = await _get_user_by_id(
            session,
            user.id,
        )

        if sender is None:
            await message.reply_text(
                "❌ Your user account was not found."
            )
            return

        recipient = await _get_user_by_username(
            session,
            recipient_input,
        )

        if recipient is None:
            await message.reply_text(
                "❌ Recipient not found."
            )
            return

        if recipient.id == sender.id:
            await message.reply_text(
                "❌ You cannot pay yourself."
            )
            return

        if sender.coins < amount:
            await message.reply_text(
                (
                    "❌ Insufficient coins.\n\n"
                    f"💰 Your balance: "
                    f"{_format_amount(sender.coins)}\n"
                    f"💸 Requested: "
                    f"{_format_amount(amount)}"
                )
            )
            return

        recipient_name = (
            f"@{recipient.username}"
            if recipient.username
            else (
                recipient.first_name
                or f"User #{recipient.id}"
            )
        )

        # Store the transaction temporarily in the user's
        # context until the confirmation callback is pressed.
        context.user_data["pending_pay"] = {
            "recipient_id": recipient.id,
            "amount": amount,
            "recipient_name": recipient_name,
        }

    await message.reply_text(
        (
            "💸 𝐂𝐎𝐍𝐅𝐈𝐑𝐌 𝐏𝐀𝐘𝐌𝐄𝐍𝐓\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 To : {recipient_name}\n"
            f"💰 Amount : {_format_amount(amount)} coins\n\n"
            "Your coins will be transferred only after "
            "you confirm."
        ),
        reply_markup=_confirm_keyboard(),
    )


async def pay_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None or not query.data:
        return

    try:
        await query.answer()
    except Exception:
        pass

    action = str(query.data).split(":", 2)

    if len(action) < 2:
        return

    if action[1] == "cancel":
        context.user_data.pop(
            "pending_pay",
            None,
        )
        await query.edit_message_text(
            "❌ Payment cancelled."
        )
        return

    if action[1] != "confirm":
        return

    pending = context.user_data.get(
        "pending_pay"
    )

    if not pending:
        await query.edit_message_text(
            "⚠️ This payment has expired."
        )
        return

    recipient_id = int(
        pending["recipient_id"]
    )
    amount = int(
        pending["amount"]
    )

    async with AsyncSessionLocal() as session:
        sender = await _get_user_by_id(
            session,
            query.from_user.id,
        )
        recipient = await _get_user_by_id(
            session,
            recipient_id,
        )

        if sender is None or recipient is None:
            await query.edit_message_text(
                "❌ Payment could not be completed."
            )
            context.user_data.pop(
                "pending_pay",
                None,
            )
            return

        if sender.id == recipient.id:
            await query.edit_message_text(
                "❌ You cannot pay yourself."
            )
            context.user_data.pop(
                "pending_pay",
                None,
            )
            return

        # Re-check the balance at confirmation time.
        if sender.coins < amount:
            await query.edit_message_text(
                (
                    "❌ Insufficient coins.\n"
                    "Your balance changed before confirmation."
                )
            )
            context.user_data.pop(
                "pending_pay",
                None,
            )
            return

        sender.coins -= amount
        recipient.coins += amount

        await session.commit()

    context.user_data.pop(
        "pending_pay",
        None,
    )

    recipient_name = pending[
        "recipient_name"
    ]

    await query.edit_message_text(
        (
            "✅ 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 To : {recipient_name}\n"
            f"💰 Sent : {_format_amount(amount)} coins\n"
            f"💰 Your new balance : "
            f"{_format_amount(sender.coins)} coins"
        )
    )


pay_handler = CommandHandler(
    "pay",
    pay,
)

pay_callback_handler = CallbackQueryHandler(
    pay_callback,
    pattern=r"^pay:(confirm|cancel):pending$",
)