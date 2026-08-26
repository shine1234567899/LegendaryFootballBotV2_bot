from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models import (
    Base,
    Club,
    ClubPlayer,
    Player,
    PlayerContract,
    User,
)
from database.database import AsyncSessionLocal


async def create_player_contract(
    club_id: int,
    player_id: int,
    salary: int = 100_000,
    duration_days: int = 30,
) -> bool:
    """Create or replace the active contract for a player in a club."""

    if salary <= 0 or duration_days <= 0:
        return False

    async with AsyncSessionLocal() as session:
        ownership = await session.scalar(
            select(ClubPlayer).where(
                ClubPlayer.club_id == club_id,
                ClubPlayer.player_id == player_id,
                ClubPlayer.is_current.is_(True),
            )
        )

        if ownership is None:
            return False

        existing = await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club_id,
                PlayerContract.player_id == player_id,
                PlayerContract.active.is_(True),
            )
        )

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=duration_days)

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
                    club_id=club_id,
                    player_id=player_id,
                    salary=salary,
                    duration_days=duration_days,
                    started_at=now,
                    expires_at=expires,
                    active=True,
                )
            )

        await session.commit()
        return True


async def get_player_contract(
    club_id: int,
    player_id: int,
):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club_id,
                PlayerContract.player_id == player_id,
                PlayerContract.active.is_(True),
            )
        )


async def terminate_player_contract(
    club_id: int,
    player_id: int,
) -> bool:
    async with AsyncSessionLocal() as session:
        contract = await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club_id,
                PlayerContract.player_id == player_id,
                PlayerContract.active.is_(True),
            )
        )

        if contract is None:
            return False

        contract.active = False
        await session.commit()
        return True


async def pay_player_salary(
    contract_id: int,
) -> tuple[bool, str]:
    """
    Pay one daily salary.

    The manager must have enough Coins.
    Payment is never made with Gems.
    """

    async with AsyncSessionLocal() as session:
        contract = await session.get(
            PlayerContract,
            contract_id,
        )

        if contract is None or not contract.active:
            return False, "CONTRACT_NOT_FOUND"

        club = await session.get(
            Club,
            contract.club_id,
        )

        if club is None:
            contract.active = False
            await session.commit()
            return False, "CLUB_NOT_FOUND"

        manager = await session.get(
            User,
            club.owner_id,
        )

        if manager is None:
            return False, "MANAGER_NOT_FOUND"

        now = datetime.now(timezone.utc)

        if now >= contract.expires_at:
            contract.active = False

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

            await session.commit()
            return False, "CONTRACT_EXPIRED"

        # Prevent paying twice during the same UTC day.
        if (
            contract.last_paid_at is not None
            and contract.last_paid_at.date() == now.date()
        ):
            return False, "ALREADY_PAID"

        if manager.coins < contract.salary:
            # No coins => player leaves the club.
            contract.active = False

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

            await session.commit()
            return False, "INSUFFICIENT_COINS"

        manager.coins -= contract.salary
        contract.last_paid_at = now

        await session.commit()
        return True, "PAID"


async def pay_all_due_salaries() -> dict[str, int]:
    """
    Process all active contracts once.

    Intended to be called by a daily scheduled job.
    """

    paid = 0
    left = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PlayerContract).where(
                PlayerContract.active.is_(True)
            )
        )
        contracts = result.scalars().all()

        now = datetime.now(timezone.utc)

        for contract in contracts:
            if now >= contract.expires_at:
                contract.active = False

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

                left += 1
                continue

            if (
                contract.last_paid_at is not None
                and contract.last_paid_at.date() == now.date()
            ):
                skipped += 1
                continue

            club = await session.get(
                Club,
                contract.club_id,
            )

            if club is None:
                contract.active = False
                left += 1
                continue

            manager = await session.get(
                User,
                club.owner_id,
            )

            if manager is None:
                contract.active = False
                left += 1
                continue

            if manager.coins < contract.salary:
                contract.active = False

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
