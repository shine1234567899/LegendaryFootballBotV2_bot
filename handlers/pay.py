from __future__ import annotations

from decimal import Decimal, InvalidOperation

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User


PAY_CONFIRM_PREFIX = "pay:confirm"
PAY_CANCEL_PREFIX = "pay:cancel"
CURRENCIES = {"coins": "coins", "gems": "gems"}


def _format_amount(amount: int) -> str:
    return f"{int(amount or 0):,}"


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
    cleaned = raw.replace(",", "").replace("_", "").strip()

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None

    if value <= 0 or value != value.to_integral_value():
        return None

    return int(value)


async def _get_user_by_id(session, user_id: int):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_user_by_username(session, username: str):
    username = username.strip().lstrip("@")

    if not username:
        return None

    result = await session.execute(
        select(User).where(User.username.ilike(username))
    )
    return result.scalar_one_or_none()


async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if len(context.args) != 3:
        await message.reply_text(
            "💸 𝐏𝐀𝐘\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Usage:\n"
            "/pay @username coins amount\n"
            "/pay @username gems amount\n\n"
            "Examples:\n"
            "/pay @manager coins 5000000\n"
            "/pay @manager gems 500"
        )
        return

    recipient_input = context.args[0]
    currency = context.args[1].lower().strip()
    amount = _parse_amount(context.args[2])

    if currency not in CURRENCIES:
        await message.reply_text("❌ Currency must be coins or gems.")
        return

    if amount is None:
        await message.reply_text("❌ Invalid amount.")
        return

    balance_field = CURRENCIES[currency]

    async with AsyncSessionLocal() as session:
        sender = await _get_user_by_id(session, user.id)

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
            await message.reply_text("❌ Recipient not found.")
            return

        if recipient.id == sender.id:
            await message.reply_text("❌ You cannot pay yourself.")
            return

        sender_balance = int(
            getattr(sender, balance_field, 0) or 0
        )

        if sender_balance < amount:
            await message.reply_text(
                "❌ Insufficient balance.\n\n"
                f"💰 Your balance: "
                f"{_format_amount(sender_balance)} {currency}\n"
                f"💸 Requested: "
                f"{_format_amount(amount)} {currency}"
            )
            return

        recipient_name = (
            f"@{recipient.username}"
            if recipient.username
            else (recipient.first_name or f"User #{recipient.id}")
        )

        context.user_data["pending_pay"] = {
            "recipient_id": recipient.id,
            "amount": amount,
            "currency": currency,
            "recipient_name": recipient_name,
        }

    await message.reply_text(
        "💸 𝐂𝐎𝐍𝐅𝐈𝐑𝐌 𝐏𝐀𝐘𝐌𝐄𝐍𝐓\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 To : {recipient_name}\n"
        f"💰 Amount : {_format_amount(amount)} {currency}\n\n"
        "Your balance will be transferred only after you confirm.",
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
        context.user_data.pop("pending_pay", None)
        await query.edit_message_text("❌ Payment cancelled.")
        return

    if action[1] != "confirm":
        return

    pending = context.user_data.get("pending_pay")

    if not pending:
        await query.edit_message_text(
            "⚠️ This payment has expired."
        )
        return

    recipient_id = int(pending["recipient_id"])
    amount = int(pending["amount"])
    currency = str(pending.get("currency", "coins")).lower()

    if currency not in CURRENCIES:
        await query.edit_message_text("❌ Invalid currency.")
        context.user_data.pop("pending_pay", None)
        return

    balance_field = CURRENCIES[currency]

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
            context.user_data.pop("pending_pay", None)
            return

        if sender.id == recipient.id:
            await query.edit_message_text(
                "❌ You cannot pay yourself."
            )
            context.user_data.pop("pending_pay", None)
            return

        sender_balance = int(
            getattr(sender, balance_field, 0) or 0
        )

        if sender_balance < amount:
            await query.edit_message_text(
                "❌ Insufficient balance.\n"
                "Your balance changed before confirmation."
            )
            context.user_data.pop("pending_pay", None)
            return

        recipient_balance = int(
            getattr(recipient, balance_field, 0) or 0
        )

        setattr(
            sender,
            balance_field,
            sender_balance - amount,
        )
        setattr(
            recipient,
            balance_field,
            recipient_balance + amount,
        )

        await session.commit()

        new_balance = int(
            getattr(sender, balance_field, 0) or 0
        )

    context.user_data.pop("pending_pay", None)

    recipient_name = pending["recipient_name"]

    await query.edit_message_text(
        "✅ 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 To : {recipient_name}\n"
        f"💰 Sent : {_format_amount(amount)} {currency}\n"
        f"💰 Your new balance : "
        f"{_format_amount(new_balance)} {currency}"
    )


pay_handler = CommandHandler("pay", pay)

pay_callback_handler = CallbackQueryHandler(
    pay_callback,
    pattern=r"^pay:(confirm|cancel):pending$",
)
