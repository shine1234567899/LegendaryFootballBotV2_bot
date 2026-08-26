from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import delete, select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import Award, User


# ==========================================================
# BALLON D'OR MANAGER SYSTEM
# ==========================================================
#
# Uses the existing Award model from models.py.
#
# Award fields used:
#   user_id
#   award_type
#   season_id
#   awarded_by
#   note
#   awarded_at
#
# No new database column is required.
# Ranking positions are stored in Award.note.
#
# COMMANDS
#
# OWNER:
#   /nomined @username
#   /ballondororder @user1 @user2 @user3 ...
#   /ballondorwinner @username
#   /clearballondor
#
# MANAGERS / PLAYERS:
#   /ballondorrank
#
# ==========================================================

NOMINEE_TYPE = "BALLON_DOR_NOMINEE"
WINNER_TYPE = "BALLON_DOR_WINNER"
RANK_PREFIX = "BALLON_DOR_RANK:"


# ==========================================================
# BASIC HELPERS
# ==========================================================

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


def clean_username(value: str) -> str:
    return value.strip().lstrip("@").casefold()


def display_username(user: User) -> str:
    return f"@{user.username}" if user.username else f"User {user.id}"


def make_rank_note(position: int) -> str:
    return f"{RANK_PREFIX}{position}"


def read_rank(note: str | None) -> int | None:
    if not note or not note.startswith(RANK_PREFIX):
        return None

    try:
        return int(note[len(RANK_PREFIX):])
    except ValueError:
        return None


async def find_user_by_username(
    session,
    username: str,
) -> User | None:
    username = clean_username(username)

    result = await session.execute(
        select(User).where(
            User.username.ilike(username)
        )
    )

    return result.scalar_one_or_none()


async def get_nomination(
    session,
    user_id: int,
) -> Award | None:
    return await session.scalar(
        select(Award).where(
            Award.award_type == NOMINEE_TYPE,
            Award.user_id == user_id,
        )
    )


async def get_nominees(session):
    result = await session.execute(
        select(Award, User)
        .join(
            User,
            User.id == Award.user_id,
        )
        .where(
            Award.award_type == NOMINEE_TYPE,
        )
    )

    rows = result.all()

    def sort_key(row):
        award, user = row
        rank = read_rank(award.note)

        if rank is None:
            return (1, 999999, display_username(user).casefold())

        return (0, rank, display_username(user).casefold())

    rows.sort(key=sort_key)

    return rows


async def get_current_winner(session):
    award = await session.scalar(
        select(Award)
        .where(
            Award.award_type == WINNER_TYPE,
        )
        .order_by(
            Award.awarded_at.desc()
        )
    )

    if award is None:
        return None

    return await session.get(User, award.user_id)


# ==========================================================
# 1. /nomined @username
# OWNER ONLY
# ==========================================================

async def nomined_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    owner = update.effective_user

    if message is None or owner is None:
        return

    if not is_owner(owner.id):
        await message.reply_text("❌ Owner only.")
        return

    if len(context.args) != 1:
        await message.reply_text(
            "🏆 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Usage:\n"
            "/nomined @username"
        )
        return

    username = clean_username(context.args[0])

    async with AsyncSessionLocal() as session:
        user = await find_user_by_username(
            session,
            username,
        )

        if user is None:
            await message.reply_text(
                f"❌ @{username} is not registered in the bot."
            )
            return

        existing = await get_nomination(
            session,
            user.id,
        )

        if existing is not None:
            await message.reply_text(
                f"⚠️ {display_username(user)} is already nominated."
            )
            return

        nominees = await get_nominees(session)
        position = len(nominees) + 1

        session.add(
            Award(
                user_id=user.id,
                award_type=NOMINEE_TYPE,
                season_id=None,
                awarded_by=owner.id,
                note=make_rank_note(position),
            )
        )

        await session.commit()

    await message.reply_text(
        "🏆 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑 — 𝐍𝐎𝐌𝐈𝐍𝐀𝐓𝐈𝐎𝐍\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Player: {display_username(user)}\n"
        f"📊 Position: #{position}\n"
        "✅ Added to the nominees."
    )


# ==========================================================
# 2. /ballondorrank
# EVERYONE
# ==========================================================

async def ballondorrank_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    async with AsyncSessionLocal() as session:
        nominees = await get_nominees(session)
        winner = await get_current_winner(session)

    if not nominees:
        await message.reply_text(
            "🏆 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❌ No nominees yet."
        )
        return

    text = (
        "🏆 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑 — 𝐑𝐀𝐍𝐊𝐈𝐍𝐆\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }

    for position, (award, user) in enumerate(
        nominees,
        start=1,
    ):
        medal = medals.get(position, f"{position}.")
        text += (
            f"{medal} {display_username(user)}\n"
        )

    if winner is not None:
        text += (
            "\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 Winner: {display_username(winner)}\n"
        )

    await message.reply_text(text)


# ==========================================================
# 3. /ballondororder
# OWNER ONLY
#
# Complete ranking replacement.
#
# Example:
# /ballondororder @messi @ronaldo @mbappe
#
# First = #1
# Second = #2
# Third = #3
# ==========================================================

async def ballondororder_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    owner = update.effective_user

    if message is None or owner is None:
        return

    if not is_owner(owner.id):
        await message.reply_text("❌ Owner only.")
        return

    if not context.args:
        await message.reply_text(
            "🏆 Usage:\n"
            "/ballondororder @player1 @player2 @player3\n\n"
            "The order you provide becomes the ranking."
        )
        return

    async with AsyncSessionLocal() as session:
        nominees = await get_nominees(session)

        if not nominees:
            await message.reply_text(
                "❌ There are no nominees."
            )
            return

        nominee_ids = {
            user.id
            for _, user in nominees
        }

        ordered_users: list[User] = []
        seen_ids: set[int] = set()

        for argument in context.args:
            username = clean_username(argument)

            user = await find_user_by_username(
                session,
                username,
            )

            if user is None:
                await message.reply_text(
                    f"❌ @{username} is not registered."
                )
                return

            if user.id not in nominee_ids:
                await message.reply_text(
                    f"❌ {display_username(user)} "
                    "is not a nominee."
                )
                return

            if user.id in seen_ids:
                await message.reply_text(
                    f"❌ {display_username(user)} "
                    "was entered twice."
                )
                return

            seen_ids.add(user.id)
            ordered_users.append(user)

        if len(ordered_users) != len(nominees):
            await message.reply_text(
                "❌ You must provide every nominee exactly once.\n\n"
                f"Nominees: {len(nominees)}\n"
                f"Provided: {len(ordered_users)}"
            )
            return

        awards_by_user = {
            award.user_id: award
            for award, _ in nominees
        }

        for position, user in enumerate(
            ordered_users,
            start=1,
        ):
            awards_by_user[user.id].note = make_rank_note(
                position
            )

        await session.commit()

    await message.reply_text(
        "🏆 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Ranking updated successfully."
    )


# ==========================================================
# 4. /ballondorwinner @username
# OWNER ONLY
# ==========================================================

async def ballondorwinner_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    owner = update.effective_user

    if message is None or owner is None:
        return

    if not is_owner(owner.id):
        await message.reply_text("❌ Owner only.")
        return

    if len(context.args) != 1:
        await message.reply_text(
            "🏆 Usage:\n"
            "/ballondorwinner @username"
        )
        return

    username = clean_username(context.args[0])

    async with AsyncSessionLocal() as session:
        user = await find_user_by_username(
            session,
            username,
        )

        if user is None:
            await message.reply_text(
                f"❌ @{username} is not registered."
            )
            return

        nomination = await get_nomination(
            session,
            user.id,
        )

        if nomination is None:
            await message.reply_text(
                f"❌ {display_username(user)} "
                "is not a Ballon d'Or nominee."
            )
            return

        # Keep exactly one current winner.
        await session.execute(
            delete(Award).where(
                Award.award_type == WINNER_TYPE
            )
        )

        session.add(
            Award(
                user_id=user.id,
                award_type=WINNER_TYPE,
                season_id=None,
                awarded_by=owner.id,
                note="Current Ballon d'Or winner",
            )
        )

        await session.commit()

    await message.reply_text(
        "🏆👑 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑 — 𝐖𝐈𝐍𝐍𝐄𝐑\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🥇 Winner: {display_username(user)}\n\n"
        "✅ Winner updated."
    )


# ==========================================================
# 5. /clearballondor
# OWNER ONLY
#
# Clears nominees AND current winner.
# ==========================================================

async def clearballondor_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    owner = update.effective_user

    if message is None or owner is None:
        return

    if not is_owner(owner.id):
        await message.reply_text("❌ Owner only.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Award).where(
                Award.award_type.in_(
                    [
                        NOMINEE_TYPE,
                        WINNER_TYPE,
                    ]
                )
            )
        )

        awards = result.scalars().all()

        if not awards:
            await message.reply_text(
                "ℹ️ Ballon d'Or is already empty."
            )
            return

        for award in awards:
            await session.delete(award)

        await session.commit()

    await message.reply_text(
        "🧹 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑 — 𝐂𝐋𝐄𝐀𝐑𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Nominees and current winner removed.\n"
        "You can start a new edition."
    )


# ==========================================================
# 6. /ballondorhelp
# EVERYONE
# ==========================================================

async def ballondorhelp_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        "🏆 𝐁𝐀𝐋𝐋𝐎𝐍 𝐃'𝐎𝐑 — 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👑 OWNER\n"
        "/nomined @username\n"
        "→ Add a nominee.\n\n"
        "/ballondororder @user1 @user2 ...\n"
        "→ Change the complete ranking.\n\n"
        "/ballondorwinner @username\n"
        "→ Select the winner.\n\n"
        "/clearballondor\n"
        "→ Reset the current edition.\n\n"
        "👥 MANAGERS / PLAYERS\n"
        "/ballondorrank\n"
        "→ View the ranking and winner."
    )


# ==========================================================
# HANDLERS
# ==========================================================

nomined_handler = CommandHandler(
    "nomined",
    nomined_command,
)

ballondorrank_handler = CommandHandler(
    "ballondorrank",
    ballondorrank_command,
)

ballondororder_handler = CommandHandler(
    "ballondororder",
    ballondororder_command,
)

ballondorwinner_handler = CommandHandler(
    "ballondorwinner",
    ballondorwinner_command,
)

clearballondor_handler = CommandHandler(
    "clearballondor",
    clearballondor_command,
)

ballondorhelp_handler = CommandHandler(
    "ballondorhelp",
    ballondorhelp_command,
)
