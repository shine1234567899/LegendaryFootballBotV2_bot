import asyncio
import time
import secrets

from telegram.error import TimedOut, RetryAfter, NetworkError, BadRequest

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from sqlalchemy import select

from database.database import AsyncSessionLocal

from database.models import (
    ClubPlayer,
    User,
    Club,
    Player,
    SavedLineup,
    SavedLineupPlayer,
    Match,
    Fixture,
)

from match_engine.friendly import (
    FriendlyError,
    get_club_by_owner,
    create_friendly_match,
    save_match_lineup,
)

from match_engine.engine import (
    MatchEngine,
    MatchTeam,
)
from music_manager import music_manager


# ==========================================================
# FRIENDLY COIN REWARDS — ADDITIVE ONLY
# ==========================================================

FRIENDLY_REWARDS = {
    "WIN": 80_000,
    "DRAW": 50_000,
    "DEFEAT": 20_000,
}

async def _give_friendly_rewards(
    home_user_id: int | None,
    away_user_id: int | None,
    home_score: int,
    away_score: int,
    match_id: str,
):
    """
    Adds the requested reward to the two managers' existing coins.
    Nothing else in the friendly system is changed.
    """
    if home_user_id is None or away_user_id is None:
        print(f"⚠️ FRIENDLY REWARD SKIPPED [{match_id}]: missing manager IDs")
        return

    if home_score > away_score:
        home_reward = FRIENDLY_REWARDS["WIN"]
        away_reward = FRIENDLY_REWARDS["DEFEAT"]
        home_label = "WIN"
        away_label = "DEFEAT"
    elif away_score > home_score:
        home_reward = FRIENDLY_REWARDS["DEFEAT"]
        away_reward = FRIENDLY_REWARDS["WIN"]
        home_label = "DEFEAT"
        away_label = "WIN"
    else:
        home_reward = FRIENDLY_REWARDS["DRAW"]
        away_reward = FRIENDLY_REWARDS["DRAW"]
        home_label = "DRAW"
        away_label = "DRAW"

    try:
        async with AsyncSessionLocal() as session:
            home = await session.get(User, int(home_user_id))
            away = await session.get(User, int(away_user_id))

            if home is None or away is None:
                print(f"⚠️ FRIENDLY REWARD SKIPPED [{match_id}]: user missing")
                await session.rollback()
                return

            home.coins = int(home.coins or 0) + home_reward
            away.coins = int(away.coins or 0) + away_reward

            await session.commit()

            print(
                f"💰 FRIENDLY REWARDS [{match_id}] "
                f"{home_user_id}={home_label}+{home_reward} | "
                f"{away_user_id}={away_label}+{away_reward}"
            )
    except Exception as error:
        print(
            f"⚠️ FRIENDLY REWARD ERROR [{match_id}]: "
            f"{type(error).__name__}: {error}"
        )



# ==========================================================
# FRIENDLY END MUSIC
# ==========================================================

async def send_friendly_end_music(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
):
    track = music_manager.pick()

    if track is None:
        print("🎵 No music found in music/.")
        return

    try:
        with track.open("rb") as audio:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                caption="🎵 𝐅𝐑𝐈𝐄𝐍𝐃𝐋𝐘 𝐌𝐀𝐓𝐂𝐇 𝐅𝐈𝐍𝐈𝐒𝐇𝐄𝐃",
            )
    except Exception as error:
        print(
            "🎵 END MUSIC ERROR:",
            type(error).__name__,
            error,
        )

# ==========================================================
# LIVE MATCH STORAGE
# ==========================================================

ACTIVE_FRIENDLY_MATCHES = {}

# ==========================================================
# FRIENDLY PAY / FORFEIT
# ==========================================================

FRIENDLY_PAY_PRESETS = (
    50_000,
    100_000,
    250_000,
    500_000,
    1_000_000,
    5_000_000,
)

def _friendly_pay_store(context):
    return context.bot_data.setdefault("friendly_pay_pending", {})


def _friendly_pay_keyboard(match_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"🪙 {amount:,}",
                callback_data=f"friendlypay_amount:{match_id}:{amount}",
            )
        ]
        for amount in FRIENDLY_PAY_PRESETS
    ])


def _friendly_pay_accept_keyboard(match_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 ACCEPT & PAY",
                callback_data=f"friendlypay_accept:{match_id}",
            ),
            InlineKeyboardButton(
                "❌ DECLINE",
                callback_data=f"friendlypay_decline:{match_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🏳️ FORFEIT",
                callback_data=f"friendly_forfeit:{match_id}",
            )
        ],
    ])


async def _create_friendly_db_match(home_club_id: int, away_club_id: int):
    """Create the persistent Fixture/Match used by /stats."""
    try:
        fixture_id, match_id, _ = await create_friendly_match(
            home_club_id,
            away_club_id,
        )
        return fixture_id, match_id
    except Exception as error:
        print(
            "⚠️ FRIENDLY DB MATCH CREATE ERROR:",
            type(error).__name__,
            error,
        )
        return None, None


async def _finish_friendly_db_match(
    db_match_id: int | None,
    home_score: int,
    away_score: int,
    engine_result=None,
):
    """Persist the final Friendly result so /stats can see it."""
    if db_match_id is None:
        return

    async with AsyncSessionLocal() as session:
        match = await session.get(Match, int(db_match_id))
        if match is None:
            return

        fixture = await session.get(Fixture, int(match.fixture_id))
        if fixture is None:
            return

        # Never overwrite a match already finalized.
        if str(match.status).lower() in {"finished", "completed", "ended"}:
            return

        match.home_score = int(home_score)
        match.away_score = int(away_score)
        match.minute = 90
        match.status = "finished"
        fixture.status = "finished"

        existing_stats = match.stats if isinstance(match.stats, dict) else {}
        if engine_result is not None:
            engine_stats = getattr(engine_result, "statistics", None)
            if isinstance(engine_stats, dict):
                existing_stats["engine_statistics"] = engine_stats

        match.stats = existing_stats

        from datetime import datetime
        match.finished_at = datetime.utcnow()

        await session.commit()


async def _give_friendly_rewards_once(
    db_match_id: int | None,
    home_user_id: int | None,
    away_user_id: int | None,
    home_score: int,
    away_score: int,
):
    """
    Pays the normal Friendly reward exactly once.
    The reward marker is persisted in Match.stats, preventing a
    duplicate payout after a restart/retry.
    """
    if db_match_id is None or home_user_id is None or away_user_id is None:
        return

    async with AsyncSessionLocal() as session:
        match = await session.get(Match, int(db_match_id))
        if match is None:
            return

        stats = match.stats if isinstance(match.stats, dict) else {}
        if stats.get("friendly_reward_paid") is True:
            return

        home = await session.get(User, int(home_user_id))
        away = await session.get(User, int(away_user_id))
        if home is None or away is None:
            return

        if home_score > away_score:
            home_reward = FRIENDLY_REWARDS["WIN"]
            away_reward = FRIENDLY_REWARDS["DEFEAT"]
        elif away_score > home_score:
            home_reward = FRIENDLY_REWARDS["DEFEAT"]
            away_reward = FRIENDLY_REWARDS["WIN"]
        else:
            home_reward = FRIENDLY_REWARDS["DRAW"]
            away_reward = FRIENDLY_REWARDS["DRAW"]

        home.coins = int(home.coins or 0) + home_reward
        away.coins = int(away.coins or 0) + away_reward

        stats["friendly_reward_paid"] = True
        stats["friendly_rewards"] = {
            "home": home_reward,
            "away": away_reward,
        }
        match.stats = stats

        await session.commit()


async def _refund_friendly_stake(match_data):
    """Refund both stakes when a paid Friendly is cancelled before play."""
    stake = int(match_data.get("stake") or 0)
    if stake <= 0:
        return

    if match_data.get("stake_refunded"):
        return

    async with AsyncSessionLocal() as session:
        home = await session.get(User, int(match_data["challenger_id"]))
        away = await session.get(User, int(match_data["opponent_id"]))
        if home is not None:
            home.coins = int(home.coins or 0) + stake
        if away is not None and match_data.get("opponent_stake_taken"):
            away.coins = int(away.coins or 0) + stake
        await session.commit()

    match_data["stake_refunded"] = True


async def _settle_friendly_stake(match_data, home_score: int, away_score: int):
    """Settle a paid Friendly: winner takes the pot; draw refunds both."""
    stake = int(match_data.get("stake") or 0)
    if stake <= 0 or match_data.get("stake_settled"):
        return

    async with AsyncSessionLocal() as session:
        home = await session.get(User, int(match_data["challenger_id"]))
        away = await session.get(User, int(match_data["opponent_id"]))
        if home is None or away is None:
            return

        pot = stake * 2
        if home_score > away_score:
            home.coins = int(home.coins or 0) + pot
        elif away_score > home_score:
            away.coins = int(away.coins or 0) + pot
        else:
            home.coins = int(home.coins or 0) + stake
            away.coins = int(away.coins or 0) + stake

        await session.commit()

    match_data["stake_settled"] = True


async def _start_accepted_friendly(
    query,
    context,
    pending,
    match_id,
):
    """Shared start path for normal and paid Friendlies."""
    challenger_id = pending["challenger_id"]
    opponent_id = pending["opponent_id"]

    home_club = await get_club_by_owner(challenger_id)
    away_club = await get_club_by_owner(opponent_id)

    if home_club is None or away_club is None:
        pending["status"] = "CANCELLED"
        if pending.get("stake"):
            await _refund_friendly_stake(pending)
        await query.message.reply_text("❌ Both managers need a club.")
        return

    try:
        home_team = await load_saved_lineup_for_club(home_club.id)
        away_team = await load_saved_lineup_for_club(away_club.id)

        if home_team is None or away_team is None:
            raise FriendlyError(
                "Both clubs must have a saved lineup with exactly 11 players."
            )

        home_team.bench = await load_bench_for_club(
            home_club.id, home_team.players
        )
        away_team.bench = await load_bench_for_club(
            away_club.id, away_team.players
        )
    except Exception as error:
        pending["status"] = "CANCELLED"
        if pending.get("stake"):
            await _refund_friendly_stake(pending)
        await query.message.reply_text(
            f"❌ FRIENDLY CANCELLED\n\n{error}"
        )
        return

    pending.update({
        "status": "LIVE",
        "home_club_id": home_club.id,
        "away_club_id": away_club.id,
    })

    # Persist the Friendly so /stats sees it.
    fixture_id, db_match_id = await _create_friendly_db_match(
        home_club.id,
        away_club.id,
    )
    pending["fixture_id"] = fixture_id
    pending["db_match_id"] = db_match_id

    try:
        initial_match_data = {
            "engine": MatchEngine(home_team, away_team),
            "home_team": home_team,
            "away_team": away_team,
            "home_club_id": home_team.club_id,
            "away_club_id": away_team.club_id,
        }

        live_message = await _safe_reply_text(
            query.message,
            build_live_message(initial_match_data),
        )

        if live_message is None:
            pending["status"] = "ERROR"
            if pending.get("stake"):
                await _refund_friendly_stake(pending)
            return

        await start_friendly_match(
            context=context,
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            chat_id=query.message.chat_id,
            live_message_id=live_message.message_id,
        )
    except Exception as error:
        pending["status"] = "ERROR"
        if pending.get("stake"):
            await _refund_friendly_stake(pending)
        print(
            "❌ FRIENDLY START ERROR:",
            type(error).__name__,
            error,
        )
        try:
            await query.message.reply_text(
                f"❌ The friendly match could not start.\n{type(error).__name__}: {error}"
            )
        except Exception:
            pass


# ==========================================================
# GET USER
# ==========================================================

async def get_user_by_username(username: str):

    username = (
        username
        .lstrip("@")
        .strip()
    )

    if not username:
        return None

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(User).where(
                User.username.ilike(username)
            )
        )

        return result.scalar_one_or_none()


# ==========================================================
# LOAD SAVED LINEUP
# ==========================================================

async def load_saved_lineup_for_club(
    club_id: int,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(SavedLineup)
            .where(
                SavedLineup.club_id == club_id
            )
            .order_by(
                SavedLineup.updated_at.desc()
            )
        )

        saved_lineups = result.scalars().all()

        if not saved_lineups:
            return None

        saved_lineup = saved_lineups[0]

        result = await session.execute(
            select(
                SavedLineupPlayer,
                Player,
            )
            .join(
                Player,
                Player.id
                == SavedLineupPlayer.player_id,
            )
            .where(
                SavedLineupPlayer.saved_lineup_id
                == saved_lineup.id
            )
            .order_by(
                SavedLineupPlayer.slot_id
            )
        )

        rows = result.all()

        if len(rows) != 11:

            raise FriendlyError(
                "Saved lineup must contain exactly 11 players."
            )

        players = []

        for saved_player, player in rows:

            player.lineup_position = str(
                saved_player.position
            ).upper()

            player.shirt_number = (
                saved_player.shirt_number
            )

            player.is_captain = (
                saved_player.is_captain
            )

            players.append(player)

        player_ids = {
            player.id
            for player in players
        }

        if len(player_ids) != 11:

            raise FriendlyError(
                "A saved lineup contains duplicate players."
            )

        goalkeepers = 0

        for player in players:

            if (
                str(
                    getattr(
                        player,
                        "position",
                        "",
                    )
                ).upper()
                == "GK"
            ):
                goalkeepers += 1

        if goalkeepers != 1:

            raise FriendlyError(
                "Saved lineup must contain exactly one goalkeeper."
            )

        result = await session.execute(
            select(Club).where(
                Club.id == club_id
            )
        )

        club = result.scalar_one_or_none()

        if club is None:

            raise FriendlyError(
                "Club not found."
            )

        return MatchTeam(
            club_id=club.id,
            name=club.name,
            players=players,
            formation=saved_lineup.formation,
            bench=[],
        )


# ==========================================================
# LOAD BENCH
# ==========================================================

async def load_bench_for_club(
    club_id: int,
    starting_players,
):

    starting_ids = {
        player.id
        for player in starting_players
    }

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Player)
            .join(
                ClubPlayer,
                ClubPlayer.player_id == Player.id,
            )
            .where(
                ClubPlayer.club_id == club_id,
                ClubPlayer.is_current.is_(True),
            )
        )

        all_players = result.scalars().all()

    bench = [
        player
        for player in all_players
        if player.id not in starting_ids
    ]

    return bench

# ==========================================================
# GOAL SCORERS
# ==========================================================

def build_goal_scorer_summary(
    result,
    home_team,
    away_team,
):

    home_goals = []
    away_goals = []

    for event in result.events:

        event_type = str(
            getattr(
                event,
                "event_type",
                "",
            )
            or ""
        ).upper()

        if event_type != "GOAL":
            continue

        minute = int(
            getattr(
                event,
                "minute",
                0,
            )
            or 0
        )

        scorer = (
            getattr(
                event,
                "player_name",
                None,
            )
            or "Unknown"
        )

        team_id = getattr(
            event,
            "team_id",
            None,
        )

        line = f"{minute}' {scorer}"

        if team_id == home_team.club_id:

            home_goals.append(line)

        elif team_id == away_team.club_id:

            away_goals.append(line)

    if not home_goals and not away_goals:

        return "⚽ No goals"

    lines = [
        (
            f"🔴 {home_team.name}"
            "                 "
            f"{away_team.name} 🔵"
        )
    ]

    count = max(
        len(home_goals),
        len(away_goals),
    )

    for i in range(count):

        home = (
            home_goals[i]
            if i < len(home_goals)
            else ""
        )

        away = (
            away_goals[i]
            if i < len(away_goals)
            else ""
        )

        lines.append(
            f"{home:<25}{away}"
        )

    return "\n".join(lines)


# ==========================================================
# EVENT ICON
# ==========================================================

def event_icon(event_type):

    event_type = str(
        event_type or ""
    ).upper()

    icons = {
        "GOAL": "⚽",
        "SHOT": "🎯",
        "SAVE": "🧤",
        "RED_CARD": "🟥",
        "YELLOW_CARD": "🟨",
        "CORNER": "🚩",
        "DANGEROUS_ATTACK": "🔥",
        "ATTACK": "⚔️",
        "POSSESSION": "⚽",
        "INTERCEPTION": "🛡️",
        "TACKLE": "🦵",
        "CLEARANCE": "🛡️",
        "FOUL": "🟨",
        "KICKOFF": "🟢",
        "HALF_TIME": "⏸️",
        "SECOND_HALF": "▶️",
        "SUBSTITUTIONS": "🔄",
        "STOPPAGE_TIME": "⏱️",
        "FULL_TIME": "🏁",
    }

    return icons.get(
        event_type,
        "📢",
    )


# ==========================================================
# EVENT TEXT
# ==========================================================

def event_text(event):

    minute = getattr(
        event,
        "minute",
        0,
    )

    event_type = str(
        getattr(
            event,
            "event_type",
            "",
        )
        or ""
    ).upper()

    team_name = (
        getattr(
            event,
            "team_name",
            "",
        )
        or ""
    )

    player_name = (
        getattr(
            event,
            "player_name",
            "",
        )
        or ""
    )

    description = (
        getattr(
            event,
            "description",
            "",
        )
        or ""
    )

    icon = event_icon(
        event_type
    )

    # ------------------------------------------------------
    # SUBSTITUTIONS
    # ------------------------------------------------------

    if event_type == "SUBSTITUTIONS":

        substitutions = (
            getattr(
                event,
                "metadata",
                {},
            )
            or {}
        ).get(
            "substitutions",
            [],
        )

        lines = [
            f"⏱️ {minute}'  🔄 SUBSTITUTIONS"
        ]

        for sub in substitutions:

            lines.append(
                (
                    f"   🔴 {sub['team_name']}: "
                    f"{sub['player_out_name']} ⬇️ "
                    f"→ {sub['player_in_name']} ⬆️"
                )
            )

        return "\n".join(lines)

    # ------------------------------------------------------
    # GOAL
    # ------------------------------------------------------

    if event_type == "GOAL":

        return (
            f"⏱️ {minute}'  ⚽ "
            f"GOAL — {player_name}\n"
            f"   {team_name}"
        )

    # ------------------------------------------------------
    # HALF TIME
    # ------------------------------------------------------

    if event_type == "HALF_TIME":

        return (
            "⏸️ HALF TIME"
        )

    # ------------------------------------------------------
    # SECOND HALF
    # ------------------------------------------------------

    if event_type == "SECOND_HALF":

        return (
            f"⏱️ {minute}'  ▶️ SECOND HALF"
        )

    # ------------------------------------------------------
    # FULL TIME
    # ------------------------------------------------------

    if event_type == "FULL_TIME":

        return (
            f"🏁 FULL TIME\n"
            f"   {description}"
        )

    # ------------------------------------------------------
    # NORMAL EVENT
    # ------------------------------------------------------

    player_part = ""

    if player_name:

        player_part = (
            f" — {player_name}"
        )

    return (
        f"⏱️ {minute}'  "
        f"{icon} "
        f"{event_type.replace('_', ' ')}"
        f"{player_part}\n"
        f"   {team_name}"
    )


# ==========================================================
# BUILD LIVE MESSAGE
# ==========================================================

def build_live_keyboard(match_data):
    """
    Buttons are kept on the live match message, but clicking them
    NEVER edits or replaces the live message. The substitution menu
    is sent as a separate message.
    """
    engine = match_data["engine"]

    if not getattr(
        engine,
        "substitution_window_open",
        False,
    ):
        return None

    home_team = match_data["home_team"]
    away_team = match_data["away_team"]

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"🔄 SUBS • {home_team.name}",
                    callback_data=(
                        f"subs_refresh:{match_data['home_club_id']}"
                    ),
                ),
                InlineKeyboardButton(
                    f"🔄 SUBS • {away_team.name}",
                    callback_data=(
                        f"subs_refresh:{match_data['away_club_id']}"
                    ),
                ),
            ]
        ]
    )


def _build_minute_strip(
    current_minute: int,
):
    """
    Long match timeline.
    Always shows a rolling 1..9 sequence and counts every minute,
    including minutes where no event happened.
    """
    current = max(
        1,
        min(
            int(current_minute or 1),
            90,
        ),
    )

    start = max(
        1,
        current - 8,
    )

    minutes = list(
        range(
            start,
            min(
                start + 9,
                91,
            ),
        )
    )

    cells = []

    for minute in minutes:

        if minute == current:
            cells.append(
                f"【{minute}'】"
            )
        else:
            cells.append(
                f" {minute}' "
            )

    return "─".join(cells)



def build_match_timeline(
    current_minute: int,
):
    """
    Display only the endpoints of the rolling 9-minute interval.

    Examples:
        minute 9  ->  1' ───────── 9'
        minute 16 ->  8' ───────── 16'
        minute 22 -> 14' ───────── 22'

    The intermediate 2..8 are deliberately NOT displayed.
    """
    current = max(
        1,
        min(
            int(current_minute or 1),
            90,
        ),
    )

    start = max(
        1,
        current - 8,
    )

    return (
        f"⏱️ {start}'"
        " ───────── "
        f"{current}'"
    )


def _latest_real_event(
    events,
):
    """
    Return the most recent real football event.
    Administrative events such as kickoff/full time are allowed
    only when there is no football action.
    """
    ignored = {
        "KICKOFF",
        "HALF_TIME",
        "SECOND_HALF",
        "STOPPAGE_TIME",
        "FULL_TIME",
    }

    for event in reversed(events):
        event_type = str(
            getattr(
                event,
                "event_type",
                "",
            )
        ).upper()

        if event_type not in ignored:
            return event

    return events[-1] if events else None


def _wrap_event_text(
    text: str,
    width: int = 28,
):
    """
    Wrap text without cutting words or characters.
    """
    import textwrap

    text = str(text or "").strip()

    if not text:
        return [""]

    return textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]


def _recent_event_box(
    event,
):
    if event is None:
        return (
            "┌──────────────────────────────┐\n"
            "│ ⚽ NO RECENT EVENT            │\n"
            "└──────────────────────────────┘"
        )

    minute = getattr(
        event,
        "minute",
        0,
    )

    event_type = str(
        getattr(
            event,
            "event_type",
            "",
        )
    ).upper()

    icon = event_icon(
        event_type
    )

    team = (
        getattr(
            event,
            "team_name",
            "",
        )
        or "MATCH"
    )

    player = (
        getattr(
            event,
            "player_name",
            "",
        )
        or ""
    )

    description = (
        getattr(
            event,
            "description",
            "",
        )
        or event_type.replace(
            "_",
            " ",
        )
    )

    # Use a larger box and wrap instead of truncating.
    width = 28

    lines = [
        "┌──────────────────────────────┐",
        f"│ ⏱️ {minute}'  {icon} "
        f"{event_type.replace('_', ' ')}",
    ]

    # Club gets its own line so home/away names can never be confused.
    for part in _wrap_event_text(
        f"🏟️ {team}",
        width,
    ):
        lines.append(
            f"│ {part:<28} │"
        )

    # Player gets its own line.
    if player:
        for part in _wrap_event_text(
            f"👤 {player}",
            width,
        ):
            lines.append(
                f"│ {part:<28} │"
            )

    # Description is wrapped over as many lines as necessary.
    for part in _wrap_event_text(
        description,
        width,
    ):
        lines.append(
            f"│ {part:<28} │"
        )

    lines.append(
        "└──────────────────────────────┘"
    )

    return "\n".join(lines)


def _match_window(minute: int):
    """
    Fixed five-minute windows:
    1-5, 6-10, 11-15, ... 86-90.
    Added time stays in the 86-90 display window.
    """
    minute = max(1, min(int(minute or 1), 90))
    start = ((minute - 1) // 5) * 5 + 1
    end = min(start + 4, 90)
    return start, end


def _events_in_current_window(match_data):
    engine = match_data["engine"]
    current = int(
        getattr(
            engine,
            "current_minute",
            1,
        )
        or 1
    )

    start, end = _match_window(current)

    result = []

    for event in match_data.get("live_events", []):
        minute = int(
            getattr(
                event,
                "minute",
                0,
            )
            or 0
        )

        # Added-time events belong to the final 86-90 display window.
        display_minute = min(minute, 90)

        if start <= display_minute <= end:
            result.append(event)

    return start, end, result


def _format_event_line(event):
    minute = int(
        getattr(
            event,
            "minute",
            0,
        )
        or 0
    )

    if minute > 90:
        minute_text = f"90+{minute - 90}'"
    else:
        minute_text = f"{minute}'"

    event_type = str(
        getattr(
            event,
            "event_type",
            "",
        )
    ).upper()

    icon = event_icon(event_type)

    team = (
        getattr(
            event,
            "team_name",
            "",
        )
        or "MATCH"
    )

    player = (
        getattr(
            event,
            "player_name",
            "",
        )
        or ""
    )

    # Important events always get their real event name.
    if event_type == "GOAL":
        label = "GOAL"
    elif event_type == "SHOT":
        label = "SHOT"
    elif event_type == "RED_CARD":
        label = "RED CARD"
    elif event_type == "VAR_CHECK":
        label = "VAR CHECK"
    elif event_type == "VAR_DECISION":
        label = "VAR"
    else:
        label = event_type.replace("_", " ")

    if player:
        return (
            f"{minute_text} {icon} {label} • "
            f"{team} • {player}"
        )

    return (
        f"{minute_text} {icon} {label} • {team}"
    )


def _important_event(event):
    return str(
        getattr(
            event,
            "event_type",
            "",
        )
    ).upper() in {
        "GOAL",
        "VAR_CHECK",
        "VAR_DECISION",
        "RED_CARD",
        "PENALTY",
        "PENALTY_SCORED",
        "PENALTY_MISSED",
    }


def build_live_message(match_data):
    engine = match_data["engine"]

    home_team = match_data["home_team"]
    away_team = match_data["away_team"]

    has_full_time = any(
        str(
            getattr(
                event,
                "event_type",
                "",
            )
        ).upper() == "FULL_TIME"
        for event in match_data.get(
            "live_events",
            [],
        )
    )

    minute = int(
        getattr(
            engine,
            "current_minute",
            0,
        )
        or 0
    )

    display_minute = (
        90
        if has_full_time
        else min(minute, 90)
    )

    start_minute, end_minute, window_events = (
        _events_in_current_window(
            match_data
        )
    )

    lines = [
        "⚽ 𝐋𝐈𝐕𝐄 𝐌𝐀𝐓𝐂𝐇",
        "━━━━━━━━━━━━━━━━━━━━",
        (
            f"🔴 {home_team.name}  "
            f"{engine.result.home_score}"
            "  -  "
            f"{engine.result.away_score}  "
            f"{away_team.name} 🔵"
        ),
        f"⏱️ {display_minute}'",
        (
            f"🕐 {start_minute}'"
            " ───────── "
            f"{end_minute}'"
        ),
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    if getattr(
        engine,
        "half_time",
        False,
    ):
        lines.append(
            "⏸️ 𝐇𝐀𝐋𝐅 𝐓𝐈𝐌𝐄"
        )
        lines.append(
            "🔄 Substitutions are open."
        )
        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

    elif has_full_time:
        lines.append(
            "🏁 𝐅𝐔𝐋𝐋 𝐓𝐈𝐌𝐄"
        )
        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )

    # ======================================================
    # ALL EVENTS IN CURRENT 5-MINUTE WINDOW
    # ======================================================

    lines.append(
        f"📋 𝐄𝐕𝐄𝐍𝐓𝐒 {start_minute}'-{end_minute}'"
    )

    if not window_events:
        lines.append(
            "• No event yet."
        )
    else:
        for event in window_events:
            # NEVER hide an event. Important events get a marker,
            # but ordinary events remain visible too.
            prefix = "🔥 " if _important_event(event) else "• "

            lines.append(
                prefix
                + _format_event_line(event)
            )

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    latest = (
        window_events[-1]
        if window_events
        else None
    )

    lines.append(
        "📌 𝐌𝐎𝐒𝐓 𝐑𝐄𝐂𝐄𝐍𝐓"
    )

    if latest is None:
        lines.append(
            "No recent event."
        )
    else:
        lines.append(
            _format_event_line(latest)
        )

    return "\n".join(lines)


# ==========================================================
# FINAL MATCH STATS + GOAL SCORERS
# ==========================================================

def build_final_match_report(
    result,
    home_team,
    away_team,
):
    stats = getattr(
        result,
        "statistics",
        {},
    )

    def pair(name):
        values = stats.get(
            name,
            [0, 0],
        )

        if not isinstance(values, (list, tuple)) or len(values) < 2:
            return 0, 0

        return values[0], values[1]

    shots_h, shots_a = pair("shots")
    target_h, target_a = pair("shots_on_target")
    poss_h, poss_a = pair("possession")
    corners_h, corners_a = pair("corners")
    yellow_h, yellow_a = pair("yellow_cards")
    red_h, red_a = pair("red_cards")
    fouls_h, fouls_a = pair("fouls")

    home_goals = []
    away_goals = []

    for event in getattr(result, "events", []):
        if str(
            getattr(
                event,
                "event_type",
                "",
            )
        ).upper() != "GOAL":
            continue

        minute = int(
            getattr(
                event,
                "minute",
                0,
            )
            or 0
        )

        # Never display 90+X as the main match minute.
        # Added-time goals are shown as 90+X.
        if minute > 90:
            minute_text = f"90+{minute - 90}'"
        else:
            minute_text = f"{minute}'"

        scorer = (
            getattr(
                event,
                "player_name",
                None,
            )
            or "Unknown"
        )

        line = f"{minute_text} {scorer}"

        if getattr(
            event,
            "team_id",
            None,
        ) == home_team.club_id:
            home_goals.append(line)
        elif getattr(
            event,
            "team_id",
            None,
        ) == away_team.club_id:
            away_goals.append(line)

    lines = [
        "📊 𝐌𝐀𝐓𝐂𝐇 𝐒𝐓𝐀𝐓𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
        (
            f"🔴 {home_team.name}  "
            f"vs  {away_team.name} 🔵"
        ),
        "",
        f"🎯 Shots              {shots_h}  -  {shots_a}",
        f"🎯 Shots on target     {target_h}  -  {target_a}",
        f"⚽ Possession          {poss_h}%  -  {poss_a}%",
        f"🚩 Corners             {corners_h}  -  {corners_a}",
        f"🟨 Yellow cards        {yellow_h}  -  {yellow_a}",
        f"🟥 Red cards           {red_h}  -  {red_a}",
        f"❌ Fouls               {fouls_h}  -  {fouls_a}",
        "",
        "⚽ 𝐆𝐎𝐀𝐋 𝐒𝐂𝐎𝐑𝐄𝐑𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    # Keep team names and their players on unambiguous lines.
    if home_goals:
        lines.append(
            f"🔴 {home_team.name}: "
            + " • ".join(home_goals)
        )
    else:
        lines.append(
            f"🔴 {home_team.name}: —"
        )

    if away_goals:
        lines.append(
            f"🔵 {away_team.name}: "
            + " • ".join(away_goals)
        )
    else:
        lines.append(
            f"🔵 {away_team.name}: —"
        )

    return "\n".join(lines)


# ==========================================================
# SUBSTITUTION OWNERSHIP
# ==========================================================

def user_owns_club_in_match(
    match_data,
    user_id: int,
    club_id: int,
) -> bool:
    """
    A manager may only manage his own club.
    The opponent can never substitute your players.
    """
    if club_id == match_data["home_club_id"]:
        return user_id == match_data["challenger_id"]

    if club_id == match_data["away_club_id"]:
        return user_id == match_data["opponent_id"]

    return False


def find_active_match_for_user(
    user_id: int,
):
    for data in ACTIVE_FRIENDLY_MATCHES.values():

        if user_id in {
            data["challenger_id"],
            data["opponent_id"],
        }:
            return data

    return None


# ==========================================================
# SAFE TELEGRAM CALLBACK ANSWER
# ==========================================================

async def _safe_query_answer(
    query,
    text=None,
    show_alert=False,
):
    """Safely acknowledge a Telegram callback query."""
    if query is None:
        return False

    try:
        if text is None:
            await query.answer()
        else:
            await query.answer(
                text,
                show_alert=show_alert,
            )
        return True
    except Exception as error:
        error_text = str(error)
        if (
            "Query is too old" in error_text
            or "query id is invalid" in error_text
            or "response timeout expired" in error_text
        ):
            return False

        print(
            "⚠️ CALLBACK ANSWER ERROR:",
            type(error).__name__,
            error,
        )
        return False


# ==========================================================
# SUB PLAYER
# ==========================================================

async def subs_player_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    try:

        _, club_id, player_id = (
            str(
                query.data
            ).split(":")
        )

        club_id = int(club_id)
        player_id = int(player_id)

    except Exception:


        return

    match_data = None

    for data in ACTIVE_FRIENDLY_MATCHES.values():

        if (
            query.from_user.id
            in {
                data["challenger_id"],
                data["opponent_id"],
            }
        ):

            if (
                club_id
                in {
                    data["home_club_id"],
                    data["away_club_id"],
                }
            ):

                match_data = data

                break

    if match_data is None:


        return

    # SECURITY: a manager can only open/operate his own club.
    if not user_owns_club_in_match(
        match_data,
        query.from_user.id,
        club_id,
    ):

        return

    engine = match_data["engine"]

    if not engine.substitution_window_open:


        return

    # ======================================================
    # GET COMPATIBLE BENCH
    # ======================================================

    substitutes = (
        engine.get_compatible_substitutes(
            club_id,
            player_id,
        )
    )

    if not substitutes:


        return

    selected = None

    for player in engine.get_starting_players(
        club_id
    ):

        if player.id == player_id:

            selected = player

            break

    if selected is None:


        return

    position = str(
        getattr(
            selected,
            "lineup_position",
            getattr(
                selected,
                "position",
                "",
            ),
        )
    ).upper()

    overall = getattr(
        selected,
        "overall",
        0,
    )

    keyboard = []

    for player in substitutes:

        player_overall = getattr(
            player,
            "overall",
            0,
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    (
                        f"⬆️ {player.name} "
                        f"• {position} "
                        f"• {player_overall}"
                    ),
                    callback_data=(
                        f"subs_replace:"
                        f"{club_id}:"
                        f"{player_id}:"
                        f"{player.id}"
                    ),
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "⬅️ BACK TO XI",
                callback_data=(
                    f"subs_refresh:{club_id}"
                ),
            )
        ]
    )

    await query.edit_message_text(
        (
            "🔄 REPLACE PLAYER\n\n"
            f"⬇️ {selected.name}\n"
            f"{position} • {overall}\n\n"
            "Available substitutes:\n"
            "Only the same position is shown."
        ),
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ==========================================================
# MAKE SUBSTITUTION
# ==========================================================
async def subs_replace_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    try:

        (
            _,
            club_id,
            player_out_id,
            player_in_id,
        ) = str(
            query.data
        ).split(":")

        club_id = int(club_id)
        player_out_id = int(
            player_out_id
        )
        player_in_id = int(
            player_in_id
        )

    except Exception:


        return

    match_data = None

    for data in ACTIVE_FRIENDLY_MATCHES.values():

        if (
            query.from_user.id
            in {
                data["challenger_id"],
                data["opponent_id"],
            }
        ):

            match_data = data

            break

    if match_data is None:


        return

    # SECURITY: the user who clicks must own the club being changed.
    if not user_owns_club_in_match(
        match_data,
        query.from_user.id,
        club_id,
    ):

        return

    engine = match_data["engine"]

    if not engine.substitution_window_open:


        return

    success, result = (
        engine.make_substitution(
            club_id=club_id,
            player_out_id=player_out_id,
            player_in_id=player_in_id,
        )
    )

    if not success:


        return


    await query.edit_message_text(
        (
            "✅ SUBSTITUTION CONFIRMED\n\n"
            f"⬇️ {result['player_out_name']}\n"
            f"{result['player_out_position']} • "
            f"{result['player_out_overall']}\n\n"
            f"⬆️ {result['player_in_name']}\n"
            f"{result['player_in_position']} • "
            f"{result['player_in_overall']}\n\n"
            "The change will appear as the "
            "first event of the second half."
        )
    )


# ==========================================================
# SUB REFRESH
# ==========================================================
async def subs_refresh_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    try:
        club_id = int(
            str(
                query.data
            ).split(":")[1]
        )
    except Exception:

        return

    match_data = find_active_match_for_user(
        query.from_user.id
    )

    if match_data is None:

        return

    # SECURITY: the clicked button can never be used
    # to operate the opponent's club.
    if not user_owns_club_in_match(
        match_data,
        query.from_user.id,
        club_id,
    ):

        return

    engine = match_data["engine"]

    if not engine.substitution_window_open:

        return


    players = engine.get_starting_players(
        club_id
    )

    if not players:
        await query.message.reply_text(
            "❌ No starting players found."
        )
        return

    keyboard = []

    for player in players:

        position = str(
            getattr(
                player,
                "lineup_position",
                getattr(
                    player,
                    "position",
                    "",
                ),
            )
        ).upper()

        overall = getattr(
            player,
            "overall",
            0,
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    (
                        f"{player.name} • "
                        f"{position} • "
                        f"{overall}"
                    ),
                    callback_data=(
                        f"subs_player:"
                        f"{club_id}:"
                        f"{player.id}"
                    ),
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "🔄 REFRESH",
                callback_data=(
                    f"subs_refresh:{club_id}"
                ),
            )
        ]
    )

    # IMPORTANT:
    # Send a NEW message instead of editing the live match.
    # Therefore the live scoreboard remains visible and the
    # other manager can use his own button independently.
    await query.message.reply_text(
        (
            "🔄 𝐒𝐔𝐁𝐒𝐓𝐈𝐓𝐔𝐓𝐈𝐎𝐍𝐒\n\n"
            "👇 Select a player from YOUR XI:"
        ),
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ==========================================================
# SAFE TELEGRAM OPERATIONS
# ==========================================================

async def _telegram_with_retry(
    operation,
    *,
    attempts: int = 4,
    base_delay: float = 1.5,
    operation_name: str = "Telegram operation",
):
    """
    Telegram can occasionally time out while the match itself is healthy.
    Retry transient network/timeout errors instead of killing the friendly.
    """
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            return await operation()

        except RetryAfter as error:
            last_error = error
            retry_after = float(
                getattr(error, "retry_after", 2)
            )
            await asyncio.sleep(
                min(max(retry_after, 1.0), 15.0)
            )

        except BadRequest:
            # BadRequest is not a transient network error.
            # Let the caller decide how to handle it.
            raise

        except (TimedOut, NetworkError) as error:
            last_error = error

            if attempt >= attempts:
                break

            delay = base_delay * attempt
            print(
                f"⚠️ {operation_name} timeout/network "
                f"(attempt {attempt}/{attempts}), "
                f"retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

        except Exception:
            raise

    print(
        f"❌ {operation_name} failed after "
        f"{attempts} attempts:",
        type(last_error).__name__ if last_error else "Unknown",
        last_error,
    )
    return None


async def _safe_edit_message(
    context,
    *,
    chat_id,
    message_id,
    text,
    reply_markup=None,
):
    async def operation():
        return await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )

    try:
        return await _telegram_with_retry(
            operation,
            operation_name="Live message edit",
        )
    except BadRequest as error:
        # This is a normal situation: the engine may generate an event
        # while the rendered Telegram text/keyboard is still identical.
        if "Message is not modified" in str(error):
            return True

        print(
            "⚠️ SAFE EDIT ERROR:",
            type(error).__name__,
            error,
        )
        return None
    except Exception as error:
        if "Message is not modified" in str(error):
            return True

        print(
            "⚠️ SAFE EDIT ERROR:",
            type(error).__name__,
            error,
        )
        return None


async def _safe_reply_text(
    message,
    text,
    *,
    reply_markup=None,
):
    async def operation():
        return await message.reply_text(
            text,
            reply_markup=reply_markup,
        )

    return await _telegram_with_retry(
        operation,
        operation_name="Telegram message send",
    )


# ==========================================================
# LIVE MATCH
# ==========================================================
async def start_friendly_match(
    context,
    match_id,
    home_team,
    away_team,
    chat_id,
    live_message_id,
):

    # ======================================================
    # ENGINE
    # ======================================================

    engine = MatchEngine(
        home_team,
        away_team,
    )

    # ======================================================
    # MATCH DATA
    # ======================================================

    pending = (
        context.bot_data
        .get(
            "pending_friendlies",
            {},
        )
        .get(match_id)
    )

    match_data = {
        "engine": engine,
        "home_team": home_team,
        "away_team": away_team,
        "home_club_id": home_team.club_id,
        "away_club_id": away_team.club_id,
        "challenger_id": None,
        "opponent_id": None,
        "chat_id": chat_id,
        "live_message_id": live_message_id,
        "live_events": [],
        "last_telegram_update": 0.0,
        "db_match_id": pending.get("db_match_id") if pending else None,
        "stake": pending.get("stake", 0) if pending else 0,
        "stake_settled": False,
        "stake_refunded": False,
    }

    if pending:

        match_data[
            "challenger_id"
        ] = pending[
            "challenger_id"
        ]

        match_data[
            "opponent_id"
        ] = pending[
            "opponent_id"
        ]

    ACTIVE_FRIENDLY_MATCHES[
        match_id
    ] = match_data

    # ======================================================
    # EVENT QUEUE
    # ======================================================

    event_queue = asyncio.Queue()

    async def on_match_event(event):

        await event_queue.put(
            event
        )

    engine.event_callback = (
        on_match_event
    )

    # ======================================================
    # TELEGRAM EVENT WORKER
    # ======================================================

    # Engine events can arrive much faster than Telegram allows
    # message edits. Collect them immediately, but update the
    # live Telegram message at most once every 2.5 seconds.
    LIVE_UPDATE_INTERVAL = 1.2

    async def telegram_event_worker():

        last_update = 0.0
        pending_update = False

        while True:

            timeout = max(
                0.1,
                LIVE_UPDATE_INTERVAL
                - (time.monotonic() - last_update),
            )

            try:
                event = await asyncio.wait_for(
                    event_queue.get(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                event = "__TICK__"

            if event is None:
                event_queue.task_done()
                break

            if event != "__TICK__":
                match_data["live_events"].append(event)
                match_data["live_events"] = match_data["live_events"][-30:]
                pending_update = True
                event_queue.task_done()

            now = time.monotonic()

            if (
                pending_update
                and now - last_update
                >= LIVE_UPDATE_INTERVAL
            ):

                try:

                    edit_result = await _safe_edit_message(
                        context,
                        chat_id=chat_id,
                        message_id=live_message_id,
                        text=build_live_message(
                            match_data
                        ),
                        reply_markup=build_live_keyboard(
                            match_data
                        ),
                    )

                    if edit_result is not None:
                        last_update = time.monotonic()
                        pending_update = False

                except Exception as error:

                    error_text = str(error)

                    if "Message is not modified" in error_text:

                        last_update = time.monotonic()
                        pending_update = False

                    elif "RetryAfter" in error_text:

                        # Do not retry immediately and trigger another
                        # flood-control error.
                        last_update = time.monotonic()

                    else:

                        print(
                            "⚠️ LIVE MESSAGE ERROR:",
                            type(error).__name__,
                            error,
                        )

        # One final update after the match.
        if pending_update:

            try:

                await _safe_edit_message(
                    context,
                    chat_id=chat_id,
                    message_id=live_message_id,
                    text=build_live_message(
                        match_data
                    ),
                    reply_markup=build_live_keyboard(
                        match_data
                    ),
                )

            except Exception as error:

                if "Message is not modified" not in str(error):

                    print(
                        "⚠️ FINAL LIVE UPDATE ERROR:",
                        type(error).__name__,
                        error,
                    )

    # ======================================================
    # START TELEGRAM EVENT WORKER
    # ======================================================

    # IMPORTANT:
    # telegram_event_worker() is only the coroutine definition.
    # It must be scheduled before the match starts.
    telegram_worker = asyncio.create_task(
        telegram_event_worker()
    )

    # ======================================================
    # RUN MATCH — NO VIDEO / NO GRAPHICS
    # ======================================================

    result = None

    try:
        # The football engine runs normally and sends its events to
        # telegram_event_worker. No renderer or MP4 generation is used.
        result = await engine.play_live()

        if result is None:
            raise RuntimeError(
                "Match engine finished without a result."
            )

    except Exception as error:

        print(
            "❌ LIVE MATCH ERROR:",
            type(error).__name__,
            error,
        )

        try:
            engine.stop()
        except Exception:
            pass

        try:
            await event_queue.put(None)
            await telegram_worker
        except Exception as worker_error:
            print(
                "⚠️ TELEGRAM WORKER STOP ERROR:",
                type(worker_error).__name__,
                worker_error,
            )

        ACTIVE_FRIENDLY_MATCHES.pop(
            match_id,
            None,
        )

        context.bot_data[
            "pending_friendlies"
        ].pop(
            match_id,
            None,
        )

        return

    # ======================================================
    # STOP EVENT WORKER
    # ======================================================

    try:

        await event_queue.join()
        await event_queue.put(None)
        await telegram_worker

    except Exception as error:

        print(
            "⚠️ TELEGRAM WORKER ERROR:",
            type(error).__name__,
            error,
        )

    # FINAL MATCH REPORT
    # ======================================================

    try:

        final_report = build_final_match_report(
            result,
            home_team,
            away_team,
        )

        await _safe_edit_message(
            context,
            chat_id=chat_id,
            message_id=live_message_id,
            reply_markup=None,
            text=(
                "🏁 𝐅𝐔𝐋𝐋 𝐓𝐈𝐌𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🔴 {home_team.name} "
                f"{result.home_score}"
                "  -  "
                f"{result.away_score} "
                f"{away_team.name} 🔵\n"
                "⏱️ 90'\n\n"
                f"{final_report}"
            ),
        )

    except Exception as error:

        print(
            "❌ FINAL MATCH REPORT ERROR:",
            type(error).__name__,
            error,
        )

    # ======================================================
    # COIN REWARD — ADDITIVE ONLY
    # ======================================================

    # Persist result first, then pay rewards exactly once.
    db_match_id = match_data.get("db_match_id")
    await _finish_friendly_db_match(
        db_match_id,
        int(result.home_score),
        int(result.away_score),
        result,
    )
    await _give_friendly_rewards_once(
        db_match_id,
        match_data.get("challenger_id"),
        match_data.get("opponent_id"),
        int(result.home_score),
        int(result.away_score),
    )
    await _settle_friendly_stake(
        match_data,
        int(result.home_score),
        int(result.away_score),
    )

    # ======================================================
    # END MUSIC
    # ======================================================

    await send_friendly_end_music(
        context,
        chat_id,
    )

    # ======================================================
    # CLEANUP
    # ======================================================

    ACTIVE_FRIENDLY_MATCHES.pop(
        match_id,
        None,
    )

    context.bot_data[
        "pending_friendlies"
    ].pop(
        match_id,
        None,
    )


# ==========================================================
# FRIENDLY INVITATION / MATCH FLOW
# ==========================================================

def _friendly_pending_store(context):
    return context.bot_data.setdefault(
        "pending_friendlies",
        {},
    )


def _find_pending_invitation(
    context,
    match_id,
):
    return _friendly_pending_store(
        context
    ).get(str(match_id))


async def friendly(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Create a local in-memory friendly invitation."""

    if update.effective_user is None or update.message is None:
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage:\n/friendly @username"
        )
        return

    challenger = update.effective_user
    opponent = context.args[0].strip()

    if not opponent.startswith("@") or len(opponent) <= 1:
        await update.message.reply_text(
            "❌ Please mention a valid username."
        )
        return

    club = await get_club_by_owner(
        challenger.id
    )

    if club is None:
        await update.message.reply_text(
            "❌ Create your club first."
        )
        return

    if opponent.lower() == (
        f"@{challenger.username or ''}".lower()
    ):
        await update.message.reply_text(
            "❌ You cannot challenge yourself."
        )
        return

    # Find the invited Telegram user now, so the accept button
    # can be securely restricted to that account.
    invited_user = await get_user_by_username(
        opponent
    )

    if invited_user is None:
        await update.message.reply_text(
            "❌ This username is not registered."
        )
        return

    for existing in _friendly_pending_store(context).values():
        if (
            existing.get("challenger_id") == challenger.id
            and existing.get("status") == "PENDING"
        ):
            await update.message.reply_text(
                "❌ You already have a pending friendly challenge."
            )
            return

    match_id = secrets.token_hex(6)

    pending = {
        "match_id": match_id,
        "challenger_id": challenger.id,
        "opponent_id": invited_user.id,
        "challenger_username": (
            f"@{challenger.username}"
            if challenger.username
            else challenger.first_name
        ),
        "opponent_username": opponent,
        "chat_id": (
            update.effective_chat.id
            if update.effective_chat
            else challenger.id
        ),
        "status": "PENDING",
    }

    _friendly_pending_store(
        context
    )[match_id] = pending

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ ACCEPT",
                    callback_data=(
                        f"friendly_accept:{match_id}"
                    ),
                ),
                InlineKeyboardButton(
                    "❌ DECLINE",
                    callback_data=(
                        f"friendly_decline:{match_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏳️ FORFEIT",
                    callback_data=(
                        f"friendly_forfeit:{match_id}"
                    ),
                )
            ],
        ]
    )

    await update.message.reply_text(
        (
            "🤝 𝐅𝐑𝐈𝐄𝐍𝐃𝐋𝐘 𝐂𝐇𝐀𝐋𝐋𝐄𝐍𝐆𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 {club.name}\n"
            f"🎯 Opponent: {opponent}\n\n"
            "⏳ Waiting for the opponent to accept..."
        ),
        reply_markup=keyboard,
    )


async def friendly_accept_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if query is None:
        return

    try:
        match_id = str(query.data).split(":", 1)[1]
    except Exception:
        return

    pending = _find_pending_invitation(context, match_id)
    if pending is None:
        await _safe_query_answer(query, "❌ Challenge no longer exists.", True)
        return

    if pending.get("status") != "PENDING":
        await _safe_query_answer(query, "❌ This challenge is no longer pending.", True)
        return

    if query.from_user.id != pending["opponent_id"]:
        await _safe_query_answer(query, "❌ This challenge is not for you.", True)
        return

    # Paid friendly: the challenger and opponent both pay the stake atomically.
    stake = int(pending.get("stake") or 0)
    if stake > 0:
        async with AsyncSessionLocal() as session:
            challenger = await session.get(User, int(pending["challenger_id"]))
            opponent = await session.get(User, int(pending["opponent_id"]))

            if challenger is None or opponent is None:
                await _safe_query_answer(query, "❌ User not found.", True)
                return

            if int(challenger.coins or 0) < stake:
                pending["status"] = "CANCELLED"
                await _safe_query_answer(query, "❌ Challenger no longer has enough coins.", True)
                await query.message.reply_text("❌ Friendly Pay cancelled: insufficient challenger balance.")
                return

            if int(opponent.coins or 0) < stake:
                await _safe_query_answer(query, "❌ You don't have enough coins.", True)
                return

            challenger.coins = int(challenger.coins or 0) - stake
            opponent.coins = int(opponent.coins or 0) - stake
            await session.commit()

        pending["opponent_stake_taken"] = True
        pending["stake_taken"] = True

    await _safe_query_answer(query, "Challenge accepted!")
    await query.edit_message_text(
        (
            "💰 𝐅𝐑𝐈𝐄𝐍𝐃𝐋𝐘 𝐏𝐀𝐘\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Stake: {stake:,} coins each\n"
            f"🏆 Pot: {stake * 2:,} coins\n\n"
            "⏳ Preparing the match..."
        ) if stake else (
            "🤝 𝐅𝐑𝐈𝐄𝐍𝐃𝐋𝐘 𝐀𝐂𝐂𝐄𝐏𝐓𝐄𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⏳ Preparing the match..."
        )
    )

    await _start_accepted_friendly(query, context, pending, match_id)


async def friendly_decline_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    try:
        match_id = str(
            query.data
        ).split(":", 1)[1]
    except Exception:
        await query.answer(
            "❌ Invalid challenge.",
            show_alert=True,
        )
        return

    pending = _find_pending_invitation(
        context,
        match_id,
    )

    if pending is None:
        await query.answer(
            "❌ Challenge not found.",
            show_alert=True,
        )
        return

    if query.from_user.id != pending["opponent_id"]:
        await query.answer(
            "❌ You cannot decline this challenge.",
            show_alert=True,
        )
        return

    pending["status"] = "DECLINED"

    await query.answer(
        "Challenge declined."
    )

    await query.edit_message_text(
        (
            "❌ 𝐅𝐑𝐈𝐄𝐍𝐃𝐋𝐘 𝐃𝐄𝐂𝐋𝐈𝐍𝐄𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "The opponent declined the challenge."
        )
    )


async def friendlypay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a Friendly Pay challenge. Coins are virtual only."""
    if update.effective_user is None or update.message is None:
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage:\n/friendlypay @username\n\nThen choose the stake."
        )
        return

    opponent = context.args[0].strip()
    if not opponent.startswith("@"):
        await update.message.reply_text("❌ Use /friendlypay @username")
        return

    challenger = update.effective_user
    invited_user = await get_user_by_username(opponent)
    if invited_user is None:
        await update.message.reply_text("❌ This username is not registered.")
        return
    if invited_user.id == challenger.id:
        await update.message.reply_text("❌ You cannot challenge yourself.")
        return

    club = await get_club_by_owner(challenger.id)
    if club is None:
        await update.message.reply_text("❌ Create your club first.")
        return

    match_id = secrets.token_hex(6)
    pending = {
        "match_id": match_id,
        "challenger_id": challenger.id,
        "opponent_id": invited_user.id,
        "challenger_username": (
            f"@{challenger.username}" if challenger.username else challenger.first_name
        ),
        "opponent_username": opponent,
        "chat_id": update.effective_chat.id if update.effective_chat else challenger.id,
        "status": "CHOOSING_STAKE",
        "stake": 0,
    }
    _friendly_pay_store(context)[match_id] = pending

    await update.message.reply_text(
        (
            "💰 𝐅𝐑𝐈𝐄𝐍𝐃𝐋𝐘 𝐏𝐀𝐘\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 {club.name}\n"
            f"🎯 Opponent: {opponent}\n\n"
            "💵 Choose the virtual coin stake.\n"
            "Both managers must put the same amount."
        ),
        reply_markup=_friendly_pay_keyboard(match_id),
    )


async def friendlypay_amount_callback(update, context):
    query = update.callback_query
    if query is None:
        return
    try:
        _, match_id, amount = str(query.data).split(":")
        amount = int(amount)
    except Exception:
        return

    pending = _friendly_pay_store(context).get(match_id)
    if pending is None or pending.get("status") != "CHOOSING_STAKE":
        await _safe_query_answer(query, "❌ This offer expired.", True)
        return

    if query.from_user.id != pending["challenger_id"]:
        await _safe_query_answer(query, "❌ Only the challenger chooses the stake.", True)
        return

    async with AsyncSessionLocal() as session:
        user = await session.get(User, int(query.from_user.id))
        if user is None or int(user.coins or 0) < amount:
            await _safe_query_answer(query, "❌ Not enough coins.", True)
            return

    pending["stake"] = amount
    pending["status"] = "PENDING"

    await _safe_query_answer(query, "Stake selected.")
    await query.edit_message_text(
        (
            "💰 𝐅𝐑𝐈𝐄𝐍𝐃𝐋𝐘 𝐏𝐀𝐘\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 {pending['challenger_username']}\n"
            f"🔵 {pending['opponent_username']}\n\n"
            f"💵 Stake: {amount:,} coins each\n"
            f"🏆 Pot: {amount * 2:,} coins\n\n"
            "The opponent must accept and pay the same stake."
        ),
        reply_markup=_friendly_pay_accept_keyboard(match_id),
    )


async def friendlypay_accept_callback(update, context):
    """
    Accept a Friendly Pay offer and hand it to the normal Friendly
    acceptance flow.

    Friendly Pay stores its pending offer in `friendly_pay_pending`,
    while `friendly_accept_callback()` reads `pending_friendlies`.
    The old adapter only changed query.data, so the normal callback
    could never find the offer.

    We deliberately DO NOT debit coins here. The normal
    `friendly_accept_callback()` performs the balance check and the
    atomic debit exactly once.
    """
    query = update.callback_query

    if query is None:
        return

    try:
        match_id = str(query.data).split(":", 1)[1]
    except Exception:
        await _safe_query_answer(
            query,
            "❌ Invalid Friendly Pay offer.",
            True,
        )
        return

    pay_store = _friendly_pay_store(context)
    pending = pay_store.get(match_id)

    if pending is None:
        await _safe_query_answer(
            query,
            "❌ Friendly Pay offer no longer exists.",
            True,
        )
        return

    if pending.get("status") != "PENDING":
        await _safe_query_answer(
            query,
            "❌ This Friendly Pay offer is no longer available.",
            True,
        )
        return

    if query.from_user.id != pending.get("opponent_id"):
        await _safe_query_answer(
            query,
            "❌ This offer is not for you.",
            True,
        )
        return

    stake = int(pending.get("stake") or 0)

    if stake <= 0:
        await _safe_query_answer(
            query,
            "❌ Invalid Friendly Pay stake.",
            True,
        )
        return

    # Verify the challenger still has enough coins before moving the
    # offer into the normal Friendly flow. The actual debit is done
    # only once by friendly_accept_callback().
    async with AsyncSessionLocal() as session:
        challenger = await session.get(
            User,
            int(pending["challenger_id"]),
        )
        opponent = await session.get(
            User,
            int(pending["opponent_id"]),
        )

        if challenger is None or opponent is None:
            await _safe_query_answer(
                query,
                "❌ User account not found.",
                True,
            )
            return

        if int(challenger.coins or 0) < stake:
            pending["status"] = "CANCELLED"
            await _safe_query_answer(
                query,
                "❌ Challenger no longer has enough coins.",
                True,
            )
            try:
                await query.edit_message_text(
                    "❌ Friendly Pay cancelled: insufficient challenger balance."
                )
            except Exception:
                pass
            return

        if int(opponent.coins or 0) < stake:
            await _safe_query_answer(
                query,
                "❌ You don't have enough coins.",
                True,
            )
            return

    # IMPORTANT: friendly_accept_callback() reads this store.
    # Copy the exact same pending object so all Friendly Pay fields
    # (stake, challenger, opponent, etc.) are preserved.
    pending_store = _friendly_pending_store(context)
    pending_store[match_id] = pending

    # Remove the duplicate source entry. The active match will now be
    # owned by the normal Friendly lifecycle.
    pay_store.pop(match_id, None)

    # Reuse the normal secure acceptance flow. It will:
    # - verify the opponent again
    # - debit BOTH stakes exactly once
    # - create the DB match
    # - load both lineups
    # - start the live engine
    query.data = f"friendly_accept:{match_id}"

    await friendly_accept_callback(
        update,
        context,
    )


async def friendlypay_decline_callback(update, context):
    query = update.callback_query
    if query is None:
        return
    try:
        match_id = str(query.data).split(":", 1)[1]
    except Exception:
        return
    pending = _friendly_pay_store(context).get(match_id)
    if pending is None:
        return
    if query.from_user.id != pending["opponent_id"]:
        await _safe_query_answer(query, "❌ This offer is not for you.", True)
        return
    pending["status"] = "DECLINED"
    await _safe_query_answer(query, "Offer declined.")
    await query.edit_message_text("❌ Friendly Pay declined.")


async def friendly_forfeit_callback(update, context):
    query = update.callback_query
    if query is None:
        return
    try:
        match_id = str(query.data).split(":", 1)[1]
    except Exception:
        return

    pending = _friendly_pending_store(context).get(match_id)
    if pending is None:
        pending = _friendly_pay_store(context).get(match_id)

    if pending is None:
        await _safe_query_answer(query, "❌ Match not found.", True)
        return

    # Forfeit cancels a pending challenge before acceptance.
    # Only the challenger who created the invitation can use it.
    if query.from_user.id != pending.get("challenger_id"):
        await _safe_query_answer(query, "❌ Only the challenger can forfeit this pending match.", True)
        return

    if pending.get("status") not in {"PENDING", "CHOOSING_STAKE"}:
        await _safe_query_answer(query, "❌ The match is already accepted/live.", True)
        return

    pending["status"] = "FORFEITED"
    await _safe_query_answer(query, "Challenge cancelled.")
    await query.edit_message_text(
        "🏳️ 𝐅𝐎𝐑𝐅𝐄𝐈𝐓\n━━━━━━━━━━━━━━━━━━━━\nThe friendly challenge has been cancelled."
    )


# ==========================================================
# SUBSTITUTION COMMAND
# ==========================================================

async def subs_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.effective_user is None or update.message is None:
        return

    match_data = find_active_match_for_user(
        update.effective_user.id
    )

    if match_data is None:
        await update.message.reply_text(
            "❌ You are not in an active friendly."
        )
        return

    engine = match_data["engine"]

    if not engine.substitution_window_open:
        await update.message.reply_text(
            "🔒 Substitutions are only available at half-time."
        )
        return

    club_id = (
        match_data["home_club_id"]
        if update.effective_user.id
        == match_data["challenger_id"]
        else match_data["away_club_id"]
    )

    players = engine.get_starting_players(
        club_id
    )

    keyboard = []

    for player in players:
        position = str(
            getattr(
                player,
                "lineup_position",
                getattr(
                    player,
                    "position",
                    "",
                ),
            )
        ).upper()

        keyboard.append(
            [
                InlineKeyboardButton(
                    (
                        f"{player.name} • "
                        f"{position} • "
                        f"{getattr(player, 'overall', 0)}"
                    ),
                    callback_data=(
                        f"subs_player:"
                        f"{club_id}:"
                        f"{player.id}"
                    ),
                )
            ]
        )

    await update.message.reply_text(
        (
            "🔄 𝐒𝐔𝐁𝐒𝐓𝐈𝐓𝐔𝐓𝐈𝐎𝐍𝐒\n\n"
            "Select a player from your XI:"
        ),
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ==========================================================
# FRIENDLY CALLBACK ROUTER
# ==========================================================

async def friendly_callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Fast callback gateway.

    The Telegram callback is ACKed and the handler returns immediately.
    The real operation is then scheduled as a separate task, so a slow
    database/engine operation can NEVER keep the Telegram button spinning.
    """
    query = update.callback_query

    if query is None or not query.data:
        return

    data = str(query.data)

    # ACK FIRST and finish this callback handler immediately.
    try:
        await query.answer()
    except Exception as error:
        print(
            "⚠️ CALLBACK ACK ERROR:",
            type(error).__name__,
            error,
        )
        # Even if Telegram says the query is already expired, do not
        # run another answer attempt.

    if data.startswith("friendly_accept:"):
        context.application.create_task(
            friendly_accept_callback(update, context),
            update=update,
        )
        return

    if data.startswith("friendly_decline:"):
        context.application.create_task(
            friendly_decline_callback(update, context),
            update=update,
        )
        return

    if data.startswith("friendlypay_amount:"):
        context.application.create_task(
            friendlypay_amount_callback(update, context),
            update=update,
        )
        return

    if data.startswith("friendlypay_accept:"):
        context.application.create_task(
            friendlypay_accept_callback(update, context),
            update=update,
        )
        return

    if data.startswith("friendlypay_decline:"):
        context.application.create_task(
            friendlypay_decline_callback(update, context),
            update=update,
        )
        return

    if data.startswith("friendly_forfeit:"):
        context.application.create_task(
            friendly_forfeit_callback(update, context),
            update=update,
        )
        return

    if data.startswith("subs_player:"):
        context.application.create_task(
            subs_player_callback(update, context),
            update=update,
        )
        return

    if data.startswith("subs_replace:"):
        context.application.create_task(
            subs_replace_callback(update, context),
            update=update,
        )
        return

    if data.startswith("subs_refresh:"):
        context.application.create_task(
            subs_refresh_callback(update, context),
            update=update,
        )
        return


# ==========================================================
# HANDLERS
# ==========================================================

friendly_handler = CommandHandler(
    "friendly",
    friendly,
)

subs_handler = CommandHandler(
    "subs",
    subs_command,
)

friendly_accept_handler = CallbackQueryHandler(
    friendly_accept_callback,
    pattern=r"^friendly_accept:.+$",
)

friendly_decline_handler = CallbackQueryHandler(
    friendly_decline_callback,
    pattern=r"^friendly_decline:.+$",
)

friendly_callback_router_handler = CallbackQueryHandler(
    friendly_callback_router,
    pattern=r"^(friendly_accept|friendly_decline|friendlypay_amount|friendlypay_accept|friendlypay_decline|friendly_forfeit|subs_player|subs_replace|subs_refresh):.+$",
)

subs_player_handler = CallbackQueryHandler(
    subs_player_callback,
    pattern=r"^subs_player:\d+:\d+$",
)

subs_replace_handler = CallbackQueryHandler(
    subs_replace_callback,
    pattern=r"^subs_replace:\d+:\d+:\d+$",
)

subs_refresh_handler = CallbackQueryHandler(
    subs_refresh_callback,
    pattern=r"^subs_refresh:\d+$",
)

friendlypay_handler = CommandHandler(
    "friendlypay",
    friendlypay,
)

friendlypay_callback_handler = CallbackQueryHandler(
    friendly_callback_router,
    pattern=r"^(friendlypay_amount|friendlypay_accept|friendlypay_decline|friendly_forfeit):.+$",
)

friendly_forfeit_handler = CallbackQueryHandler(
    friendly_forfeit_callback,
    pattern=r"^friendly_forfeit:.+$",
)
