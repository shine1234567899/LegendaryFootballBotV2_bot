from __future__ import annotations
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from sqlalchemy import select, desc

from database.database import AsyncSessionLocal
from database.models import (
    User,
    Club,
    League,
    LeagueSeasonClub,
    ClubPlayer,
    Player,
)



IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "profile.jpg"
# ==========================================================
# PROFILE
# ==========================================================
#
# /profile
#
# Displays:
#   👤 manager information
#   ⚽ club information
#   🏆 current league / division
#   👥 current squad size
#   💰 coins
#   💎 gems
#
# No profile field is modified by this command.
# ==========================================================


async def _get_profile_data(user_id: int):
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(
                User.id == user_id
            )
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            return None

        club_result = await session.execute(
            select(Club).where(
                Club.owner_id == user_id
            )
        )
        club = club_result.scalar_one_or_none()

        if club is None:
            return {
                "user": user,
                "club": None,
                "league": None,
                "membership": None,
                "squad_size": 0,
            }

        membership_result = await session.execute(
            select(LeagueSeasonClub)
            .where(
                LeagueSeasonClub.club_id == club.id
            )
            .order_by(
                desc(
                    LeagueSeasonClub.season_id
                )
            )
        )
        membership = (
            membership_result.scalars().first()
        )

        league = None

        if membership is not None:
            league_result = await session.execute(
                select(League).where(
                    League.id == membership.league_id
                )
            )
            league = (
                league_result.scalar_one_or_none()
            )

        squad_result = await session.execute(
            select(ClubPlayer)
            .where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
        )

        squad_size = len(
            squad_result.scalars().all()
        )

        return {
            "user": user,
            "club": club,
            "league": league,
            "membership": membership,
            "squad_size": squad_size,
        }


def _profile_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📊 STATS",
                    callback_data="profile:stats",
                ),
                InlineKeyboardButton(
                    "🏆 LEAGUE",
                    callback_data="profile:league",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 REFRESH",
                    callback_data="profile:refresh",
                ),
            ],
        ]
    )


def _render_profile(data) -> str:
    user = data["user"]
    club = data["club"]
    league = data["league"]
    membership = data["membership"]

    manager_name = (
        user.first_name
        or user.username
        or f"Manager #{user.id}"
    )

    text = [
        "👤 𝐌𝐘 𝐏𝐑𝐎𝐅𝐈𝐋𝐄",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤 Manager : {manager_name}",
    ]

    if user.username:
        text.append(
            f"🔗 Username : @{user.username}"
        )

    text.extend(
        [
            "",
            "⚽ 𝐂𝐋𝐔𝐁",
        ]
    )

    if club is None:
        text.append(
            "❌ No club created yet."
        )
    else:
        text.extend(
            [
                f"🏷️ Name : {club.name}",
                f"🌍 Country : {club.country}",
                f"🏟️ Stadium : {club.stadium_name}",
                f"👥 Players : {data['squad_size']}",
            ]
        )

        if league is not None and membership is not None:
            text.extend(
                [
                    "",
                    "🏆 𝐋𝐄𝐀𝐆𝐔𝐄",
                    f"🏆 {league.name}",
                    f"📊 Division : {league.tier}",
                    f"📍 Position : "
                    f"{membership.position or '-'}",
                    f"🏅 Points : {membership.points}",
                ]
            )
        else:
            text.extend(
                [
                    "",
                    "🏆 League : Not registered",
                ]
            )

    text.extend(
        [
            "",
            "💰 𝐄𝐂𝐎𝐍𝐎𝐌𝐘",
            f"🪙 Coins : {user.coins:,}",
            f"💎 Gems : {user.gems:,}",
        ]
    )

    return "\n".join(text)


async def _send_profile(
    target,
    user_id: int,
    edit: bool = False,
):
    data = await _get_profile_data(
        user_id
    )

    if data is None:
        text = (
            "👤 𝐏𝐑𝐎𝐅𝐈𝐋𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❌ User not found."
        )
        markup = None
    else:
        text = _render_profile(data)
        markup = _profile_keyboard()

    if edit:
        await target.edit_message_text(
            text,
            reply_markup=markup,
        )
    else:
        await target.reply_text(
            text,
            reply_markup=markup,
        )


async def profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    await _send_profile(
        message,
        user.id,
    )


async def profile_callback(
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

    action = str(
        query.data
    ).split(":", 1)[1]

    data = await _get_profile_data(
        query.from_user.id
    )

    if data is None:
        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='👤 𝐏𝐑𝐎𝐅𝐈𝐋𝐄\n━━━━━━━━━━━━━━━━━━━━\n❌ User not found.',
)
        return

    if action == "refresh":
        await _send_profile(
            query,
            query.from_user.id,
            edit=True,
        )
        return

    if action == "stats":
        text = _render_profile(data)

        if data["membership"] is not None:
            membership = data["membership"]
            text += (
                "\n\n📈 𝐋𝐄𝐀𝐆𝐔𝐄 𝐒𝐓𝐀𝐓𝐒\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🎮 Played : {membership.played}\n"
                f"✅ Wins : {membership.wins}\n"
                f"🤝 Draws : {membership.draws}\n"
                f"❌ Losses : {membership.losses}\n"
                f"⚽ GF : {membership.goals_for}\n"
                f"🥅 GA : {membership.goals_against}\n"
                f"📈 GD : "
                f"{membership.goals_for - membership.goals_against}\n"
                f"🏅 Points : {membership.points}"
            )

        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=text,
    reply_markup=_profile_keyboard(),
)
        return

    if action == "league":
        if (
            data["league"] is None
            or data["membership"] is None
        ):
            text = (
                "🏆 𝐌𝐘 𝐋𝐄𝐀𝐆𝐔𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Your club is not registered in a league."
            )
        else:
            league = data["league"]
            membership = data["membership"]

            text = (
                "🏆 𝐌𝐘 𝐋𝐄𝐀𝐆𝐔𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🏆 {league.name}\n"
                f"📊 Division : {league.tier}\n"
                f"📍 Position : "
                f"{membership.position or '-'}\n"
                f"🏅 Points : {membership.points}\n"
                f"🎮 Played : {membership.played}\n"
                f"✅ Wins : {membership.wins}\n"
                f"🤝 Draws : {membership.draws}\n"
                f"❌ Losses : {membership.losses}"
            )

        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=text,
    reply_markup=_profile_keyboard(),
)


profile_handler = CommandHandler(
    "profile",
    profile,
)

profile_callback_handler = CallbackQueryHandler(
    profile_callback,
    pattern=r"^profile:(stats|league|refresh)$",
)