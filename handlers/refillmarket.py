import random
import csv
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import select

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import Player, TransferListing


MARKET_SIZE = 5
TARGET_TRANSFER_PLAYERS = 500

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "data" / "fc26_players.csv"


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

        # --------------------------------------------------
        # Ensure CSV players exist in Player
        # --------------------------------------------------
        # Existing Player rows are NEVER deleted or modified.
        # New CSV rows are inserted only when their name does
        # not already exist, preventing duplicate players.

        if CSV_FILE.exists():
            csv_result = await session.execute(
                select(Player.name)
            )
            existing_names = {
                (name or "").strip().casefold()
                for name in csv_result.scalars().all()
                if name
            }

            try:
                with open(
                    CSV_FILE,
                    "r",
                    encoding="utf-8-sig",
                    newline="",
                ) as file:
                    rows = csv.DictReader(file)

                    for row in rows:
                        name = (row.get("name") or "").strip()

                        if not name or name.casefold() in existing_names:
                            continue

                        try:
                            country = (row.get("country") or "").strip()
                            position = (row.get("position") or "").strip()
                            age = int(row["age"])
                            overall = int(row["overall"])
                            potential = int(row["potential"])
                            value = int(row["value"])
                        except (KeyError, ValueError, TypeError):
                            continue

                        session.add(
                            Player(
                                name=name,
                                country=country,
                                position=position,
                                age=age,
                                overall=overall,
                                potential=potential,
                                value=value,
                                image_file_id=None,
                                starter_pool=False,
                            )
                        )

                        existing_names.add(name.casefold())

                await session.flush()

            except (OSError, csv.Error):
                # If the CSV cannot be read, continue with players
                # already present in the database.
                pass

        # --------------------------------------------------
        # Eligible players
        # --------------------------------------------------
        # Includes players imported from CSV.
        # OVR >= 78 and not already listed as available.
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