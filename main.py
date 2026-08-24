from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
)

from handlers.trade import trade_handler
from handlers.pay import pay_handler
from handlers.addcoins import addcoins_handler
from handlers.sendplayer import sendplayer_handler
from handlers.language import (language_handler, language_callback_handler)
from handlers.quiz import quiz_handler, quiz_callback_handler
from handlers.cup import cup_handler
from handlers.calendar import calendar_handler
from handlers.createclub import (
    createclub_handler,
)

from handlers.myclub import (
    myclub,
)

from handlers.addplayer import (
    addplayer_handler,
)

from handlers.squad import (
    squad,
    squad_callback_handler,
    player_callback_handler,
)

from handlers.refillmarket import (
    refill_market_handler,
)

from config import BOT_TOKEN

from handlers.start import (
    start,
)

from handlers.transfermarket import (
    transfermarket_handler,
    transfermarket_callback_handler,
)

from handlers.lineup import (
    lineup_handler,
    lineup_callback_handler,
    lineup_player_callback_handler,
)

from handlers.training import (
    training_handler,
    training_callback_handler,
)

from handlers.friendly import (
    friendly_handler,
    friendly_callback_router_handler,
)
from handlers.friendly import (
    subs_handler,
)

from database.database import (
    init_database,
)
from handlers.resetgame import (
    resetgame_handler,
    resetgame_callback_handler,
)
from handlers.setinfo import (
    setinfo_handler,
)
from handlers.league import (
    league_handler,
    league_callback_handler,
)
from handlers.adddivision import (
    adddivision_handler,
)
from handlers.startleague import (
    startleague_handler,
)
from handlers.starteurope import (
    starteurope_handler,
)
from handlers.createleague import (
    createleague_handler,
)
from handlers.league_europe import (
    league_europe_handler,
)
from handlers.startcup import startcup_handler
from handlers.cupmatches import cupmatches_handler
from handlers.cupnextround import cupnextround_handler
from handlers.help import help_handler, help_callback_handler
from handlers.stats import (
    stats_handler,
    stats_callback_handler,
)
from handlers.news import news_handler
from handlers.profile import (
    profile_handler,
    profile_callback_handler,
)
from handlers.pay import (
    pay_handler,
    pay_callback_handler,
)
from handlers.rankings import (
    rankings_handler,
    rankings_callback_handler,
)
from handlers.matches import (
    matches_handler,
    matches_callback_handler,
)
from handlers.trade import (
    trade_handler,
    trade_callback_handler,
)
from handlers.annonce import annonce_handler
from handlers.daily import daily_handler
from handlers.ref import ref_handler
from handlers.sanction import sanction_handler
from handlers.leagueids import leagueids_handler
from services.localization import install_localization




# ==========================================================
# DATABASE INITIALIZATION
# ==========================================================
async def post_init(
    application,
):

    print(
        "🗄️ Initializing database..."
    )

    await init_database()

    print(
        "✅ Database ready."
    )

    # ======================================================
    # TELEGRAM BOT COMMAND MENU
    # ======================================================
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("myclub", "View your club"),
        BotCommand("squad", "View your squad"),
        BotCommand("createclub", "Create your club"),
        BotCommand("addplayer", "Add a player"),
        BotCommand("transfermarket", "Open the transfer market"),
        BotCommand("refillmarket", "Refill the transfer market"),
        BotCommand("lineup", "Manage your lineup"),
        BotCommand("training", "Train your players"),
        BotCommand("friendly", "Play a friendly match"),
        BotCommand("matches", "View your matches"),
        BotCommand("league", "Open leagues"),
        BotCommand("leagueids", "View league IDs"),
        BotCommand("createleague", "Create a league"),
        BotCommand("adddivision", "Add a division"),
        BotCommand("startleague", "Start a league"),
        BotCommand("starteurope", "Start European competition"),
        BotCommand("leagueeurope", "Open European leagues"),
        BotCommand("startcup", "Start the Cup"),
        BotCommand("cup", "Open Cup"),
        BotCommand("cupmatches", "View Cup matches"),
        BotCommand("cupnextround", "Start the next Cup round"),
        BotCommand("quiz", "Play the football quiz"),
        BotCommand("profile", "View your profile"),
        BotCommand("stats", "View your statistics"),
        BotCommand("rankings", "View rankings"),
        BotCommand("daily", "Claim your daily reward"),
        BotCommand("ref", "View your referral link"),
        BotCommand("pay", "Send Coins or Gems"),
        BotCommand("trade", "Trade with another manager"),
        BotCommand("sendplayer", "Send a player"),
        BotCommand("addcoins", "Add Coins"),
        BotCommand("sanction", "Manage sanctions"),
        BotCommand("news", "View football news"),
        BotCommand("calendar", "View the calendar"),
        BotCommand("annonce", "Send discour owner"),
        BotCommand("language", "Change language"),
        BotCommand("help", "View help"),
    ]

    try:
        await application.bot.set_my_commands(commands)
        print(
            f"✅ Telegram command menu updated: {len(commands)} commands."
        )
    except Exception as error:
        print(
            "⚠️ Could not update Telegram command menu:",
            type(error).__name__,
            error,
        )


# ==========================================================
# MAIN
# ==========================================================

def main():
    install_localization()
    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ======================================================
    # BASIC
    # ======================================================

    application.add_handler(
        friendly_callback_router_handler
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        createclub_handler
    )

    application.add_handler(
        CommandHandler(
            "myclub",
            myclub,
        )
    )

    application.add_handler(
        CommandHandler(
            "squad",
            squad,
        )
    )
    application.add_handler(annonce_handler)

    application.add_handler(
        squad_callback_handler
    )

    application.add_handler(
        player_callback_handler
    )

    application.add_handler(
        addplayer_handler
    )

    # ======================================================
    # MARKET
    # ======================================================

    application.add_handler(
        refill_market_handler
    )

    application.add_handler(
        transfermarket_handler
    )

    application.add_handler(
        transfermarket_callback_handler
    )

    # ======================================================
    # LINEUP
    # ======================================================

    application.add_handler(
        lineup_handler
    )

    application.add_handler(
        lineup_callback_handler
    )

    application.add_handler(
        lineup_player_callback_handler
    )

    # ======================================================
    # TRAINING
    # ======================================================

    application.add_handler(
        training_handler
    )

    application.add_handler(
        training_callback_handler
    )

    # ======================================================
    # FRIENDLY
    # ======================================================

    application.add_handler(
        friendly_handler
    )

    application.add_handler(
        subs_handler
    )
    application.add_handler(
    resetgame_handler
)

    application.add_handler(
    resetgame_callback_handler
)   
    application.add_handler(
    setinfo_handler
)
    application.add_handler(league_handler)
    application.add_handler(league_callback_handler)
    application.add_handler(
    adddivision_handler
)
    application.add_handler(
    startleague_handler
)
    application.add_handler(
    starteurope_handler
)
    application.add_handler(
    createleague_handler
)
    application.add_handler(
    league_europe_handler
)
    application.add_handler(startcup_handler)
    application.add_handler(cupmatches_handler)
    application.add_handler(cupnextround_handler)
    application.add_handler(help_handler)
    application.add_handler(help_callback_handler)
    application.add_handler(stats_handler)
    application.add_handler(stats_callback_handler)
    application.add_handler(news_handler)
    application.add_handler(profile_handler)
    application.add_handler(profile_callback_handler)
    application.add_handler(pay_handler)
    application.add_handler(pay_callback_handler)

    application.add_handler(rankings_handler)
    application.add_handler(rankings_callback_handler)
    application.add_handler(matches_handler)
    application.add_handler(matches_callback_handler)
    
    application.add_handler(trade_handler)
    application.add_handler(trade_callback_handler)
    application.add_handler(daily_handler)
    application.add_handler(ref_handler)
    application.add_handler(sanction_handler)
    application.add_handler(leagueids_handler)

    # ======================================================
    # START
    # ======================================================

    print(
        "🤖 Bot is running..."
    )

    application.add_handler(calendar_handler)

    application.add_handler(cup_handler)

    application.add_handler(quiz_handler)
    application.add_handler(quiz_callback_handler)


    application.add_handler(language_handler)
    application.add_handler(language_callback_handler)


    application.add_handler(sendplayer_handler)

    application.add_handler(addcoins_handler)

    application.run_polling()


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()