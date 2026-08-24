from __future__ import annotations

from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select, func, desc, asc

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    League,
    LeagueSeasonClub,
    Season,
)


IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "league.jpg"

MAX_CLUBS_PER_LEAGUE = 20
DIVISIONS_PER_PAGE = 10


DEFAULT_LEAGUES = (
    ("Premier League", "England"),
    ("La Liga", "Spain"),
    ("Serie A", "Italy"),
    ("Bundesliga", "Germany"),
    ("Ligue 1", "France"),
)


# ==========================================================
# V1-STYLE PRESENTATION
# ==========================================================


def _dashboard_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📊 MY STANDING",
                    callback_data="league:standing",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📅 FIXTURES",
                    callback_data="league:fixtures",
                ),
                InlineKeyboardButton(
                    "📈 STATS",
                    callback_data="league:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🚪 QUIT LEAGUE",
                    callback_data="league:quit",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="league:close",
                ),
            ],
        ]
    )


def _close_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "❌ CLOSE",
                callback_data="league:close",
            )
        ]]
    )


def _league_list_keyboard(leagues):
    rows = []

    for league, club_count in leagues:
        capacity = min(
            MAX_CLUBS_PER_LEAGUE,
            int(league.max_clubs or MAX_CLUBS_PER_LEAGUE),
        )

        rows.append(
            [
                InlineKeyboardButton(
                    (
                        f"🏆 {league.name} "
                        f"• {club_count}/{capacity}"
                    ),
                    callback_data=(
                        f"league:divisions:{league.id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="league:refresh",
            ),
            InlineKeyboardButton(
                "❌ Close",
                callback_data="league:close",
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def _division_keyboard(
    parent_id: int,
    divisions,
):
    rows = []

    for division, club_count in divisions:
        capacity = min(
            MAX_CLUBS_PER_LEAGUE,
            int(
                division.max_clubs
                or MAX_CLUBS_PER_LEAGUE
            ),
        )

        is_parent = division.id == parent_id
        is_active = str(division.status).lower() == "active"

        if is_parent:
            label = f"🏆 {division.name}"
        else:
            label = (
                f"🏆 Division {division.tier} — "
                f"{division.name}"
            )

        label += f" • {club_count}/{capacity}"

        # Every division is selectable. Its current status does not prevent
        # the user from opening/joining it.
        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=(
                        f"league:division:{division.id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="league:back",
            ),
            InlineKeyboardButton(
                "❌ Close",
                callback_data="league:close",
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


# ==========================================================
# DB HELPERS
# ==========================================================


async def _get_my_club(
    user_id: int,
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(
                Club.owner_id == user_id
            )
        )
        return result.scalar_one_or_none()


async def _active_season(
    session,
):
    result = await session.execute(
        select(Season)
        .where(
            Season.is_active.is_(True)
        )
        .order_by(
            Season.number.desc()
        )
    )
    return result.scalars().first()


async def _registration_season(
    session,
):
    season = await _active_season(session)

    if season is not None:
        return season

    result = await session.execute(
        select(func.max(Season.number))
    )
    next_number = int(
        result.scalar() or 0
    ) + 1

    season = Season(
        name=f"Season {next_number}",
        number=next_number,
        is_active=True,
        started_at=None,
    )

    session.add(season)
    await session.flush()

    return season


async def _ensure_default_leagues(
    session,
):
    for name, country in DEFAULT_LEAGUES:
        result = await session.execute(
            select(League).where(
                League.name == name
            )
        )
        league = result.scalar_one_or_none()

        if league is None:
            session.add(
                League(
                    name=name,
                    country=country,
                    tier=1,
                    max_clubs=MAX_CLUBS_PER_LEAGUE,
                    status="active",
                    parent_league_id=None,
                    promotion_target_id=None,
                    relegation_target_id=None,
                    promotion_slots=0,
                    relegation_slots=0,
                )
            )
        elif league.status != "active":
            league.status = "active"


async def _season_started(
    session,
    season_id: int,
):
    result = await session.execute(
        select(Season.started_at).where(
            Season.id == season_id
        )
    )

    return (
        result.scalar_one_or_none()
        is not None
    )


async def _club_membership(
    session,
    club_id: int,
    season_id: int,
):
    result = await session.execute(
        select(
            LeagueSeasonClub
        ).where(
            LeagueSeasonClub.club_id == club_id,
            LeagueSeasonClub.season_id == season_id,
        )
    )

    return result.scalars().first()


async def _joinable_leagues(
    session,
    season_id: int,
):
    result = await session.execute(
        select(
            League,
            func.count(
                LeagueSeasonClub.id
            ).label("club_count"),
        )
        .outerjoin(
            LeagueSeasonClub,
            (
                (LeagueSeasonClub.league_id == League.id)
                & (LeagueSeasonClub.season_id == season_id)
            ),
        )
        .where(
            League.status == "active",
            League.parent_league_id.is_(None),
        )
        .group_by(
            League.id
        )
        .order_by(
            League.name.asc(),
            League.id.asc(),
        )
    )

    rows = []

    for league, club_count in result.all():
        capacity = min(
            MAX_CLUBS_PER_LEAGUE,
            int(
                league.max_clubs
                or MAX_CLUBS_PER_LEAGUE
            ),
        )

        if int(club_count) < capacity:
            rows.append(
                (
                    league,
                    int(club_count),
                )
            )

    return rows


async def _divisions(
    session,
    parent_league_id: int,
    season_id: int,
):
    """
    Return the selected main league plus every league belonging to its
    division family.

    A division can be linked through parent_league_id. Older league data can
    also be linked through promotion_target_id/relegation_target_id, so those
    relationships are followed too. We deliberately do not require
    status == "active" here: all divisions remain visible and selectable in the
    division menu, regardless of their current status.
    """
    result = await session.execute(
        select(League).order_by(
            League.tier.asc(),
            League.id.asc(),
        )
    )
    all_leagues = list(result.scalars().all())

    parent = next(
        (
            league
            for league in all_leagues
            if league.id == parent_league_id
        ),
        None,
    )

    if parent is None:
        return []

    # Build an undirected family graph. This covers both the intended
    # parent/child hierarchy and existing promotion/relegation links.
    graph = {}

    for league in all_leagues:
        graph.setdefault(league.id, set())

        if league.parent_league_id is not None:
            graph.setdefault(league.parent_league_id, set()).add(league.id)
            graph[league.id].add(league.parent_league_id)

        if league.promotion_target_id is not None:
            graph.setdefault(league.promotion_target_id, set()).add(league.id)
            graph[league.id].add(league.promotion_target_id)

        if league.relegation_target_id is not None:
            graph.setdefault(league.relegation_target_id, set()).add(league.id)
            graph[league.id].add(league.relegation_target_id)

    selected_ids = {parent.id}
    queue = [parent.id]

    while queue:
        current_id = queue.pop(0)

        for related_id in graph.get(current_id, set()):
            if related_id not in selected_ids:
                selected_ids.add(related_id)
                queue.append(related_id)

    # Count clubs in the selected season.
    count_result = await session.execute(
        select(
            LeagueSeasonClub.league_id,
            func.count(LeagueSeasonClub.id),
        )
        .where(
            LeagueSeasonClub.season_id == season_id,
            LeagueSeasonClub.league_id.in_(selected_ids),
        )
        .group_by(LeagueSeasonClub.league_id)
    )

    counts = {
        int(league_id): int(count)
        for league_id, count in count_result.all()
    }

    selected = [
        league
        for league in all_leagues
        if league.id in selected_ids
    ]

    selected.sort(
        key=lambda league: (
            0 if league.id == parent.id else 1,
            int(league.tier or 0),
            league.id,
        )
    )

    return [
        (
            league,
            counts.get(league.id, 0),
        )
        for league in selected
    ]


# ==========================================================
# PHOTO UI
# ==========================================================


async def _reply_photo(
    target,
    caption: str,
    reply_markup=None,
):
    """Send the initial photo-based league UI."""
    with open(IMAGE_FILE, "rb") as photo:
        await target.reply_photo(
            photo=photo,
            caption=caption,
            reply_markup=reply_markup,
        )


async def _edit_league_message(
    query,
    caption: str,
    reply_markup=None,
):
    """
    Keep the same Telegram message while navigating the league UI.
    The original photo stays in place; only its caption/buttons change.
    """
    try:
        await query.message.edit_caption(
            caption=caption,
            reply_markup=reply_markup,
        )
        return True
    except BadRequest as error:
        if "Message is not modified" in str(error):
            return True

        # Fallback only when the current message cannot be edited as a photo.
        if "There is no caption" in str(error):
            try:
                await query.message.edit_text(
                    caption,
                    reply_markup=reply_markup,
                )
                return True
            except Exception:
                pass

        print(
            "⚠️ League message edit failed:",
            type(error).__name__,
            error,
        )
        return False
    except Exception as error:
        print(
            "⚠️ League message edit failed:",
            type(error).__name__,
            error,
        )
        return False


async def _show_leagues(
    query_or_message,
    session,
    season,
    edit=False,
):
    leagues = await _joinable_leagues(
        session,
        season.id,
    )

    caption = (
        "🏆 𝐂𝐇𝐎𝐎𝐒𝐄 𝐘𝐎𝐔𝐑 𝐋𝐄𝐀𝐆𝐔𝐄\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {season.name}\n\n"
        "🇬🇧 Premier League\n"
        "🇪🇸 La Liga\n"
        "🇮🇹 Serie A\n"
        "🇩🇪 Bundesliga\n"
        "🇫🇷 Ligue 1\n"
        "➕ Owner-created leagues\n\n"
        "👥 Maximum : 20 clubs per division"
    )

    if not leagues:
        caption += (
            "\n\n❌ No league with free space."
        )

    markup = (
        _league_list_keyboard(leagues)
        if leagues
        else _close_keyboard()
    )

    if edit:
        await _edit_league_message(
            query_or_message,
            caption,
            markup,
        )
    else:
        await _reply_photo(
            query_or_message,
            caption,
            markup,
        )


async def _show_division_menu(
    query,
    session,
    season,
    parent_league,
):
    divisions = await _divisions(
        session,
        parent_league.id,
        season.id,
    )

    if not divisions:
        divisions = [
            (parent_league, 0)
        ]

    caption = (
        "🏆 𝐂𝐇𝐎𝐎𝐒𝐄 𝐘𝐎𝐔𝐑 𝐃𝐈𝐕𝐈𝐒𝐈𝐎𝐍\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 {parent_league.name}\n"
        f"📅 {season.name}\n\n"
        "Select a division:"
    )

    await _edit_league_message(
        query,
        caption,
        _division_keyboard(
            parent_league.id,
            divisions,
        ),
    )


# ==========================================================
# /LEAGUE
# ==========================================================


async def league(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    club = await _get_my_club(
        user.id
    )

    if club is None:
        await _reply_photo(
            message,
            "❌ Create your club first.",
        )
        return

    async with AsyncSessionLocal() as session:
        await _ensure_default_leagues(session)

        season = await _registration_season(
            session
        )

        membership = await _club_membership(
            session,
            club.id,
            season.id,
        )

        await session.commit()

    if membership is None:
        async with AsyncSessionLocal() as session:
            await _show_leagues(
                message,
                session,
                season,
                edit=False,
            )
        return

    await _reply_photo(
        message,
        (
            "🏆 𝐋𝐄𝐀𝐆𝐔𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚽ Club ID : {club.id}\n"
            f"🏅 League ID : {membership.league_id}\n"
            f"📅 Season ID : {membership.season_id}\n\n"
            f"📍 Position : {membership.position or '-'}\n"
            f"🏆 Points : {membership.points}\n"
            f"🎮 Played : {membership.played}\n"
            f"✅ Wins : {membership.wins}\n"
            f"🤝 Draws : {membership.draws}\n"
            f"❌ Losses : {membership.losses}\n"
            f"⚽ Goals : {membership.goals_for}\n"
            f"🥅 Against : {membership.goals_against}"
        ),
        reply_markup=_dashboard_keyboard(),
    )


# ==========================================================
# CALLBACKS
# ==========================================================


async def league_callback(
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

    parts = str(
        query.data
    ).split(":")

    action = (
        parts[1]
        if len(parts) > 1
        else ""
    )

    if action == "close":
        await _edit_league_message(
            query,
            "🏆 League closed.",
            None,
        )
        return

    async with AsyncSessionLocal() as session:
        club = await _get_my_club(
            query.from_user.id
        )

        if club is None:
            await _reply_photo(
                query.message,
                "❌ Club not found.",
            )
            return

        season = await _registration_season(
            session
        )

        # --------------------------------------------------
        # BACK
        # --------------------------------------------------

        if action == "back":
            await _show_leagues(
                query,
                session,
                season,
                edit=True,
            )
            await session.commit()
            return

        # --------------------------------------------------
        # REFRESH
        # --------------------------------------------------

        if action == "refresh":
            membership = await _club_membership(
                session,
                club.id,
                season.id,
            )

            if membership is not None:
                await session.commit()
                await _edit_league_message(
                    query,
                    (
                        "⚠️ Your club is already registered.\n"
                        "Use /league to open your dashboard."
                    ),
                )
                return

            await _show_leagues(
                query,
                session,
                season,
                edit=True,
            )
            await session.commit()
            return

        # --------------------------------------------------
        # SHOW DIVISIONS
        # --------------------------------------------------

        if action == "divisions":
            if len(parts) != 3:
                await session.commit()
                return

            parent_id = int(parts[2])

            result = await session.execute(
                select(League).where(
                    League.id == parent_id,
                    League.status == "active",
                )
            )

            parent = (
                result.scalar_one_or_none()
            )

            if parent is None:
                await session.commit()
                await _edit_league_message(
                    query,
                    "❌ This league is no longer available.",
                )
                return

            await _show_division_menu(
                query,
                session,
                season,
                parent,
            )
            await session.commit()
            return

        # --------------------------------------------------
        # JOIN A DIVISION
        # --------------------------------------------------

        if action == "division":
            if len(parts) != 3:
                await session.commit()
                return

            division_id = int(parts[2])

            # HARD DUPLICATE BLOCK:
            # one club = one domestic division per season.
            existing = await _club_membership(
                session,
                club.id,
                season.id,
            )

            if existing is not None:
                await session.commit()
                await _edit_league_message(
                    query,
                    (
                        "⚠️ Your club is already registered "
                        "for this season.\n\n"
                        "You cannot join another division."
                    ),
                )
                return

            if await _season_started(
                session,
                season.id,
            ):
                await session.commit()
                await _edit_league_message(
                    query,
                    (
                        "🔒 The season has already started.\n"
                        "New registrations are closed."
                    ),
                )
                return

            result = await session.execute(
                select(League).where(
                    League.id == division_id,
                )
            )

            selected = (
                result.scalar_one_or_none()
            )

            if selected is None:
                await session.commit()
                await _edit_league_message(
                    query,
                    "❌ This division is no longer available.",
                )
                return

            count_result = await session.execute(
                select(
                    func.count(
                        LeagueSeasonClub.id
                    )
                ).where(
                    LeagueSeasonClub.league_id
                    == selected.id,
                    LeagueSeasonClub.season_id
                    == season.id,
                )
            )

            count = int(
                count_result.scalar() or 0
            )

            capacity = min(
                MAX_CLUBS_PER_LEAGUE,
                int(
                    selected.max_clubs
                    or MAX_CLUBS_PER_LEAGUE
                ),
            )

            if count >= capacity:
                await session.commit()
                await _edit_league_message(
                    query,
                    f"❌ This division is full ({capacity}/{capacity}).",
                )
                return

            # Final duplicate check before insertion.
            existing = await _club_membership(
                session,
                club.id,
                season.id,
            )

            if existing is not None:
                await session.commit()
                await _edit_league_message(
                    query,
                    "⚠️ Your club is already registered for this season.",
                )
                return

            club.league_id = selected.id

            session.add(
                LeagueSeasonClub(
                    league_id=selected.id,
                    club_id=club.id,
                    season_id=season.id,
                    position=None,
                    points=0,
                    played=0,
                    wins=0,
                    draws=0,
                    losses=0,
                    goals_for=0,
                    goals_against=0,
                )
            )

            await session.commit()

            await _edit_league_message(
                query,
                (
                    "✅ 𝐋𝐄𝐀𝐆𝐔𝐄 𝐉𝐎𝐈𝐍𝐄𝐃\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚽ Club : {club.name}\n"
                    f"🏆 {selected.name}\n"
                    f"📊 Division : {selected.tier}\n"
                    f"📅 {season.name}\n\n"
                    "👥 Maximum : 20 clubs"
                ),
            )
            return

        # --------------------------------------------------
        # QUIT
        # --------------------------------------------------

        if action == "quit":
            membership = await _club_membership(
                session,
                club.id,
                season.id,
            )

            if membership is None:
                await session.commit()
                await _edit_league_message(
                    query,
                    "ℹ️ Your club is not registered.",
                )
                return

            if await _season_started(
                session,
                season.id,
            ):
                await session.commit()
                await _edit_league_message(
                    query,
                    (
                        "🔒 The season has started.\n"
                        "You cannot leave your league now."
                    ),
                )
                return

            await session.delete(
                membership
            )
            club.league_id = None

            await session.commit()

            await _edit_league_message(
                query,
                (
                    "🚪 𝐋𝐄𝐀𝐆𝐔𝐄 𝐋𝐄𝐅𝐓\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚽ Club : {club.name}\n\n"
                    "You left successfully."
                ),
            )
            return

        # --------------------------------------------------
        # ORIGINAL V1-STYLE DASHBOARD CALLBACKS
        # --------------------------------------------------

        if action in {
            "standing",
            "fixtures",
            "stats",
        }:
            membership = await _club_membership(
                session,
                club.id,
                season.id,
            )

            if membership is None:
                await session.commit()
                await _edit_league_message(
                    query,
                    (
                        "🏆 𝐋𝐄𝐀𝐆𝐔𝐄\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "Your club is not registered yet."
                    ),
                    reply_markup=_dashboard_keyboard(),
                )
                return

            if action == "standing":
                caption = (
                    "📊 𝐌𝐘 𝐋𝐄𝐀𝐆𝐔𝐄 𝐒𝐓𝐀𝐍𝐃𝐈𝐍𝐆\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚽ {club.name}\n"
                    f"📍 Position : {membership.position or '-'}\n"
                    f"🏆 Points : {membership.points}\n"
                    f"🎮 Played : {membership.played}\n"
                    f"✅ Wins : {membership.wins}\n"
                    f"🤝 Draws : {membership.draws}\n"
                    f"❌ Losses : {membership.losses}\n"
                    f"⚽ GF : {membership.goals_for}\n"
                    f"🥅 GA : {membership.goals_against}\n"
                    f"📈 GD : "
                    f"{membership.goals_for - membership.goals_against}"
                )

            elif action == "fixtures":
                caption = (
                    "📅 𝐋𝐄𝐀𝐆𝐔𝐄 𝐅𝐈𝐗𝐓𝐔𝐑𝐄𝐒\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "Fixture display will be connected to "
                    "the league scheduler."
                )

            else:
                caption = (
                    "📈 𝐋𝐄𝐀𝐆𝐔𝐄 𝐒𝐓𝐀𝐓𝐒\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎮 Played : {membership.played}\n"
                    f"✅ Wins : {membership.wins}\n"
                    f"🤝 Draws : {membership.draws}\n"
                    f"❌ Losses : {membership.losses}\n"
                    f"⚽ Goals : {membership.goals_for}\n"
                    f"🥅 Against : {membership.goals_against}\n"
                    f"📈 GD : "
                    f"{membership.goals_for - membership.goals_against}"
                )

            await session.commit()

            await _edit_league_message(
                query,
                caption,
                _dashboard_keyboard(),
            )


league_handler = CommandHandler(
    "league",
    league,
)


league_callback_handler = CallbackQueryHandler(
    league_callback,
    pattern=(
        r"^league:"
        r"(standing|fixtures|stats|close|refresh|quit|divisions|division|back)"
        r"(?::\d+)?$"
    ),
)