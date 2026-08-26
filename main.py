from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from handlers.trade import trade_handler
from handlers.pay import pay_handler
from handlers.addcoins import addcoins_handler

from handlers.achat import (
    achat_handler,
    achat_callback_handler,
    precheckout_handler,
    successful_payment_handler,
)
from handlers.sendplayer import sendplayer_handler
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
    start_menu_callback_handler,
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
    friendlypay_handler,
    friendlypay_callback_handler,
    friendlypay_decline_callback,
    friendly_forfeit_callback,
)
from handlers.friendly import (
    subs_handler,
)

from database.database import (
    init_database,
)

from life_world.handlers.life import life_handler
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
from handlers.balance import balance_handler
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
from handlers.annonce import (
    annonce_handler,
    group_tracker_handler,
)
from handlers.daily import daily_handler
from handlers.ref import ref_handler, process_referral_start
from handlers.leagueids import leagueids_handler
from handlers.command import command_handler
from handlers.commandrank import commandrank_handler
from handlers.richlist import richlist_handler, richlist_callback_handler
from handlers.command_tracker import command_tracker_handler
from handlers.pari import pari_handler
from handlers.manager_sponsors import (
    sponsor_handler,
    sponsors_handler,
    sponsor_select_callback_handler,
)
from handlers.manager_contract_commands import (
    contract_handler,
    create_contract_handler,
    contract_pay_handler,
    contract_pay_callback_handler,
)
from handlers.manager_transfers_contracts import (
    sellplayer_handler,
    releaseplayer_handler,
    mytransfers_handler,
)
from handlers.manager_ballondor import (
    nomined_handler,
    ballondorrank_handler,
    ballondororder_handler,
    ballondorwinner_handler,
    clearballondor_handler,
    ballondorhelp_handler,
)
from handlers.manager_contracts import (
    pay_all_due_salaries,
)
from handlers.manager_sponsors import (
    pay_all_due_sponsors,
)
from handlers.users_owner import users_handler
from handlers.sanction import sanction_handler, payfine_handler



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

    # Ensure old squads also receive their automatic contracts.
    try:
        from handlers.manager_contracts import ensure_all_current_players_have_contracts
        created_contracts = await ensure_all_current_players_have_contracts()
        print(f"✅ Automatic contracts checked: {created_contracts} created.")
    except Exception as error:
        print(f"⚠️ Automatic contract check failed: {type(error).__name__}: {error}")

    print(
        "✅ Database ready."
    )

    # ======================================================
    # TELEGRAM BOT COMMAND MENU
    # ======================================================
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("life", "Open Life World"),
        BotCommand("myclub", "View your club"),
        BotCommand("squad", "View your squad"),
        BotCommand("createclub", "Create your club"),
        BotCommand("addplayer", "Add a player"),
        BotCommand("transfer", "Open the transfer market"),
        BotCommand("refillmarket", "Refill the transfer market"),
        BotCommand("friendlypay", "Play a Friendly with a virtual stake"),
        BotCommand("pari", "Football predictions"),
        BotCommand("lineup", "Manage your lineup"),
        BotCommand("training", "Train your players"),
        BotCommand("friendly", "Play a friendly match"),
        BotCommand("matches", "View your matches"),
        BotCommand("league", "Open leagues"),
        BotCommand("leagueids", "View league IDs"),
        BotCommand("createleague", "Create a league"),
        BotCommand("adddivision", "Add a division"),
        BotCommand("startleague", "Start a league"),
        BotCommand("achat", "Buy coins and Gems"),
        BotCommand("starteurope", "Start European competition"),
        BotCommand("leagueeurope", "Open European leagues"),
        BotCommand("startcup", "Start the Cup"),
        BotCommand("cup", "Open Cup"),
        BotCommand("cupmatches", "View Cup matches"),
        BotCommand("cupnextround", "Start the next Cup round"),
        BotCommand("quiz", "Play the football quiz"),
        BotCommand("profile", "View your profile"),
        BotCommand("balance", "View your balance"),
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
        BotCommand("help", "View help"),
        BotCommand("command", "View your daily command count"),
        BotCommand("commandrank", "View command rankings"),
        BotCommand("richlist", "View the richest managers"),
        BotCommand("contracts", "View player contracts"),
        BotCommand("contract", "Create or renew a player contract"),
        BotCommand("paysalary", "Pay a player salary"),
        BotCommand("sellplayer", "List a player for sale"),
        BotCommand("releaseplayer", "Release a player"),
        BotCommand("mytransfers", "View your transfer listings"),
        BotCommand("sponsor", "Manage club sponsors"),
        BotCommand("sponsors", "View active sponsors"),
        BotCommand("nomined", "Add a Ballon d'Or nominee"),
        BotCommand("ballondorrank", "View Ballon d'Or ranking"),
        BotCommand("ballondororder", "Set Ballon d'Or ranking"),
        BotCommand("ballondorwinner", "Set Ballon d'Or winner"),
        BotCommand("clearballondor", "Reset Ballon d'Or"),
        BotCommand("users", "View all bot users"),
        BotCommand("payfine", "Pay your sanction fine"),
        BotCommand("ballondorhelp", "Ballon d'Or commands"),
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


# ==========================================================
# DAILY MANAGER PAYMENTS
# ==========================================================

async def daily_manager_payments(context):
    """Pay due player salaries and sponsor income once per day."""
    try:
        salary_result = await pay_all_due_salaries()
    except Exception as exc:
        print(f"[DAILY PAYMENTS] salary error: {exc}")
        salary_result = {"paid": 0, "left": 0, "skipped": 0}

    try:
        sponsor_result = await pay_all_due_sponsors()
    except Exception as exc:
        print(f"[DAILY PAYMENTS] sponsor error: {exc}")
        sponsor_result = {"paid": 0, "expired": 0, "skipped": 0}

    print(
        "[DAILY PAYMENTS] "
        f"salaries_paid={salary_result.get('paid', 0)} "
        f"salaries_left={salary_result.get('left', 0)} "
        f"sponsors_paid={sponsor_result.get('paid', 0)} "
        f"sponsors_expired={sponsor_result.get('expired', 0)}"
    )


async def referral_aware_start(update, context):
    """Register a referral payload, then run the normal /start."""
    try:
        await process_referral_start(update, context)
    except Exception as error:
        print(
            "⚠️ Referral processing error:",
            type(error).__name__,
            error,
        )

    await start(update, context)


def main():
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

    # ======================================================
    # GLOBAL TRACKING / REFERRALS
    # ======================================================

    application.add_handler(
        command_tracker_handler,
        group=-10,
    )

    application.add_handler(
        group_tracker_handler,
        group=-11,
    )

    application.add_handler(
        friendly_callback_router_handler
    )

    application.add_handler(
        CommandHandler(
            "start",
            referral_aware_start,
        ),
        group=0,
    )

    # START MENU BUTTONS
    application.add_handler(
        start_menu_callback_handler
    )

    # ======================================================
    # LIFE WORLD
    # ======================================================

    application.add_handler(
        life_handler
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
        friendlypay_handler
    )
    # Friendly/Friendly Pay callbacks are handled by the single router.

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
    
    application.add_handler(balance_handler)

    application.add_handler(achat_handler)
    application.add_handler(achat_callback_handler)
    application.add_handler(precheckout_handler)
    application.add_handler(successful_payment_handler)

    application.add_handler(rankings_handler)
    application.add_handler(rankings_callback_handler)
    application.add_handler(matches_handler)
    application.add_handler(matches_callback_handler)
    
    application.add_handler(trade_handler)
    application.add_handler(trade_callback_handler)
    application.add_handler(daily_handler)
    application.add_handler(ref_handler)
    # Sanction enforcement MUST run before normal commands.
    application.add_handler(sanction_handler, group=-100)
    application.add_handler(payfine_handler, group=-99)
    application.add_handler(leagueids_handler)

    # ======================================================
    # COMMAND / RICHLIST
    # ======================================================

    application.add_handler(command_handler)
    application.add_handler(commandrank_handler)
    application.add_handler(richlist_handler)
    application.add_handler(richlist_callback_handler)
    application.add_handler(pari_handler)
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


    application.add_handler(sendplayer_handler)

    application.add_handler(addcoins_handler)
    application.add_handler(users_handler)

    # ======================================================
    # MANAGER — CONTRACTS / PLAYER SALES
    # ======================================================

    application.add_handler(contract_handler)
    application.add_handler(create_contract_handler)
    application.add_handler(contract_pay_handler)
    application.add_handler(contract_pay_callback_handler)

    application.add_handler(sellplayer_handler)
    application.add_handler(releaseplayer_handler)
    application.add_handler(mytransfers_handler)

    # ======================================================
    # MANAGER — SPONSORS
    # ======================================================

    application.add_handler(sponsor_handler)
    application.add_handler(sponsors_handler)
    application.add_handler(sponsor_select_callback_handler)

    # ======================================================
    # MANAGER — BALLON D'OR
    # ======================================================

    application.add_handler(nomined_handler)
    application.add_handler(ballondorrank_handler)
    application.add_handler(ballondororder_handler)
    application.add_handler(ballondorwinner_handler)
    application.add_handler(clearballondor_handler)
    application.add_handler(ballondorhelp_handler)

    application.run_polling()


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()
