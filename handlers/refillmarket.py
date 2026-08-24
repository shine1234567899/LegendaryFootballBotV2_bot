import random
from datetime import datetime, timezone

from sqlalchemy import select

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import Player, TransferListing


MARKET_SIZE = 5


async def refill_market(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message is None or update.effective_user is None:
        return

    # 🔐 OWNER ONLY
    if update.effective_user.id not in OWNER_IDS:
        await update.message.reply_text(
            "❌ You are not authorized to use this command."
        )
        return

    async with AsyncSessionLocal() as session:

        # Joueurs déjà présents sur le marché
        listed_result = await session.execute(
            select(TransferListing.player_id).where(
                TransferListing.status == "available"
            )
        )

        listed_ids = set(listed_result.scalars().all())

        # Joueurs éligibles :
        # - tous les joueurs présents dans la table Player
        #   (y compris ceux importés depuis le CSV)
        # - OVR >= 78
        # - pas déjà disponibles sur le marché
        #
        # IMPORTANT :
        # Les joueurs importés depuis le CSV peuvent avoir
        # starter_pool=True. On ne doit donc PAS les exclure ici.
        if listed_ids:
            result = await session.execute(
                select(Player).where(
                    Player.overall >= 78,
                    ~Player.id.in_(listed_ids),
                )
            )
        else:
            result = await session.execute(
                select(Player).where(
                    Player.overall >= 78,
                )
            )

        candidates = result.scalars().all()

        if not candidates:
            await update.message.reply_text(
                "❌ No eligible players are available."
            )
            return

        # Mélange pour avoir des joueurs différents
        random.shuffle(candidates)

        selected = candidates[:MARKET_SIZE]

        added = []

        for player in selected:

            listing = TransferListing(
                player_id=player.id,
                price=player.value,
                currency="COINS",
                status="available",
                listed_at=datetime.now(timezone.utc),
                sold_at=None,
            )

            session.add(listing)

            added.append(player)

        await session.commit()

    lines = [
        "🔥━━━━━━━━━━━━━━━━━━━━🔥",
        "      𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗠𝗔𝗥𝗞𝗘𝗧",
        "🔥━━━━━━━━━━━━━━━━━━━━🔥",
        "",
        f"✅ {len(added)} player(s) added",
        "",
    ]

    for player in added:
        lines.append(
            f"⚽ {player.name}\n"
            f"⭐ OVR {player.overall} • "
            f"{player.position} • "
            f"🌍 {player.country}\n"
            f"💰 {player.value:,} Coins\n"
        )

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━",
        f"📊 Market: {len(added)}/{MARKET_SIZE}",
    ])

    await update.message.reply_text(
        "\n".join(lines)
    )


refill_market_handler = CommandHandler(
    "refillmarket",
    refill_market,
)