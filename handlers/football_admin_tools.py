"""
Legendary Football — Match & Market Admin Tools

Commands prepared for the existing football bot:

1) /cancelpending
   Manager command.
   Cancels EVERY pending friendly invitation involving the
   manager, including invitations created before the command.

   Usage:
       /cancelpending
       /cancelpending @manager

   If no username is supplied, the command acts on the manager
   who executes it.

2) /clearmarket
   OWNER ONLY.
   Removes every currently available transfer-market listing,
   while keeping the Player records intact.

   CSV players are NOT deleted from Player. If a player from
   fc26_players.csv is missing from Player, it is imported again.
   Therefore /refillmarket can draw those same CSV players again.

IMPORTANT:
- main.py is intentionally NOT modified.
- This module uses the project's current CSV friendly-match
  storage and SQLAlchemy transfer-market storage.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import Player, TransferListing


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FRIENDLY_FILE = BASE_DIR / "data" / "friendly_matches.csv"

CSV_PLAYERS_FILE = BASE_DIR / "data" / "fc26_players.csv"


# ============================================================
# FRIENDLY MATCH CSV
# ============================================================

FRIENDLY_FIELDS = [
    "match_id",
    "host_id",
    "host_username",
    "opponent_id",
    "opponent_username",
    "status",
    "chat_id",
    "created_at",
]


def _ensure_friendly_file() -> None:
    FRIENDLY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if FRIENDLY_FILE.exists():
        return

    with FRIENDLY_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FRIENDLY_FIELDS,
        )
        writer.writeheader()


def _read_friendly_matches() -> list[dict]:
    _ensure_friendly_file()

    with FRIENDLY_FILE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def _write_friendly_matches(
    matches: list[dict],
) -> None:

    _ensure_friendly_file()

    # Preserve columns from the current file if it contains
    # additional fields used by a newer match_manager.py.
    fieldnames = list(FRIENDLY_FIELDS)

    if matches:
        for key in matches[0].keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with FRIENDLY_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(matches)


def _normalize_username(
    username: str,
) -> str:

    username = str(
        username or ""
    ).strip()

    if username.startswith("@"):
        username = username[1:]

    return username.casefold()


def _is_pending(
    match: dict,
) -> bool:

    return (
        str(
            match.get("status", "")
        ).strip().upper()
        == "PENDING"
    )


def _manager_is_in_match(
    match: dict,
    username: str,
) -> bool:

    username = _normalize_username(
        username
    )

    host = _normalize_username(
        match.get(
            "host_username",
            "",
        )
    )

    opponent = _normalize_username(
        match.get(
            "opponent_username",
            "",
        )
    )

    return username in {
        host,
        opponent,
    }


# ============================================================
# CANCEL ALL PENDING FOR A MANAGER
# ============================================================

def cancel_all_pending_for_manager(
    username: str,
) -> dict:
    """
    Cancel ALL PENDING friendly invitations involving username.

    There is deliberately NO date restriction.
    Old pending invitations are therefore cancelled too.
    """

    username = _normalize_username(
        username
    )

    if not username:
        return {
            "success": False,
            "cancelled": 0,
            "message": (
                "❌ Invalid manager username."
            ),
        }

    matches = _read_friendly_matches()

    cancelled = 0
    affected_matches = []

    now = datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )

    for match in matches:

        if not _is_pending(match):
            continue

        if not _manager_is_in_match(
            match,
            username,
        ):
            continue

        match["status"] = "CANCELLED"

        # If the current CSV version has these columns,
        # keep useful audit information.
        if "cancelled_at" in match:
            match["cancelled_at"] = now

        if "updated_at" in match:
            match["updated_at"] = now

        cancelled += 1

        affected_matches.append(
            {
                "match_id": match.get(
                    "match_id",
                    "",
                ),
                "host_username": match.get(
                    "host_username",
                    "",
                ),
                "opponent_username": match.get(
                    "opponent_username",
                    "",
                ),
            }
        )

    if cancelled:
        _write_friendly_matches(
            matches
        )

    return {
        "success": True,
        "manager": username,
        "cancelled": cancelled,
        "matches": affected_matches,
        "message": (
            f"✅ {cancelled} pending match(es) "
            f"cancelled for @{username}."
        ),
    }


# ============================================================
# TELEGRAM — CANCEL PENDING
# ============================================================

async def cancel_pending_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    # By default, the command acts on the manager who
    # executed it.
    username = (
        context.args[0]
        if context.args
        else user.username
    )

    if not username:
        await message.reply_text(
            (
                "❌ Your Telegram account has no username.\n"
                "Use: /cancelpending @username"
            )
        )
        return

    result = cancel_all_pending_for_manager(
        username
    )

    if not result["success"]:
        await message.reply_text(
            result["message"]
        )
        return

    if result["cancelled"] == 0:
        await message.reply_text(
            (
                "📭 <b>PENDING MATCHES</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Manager : @{result['manager']}\n\n"
                "No pending friendly match was found."
            )
        )
        return

    lines = [
        "🚫 <b>PENDING MATCHES CANCELLED</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤 Manager : @{result['manager']}",
        f"❌ Cancelled : {result['cancelled']}",
        "",
    ]

    for item in result["matches"]:
        host = item["host_username"] or "?"
        opponent = item["opponent_username"] or "?"

        lines.append(
            f"⚽ @{host} vs @{opponent}"
        )

    await message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# MARKET — CSV PLAYER IMPORT
# ============================================================

def _csv_int(
    value,
) -> int | None:

    try:
        return int(
            str(value).strip()
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


async def ensure_csv_players_exist(
    session,
) -> int:
    """
    Ensure players from fc26_players.csv exist in Player.

    Existing Player records are preserved.
    Missing CSV records are inserted.
    """

    if not CSV_PLAYERS_FILE.exists():
        return 0

    result = await session.execute(
        select(Player.name)
    )

    existing_names = {
        str(name).strip().casefold()
        for name in result.scalars().all()
        if name
    }

    added = 0

    try:
        with CSV_PLAYERS_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            rows = csv.DictReader(file)

            for row in rows:

                name = (
                    row.get("name")
                    or ""
                ).strip()

                if (
                    not name
                    or name.casefold()
                    in existing_names
                ):
                    continue

                country = (
                    row.get("country")
                    or ""
                ).strip()

                position = (
                    row.get("position")
                    or ""
                ).strip()

                age = _csv_int(
                    row.get("age")
                )

                overall = _csv_int(
                    row.get("overall")
                )

                potential = _csv_int(
                    row.get("potential")
                )

                value = _csv_int(
                    row.get("value")
                )

                if None in {
                    age,
                    overall,
                    potential,
                    value,
                }:
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

                existing_names.add(
                    name.casefold()
                )

                added += 1

    except (
        OSError,
        csv.Error,
    ):
        return added

    if added:
        await session.flush()

    return added


# ============================================================
# OWNER — CLEAR MARKET
# ============================================================

async def clear_transfer_market() -> dict:
    """
    Empty the currently available transfer market.

    IMPORTANT:
    Player rows are NOT deleted.

    Only TransferListing rows with status='available'
    are removed. This makes the corresponding players
    eligible for a future /refillmarket again.

    CSV players are then restored into Player if they are
    missing, so the CSV remains a reusable source pool.
    """

    async with AsyncSessionLocal() as session:

        # Count current market first.
        result = await session.execute(
            select(TransferListing.player_id).where(
                TransferListing.status
                == "available"
            )
        )

        listed_player_ids = list(
            result.scalars().all()
        )

        # Remove only market listings.
        delete_result = await session.execute(
            delete(TransferListing).where(
                TransferListing.status
                == "available"
            )
        )

        removed_listings = (
            delete_result.rowcount or 0
        )

        # Make sure CSV players still exist in Player.
        imported_csv_players = (
            await ensure_csv_players_exist(
                session
            )
        )

        await session.commit()

    return {
        "success": True,
        "removed_listings": removed_listings,
        "players_released": len(
            set(listed_player_ids)
        ),
        "csv_players_restored": (
            imported_csv_players
        ),
    }


# ============================================================
# TELEGRAM — OWNER CLEAR MARKET
# ============================================================

async def clear_market_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if user.id not in OWNER_IDS:
        await message.reply_text(
            "❌ You are not authorized to use this command."
        )
        return

    result = await clear_transfer_market()

    await message.reply_text(
        (
            "🧹 <b>TRANSFER MARKET CLEARED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🗑️ Listings removed : "
            f"<b>{result['removed_listings']}</b>\n"
            f"⚽ Players released : "
            f"<b>{result['players_released']}</b>\n"
            f"📄 CSV players restored : "
            f"<b>{result['csv_players_restored']}</b>\n\n"
            "✅ The Player records were kept.\n"
            "🔄 /refillmarket can now draw from "
            "the same eligible player pool again."
        )
    )


# ============================================================
# HANDLERS
# ============================================================

cancel_pending_handler = CommandHandler(
    "cancelpending",
    cancel_pending_command,
)

clear_market_handler = CommandHandler(
    "clearmarket",
    clear_market_command,
)


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "cancel_all_pending_for_manager",
    "cancel_pending_command",
    "clear_transfer_market",
    "clear_market_command",
    "cancel_pending_handler",
    "clear_market_handler",
]
