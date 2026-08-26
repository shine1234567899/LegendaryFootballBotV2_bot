from pathlib import Path

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

from sqlalchemy import select, delete

from database.database import AsyncSessionLocal

from database.models import (
    Club,
    ClubPlayer,
    Player,
    SavedLineup,
    SavedLineupPlayer,
)


# ==========================================================
# PATH
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LINEUP_BANNER = (
    BASE_DIR
    / "assets"
    / "LINEUP.jpg"
)


# ==========================================================
# FORMATIONS
# ==========================================================

FORMATIONS = {

    "4-4-2": [
        ["ATT", "ATT"],
        ["MID", "MID", "MID", "MID"],
        ["DEF", "DEF", "DEF", "DEF"],
        ["GK"],
    ],

    "4-3-3": [
        ["ATT"],
        ["ATT", "ATT"],
        ["MID", "MID", "MID"],
        ["DEF", "DEF", "DEF", "DEF"],
        ["GK"],
    ],

    "4-2-3-1": [
        ["ATT"],
        ["MID", "MID", "MID"],
        ["MID", "MID"],
        ["DEF", "DEF", "DEF", "DEF"],
        ["GK"],
    ],

    "4-3-1-2": [
        ["ATT", "ATT"],
        ["MID"],
        ["MID", "MID", "MID"],
        ["DEF", "DEF", "DEF", "DEF"],
        ["GK"],
    ],

    "3-5-2": [
        ["ATT", "ATT"],
        ["MID", "MID", "MID", "MID", "MID"],
        ["DEF", "DEF", "DEF"],
        ["GK"],
    ],

    "3-4-3": [
        ["ATT", "ATT", "ATT"],
        ["MID", "MID", "MID", "MID"],
        ["DEF", "DEF", "DEF"],
        ["GK"],
    ],

    "5-3-2": [
        ["ATT", "ATT"],
        ["MID", "MID", "MID"],
        ["DEF", "DEF", "DEF", "DEF", "DEF"],
        ["GK"],
    ],

    "5-4-1": [
        ["ATT"],
        ["MID", "MID", "MID", "MID"],
        ["DEF", "DEF", "DEF", "DEF", "DEF"],
        ["GK"],
    ],
}


# ==========================================================
# CLUB + PLAYERS
# ==========================================================

async def get_club_players(
    user_id: int,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Club).where(
                Club.owner_id == user_id
            )
        )

        club = (
            result.scalar_one_or_none()
        )

        if club is None:

            return None, []

        result = await session.execute(
            select(Player)
            .join(
                ClubPlayer,
                ClubPlayer.player_id
                == Player.id,
            )
            .where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
            .order_by(
                Player.overall.desc()
            )
        )

        players = result.scalars().all()

        return club, players


# ==========================================================
# LOAD SAVED LINEUP
# ==========================================================

async def load_saved_lineup(
    club_id: int,
    formation: str,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(SavedLineup).where(
                SavedLineup.club_id
                == club_id,

                SavedLineup.formation
                == formation,
            )
        )

        saved = (
            result.scalar_one_or_none()
        )

        if saved is None:

            return {}

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
                == saved.id,
            )
        )

        rows = result.all()

        lineup = {}

        for (
            saved_player,
            player,
        ) in rows:

            # Vérifie que le slot existe encore
            # dans la formation actuelle.

            slot_id = (
                saved_player.slot_id
            )

            lineup[slot_id] = {
                "id": player.id,
                "name": player.name,
                "overall": player.overall,
                "position": player.position,
            }

        return lineup


# ==========================================================
# SAVE LINEUP
# ==========================================================

async def save_lineup_to_database(
    user_id: int,
    formation: str,
    lineup_players: dict,
):

    # ======================================================
    # FORMATION CHECK
    # ======================================================

    if formation not in FORMATIONS:

        raise ValueError(
            "Invalid formation."
        )

    # ======================================================
    # EXACT 11
    # ======================================================

    if len(lineup_players) != 11:

        raise ValueError(
            "A lineup requires exactly 11 players."
        )

    # ======================================================
    # EXPECTED SLOTS
    # ======================================================

    expected_slots = set()

    for row_index, row in enumerate(
        FORMATIONS[formation]
    ):

        for slot_index in range(
            len(row)
        ):

            expected_slots.add(
                f"{row_index}_{slot_index}"
            )

    actual_slots = set(
        lineup_players.keys()
    )

    if actual_slots != expected_slots:

        raise ValueError(
            "Some lineup positions are missing."
        )

    # ======================================================
    # CLUB
    # ======================================================

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Club).where(
                Club.owner_id == user_id
            )
        )

        club = (
            result.scalar_one_or_none()
        )

        if club is None:

            raise ValueError(
                "Club not found."
            )

        # ==================================================
        # PLAYER IDS
        # ==================================================

        player_ids = [
            player["id"]
            for player
            in lineup_players.values()
        ]

        if len(
            set(player_ids)
        ) != 11:

            raise ValueError(
                "A player cannot appear twice."
            )

        # ==================================================
        # CLUB OWNERSHIP
        # ==================================================

        result = await session.execute(
            select(
                ClubPlayer.player_id
            )
            .where(
                ClubPlayer.club_id
                == club.id,

                ClubPlayer.is_current.is_(True),

                ClubPlayer.player_id.in_(
                    player_ids
                ),
            )
        )

        owned_ids = {
            row[0]
            for row in result.all()
        }

        if owned_ids != set(
            player_ids
        ):

            raise ValueError(
                "One or more players do not "
                "belong to your current squad."
            )

        # ==================================================
        # VERIFY POSITIONS
        # ==================================================

        for slot_id, data in (
            lineup_players.items()
        ):

            row_index, slot_index = (
                map(
                    int,
                    slot_id.split("_"),
                )
            )

            required_position = (
                FORMATIONS[
                    formation
                ][row_index][slot_index]
            )

            player_position = str(
                data["position"]
            ).upper()

            if (
                player_position
                != required_position
            ):

                raise ValueError(
                    f"{data['name']} is "
                    f"{player_position}, "
                    f"not {required_position}."
                )

        # ==================================================
        # FIND EXISTING SAVED LINEUP
        # ==================================================

        result = await session.execute(
            select(SavedLineup).where(
                SavedLineup.club_id
                == club.id,

                SavedLineup.formation
                == formation,
            )
        )

        saved_lineup = (
            result.scalar_one_or_none()
        )

        # ==================================================
        # CREATE
        # ==================================================

        if saved_lineup is None:

            saved_lineup = SavedLineup(
                club_id=club.id,
                formation=formation,
            )

            session.add(
                saved_lineup
            )

            await session.flush()

        # ==================================================
        # DELETE OLD PLAYERS
        # ==================================================

        await session.execute(
            delete(
                SavedLineupPlayer
            ).where(
                SavedLineupPlayer.saved_lineup_id
                == saved_lineup.id
            )
        )

        # ==================================================
        # INSERT NEW PLAYERS
        # ==================================================

        for slot_id, data in (
            lineup_players.items()
        ):

            saved_player = (
                SavedLineupPlayer(
                    saved_lineup_id=(
                        saved_lineup.id
                    ),
                    player_id=data["id"],
                    slot_id=slot_id,
                    position=str(
                        data["position"]
                    ).upper(),
                    shirt_number=None,
                    is_captain=False,
                )
            )

            session.add(
                saved_player
            )

        await session.commit()

        return saved_lineup.id


# ==========================================================
# FORMATION MENU
# ==========================================================

def formation_keyboard():

    keyboard = []

    formations = list(
        FORMATIONS.keys()
    )

    for i in range(
        0,
        len(formations),
        2,
    ):

        row = []

        for formation in formations[
            i:i + 2
        ]:

            row.append(
                InlineKeyboardButton(
                    f"⚽ {formation}",
                    callback_data=(
                        "lineup_formation:"
                        f"{formation}"
                    ),
                )
            )

        keyboard.append(row)

    return InlineKeyboardMarkup(
        keyboard
    )


def formation_text():

    return (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗟𝗜𝗡𝗘𝗨𝗣\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        "🏟️ CHOOSE YOUR FORMATION\n\n"
        "Select the tactical system "
        "your manager wants to use.\n\n"
        "🧤 GK  •  🛡️ DEF  •  "
        "⚙️ MID  •  ⚡ ATT\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ==========================================================
# POSITION EMOJI
# ==========================================================

def position_emoji(
    position,
):

    return {
        "GK": "🧤",
        "DEF": "🛡️",
        "MID": "⚙️",
        "ATT": "⚡",
    }.get(
        position,
        "⚽",
    )


# ==========================================================
# LINEUP KEYBOARD
# ==========================================================

def build_lineup_keyboard(
    formation,
    lineup=None,
):

    lineup = lineup or {}

    keyboard = []

    rows = FORMATIONS[
        formation
    ]

    for row_index, row in enumerate(
        rows
    ):

        buttons = []

        for slot_index, position in enumerate(
            row
        ):

            slot_id = (
                f"{row_index}_{slot_index}"
            )

            player = lineup.get(
                slot_id
            )

            if player:

                text = (
                    f"{position_emoji(position)} "
                    f"{player['name']} "
                    f"• {player['overall']}"
                )

            else:

                text = (
                    f"{position_emoji(position)} "
                    f"{position}"
                )

            buttons.append(
                InlineKeyboardButton(
                    text,
                    callback_data=(
                        "lineup_slot:"
                        f"{formation}:"
                        f"{row_index}:"
                        f"{slot_index}"
                    ),
                )
            )

        keyboard.append(
            buttons
        )

    keyboard.append([
        InlineKeyboardButton(
            "🔄 CHANGE FORMATION",
            callback_data=(
                "lineup_change"
            ),
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            "💾 SAVE LINEUP",
            callback_data=(
                "lineup_save"
            ),
        )
    ])

    return InlineKeyboardMarkup(
        keyboard
    )


# ==========================================================
# SAFE EDIT
# ==========================================================

async def edit_lineup_message(
    query,
    text,
    keyboard,
):

    message = query.message

    if message is None:
        return

    if message.photo:

        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
        )

    else:

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )


# ==========================================================
# /LINEUP
# ==========================================================

async def lineup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        update.message is None
        or update.effective_user is None
    ):

        return

    user_id = (
        update.effective_user.id
    )

    club, players = (
        await get_club_players(
            user_id
        )
    )

    if club is None:

        await update.message.reply_text(
            "❌ You don't have a club yet."
        )

        return

    # ------------------------------------------------------
    # Session temporaire
    # ------------------------------------------------------

    context.user_data[
        "lineup_formation"
    ] = None

    context.user_data[
        "lineup_players"
    ] = {}

    context.user_data[
        "selected_lineup_slot"
    ] = None

    # ------------------------------------------------------
    # Formation menu
    # ------------------------------------------------------

    text = formation_text()

    if LINEUP_BANNER.exists():

        with open(
            LINEUP_BANNER,
            "rb",
        ) as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=(
                    formation_keyboard()
                ),
            )

    else:

        await update.message.reply_text(
            text,
            reply_markup=(
                formation_keyboard()
            ),
        )


# ==========================================================
# MAIN CALLBACK
# ==========================================================

async def lineup_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    data = query.data or ""

    # ======================================================
    # FORMATION
    # ======================================================

    if data.startswith(
        "lineup_formation:"
    ):

        formation = data.split(
            ":",
            1
        )[1]

        if formation not in FORMATIONS:

            await query.answer(
                "❌ Invalid formation.",
                show_alert=True,
            )

            return

        await query.answer()

        user_id = (
            query.from_user.id
        )

        club, players = (
            await get_club_players(
                user_id
            )
        )

        if club is None:

            await query.answer(
                "❌ Club not found.",
                show_alert=True,
            )

            return

        # --------------------------------------------------
        # LOAD SAVED FORMATION
        # --------------------------------------------------

        try:

            saved_players = (
                await load_saved_lineup(
                    club.id,
                    formation,
                )
            )

        except Exception as error:

            print(
                "LOAD SAVED LINEUP ERROR:",
                type(error).__name__,
                error,
            )

            saved_players = {}

        # --------------------------------------------------
        # SESSION
        # --------------------------------------------------

        context.user_data[
            "lineup_formation"
        ] = formation

        context.user_data[
            "lineup_players"
        ] = saved_players

        context.user_data[
            "selected_lineup_slot"
        ] = None

        # --------------------------------------------------
        # MESSAGE
        # --------------------------------------------------

        if saved_players:

            text = (
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
                "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗟𝗜𝗡𝗘𝗨𝗣\n"
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
                f"🏟️ Formation : "
                f"{formation}\n\n"
                "✅ Saved lineup loaded.\n"
                f"👥 Players: "
                f"{len(saved_players)}/11\n\n"
                "👇 Select a position "
                "to change it."
            )

        else:

            text = (
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
                "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗟𝗜𝗡𝗘𝗨𝗣\n"
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
                f"🏟️ Formation : "
                f"{formation}\n\n"
                "🆕 No saved lineup "
                "for this formation.\n\n"
                "👇 Place your players."
            )

        await edit_lineup_message(
            query,
            text,
            build_lineup_keyboard(
                formation,
                saved_players,
            ),
        )

        return

    # ======================================================
    # CHANGE FORMATION
    # ======================================================

    if data == "lineup_change":

        await query.answer()

        await edit_lineup_message(
            query,
            formation_text(),
            formation_keyboard(),
        )

        return

    # ======================================================
    # SLOT
    # ======================================================

    if data.startswith(
        "lineup_slot:"
    ):

        parts = data.split(":")

        if len(parts) != 4:

            await query.answer(
                "❌ Invalid slot.",
                show_alert=True,
            )

            return

        formation = parts[1]

        try:

            row_index = int(
                parts[2]
            )

            slot_index = int(
                parts[3]
            )

        except ValueError:

            await query.answer(
                "❌ Invalid slot.",
                show_alert=True,
            )

            return

        if formation not in FORMATIONS:

            await query.answer(
                "❌ Invalid formation.",
                show_alert=True,
            )

            return

        rows = FORMATIONS[
            formation
        ]

        if row_index >= len(rows):

            await query.answer(
                "❌ Invalid row.",
                show_alert=True,
            )

            return

        if slot_index >= len(
            rows[row_index]
        ):

            await query.answer(
                "❌ Invalid slot.",
                show_alert=True,
            )

            return

        position = rows[
            row_index
        ][slot_index]

        context.user_data[
            "selected_lineup_slot"
        ] = {
            "formation": formation,
            "row": row_index,
            "slot": slot_index,
            "position": position,
        }

        await query.answer()

        await show_players_for_position(
            query,
            context,
            position,
        )

        return

    # ======================================================
    # BACK
    # ======================================================

    if data == "lineup_back":

        await query.answer()

        formation = context.user_data.get(
            "lineup_formation"
        )

        if formation not in FORMATIONS:

            await edit_lineup_message(
                query,
                formation_text(),
                formation_keyboard(),
            )

            return

        lineup_players = (
            context.user_data.get(
                "lineup_players",
                {},
            )
        )

        text = (
            "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
            "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗟𝗜𝗡𝗘𝗨𝗣\n"
            "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
            f"🏟️ Formation : "
            f"{formation}\n\n"
            f"👥 Players: "
            f"{len(lineup_players)}/11\n\n"
            "👇 Select a position."
        )

        await edit_lineup_message(
            query,
            text,
            build_lineup_keyboard(
                formation,
                lineup_players,
            ),
        )

        return

    # ======================================================
    # SAVE
    # ======================================================

    if data == "lineup_save":

        formation = context.user_data.get(
            "lineup_formation"
        )

        lineup_players = (
            context.user_data.get(
                "lineup_players",
                {},
            )
        )

        if formation not in FORMATIONS:

            await query.answer(
                "❌ Select a formation first.",
                show_alert=True,
            )

            return

        # --------------------------------------------------
        # REFRESH CURRENT SQUAD BEFORE SAVING
        # --------------------------------------------------
        # A trade can happen while the lineup screen is still open.
        # In that case context.user_data may still contain a player
        # who has already left this club. Remove only those stale
        # entries before attempting the database save.
        club, current_players = await get_club_players(
            query.from_user.id
        )

        if club is None:
            await query.answer(
                "❌ Club not found.",
                show_alert=True,
            )
            return

        current_player_ids = {
            player.id for player in current_players
        }

        stale_slots = [
            slot_id
            for slot_id, player in lineup_players.items()
            if player.get("id") not in current_player_ids
        ]

        if stale_slots:
            stale_names = [
                lineup_players[slot_id].get("name", "Unknown")
                for slot_id in stale_slots
            ]

            for slot_id in stale_slots:
                lineup_players.pop(slot_id, None)

            context.user_data["lineup_players"] = lineup_players

            names = ", ".join(stale_names[:3])
            if len(stale_names) > 3:
                names += f" +{len(stale_names) - 3}"

            await query.answer(
                (
                    f"⚠️ {names} n'est plus dans votre effectif. "
                    "Le joueur a été retiré du lineup : choisissez "
                    "un remplaçant puis sauvegardez."
                ),
                show_alert=True,
            )

            # Refresh the pitch immediately so the stale player
            # disappears from the buttons.
            text = (
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
                "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗟𝗜𝗡𝗘𝗨𝗣\n"
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
                f"🏟️ Formation : {formation}\n\n"
                "⚠️ Un joueur a quitté votre effectif.\n"
                f"👥 Players: {len(lineup_players)}/11\n\n"
                "👇 Sélectionnez un nouveau joueur."
            )

            await edit_lineup_message(
                query,
                text,
                build_lineup_keyboard(
                    formation,
                    lineup_players,
                ),
            )
            return

        if len(lineup_players) != 11:

            await query.answer(
                (
                    f"❌ You have "
                    f"{len(lineup_players)}/11 players."
                ),
                show_alert=True,
            )

            return

        try:

            await save_lineup_to_database(
                user_id=query.from_user.id,
                formation=formation,
                lineup_players=lineup_players,
            )

        except ValueError as error:

            await query.answer(
                f"❌ {error}",
                show_alert=True,
            )

            return

        except Exception as error:

            print(
                "SAVE LINEUP ERROR:",
                type(error).__name__,
                error,
            )

            await query.answer(
                "❌ Unable to save lineup.",
                show_alert=True,
            )

            return

        await query.answer(
            "✅ Lineup saved permanently!",
            show_alert=True,
        )

        text = (
            "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
            "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗟𝗜𝗡𝗘𝗨𝗣\n"
            "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
            f"🏟️ Formation : "
            f"{formation}\n\n"
            "💾 LINEUP SAVED\n\n"
            "✅ Your 11 players are now "
            "saved for this formation.\n\n"
            "You can change formation "
            "without losing this lineup."
        )

        await edit_lineup_message(
            query,
            text,
            build_lineup_keyboard(
                formation,
                lineup_players,
            ),
        )

        return


# ==========================================================
# PLAYERS FOR POSITION
# ==========================================================

async def show_players_for_position(
    query,
    context,
    position,
):

    user_id = (
        query.from_user.id
    )

    club, players = (
        await get_club_players(
            user_id
        )
    )

    if club is None:

        await query.answer(
            "❌ Club not found.",
            show_alert=True,
        )

        return

    lineup_players = (
        context.user_data.get(
            "lineup_players",
            {},
        )
    )

    # ------------------------------------------------------
    # Joueurs déjà utilisés ailleurs
    # ------------------------------------------------------

    used_player_ids = {
        player["id"]
        for player in
        lineup_players.values()
    }

    # ------------------------------------------------------
    # Slot actuellement sélectionné
    # ------------------------------------------------------

    selected_slot = (
        context.user_data.get(
            "selected_lineup_slot"
        )
    )

    current_slot = None

    if selected_slot:

        current_slot = (
            f"{selected_slot['row']}_"
            f"{selected_slot['slot']}"
        )

    compatible = []

    for player in players:

        if (
            player.position.upper()
            != position
        ):
            continue

        # Le joueur actuellement dans le
        # slot reste sélectionnable.

        if (
            player.id in used_player_ids
            and not (
                current_slot
                and lineup_players.get(
                    current_slot,
                    {},
                ).get("id")
                == player.id
            )
        ):
            continue

        compatible.append(
            player
        )

    keyboard = []

    for player in compatible:

        keyboard.append([
            InlineKeyboardButton(
                (
                    f"{player.name} "
                    f"• ⭐ {player.overall}"
                ),
                callback_data=(
                    f"lineup_player:"
                    f"{player.id}"
                ),
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ BACK TO PITCH",
            callback_data=(
                "lineup_back"
            ),
        )
    ])

    text = (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "       𝗣𝗟𝗔𝗬𝗘𝗥 𝗦𝗘𝗟𝗘𝗖𝗧𝗜𝗢𝗡\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        f"{position_emoji(position)} "
        f"SELECT {position}\n\n"
    )

    if not compatible:

        text += (
            f"❌ No {position} available."
        )

    else:

        text += (
            f"👥 {len(compatible)} "
            "players available."
        )

    await edit_lineup_message(
        query,
        text,
        InlineKeyboardMarkup(
            keyboard
        ),
    )


# ==========================================================
# PLAYER SELECTION
# ==========================================================

async def lineup_player_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    data = query.data or ""

    try:

        player_id = int(
            data.split(":")[1]
        )

    except (
        IndexError,
        ValueError,
    ):

        await query.answer(
            "❌ Invalid player.",
            show_alert=True,
        )

        return

    selected_slot = (
        context.user_data.get(
            "selected_lineup_slot"
        )
    )

    if not selected_slot:

        await query.answer(
            "❌ No position selected.",
            show_alert=True,
        )

        return

    formation = selected_slot[
        "formation"
    ]

    row_index = selected_slot[
        "row"
    ]

    slot_index = selected_slot[
        "slot"
    ]

    required_position = (
        selected_slot["position"]
    )

    user_id = (
        query.from_user.id
    )

    club, players = (
        await get_club_players(
            user_id
        )
    )

    if club is None:

        await query.answer(
            "❌ You don't have a club.",
            show_alert=True,
        )

        return

    player = next(
        (
            p
            for p in players
            if p.id == player_id
        ),
        None,
    )

    if player is None:

        await query.answer(
            "❌ Player not found.",
            show_alert=True,
        )

        return

    # ======================================================
    # POSITION
    # ======================================================

    if (
        player.position.upper()
        != required_position
    ):

        await query.answer(
            (
                f"❌ {player.name} is a "
                f"{player.position.upper()}."
            ),
            show_alert=True,
        )

        return

    lineup_players = (
        context.user_data.get(
            "lineup_players",
            {},
        )
    )

    current_slot = (
        f"{row_index}_{slot_index}"
    )

    # ======================================================
    # DUPLICATE
    # ======================================================

    for (
        slot_id,
        selected_player,
    ) in lineup_players.items():

        if (
            selected_player["id"]
            == player.id
            and slot_id
            != current_slot
        ):

            await query.answer(
                "❌ This player is already "
                "in your lineup.",
                show_alert=True,
            )

            return

    # ======================================================
    # PLACE PLAYER
    # ======================================================

    lineup_players[
        current_slot
    ] = {
        "id": player.id,
        "name": player.name,
        "overall": player.overall,
        "position": player.position,
    }

    context.user_data[
        "lineup_players"
    ] = lineup_players

    context.user_data[
        "selected_lineup_slot"
    ] = None

    await query.answer(
        f"✅ {player.name} placed."
    )

    # ======================================================
    # RETURN TO PITCH
    # ======================================================

    text = (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗟𝗜𝗡𝗘𝗨𝗣\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        f"🏟️ Formation : "
        f"{formation}\n\n"
        f"✅ {player.name}\n"
        f"⭐ OVR : {player.overall}\n\n"
        f"👥 Players: "
        f"{len(lineup_players)}/11\n\n"
        "👇 Select another position."
    )

    await edit_lineup_message(
        query,
        text,
        build_lineup_keyboard(
            formation,
            lineup_players,
        ),
    )


# ==========================================================
# HANDLERS
# ==========================================================

lineup_handler = CommandHandler(
    "lineup",
    lineup,
)

lineup_callback_handler = (
    CallbackQueryHandler(
        lineup_callback,
        pattern=(
            r"^lineup_"
            r"(formation:.+|change|slot:.+|save|back)$"
        ),
    )
)

lineup_player_callback_handler = (
    CallbackQueryHandler(
        lineup_player_callback,
        pattern=r"^lineup_player:\d+$",
    )
)