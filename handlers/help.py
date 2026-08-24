from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "help.jpg"
)

# EXACT command list currently registered in main.py.
COMMAND_PAGES = [
    (
        "⚽ 𝐂𝐋𝐔𝐁",
        [
            ("/start", "Start the game"),
            ("/myclub", "View your club"),
            ("/squad", "View your squad"),
            ("/createclub", "Create your club"),
            ("/addplayer", "Add a player"),
            ("/profile", "View your profile"),
            ("/setinfo", "Change club information"),
            ("/language", "Change bot language"),
        ],
    ),
    (
        "🏟️ 𝐌𝐀𝐑𝐊𝐄𝐓 & 𝐏𝐋𝐀𝐘",
        [
            ("/transfermarket", "Open the transfer market"),
            ("/refillmarket", "Refill the transfer market"),
            ("/lineup", "Manage your lineup"),
            ("/training", "Train your players"),
            ("/friendly", "Play a friendly match"),
            ("/matches", "View your matches"),
            ("/sendplayer", "Send a player"),
        ],
    ),
    (
        "🏆 𝐋𝐄𝐀𝐆𝐔𝐄",
        [
            ("/league", "View and join leagues"),
            ("/leagueids", "View league IDs"),
            ("/createleague", "Create a league"),
            ("/adddivision", "Add a division"),
            ("/startleague", "Start league competition"),
            ("/stats", "View statistics"),
            ("/rankings", "View rankings"),
            ("/calendar", "View competition calendar"),
        ],
    ),
    (
        "🌍 𝐄𝐔𝐑𝐎𝐏𝐄",
        [
            ("/starteurope", "Start European competition"),
            ("/league_europe", "View European leagues"),
        ],
    ),
    (
        "🏆 𝐂𝐔𝐏",
        [
            ("/cup", "View Cup information"),
            ("/startcup", "Start the Cup"),
            ("/cupmatches", "View Cup matches"),
            ("/cupnextround", "Generate the next Cup round"),
        ],
    ),
    (
        "💰 𝐄𝐂𝐎𝐍𝐎𝐌𝐘 & 𝐒𝐎𝐂𝐈𝐀𝐋",
        [
            ("/trade", "Trade with another manager"),
            ("/pay", "Send Coins or Gems"),
            ("/daily", "Claim daily reward"),
            ("/ref", "Referral system"),
            ("/addcoins", "Add Coins"),
        ],
    ),
    (
        "🧠 𝐐𝐔𝐈𝐙 & 𝐈𝐍𝐅𝐎",
        [
            ("/quiz", "Play the football quiz"),
            ("/news", "View bot news"),
            ("/help", "Open this help"),
        ],
    ),
    (
        "🔒 𝐎𝐖𝐍𝐄𝐑 / 𝐀𝐃𝐌𝐈𝐍",
        [
            ("/sanction", "Manage sanctions"),
            ("/annonce", "Send an announcement"),
        ],
    ),
]

GUIDE_PAGES = [
    (
        "🎮 𝐇𝐎𝐖 𝐓𝐎 𝐏𝐋𝐀𝐘",
        "1️⃣ Use /start to create your manager profile.\n"
        "2️⃣ Create your club with /createclub.\n"
        "3️⃣ Build your squad and manage your lineup.\n"
        "4️⃣ Buy players from the transfer market.\n"
        "5️⃣ Train your players to improve your team.\n"
        "6️⃣ Join a league and compete in matches.",
    ),
    (
        "⚽ 𝐌𝐀𝐓𝐂𝐇𝐄𝐒",
        "🤝 Use /friendly to play friendly matches.\n"
        "🏆 League matches are managed through your league.\n"
        "🌍 European competitions use their own schedule.\n"
        "🏆 Cup matches are managed through the Cup commands.\n"
        "📅 Use /calendar and /matches to follow competitions.",
    ),
    (
        "💰 𝐂𝐎𝐈𝐍𝐒 & 𝐆𝐄𝐌𝐒",
        "💰 Coins are used for the game's economy.\n"
        "💎 Gems are the premium currency.\n"
        "🎁 /daily gives your daily reward.\n"
        "🤝 /pay lets a manager send Coins or Gems.\n"
        "🔄 /trade handles player trading.",
    ),
    (
        "🧠 𝐐𝐔𝐈𝐙",
        "🧠 Use /quiz to start.\n"
        "🌍 Choose French or English.\n"
        "⏱️ You have limited time for each question.\n"
        "✅ A correct answer gives Coins.\n"
        "❌ A wrong answer ends the current quiz.",
    ),
]


def _main_keyboard(page: int):
    rows = []

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data=f"help:page:{page - 1}",
            )
        )
    if page < len(COMMAND_PAGES) - 1:
        nav.append(
            InlineKeyboardButton(
                "NEXT ➡️",
                callback_data=f"help:page:{page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                "🎮 GUIDE",
                callback_data="help:guide:0",
            ),
            InlineKeyboardButton(
                "❌ CLOSE",
                callback_data="help:close",
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def _guide_keyboard(page: int):
    nav = []

    if page > 0:
        nav.append(
            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data=f"help:guide:{page - 1}",
            )
        )

    if page < len(GUIDE_PAGES) - 1:
        nav.append(
            InlineKeyboardButton(
                "NEXT ➡️",
                callback_data=f"help:guide:{page + 1}",
            )
        )

    rows = []
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                "📖 COMMANDS",
                callback_data="help:page:0",
            ),
            InlineKeyboardButton(
                "❌ CLOSE",
                callback_data="help:close",
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def _commands_text(page: int):
    title, commands = COMMAND_PAGES[page]

    lines = [
        "📖 𝐋𝐄𝐆𝐄𝐍𝐃𝐀𝐑𝐘 𝐅𝐎𝐎𝐓𝐁𝐀𝐋𝐋 𝐁𝐎𝐓",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        title,
        "",
    ]

    for command, description in commands:
        lines.append(
            f"▫️ {command} — {description}"
        )

    lines.extend(
        [
            "",
            f"📄 Page {page + 1}/{len(COMMAND_PAGES)}",
        ]
    )

    return "\n".join(lines)


def _guide_text(page: int):
    title, body = GUIDE_PAGES[page]

    return (
        "📖 𝐋𝐄𝐆𝐄𝐍𝐃𝐀𝐑𝐘 𝐅𝐎𝐎𝐓𝐁𝐀𝐋𝐋 𝐁𝐎𝐓\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{title}\n\n"
        f"{body}\n\n"
        f"📄 Guide {page + 1}/{len(GUIDE_PAGES)}"
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        _commands_text(0),
        reply_markup=_main_keyboard(0),
    )


async def help_callback(
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

    parts = query.data.split(":")

    try:
        if parts[1] == "close":
            await query.message.delete()
            return

        if parts[1] == "page":
            page = int(parts[2])
            page = max(
                0,
                min(
                    page,
                    len(COMMAND_PAGES) - 1,
                ),
            )

            await query.message.edit_text(
                _commands_text(page),
                reply_markup=_main_keyboard(page),
            )
            return

        if parts[1] == "guide":
            page = int(parts[2])
            page = max(
                0,
                min(
                    page,
                    len(GUIDE_PAGES) - 1,
                ),
            )

            await query.message.edit_text(
                _guide_text(page),
                reply_markup=_guide_keyboard(page),
            )

    except Exception as error:
        if "Message is not modified" not in str(error):
            print(
                "⚠️ HELP CALLBACK ERROR:",
                type(error).__name__,
                error,
            )


help_handler = CommandHandler(
    "help",
    help_command,
)

help_callback_handler = CallbackQueryHandler(
    help_callback,
    pattern=r"^help:(page|guide|close)(:\d+)?$",
)