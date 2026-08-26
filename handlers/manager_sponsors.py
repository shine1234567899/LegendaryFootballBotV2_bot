from __future__ import annotations

from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import AsyncSessionLocal
from database.models import Base, Club, User


# ==========================================================
# SPONSORS
# ==========================================================

MAX_SPONSORS_PER_CLUB = 3

# Brand: (activation_fee, daily_income)
# All amounts are virtual Coins.
SPONSOR_OFFERS: dict[str, tuple[int, int]] = {
    "Nike": (5_000_000, 500_000),
    "Adidas": (4_500_000, 450_000),
    "Puma": (3_500_000, 350_000),
    "Emirates": (6_000_000, 600_000),
    "Qatar Airways": (6_500_000, 650_000),
    "Pepsi": (4_000_000, 400_000),
    "Coca-Cola": (4_500_000, 450_000),
    "Red Bull": (5_000_000, 500_000),
    "Samsung": (5_500_000, 550_000),
    "Sony": (4_500_000, 450_000),
    "Apple": (7_500_000, 750_000),
    "Microsoft": (6_500_000, 650_000),
    "Mastercard": (5_000_000, 500_000),
    "Visa": (5_000_000, 500_000),
    "EA Sports": (4_000_000, 400_000),
    "Spotify": (4_500_000, 450_000),
    "Amazon": (7_000_000, 700_000),
    "Google": (7_000_000, 700_000),
    "Toyota": (5_000_000, 500_000),
    "Hyundai": (4_000_000, 400_000),
}


class ClubSponsor(Base):
    __tablename__ = "club_sponsors"

    id: Mapped[int] = mapped_column(primary_key=True)

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    activation_fee: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    daily_income: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    duration_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    club: Mapped["Club"] = relationship()


async def _get_manager_club(session, user_id: int):
    return await session.scalar(
        select(Club).where(Club.owner_id == user_id)
    )


async def sponsor_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Open the sponsor list."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        club = await _get_manager_club(session, user.id)

        if club is None:
            await message.reply_text("❌ You don't have a club.")
            return

        result = await session.execute(
            select(ClubSponsor).where(
                ClubSponsor.club_id == club.id,
                ClubSponsor.active.is_(True),
            )
        )
        active = result.scalars().all()

    if len(active) >= MAX_SPONSORS_PER_CLUB:
        await message.reply_text(
            "🤝 𝐒𝐏𝐎𝐍𝐒𝐎𝐑𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❌ Your club already has 3 active sponsors."
        )
        return

    active_names = {s.name.casefold() for s in active}

    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for name, (activation_fee, daily_income) in SPONSOR_OFFERS.items():
        if name.casefold() in active_names:
            continue

        row.append(
            InlineKeyboardButton(
                f"{name} • {activation_fee:,}",
                callback_data=f"sponsor_select:{name}",
            )
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    await message.reply_text(
        "🤝 𝐒𝐏𝐎𝐍𝐒𝐎𝐑 𝐎𝐅𝐅𝐄𝐑𝐒\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Available slots: "
        f"{MAX_SPONSORS_PER_CLUB - len(active)}/{MAX_SPONSORS_PER_CLUB}\n\n"
        "💳 The displayed amount is the activation fee.\n"
        "💰 After payment, the sponsor pays every day.\n\n"
        "Choose a sponsor:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def sponsor_select_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    try:
        sponsor_name = query.data.split(":", 1)[1]
    except (AttributeError, IndexError):
        await query.answer("❌ Invalid sponsor.", show_alert=True)
        return

    offer = SPONSOR_OFFERS.get(sponsor_name)

    if offer is None:
        await query.answer("❌ Sponsor unavailable.", show_alert=True)
        return

    activation_fee, daily_income = offer

    async with AsyncSessionLocal() as session:
        club = await _get_manager_club(
            session,
            query.from_user.id,
        )

        if club is None:
            await query.answer(
                "❌ You don't have a club.",
                show_alert=True,
            )
            return

        result = await session.execute(
            select(ClubSponsor).where(
                ClubSponsor.club_id == club.id,
                ClubSponsor.active.is_(True),
            )
        )
        active = result.scalars().all()

        if len(active) >= MAX_SPONSORS_PER_CLUB:
            await query.answer(
                "❌ Your club already has 3 sponsors.",
                show_alert=True,
            )
            return

        if any(
            sponsor.name.casefold() == sponsor_name.casefold()
            for sponsor in active
        ):
            await query.answer(
                "❌ This sponsor already sponsors your club.",
                show_alert=True,
            )
            return

        manager = await session.get(
            User,
            query.from_user.id,
        )

        if manager is None:
            await query.answer(
                "❌ Manager account not found.",
                show_alert=True,
            )
            return

        if manager.coins < activation_fee:
            await query.answer(
                f"❌ You need {activation_fee:,} Coins.",
                show_alert=True,
            )
            return

        manager.coins -= activation_fee

        now = datetime.now(timezone.utc)

        session.add(
            ClubSponsor(
                club_id=club.id,
                name=sponsor_name,
                activation_fee=activation_fee,
                daily_income=daily_income,
                duration_days=30,
                started_at=now,
                expires_at=now + timedelta(days=30),
                active=True,
            )
        )

        await session.commit()

    await query.answer("✅ Sponsor activated!")

    await query.edit_message_text(
        "🤝 𝐒𝐏𝐎𝐍𝐒𝐎𝐑 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 Sponsor: {sponsor_name}\n"
        f"💳 Activation fee: -{activation_fee:,} Coins\n"
        f"💰 Daily income: +{daily_income:,} Coins/day\n"
        "📅 Contract: 30 days\n\n"
        "✅ Sponsor is now active."
    )


async def sponsors_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Show active sponsors for the manager's club."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        club = await _get_manager_club(session, user.id)

        if club is None:
            await message.reply_text("❌ You don't have a club.")
            return

        result = await session.execute(
            select(ClubSponsor).where(
                ClubSponsor.club_id == club.id,
                ClubSponsor.active.is_(True),
            ).order_by(ClubSponsor.name)
        )
        sponsors = result.scalars().all()

    if not sponsors:
        await message.reply_text(
            "🤝 Your club has no active sponsors.\n"
            "Use /sponsor to choose one."
        )
        return

    text = (
        "🤝 𝐌𝐘 𝐒𝐏𝐎𝐍𝐒𝐎𝐑𝐒\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for sponsor in sponsors:
        text += (
            f"🏢 {sponsor.name}\n"
            f"💳 Activation: {sponsor.activation_fee:,} Coins\n"
            f"💰 +{sponsor.daily_income:,} Coins/day\n"
            f"⏳ Expires: "
            f"{sponsor.expires_at.strftime('%d/%m/%Y')}\n\n"
        )

    await message.reply_text(text)


async def collect_sponsor_income(club_id: int) -> dict[str, int]:
    """
    Pay one daily income for each active sponsor of one club.
    Safe to call repeatedly during the same day.
    """
    paid = 0
    expired = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        manager = await session.scalar(
            select(User)
            .join(Club, Club.owner_id == User.id)
            .where(Club.id == club_id)
        )

        if manager is None:
            return {
                "paid": 0,
                "expired": 0,
                "skipped": 0,
            }

        result = await session.execute(
            select(ClubSponsor).where(
                ClubSponsor.club_id == club_id,
                ClubSponsor.active.is_(True),
            )
        )
        sponsors = result.scalars().all()

        now = datetime.now(timezone.utc)

        for sponsor in sponsors:
            if now >= sponsor.expires_at:
                sponsor.active = False
                expired += 1
                continue

            if (
                sponsor.last_paid_at is not None
                and sponsor.last_paid_at.date() == now.date()
            ):
                skipped += 1
                continue

            manager.coins += sponsor.daily_income
            sponsor.last_paid_at = now
            paid += 1

        await session.commit()

    return {
        "paid": paid,
        "expired": expired,
        "skipped": skipped,
    }


async def pay_all_due_sponsors() -> dict[str, int]:
    """
    Process every club's active sponsors.

    Called by the daily scheduler in main.py.
    """
    paid = 0
    expired = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClubSponsor.club_id).where(
                ClubSponsor.active.is_(True)
            ).distinct()
        )
        club_ids = [row[0] for row in result.all()]

    for club_id in club_ids:
        result = await collect_sponsor_income(club_id)
        paid += result["paid"]
        expired += result["expired"]
        skipped += result["skipped"]

    return {
        "paid": paid,
        "expired": expired,
        "skipped": skipped,
    }


sponsor_handler = CommandHandler(
    "sponsor",
    sponsor_command,
)

sponsors_handler = CommandHandler(
    "sponsors",
    sponsors_command,
)

sponsor_select_callback_handler = CallbackQueryHandler(
    sponsor_select_callback,
    pattern=r"^sponsor_select:.+$",
)
