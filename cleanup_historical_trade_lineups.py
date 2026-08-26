from database.database import AsyncSessionLocal
from database.models import Trade, Club, SavedLineup, SavedLineupPlayer
from sqlalchemy import select, delete


async def cleanup_historical_traded_players():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Trade).where(
                Trade.status.in_(["accepted", "ACCEPTED"])
            )
        )
        trades = result.scalars().all()

        removed = 0

        for trade in trades:
            sender_club = await session.scalar(
                select(Club).where(Club.owner_id == trade.sender_id)
            )
            receiver_club = await session.scalar(
                select(Club).where(Club.owner_id == trade.receiver_id)
            )

            if sender_club is not None:
                sender_lineups = select(SavedLineup.id).where(
                    SavedLineup.club_id == sender_club.id
                )
                result = await session.execute(
                    delete(SavedLineupPlayer).where(
                        SavedLineupPlayer.saved_lineup_id.in_(sender_lineups),
                        SavedLineupPlayer.player_id == trade.offered_player_id,
                    )
                )
                removed += result.rowcount or 0

            if receiver_club is not None:
                receiver_lineups = select(SavedLineup.id).where(
                    SavedLineup.club_id == receiver_club.id
                )
                result = await session.execute(
                    delete(SavedLineupPlayer).where(
                        SavedLineupPlayer.saved_lineup_id.in_(receiver_lineups),
                        SavedLineupPlayer.player_id == trade.requested_player_id,
                    )
                )
                removed += result.rowcount or 0

        await session.commit()
        print(f"✅ Historical trade lineup cleanup: {removed} lineup entries removed.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(cleanup_historical_traded_players())
