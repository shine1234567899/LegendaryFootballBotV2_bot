from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    ClubPlayer,
    Player,
    PlayerContract,
    User,
)

INITIAL_SALARY = 100_000
INITIAL_DURATION_DAYS = 30

# Daily salary is determined by the player's Overall.
# Edit these thresholds if you want a different economy.
SALARY_BY_OVERALL = (
    (95, 2_000_000),
    (90, 1_000_000),
    (85, 500_000),
    (80, 250_000),
    (0, 100_000),
)


def initial_contract_salary(player: Player) -> int:
    """Return the automatic daily salary based on Overall."""
    overall = int(getattr(player, "overall", 0) or 0)
    for minimum_overall, salary in SALARY_BY_OVERALL:
        if overall >= minimum_overall:
            return salary
    return INITIAL_SALARY


async def ensure_player_contract(session, club_id: int, player_id: int):
    """
    Guarantee one active initial contract for a current squad player.
    Safe to call repeatedly.
    """
    ownership = await session.scalar(
        select(ClubPlayer).where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.player_id == player_id,
            ClubPlayer.is_current.is_(True),
        )
    )
    if ownership is None:
        return None

    existing = await session.scalar(
        select(PlayerContract).where(
            PlayerContract.club_id == club_id,
            PlayerContract.player_id == player_id,
            PlayerContract.active.is_(True),
        )
    )
    if existing is not None:
        return existing

    player = await session.get(Player, player_id)
    if player is None:
        return None

    now = datetime.now(timezone.utc)
    contract = PlayerContract(
        club_id=club_id,
        player_id=player_id,
        salary=initial_contract_salary(player),
        duration_days=INITIAL_DURATION_DAYS,
        started_at=now,
        expires_at=now + timedelta(days=INITIAL_DURATION_DAYS),
        last_paid_at=None,
        active=True,
    )
    session.add(contract)
    await session.flush()
    return contract


async def ensure_all_current_players_have_contracts() -> int:
    """Backfill missing contracts for all players currently in squads."""
    created = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClubPlayer).where(ClubPlayer.is_current.is_(True))
        )

        for ownership in result.scalars().all():
            existing = await session.scalar(
                select(PlayerContract).where(
                    PlayerContract.club_id == ownership.club_id,
                    PlayerContract.player_id == ownership.player_id,
                    PlayerContract.active.is_(True),
                )
            )

            if existing is None:
                contract = await ensure_player_contract(
                    session,
                    ownership.club_id,
                    ownership.player_id,
                )
                if contract is not None:
                    created += 1

        await session.commit()

    return created


async def create_player_contract(
    club_id: int,
    player_id: int,
    salary: int,
    duration_days: int = INITIAL_DURATION_DAYS,
):
    """
    Create/renew a contract.

    IMPORTANT: a negotiated salary must be strictly greater than
    the player's current salary.
    """
    if salary <= 0 or duration_days <= 0:
        return False, "INVALID_VALUES", None

    async with AsyncSessionLocal() as session:
        ownership = await session.scalar(
            select(ClubPlayer).where(
                ClubPlayer.club_id == club_id,
                ClubPlayer.player_id == player_id,
                ClubPlayer.is_current.is_(True),
            )
        )
        if ownership is None:
            return False, "PLAYER_NOT_IN_SQUAD", None

        contract = await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club_id,
                PlayerContract.player_id == player_id,
                PlayerContract.active.is_(True),
            )
        )

        if contract is None:
            contract = await ensure_player_contract(
                session, club_id, player_id
            )

        if contract is None:
            return False, "CONTRACT_NOT_CREATED", None

        old_salary = contract.salary

        if salary <= old_salary:
            return False, "SALARY_TOO_LOW", old_salary

        now = datetime.now(timezone.utc)
        contract.salary = salary
        contract.duration_days = duration_days
        contract.started_at = now
        contract.expires_at = now + timedelta(days=duration_days)
        contract.last_paid_at = None
        contract.active = True

        await session.commit()
        return True, "SIGNED", old_salary


async def get_player_contract(club_id: int, player_id: int):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club_id,
                PlayerContract.player_id == player_id,
                PlayerContract.active.is_(True),
            )
        )


async def _remove_player_from_squad(session, contract, now):
    ownership = await session.scalar(
        select(ClubPlayer).where(
            ClubPlayer.club_id == contract.club_id,
            ClubPlayer.player_id == contract.player_id,
            ClubPlayer.is_current.is_(True),
        )
    )
    if ownership is not None:
        ownership.is_current = False
        ownership.left_at = now


async def pay_player_salary(contract_id: int):
    async with AsyncSessionLocal() as session:
        contract = await session.get(PlayerContract, contract_id)
        if contract is None or not contract.active:
            return False, "CONTRACT_NOT_FOUND"

        club = await session.get(Club, contract.club_id)
        if club is None:
            contract.active = False
            await session.commit()
            return False, "CLUB_NOT_FOUND"

        manager = await session.get(User, club.owner_id)
        if manager is None:
            return False, "MANAGER_NOT_FOUND"

        now = datetime.now(timezone.utc)

        if now >= contract.expires_at:
            contract.active = False
            await _remove_player_from_squad(session, contract, now)
            await session.commit()
            return False, "CONTRACT_EXPIRED"

        if (
            contract.last_paid_at is not None
            and contract.last_paid_at.date() == now.date()
        ):
            return False, "ALREADY_PAID"

        if manager.coins < contract.salary:
            contract.active = False
            await _remove_player_from_squad(session, contract, now)
            await session.commit()
            return False, "INSUFFICIENT_COINS"

        manager.coins -= contract.salary
        contract.last_paid_at = now
        await session.commit()
        return True, "PAID"


async def pay_all_due_salaries():
    paid = 0
    left = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PlayerContract).where(
                PlayerContract.active.is_(True)
            )
        )

        now = datetime.now(timezone.utc)

        for contract in result.scalars().all():
            if now >= contract.expires_at:
                contract.active = False
                await _remove_player_from_squad(session, contract, now)
                left += 1
                continue

            if (
                contract.last_paid_at is not None
                and contract.last_paid_at.date() == now.date()
            ):
                skipped += 1
                continue

            club = await session.get(Club, contract.club_id)
            if club is None:
                contract.active = False
                left += 1
                continue

            manager = await session.get(User, club.owner_id)
            if manager is None:
                skipped += 1
                continue

            if manager.coins < contract.salary:
                contract.active = False
                await _remove_player_from_squad(session, contract, now)
                left += 1
                continue

            manager.coins -= contract.salary
            contract.last_paid_at = now
            paid += 1

        await session.commit()

    return {
        "paid": paid,
        "left": left,
        "skipped": skipped,
    }



async def sync_default_salaries() -> int:
    """Update legacy 100,000/day contracts to the current Overall salary tier."""
    changed = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PlayerContract, Player)
            .join(Player, Player.id == PlayerContract.player_id)
            .where(PlayerContract.active.is_(True), PlayerContract.salary == INITIAL_SALARY)
        )
        for contract, player in result.all():
            new_salary = initial_contract_salary(player)
            if new_salary != contract.salary:
                contract.salary = new_salary
                changed += 1
        await session.commit()
    return changed

async def contracts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show every current squad player and his active contract."""
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    async with AsyncSessionLocal() as session:
        club = await session.scalar(
            select(Club).where(Club.owner_id == user.id)
        )
        if club is None:
            await message.reply_text("❌ Create your club first.")
            return

        result = await session.execute(
            select(ClubPlayer, Player, PlayerContract)
            .join(Player, Player.id == ClubPlayer.player_id)
            .outerjoin(
                PlayerContract,
                (PlayerContract.club_id == Club.id)
                & (PlayerContract.player_id == Player.id)
                & (PlayerContract.active.is_(True)),
            )
            .where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
            .order_by(Player.overall.desc(), Player.name.asc())
        )
        rows = result.all()

    if not rows:
        await message.reply_text("📭 Your squad has no players.")
        return

    lines = [
        "📄 𝐌𝐘 𝐏𝐋𝐀𝐘𝐄𝐑 𝐂𝐎𝐍𝐓𝐑𝐀𝐂𝐓𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🏟️ {club.name}",
        "",
    ]

    for _, player, contract in rows:
        salary = (
            contract.salary
            if contract is not None
            else initial_contract_salary(player)
        )
        status = "ACTIVE" if contract is not None else "MISSING"

        lines.append(
            f"⚽ {player.name} • {player.overall} OVR\n"
            f"   💰 {salary:,} Coins/day\n"
            f"   📅 {contract.duration_days if contract else INITIAL_DURATION_DAYS} days\n"
            f"   🟢 {status}\n"
        )

    text = "\n".join(lines)
    if len(text) <= 3900:
        await message.reply_text(text)
        return

    current = ""
    for block in lines:
        candidate = (current + "\n" + block).strip()
        if len(candidate) > 3800:
            await message.reply_text(current)
            current = block
        else:
            current = candidate
    if current:
        await message.reply_text(current)


contracts_handler = CommandHandler("contracts", contracts_command)
