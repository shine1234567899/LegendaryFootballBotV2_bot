from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import StarPayment, User


# ==========================================================
# TELEGRAM STARS SHOP
# ==========================================================
#
# /achat
#
# Base pack:
#   50 Telegram Stars -> 60,000 Coins
#   50 Telegram Stars -> 200 Gems
#
# Payment is processed with Telegram Stars (XTR).
# Credits are granted only after Telegram confirms payment.
# Each Telegram charge ID is stored so a successful payment
# cannot be credited twice.
# ==========================================================

PRODUCTS = {
    "coins_50": {"label": "500,000 Coins", "description": "Get 500,000 Coins for 50 Telegram Stars.", "stars": 50, "coins": 500_000, "gems": 0},
    "coins_100": {"label": "1,200,000 Coins", "description": "Get 1,200,000 Coins for 100 Telegram Stars.", "stars": 100, "coins": 1_200_000, "gems": 0},
    "coins_200": {"label": "2,600,000 Coins", "description": "Get 2,600,000 Coins for 200 Telegram Stars.", "stars": 200, "coins": 2_600_000, "gems": 0},
    "coins_500": {"label": "7,000,000 Coins", "description": "Get 7,000,000 Coins for 500 Telegram Stars.", "stars": 500, "coins": 7_000_000, "gems": 0},
    "coins_1000": {"label": "16,000,000 Coins", "description": "Get 16,000,000 Coins for 1000 Telegram Stars.", "stars": 1000, "coins": 16_000_000, "gems": 0},
    "gems_50": {"label": "200 Gems", "description": "Get 200 Gems for 50 Telegram Stars.", "stars": 50, "coins": 0, "gems": 200},
}


PAYLOAD_PREFIX = "lfb_achat:"


def _shop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🪙 500,000 Coins — ⭐ 50", callback_data=f"{PAYLOAD_PREFIX}coins_50")],
            [InlineKeyboardButton("🪙 1,200,000 Coins — ⭐ 100", callback_data=f"{PAYLOAD_PREFIX}coins_100")],
            [InlineKeyboardButton("🪙 2,600,000 Coins — ⭐ 200", callback_data=f"{PAYLOAD_PREFIX}coins_200")],
            [InlineKeyboardButton("🪙 7,000,000 Coins — ⭐ 500", callback_data=f"{PAYLOAD_PREFIX}coins_500")],
            [InlineKeyboardButton("🪙 16,000,000 Coins — ⭐ 1000", callback_data=f"{PAYLOAD_PREFIX}coins_1000")],
            [InlineKeyboardButton("💎 200 Gems — ⭐ 50", callback_data=f"{PAYLOAD_PREFIX}gems_50")],
        ]
    )


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔙 Back",
                    callback_data=f"{PAYLOAD_PREFIX}back",
                )
            ]
        ]
    )


def _shop_text() -> str:
    return (
        "🛒 𝐒𝐓𝐀𝐑𝐒 𝐒𝐇𝐎𝐏\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose what you want to buy:\n\n"
        "🪙 500,000 Coins — ⭐ 50 Stars\n"
        "🪙 1,200,000 Coins — ⭐ 100 Stars\n"
        "🪙 2,600,000 Coins — ⭐ 200 Stars\n"
        "🪙 7,000,000 Coins — ⭐ 500 Stars\n"
        "🪙 16,000,000 Coins — ⭐ 1000 Stars\n"
        "💎 200 Gems — ⭐ 50 Stars"
    )

async def achat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    await message.reply_text(_shop_text(), reply_markup=_shop_keyboard())


async def achat_callback(
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

    action = str(query.data).split(":", 1)[1]

    if action == "back":
        await query.edit_message_text(_shop_text(), reply_markup=_shop_keyboard())
        return

    product = PRODUCTS.get(action)

    if product is None:
        return

    user = query.from_user

    # A short payload is safer and easier to validate than trusting
    # arbitrary callback data during the payment flow.
    payload = f"{PAYLOAD_PREFIX}{action}:{user.id}"

    await query.message.reply_text(
        (
            "⭐ 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐌 𝐒𝐓𝐀𝐑𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Product: {product['label']}\n"
            f"Price: ⭐ {product['stars']} Stars\n\n"
            "Press the payment button below to continue."
        ),
        reply_markup=_back_keyboard(),
    )

    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=product["label"],
        description=product["description"],
        payload=payload,
        currency="XTR",
        prices=[
            LabeledPrice(
                label=product["label"],
                amount=product["stars"],
            )
        ],
    )


async def precheckout_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.pre_checkout_query

    if query is None:
        return

    payload = str(query.invoice_payload)

    if not payload.startswith(PAYLOAD_PREFIX):
        await query.answer(
            ok=False,
            error_message="Invalid payment.",
        )
        return

    raw = payload[len(PAYLOAD_PREFIX):]
    parts = raw.split(":")

    if len(parts) != 2:
        await query.answer(
            ok=False,
            error_message="Invalid payment.",
        )
        return

    product_id, user_id_text = parts

    product = PRODUCTS.get(product_id)

    try:
        payload_user_id = int(user_id_text)
    except ValueError:
        product = None
        payload_user_id = 0

    if product is None or payload_user_id != query.from_user.id:
        await query.answer(
            ok=False,
            error_message="This payment does not belong to your account.",
        )
        return

    if query.currency != "XTR" or query.total_amount != product["stars"]:
        await query.answer(
            ok=False,
            error_message="Invalid Stars amount.",
        )
        return

    await query.answer(ok=True)


async def successful_payment_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    telegram_user = update.effective_user

    if (
        message is None
        or telegram_user is None
        or message.successful_payment is None
    ):
        return

    payment = message.successful_payment
    payload = str(payment.invoice_payload)

    if not payload.startswith(PAYLOAD_PREFIX):
        return

    raw = payload[len(PAYLOAD_PREFIX):]
    parts = raw.split(":")

    if len(parts) != 2:
        return

    product_id, user_id_text = parts

    try:
        payload_user_id = int(user_id_text)
    except ValueError:
        return

    if payload_user_id != telegram_user.id:
        return

    product = PRODUCTS.get(product_id)

    if (
        product is None
        or payment.currency != "XTR"
        or payment.total_amount != product["stars"]
    ):
        return

    charge_id = payment.telegram_payment_charge_id

    async with AsyncSessionLocal() as session:
        # Persistent idempotency check.
        existing = await session.execute(
            select(StarPayment).where(
                StarPayment.telegram_payment_charge_id
                == charge_id
            )
        )

        if existing.scalar_one_or_none() is not None:
            return

        user = await session.get(User, telegram_user.id)

        if user is None:
            return

        if product["coins"]:
            user.coins += product["coins"]

        if product["gems"]:
            user.gems += product["gems"]

        session.add(
            StarPayment(
                telegram_payment_charge_id=charge_id,
                user_id=telegram_user.id,
                product=product_id,
                stars=product["stars"],
                coins=product["coins"],
                gems=product["gems"],
            )
        )

        await session.commit()

        balance_text = (
            f"🪙 Coins: {user.coins:,}\n"
            f"💎 Gems: {user.gems:,}"
        )

    await message.reply_text(
        (
            "✅ 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⭐ Stars spent: {product['stars']}\n"
            f"📦 Received: {product['label']}\n\n"
            f"{balance_text}"
        )
    )


achat_handler = CommandHandler(
    "achat",
    achat,
)

achat_callback_handler = CallbackQueryHandler(
    achat_callback,
    pattern=r"^lfb_achat:(coins_50|coins_100|coins_200|coins_500|coins_1000|gems_50|gems_100|gems_200|gems_500|gems_1000|back)$",
)

precheckout_handler = PreCheckoutQueryHandler(
    precheckout_callback,
)

successful_payment_handler = MessageHandler(
    filters.SUCCESSFUL_PAYMENT,
    successful_payment_callback,
)