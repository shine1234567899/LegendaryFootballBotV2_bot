from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import (
    User,
    Club,
    ClubPlayer,
    Player,
    PlayerContract,
)


DEFAULT_SALARY = 100_000
DEFAULT_DURATION_DAYS = 30

SALARY_BY_OVERALL = (
    (95, 2_000_000),
    (90, 1_000_000),
    (85, 500_000),
    (80, 250_000),
    (0, 100_000),
)

def salary_from_overall(overall: int) -> int:
    for minimum, salary in SALARY_BY_OVERALL:
        if overall >= minimum:
            return salary
    return 100_000


async def _get_manager_club(session, user_id: int):
    result = await session.execute(
        select(Club).where(Club.owner_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_club_player(session, club_id: int, player_name: str):
    result = await session.execute(
        select(ClubPlayer, Player)
        .join(Player, Player.id == ClubPlayer.player_id)
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
            Player.name.ilike(player_name.strip()),
        )
    )
    return result.first()


async def contract_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        club = await _get_manager_club(session, user.id)

        if club is None:
            await message.reply_text(
                "❌ You don't have a club yet.\n"
                "Use /createclub first."
            )
            return

        result = await session.execute(
            select(PlayerContract, Player)
            .join(Player, Player.id == PlayerContract.player_id)
            .where(
                PlayerContract.club_id == club.id,
                PlayerContract.active.is_(True),
            )
            .order_by(Player.name)
        )

        rows = result.all()

    if not rows:
        await message.reply_text(
            "📄 No active player contracts yet.\n\n"
            "Use:\n"
            "/contract Player Name [salary] [days]"
        )
        return

    text = (
        "📄 𝐂𝐋𝐔𝐁 𝐂𝐎𝐍𝐓𝐑𝐀𝐂𝐓𝐒\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for contract, player in rows:
        expires = contract.expires_at.strftime("%d/%m/%Y")
        text += (
            f"⚽ {player.name}\n"
            f"💰 Salary: {contract.salary:,} Coins/day\n"
            f"📅 Duration: {contract.duration_days} days\n"
            f"⏳ Expires: {expires}\n\n"
        )

    await message.reply_text(text)


async def create_contract_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if len(context.args) < 1:
        await message.reply_text(
            "📄 Usage:\n"
            "/contract Player Name [salary] [days]\n\n"
            "Example:\n"
            "/contract Cristiano Ronaldo 500000 30"
        )
        return

    # The last two arguments are optional numeric values.
    args = context.args[:]
    salary = None
    duration_days = DEFAULT_DURATION_DAYS

    explicit_salary = False
    if len(args) >= 2:
        try:
            salary = int(args[-2])
            duration_days = int(args[-1])
            player_name = " ".join(args[:-2]).strip()
            explicit_salary = True
        except ValueError:
            player_name = " ".join(args).strip()
    else:
        player_name = " ".join(args).strip()

    if not player_name:
        await message.reply_text("❌ Player name is required.")
        return

    if duration_days <= 0:
        await message.reply_text(
            "❌ Duration must be greater than 0."
        )
        return

    async with AsyncSessionLocal() as session:
        club = await _get_manager_club(session, user.id)

        if club is None:
            await message.reply_text(
                "❌ You don't have a club yet."
            )
            return

        row = await _get_club_player(
            session,
            club.id,
            player_name,
        )

        if row is None:
            await message.reply_text(
                "❌ This player is not currently in your club."
            )
            return

        _, player = row

        # If the manager does not explicitly provide a salary, calculate it
        # from the player's Overall. Explicit negotiated salaries are kept.
        if not explicit_salary:
            salary = salary_from_overall(int(player.overall or 0))

        if salary <= 0:
            await message.reply_text(
                "❌ Salary must be greater than 0."
            )
            return

        existing = await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club.id,
                PlayerContract.player_id == player.id,
                PlayerContract.active.is_(True),
            )
        )

        now = datetime.now(timezone.utc)
        expires = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        from datetime import timedelta
        expires += timedelta(days=duration_days)

        if existing is not None:
            existing.salary = salary
            existing.duration_days = duration_days
            existing.started_at = now
            existing.expires_at = expires
            existing.last_paid_at = None
            existing.active = True
        else:
            session.add(
                PlayerContract(
                    club_id=club.id,
                    player_id=player.id,
                    salary=salary,
                    duration_days=duration_days,
                    started_at=now,
                    expires_at=expires,
                    active=True,
                )
            )

        await session.commit()

    await message.reply_text(
        "✅ 𝐂𝐎𝐍𝐓𝐑𝐀𝐂𝐓 𝐒𝐈𝐆𝐍𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ Player: {player.name}\n"
        f"💰 Salary: {salary:,} Coins/day\n"
        f"📅 Duration: {duration_days} days\n\n"
        "🤝 The player is now under contract."
    )


async def contract_pay_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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
            select(PlayerContract, Player)
            .join(Player, Player.id == PlayerContract.player_id)
            .where(
                PlayerContract.club_id == club.id,
                PlayerContract.active.is_(True),
            )
            .order_by(Player.name)
        )
        rows = result.all()

    if not rows:
        await message.reply_text(
            "❌ Your club has no active contracts."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"💰 Pay {player.name}",
                callback_data=f"contract_pay:{contract.id}",
            )
        ]
        for contract, player in rows
    ]

    await message.reply_text(
        "💰 𝐏𝐀𝐘 𝐏𝐋𝐀𝐘𝐄𝐑 𝐒𝐀𝐋𝐀𝐑𝐈𝐄𝐒\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose a player:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def contract_pay_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        contract_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return

    async with AsyncSessionLocal() as session:
        contract = await session.get(PlayerContract, contract_id)

        if contract is None or not contract.active:
            await query.answer(
                "❌ Contract is no longer active.",
                show_alert=True,
            )
            return

        club = await session.get(Club, contract.club_id)

        if club is None or club.owner_id != query.from_user.id:
            await query.answer(
                "❌ This contract does not belong to you.",
                show_alert=True,
            )
            return

        manager = await session.get(User, club.owner_id)
        player = await session.get(Player, contract.player_id)

        if manager is None or player is None:
            await query.answer(
                "❌ Contract data is incomplete.",
                show_alert=True,
            )
            return

        now = datetime.now(timezone.utc)

        if contract.expires_at <= now:
            contract.active = False

            ownership = await session.scalar(
                select(ClubPlayer).where(
                    ClubPlayer.club_id == club.id,
                    ClubPlayer.player_id == player.id,
                    ClubPlayer.is_current.is_(True),
                )
            )

            if ownership:
                ownership.is_current = False
                ownership.left_at = now

            await session.commit()

            await query.answer(
                "❌ Contract expired. Player left the club.",
                show_alert=True,
            )
            return

        if (
            contract.last_paid_at is not None
            and contract.last_paid_at.date() == now.date()
        ):
            await query.answer(
                "✅ This salary has already been paid today.",
                show_alert=True,
            )
            return

        if manager.coins < contract.salary:
            contract.active = False

            ownership = await session.scalar(
                select(ClubPlayer).where(
                    ClubPlayer.club_id == club.id,
                    ClubPlayer.player_id == player.id,
                    ClubPlayer.is_current.is_(True),
                )
            )

            if ownership:
                ownership.is_current = False
                ownership.left_at = now

            await session.commit()

            await query.answer(
                "❌ Not enough Coins. The player has left the club.",
                show_alert=True,
            )
            return

        manager.coins -= contract.salary
        contract.last_paid_at = now

        await session.commit()

    await query.answer(
        f"✅ {player.name}'s salary was paid.",
        show_alert=True,
    )


contract_handler = CommandHandler(
    "contracts",
    contract_command,
)

create_contract_handler = CommandHandler(
    "contract",
    create_contract_command,
)

contract_pay_handler = CommandHandler(
    "paysalary",
    contract_pay_command,
)

contract_pay_callback_handler = CallbackQueryHandler(
    contract_pay_callback,
    pattern=r"^contract_pay:\d+$",
)
