from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

# ==========================================================
# [MWL] MANUWORLD — HANDLERS
# ==========================================================

from life_world.handlers.life import life_handler

from life_world.handlers.lifestyle_stats import (
    register_lifestyle_stats_handlers,
)

from life_world.handlers.business import (
    register_business_handlers,
)

from life_world.handlers.jobs import (
    register_jobs_handlers,
)

from life_world.handlers.company_jobs import (
    register_company_jobs_handlers,
)

from life_world.handlers.company_contract import (
    contracts_command,
    contract_command,
    contract_accept_command,
    contract_tasks_command,
    contract_complete_command,
    contract_callback,
)

from life_world.handlers.company_market import (
    register_company_market_handlers,
)

from life_world.handlers.company_market_management import (
    register_company_market_management_handlers,
)

from life_world.handlers.bank import (
    register_bank_handlers,
)

from life_world.handlers.credit_card import (
    register_credit_card_handlers,
)

from life_world.handlers.loan import (
    register_loan_handlers,
)

from life_world.handlers.education import (
    school_command,
    study_command,
    domain_command,
    domain_callback,
)

from life_world.handlers.domain_exams import (
    register_domain_exam_handlers,
)

from life_world.handlers.school_enrollment import (
    register_school_enrollment_handlers,
)

from life_world.handlers.school_profile import (
    register_school_profile_handlers,
)

from life_world.handlers.family import (
    register_family_handlers,
)

from life_world.handlers.adoption import (
    register_adoption_handlers,
)

from life_world.handlers.marriage import (
    register_marriage_handlers,
)

from life_world.handlers.friendship import (
    register_friendship_handlers,
)

from life_world.handlers.health import (
    register_health_handlers,
)
from life_world.handlers.hospital import (
    register_hospital_handlers,
)

from life_world.handlers.housing import (
    register_housing_handlers,
)
from life_world.handlers.politics import (
    register_politics_handlers,
)

from life_world.handlers.inventory import (
    register_inventory_handlers,
)

from life_world.handlers.life_events import (
    register_life_events_handlers,
)

from life_world.handlers.expenses import (
    register_expenses_handlers,
)

from life_world.handlers.skills import (
    register_skills_handlers,
)

from life_world.handlers.wealth import (
    register_wealth_handlers,
)

from life_world.handlers.mwl_core import register_mwl_core_handlers
from life_world.core import ensure_v3_schema

from life_world.handlers.economy import (
    addlifecoins_handler,
    paylife_handler,
)


from life_world.handlers.lifestyle_stats import (
    lifestyle_command,
    lifestyle_callback,
)

from life_world.handlers.business import (
    business_command,
    businesses_command,
    business_create_command,
    business_callback,
)

from life_world.handlers.jobs import (
    jobs_command,
    job_command,
    jobsearch_command,
    applyjob_command,
    resign_command,
    jobs_callback,
)

from life_world.handlers.company_jobs import (
    joboffers_command,
    companyjobs_command,
    createjob_command,
    applyjoboffer_command,
    companyjobs_callback,
)

from life_world.handlers.company_contract import (
    contracts_command,
    contract_command,
    contract_accept_command,
    contract_tasks_command,
    contract_complete_command,
    contract_callback,
)

# ==========================================================
# [MWL] MANUWORLD — DATABASE
# ==========================================================

from life_world.database import (
    ensure_life_tables,
    ensure_life_world_migrations,
)

# ==========================================================
# [LFB] LEGENDARY FOOTBALL BOT
# ==========================================================

from handlers.trade import (
    trade_handler,
    trade_callback_handler,
    trade_response_handler,
)

from handlers.pay import (
    pay_handler,
    pay_callback_handler,
)

from handlers.addcoins import (
    addcoins_handler,
)

from handlers.achat import (
    achat_handler,
    achat_callback_handler,
    precheckout_handler,
    successful_payment_handler,
)

from handlers.sendplayer import (
    sendplayer_handler,
)

from handlers.quiz import (
    quiz_handler,
    quiz_callback_handler,
)

from handlers.cup import (
    cup_handler,
)

from handlers.calendar import (
    calendar_handler,
)

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

from handlers.startcup import (
    startcup_handler,
)

from handlers.cupmatches import (
    cupmatches_handler,
)

from handlers.cupnextround import (
    cupnextround_handler,
)

from handlers.help import (
    help_handler,
    help_callback_handler,
)

from handlers.stats import (
    stats_handler,
    stats_callback_handler,
)

from handlers.news import (
    news_handler,
)

from handlers.profile import (
    profile_handler,
    profile_callback_handler,
)

from handlers.balance import (
    balance_handler,
)

from handlers.rankings import (
    rankings_handler,
    rankings_callback_handler,
)

from handlers.matches import (
    matches_handler,
    matches_callback_handler,
)

from handlers.annonce import (
    annonce_handler,
    group_tracker_handler,
)

from handlers.daily import (
    daily_handler,
)

from handlers.ref import (
    ref_handler,
    process_referral_start,
)

from handlers.leagueids import (
    leagueids_handler,
)

from handlers.command import (
    command_handler,
)

from handlers.commandrank import (
    commandrank_handler,
)

from handlers.richlist import (
    richlist_handler,
    richlist_callback_handler,
)

from handlers.command_tracker import (
    command_tracker_handler,
)

from handlers.pari import (
    pari_handler,
)

from handlers.manager_sponsors import (
    sponsor_handler,
    sponsors_handler,
    sponsor_select_callback_handler,
    pay_all_due_sponsors,
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
    release_callback_handler,
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
    ensure_all_current_players_have_contracts,
)

from handlers.users_owner import (
    users_handler,
)

from handlers.sanction import (
    sanction_handler,
    payfine_handler,
)

from handlers.stopleague import (
    stopleague_handler,
)

from handlers.football_admin_tools import (
    cancel_pending_handler,
    clear_market_handler,
)
from life_world.handlers.work import (
    work_handler,
)


# ==========================================================
# DATABASE INITIALIZATION
# ==========================================================

async def post_init(
    application,
):

    print(
        "🗄️ Initializing database..."
    )

    # ------------------------------------------------------
    # [LFB] DATABASE
    # ------------------------------------------------------

    await init_database()

    # ------------------------------------------------------
    # [MWL] DATABASE
    # ------------------------------------------------------

    try:

        print(
            "🌍 [MWL] Initializing MANUWORLD database..."
        )

        await ensure_life_tables()

        await ensure_life_world_migrations()
        await ensure_v3_schema()

        print(
            "✅ [MWL] MANUWORLD database ready."
        )

    except Exception as error:

        print(
            "⚠️ [MWL] MANUWORLD database initialization failed:",
            type(error).__name__,
            error,
        )

    # ------------------------------------------------------
    # [LFB] AUTOMATIC PLAYER CONTRACTS
    # ------------------------------------------------------

    try:

        created_contracts = (
            await ensure_all_current_players_have_contracts()
        )

        print(
            "✅ [LFB] Automatic contracts checked: "
            f"{created_contracts} created."
        )

    except Exception as error:

        print(
            "⚠️ [LFB] Automatic contract check failed:",
            type(error).__name__,
            error,
        )

    print(
        "✅ Database ready."
    )

    # ======================================================
    # TELEGRAM BOT COMMAND MENU
    #
    # [MWL] ALWAYS BEFORE [LFB]
    # ======================================================

    commands = [

        # ==================================================
        # [MWL] MANUWORLD
        # ==================================================

        BotCommand(
            "life",
            "[MWL] Open MANUWORLD",
        ),

        BotCommand(
            "lifestyle",
            "[MWL] Lifestyle statistics",
        ),

        BotCommand(
            "business",
            "[MWL] Manage your business",
        ),

        BotCommand(
            "businesses",
            "[MWL] View your businesses",
        ),

        BotCommand(
            "business_create",
            "[MWL] Create a business",
        ),

        BotCommand(
            "jobs",
            "[MWL] View available jobs",
        ),

        BotCommand(
            "job",
            "[MWL] View current job",
        ),

        BotCommand(
            "jobsearch",
            "[MWL] Search for a job",
        ),

        BotCommand(
            "applyjob",
            "[MWL] Apply for a job",
        ),

        BotCommand(
            "resign",
            "[MWL] Resign from your job",
        ),

        BotCommand(
            "joboffers",
            "[MWL] View company job offers",
        ),

        BotCommand(
            "companyjobs",
            "[MWL] View company jobs",
        ),

        BotCommand(
            "createjob",
            "[MWL] Create a company job",
        ),

        BotCommand(
            "applyjoboffer",
            "[MWL] Apply to a company job",
        ),

        BotCommand(
            "contracts",
            "[MWL] Company contracts",
        ),

        BotCommand(
            "contract_accept",
            "[MWL] Accept company contract",
        ),

        BotCommand(
            "contract_tasks",
            "[MWL] View contract tasks",
        ),

        BotCommand(
            "contract_complete",
            "[MWL] Complete contract task",
        ),

        BotCommand(
            "market",
            "[MWL] Company market",
        ),

        BotCommand(
            "marketmanage",
            "[MWL] Manage company market",
        ),

        BotCommand(
            "bank",
            "[MWL] Manage bank",
        ),

        BotCommand(
            "card",
            "[MWL] Manage bank card",
        ),

        BotCommand(
            "loan",
            "[MWL] Manage loans",
        ),

        BotCommand(
            "school",
            "[MWL] Open school",
        ),

        BotCommand(
            "study",
            "[MWL] Study",
        ),

        BotCommand(
            "domain",
            "[MWL] Choose study domain",
        ),

        BotCommand(
            "exam",
            "[MWL] Take exam",
        ),

        BotCommand(
            "schoolenroll",
            "[MWL] Enroll in school",
        ),

        BotCommand(
            "changeschool",
            "[MWL] Change school",
        ),

        BotCommand(
            "schoolprofile",
            "[MWL] School profile",
        ),

        BotCommand(
            "orientation",
            "[MWL] School orientation",
        ),

        BotCommand(
            "family",
            "[MWL] Family",
        ),

        BotCommand(
            "adopt",
            "[MWL] Adopt a child",
        ),

        BotCommand(
            "adoption",
            "[MWL] Adoption",
        ),

        BotCommand(
            "children",
            "[MWL] View children",
        ),

        BotCommand(
            "marry",
            "[MWL] Get married",
        ),

        BotCommand(
            "marriage",
            "[MWL] Marriage",
        ),

        BotCommand(
            "divorce",
            "[MWL] Divorce",
        ),

        BotCommand(
            "addfriend",
            "[MWL] Add a friend",
        ),

        BotCommand(
            "friendrequests",
            "[MWL] Friend requests",
        ),

        BotCommand(
            "friends",
            "[MWL] Friends",
        ),

        BotCommand(
            "health",
            "[MWL] Health",
        ),

        BotCommand(
            "housing",
            "[MWL] Housing",
        ),

        BotCommand(
            "inventory",
            "[MWL] Inventory",
        ),

        BotCommand(
            "events",
            "[MWL] Life events",
        ),

        BotCommand(
            "expenses",
            "[MWL] Expenses",
        ),

        BotCommand(
            "expense",
            "[MWL] Add an expense",
        ),

        BotCommand(
            "skills",
            "[MWL] Skills",
        ),

        BotCommand(
            "wealth",
            "[MWL] Wealth",
        ),

        BotCommand(
            "addlifecoins",
            "[MWL] Add Life Coins",
        ),

        BotCommand(
            "paylife",
            "[MWL] Pay Life Coins",
        ),

        BotCommand(
            "start",
            "[LFB] Start the bot",
        ),

        BotCommand(
            "myclub",
            "[LFB] View your club",
        ),

        BotCommand(
            "squad",
            "[LFB] View your squad",
        ),

        BotCommand(
            "createclub",
            "[LFB] Create your club",
        ),

        BotCommand(
            "addplayer",
            "[LFB] Add a player",
        ),

        BotCommand(
            "transfer",
            "[LFB] Open transfer market",
        ),

        BotCommand(
            "refillmarket",
            "[LFB] Refill transfer market",
        ),

        BotCommand(
            "friendlypay",
            "[LFB] Friendly with virtual stake",
        ),

        BotCommand(
            "pari",
            "[LFB] Football predictions",
        ),

        BotCommand(
            "lineup",
            "[LFB] Manage lineup",
        ),

        BotCommand(
            "training",
            "[LFB] Train players",
        ),

        BotCommand(
            "friendly",
            "[LFB] Play a friendly",
        ),

        BotCommand(
            "subs",
            "[LFB] Manage substitutions",
        ),

        BotCommand(
            "matches",
            "[LFB] View matches",
        ),

        BotCommand(
            "league",
            "[LFB] Open leagues",
        ),

        BotCommand(
            "leagueids",
            "[LFB] View league IDs",
        ),

        BotCommand(
            "createleague",
            "[LFB] Create a league",
        ),

        BotCommand(
            "adddivision",
            "[LFB] Add a division",
        ),

        BotCommand(
            "startleague",
            "[LFB] Start a league",
        ),

        BotCommand(
            "starteurope",
            "[LFB] Start European competition",
        ),

        BotCommand(
            "leagueeurope",
            "[LFB] Open European leagues",
        ),

        BotCommand(
            "startcup",
            "[LFB] Start the Cup",
        ),

        BotCommand(
            "cup",
            "[LFB] Open Cup",
        ),

        BotCommand(
            "cupmatches",
            "[LFB] View Cup matches",
        ),

        BotCommand(
            "cupnextround",
            "[LFB] Start next Cup round",
        ),

        BotCommand(
            "quiz",
            "[LFB] Football quiz",
        ),

        BotCommand(
            "profile",
            "[LFB] View profile",
        ),

        BotCommand(
            "balance",
            "[LFB] View balance",
        ),

        BotCommand(
            "stats",
            "[LFB] View statistics",
        ),

        BotCommand(
            "rankings",
            "[LFB] View rankings",
        ),

        BotCommand(
            "calendar",
            "[LFB] View calendar",
        ),

        BotCommand(
            "daily",
            "[LFB] Daily reward",
        ),

        BotCommand(
            "ref",
            "[LFB] Referral link",
        ),

        BotCommand(
            "pay",
            "[LFB] Send Coins or Gems",
        ),

        BotCommand(
            "trade",
            "[LFB] Trade with another manager",
        ),

        BotCommand(
            "sendplayer",
            "[LFB] Send a player",
        ),

        BotCommand(
            "addcoins",
            "[LFB] Add Coins",
        ),

        BotCommand(
            "sanction",
            "[LFB] Manage sanctions",
        ),

        BotCommand(
            "payfine",
            "[LFB] Pay sanction fine",
        ),

        BotCommand(
            "news",
            "[LFB] Football news",
        ),

        BotCommand(
            "annonce",
            "[LFB] Owner announcement",
        ),

        BotCommand(
            "help",
            "[LFB] Help",
        ),

        BotCommand(
            "command",
            "[LFB] Daily command count",
        ),

        BotCommand(
            "commandrank",
            "[LFB] Command rankings",
        ),

        BotCommand(
            "richlist",
            "[LFB] Richest managers",
        ),

        BotCommand(
            "contract",
            "[LFB] Create or renew player contract",
        ),

        BotCommand(
            "paysalary",
            "[LFB] Pay player salary",
        ),

        BotCommand(
            "sellplayer",
            "[LFB] List player for sale",
        ),

        BotCommand(
            "releaseplayer",
            "[LFB] Release player",
        ),
    ]


    try:

        await application.bot.set_my_commands(
            commands
        )

        print(
            "✅ Telegram command menu updated: "
            f"{len(commands)} commands (Telegram limit: 100 per scope)."
        )

    except Exception as error:

        print(
            "⚠️ Could not update Telegram command menu:",
            type(error).__name__,
            error,
        )


# ==========================================================
# [LFB] DAILY MANAGER PAYMENTS
# ==========================================================

async def daily_manager_payments(
    context,
):

    try:

        salary_result = (
            await pay_all_due_salaries()
        )

    except Exception as exc:

        print(
            f"[LFB DAILY PAYMENTS] salary error: {exc}"
        )

        salary_result = {
            "paid": 0,
            "left": 0,
            "skipped": 0,
        }

    try:

        sponsor_result = (
            await pay_all_due_sponsors()
        )

    except Exception as exc:

        print(
            f"[LFB DAILY PAYMENTS] sponsor error: {exc}"
        )

        sponsor_result = {
            "paid": 0,
            "expired": 0,
            "skipped": 0,
        }

    print(
        "[LFB DAILY PAYMENTS] "
        f"salaries_paid={salary_result.get('paid', 0)} "
        f"salaries_left={salary_result.get('left', 0)} "
        f"sponsors_paid={sponsor_result.get('paid', 0)} "
        f"sponsors_expired={sponsor_result.get('expired', 0)}"
    )


# ==========================================================
# [LFB] REFERRAL-AWARE START
# ==========================================================

async def referral_aware_start(
    update,
    context,
):

    try:

        await process_referral_start(
            update,
            context,
        )

    except Exception as error:

        print(
            "⚠️ [LFB] Referral processing error:",
            type(error).__name__,
            error,
        )

    await start(
        update,
        context,
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # ======================================================
    # [LFB] GLOBAL / PRIORITY CALLBACKS
    # ======================================================

    application.add_handler(
        trade_response_handler,
        group=-20,
    )

    application.add_handler(
        command_tracker_handler,
        group=-10,
    )

    application.add_handler(
        group_tracker_handler,
        group=-11,
    )

    # Friendly / FriendlyPay / substitutions router.
    application.add_handler(
        friendly_callback_router_handler
    )

    # ======================================================
    # [LFB] START
    # ======================================================

    application.add_handler(
        CommandHandler(
            "start",
            referral_aware_start,
        ),
        group=0,
    )

    application.add_handler(
        start_menu_callback_handler
    )

    # ======================================================
    # [MWL] MANUWORLD
    #
    # All MANUWORLD handlers are registered before the
    # normal LFB handlers.
    # ======================================================

    application.add_handler(
        life_handler
    )

    # Core systems with their own complete registration.
    register_mwl_core_handlers(application)
    register_lifestyle_stats_handlers(application)
    register_business_handlers(application)
    register_jobs_handlers(application)
    register_company_jobs_handlers(application)

    # Company contracts: /contract belongs to LFB, so the
    # MWL company-contract command uses /contract_mwl while
    # the remaining MWL company-contract commands keep their
    # original names.
        # ======================================================
    # [MWL] WORK
    # ======================================================

    application.add_handler(
        work_handler
    )
    application.add_handler(
        CommandHandler(
            "contracts",
            contracts_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "contract_mwl",
            contract_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "contract_accept",
            contract_accept_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "contract_tasks",
            contract_tasks_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "contract_complete",
            contract_complete_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            contract_callback,
            pattern=r"^contract:",
        )
    )

    register_company_market_handlers(application)
    register_company_market_management_handlers(application)

    register_bank_handlers(application)
    register_credit_card_handlers(application)
    register_loan_handlers(application)

    # Education: /exam is handled by the complete interactive
    # domain-exam engine below, not the preparation-only command
    # from education.py.
    application.add_handler(
        CommandHandler(
            "school",
            school_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "study",
            study_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "domain",
            domain_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            domain_callback,
            pattern=r"^edu_domain:",
        )
    )

    register_domain_exam_handlers(application)
    register_school_enrollment_handlers(application)
    register_school_profile_handlers(application)

    register_family_handlers(application)
    register_adoption_handlers(application)
    register_marriage_handlers(application)
    register_friendship_handlers(application)
    register_health_handlers(application)
    register_hospital_handlers(application)
    register_housing_handlers(application)
    register_politics_handlers(application)
    register_inventory_handlers(application)
    register_life_events_handlers(application)
    register_expenses_handlers(application)
    register_skills_handlers(application)
    register_wealth_handlers(application)

    application.add_handler(
        addlifecoins_handler
    )

    application.add_handler(
        paylife_handler
    )

    # ======================================================
    # [LFB] CLUB
    # ======================================================

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

    application.add_handler(
        squad_callback_handler
    )

    application.add_handler(
        player_callback_handler
    )

    application.add_handler(
        annonce_handler
    )

    application.add_handler(
        addplayer_handler
    )

    # ======================================================
    # [LFB] MARKET
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
    # [LFB] FOOTBALL ADMIN
    # ======================================================

    application.add_handler(
        cancel_pending_handler
    )

    application.add_handler(
        clear_market_handler
    )

    # ======================================================
    # [LFB] LINEUP
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
    # [LFB] TRAINING
    # ======================================================

    application.add_handler(
        training_handler
    )

    application.add_handler(
        training_callback_handler
    )

    # ======================================================
# [LFB] FRIENDLY
# ======================================================

    application.add_handler(
    friendly_handler
)

    application.add_handler(
    friendlypay_handler
)

    application.add_handler(
    friendlypay_callback_handler
)

    application.add_handler(
    subs_handler
)

    # ======================================================
    # [LFB] MATCH / LEAGUE / CUP
    # ======================================================

    application.add_handler(
        resetgame_handler
    )

    application.add_handler(
        resetgame_callback_handler
    )

    application.add_handler(
        setinfo_handler
    )

    application.add_handler(
        league_handler
    )

    application.add_handler(
        league_callback_handler
    )

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

    application.add_handler(
        stopleague_handler
    )

    application.add_handler(
        startcup_handler
    )

    application.add_handler(
        cupmatches_handler
    )

    application.add_handler(
        cupnextround_handler
    )

    # ======================================================
    # [LFB] INFORMATION
    # ======================================================

    application.add_handler(
        help_handler
    )

    application.add_handler(
        help_callback_handler
    )

    application.add_handler(
        stats_handler
    )

    application.add_handler(
        stats_callback_handler
    )

    application.add_handler(
        news_handler
    )

    application.add_handler(
        profile_handler
    )

    application.add_handler(
        profile_callback_handler
    )

    application.add_handler(
        balance_handler
    )

    application.add_handler(
        rankings_handler
    )

    application.add_handler(
        rankings_callback_handler
    )

    application.add_handler(
        matches_handler
    )

    application.add_handler(
        matches_callback_handler
    )

    # ======================================================
    # [LFB] ECONOMY
    # ======================================================

    application.add_handler(
        pay_handler
    )

    application.add_handler(
        pay_callback_handler
    )

    application.add_handler(
        balance_handler
    )

    application.add_handler(
        achat_handler
    )

    application.add_handler(
        achat_callback_handler
    )

    application.add_handler(
        precheckout_handler
    )

    application.add_handler(
        successful_payment_handler
    )

    application.add_handler(
        trade_handler
    )

    application.add_handler(
        trade_callback_handler
    )

    application.add_handler(
        daily_handler
    )

    application.add_handler(
        ref_handler
    )

    application.add_handler(
        pari_handler
    )

    # ======================================================
    # [LFB] SANCTIONS
    # ======================================================

    application.add_handler(
        sanction_handler,
        group=-100,
    )

    application.add_handler(
        payfine_handler,
        group=-99,
    )

    # ======================================================
    # [LFB] COMMAND / RICHLIST
    # ======================================================

    application.add_handler(
        leagueids_handler
    )

    application.add_handler(
        command_handler
    )

    application.add_handler(
        commandrank_handler
    )

    application.add_handler(
        richlist_handler
    )

    application.add_handler(
        richlist_callback_handler
    )

    # ======================================================
    # [LFB] OTHER
    # ======================================================

    application.add_handler(
        calendar_handler
    )

    application.add_handler(
        cup_handler
    )

    application.add_handler(
        quiz_handler
    )

    application.add_handler(
        quiz_callback_handler
    )

    application.add_handler(
        sendplayer_handler
    )

    application.add_handler(
        addcoins_handler
    )

    application.add_handler(
        users_handler
    )

    # ======================================================
    # [LFB] MANAGER — PLAYER CONTRACTS
    # ======================================================

    application.add_handler(
        contract_handler
    )

    application.add_handler(
        create_contract_handler
    )

    application.add_handler(
        contract_pay_handler
    )

    application.add_handler(
        contract_pay_callback_handler
    )

    # ======================================================
    # [LFB] MANAGER — TRANSFERS
    # ======================================================

    application.add_handler(
        sellplayer_handler
    )

    application.add_handler(
        releaseplayer_handler
    )

    application.add_handler(
        release_callback_handler,
        group=-19,
    )

    application.add_handler(
        mytransfers_handler
    )

    # ======================================================
    # [LFB] MANAGER — SPONSORS
    # ======================================================

    application.add_handler(
        sponsor_handler
    )

    application.add_handler(
        sponsors_handler
    )

    application.add_handler(
        sponsor_select_callback_handler
    )

    # ======================================================
    # [LFB] MANAGER — BALLON D'OR
    # ======================================================

    application.add_handler(
        nomined_handler
    )

    application.add_handler(
        ballondorrank_handler
    )

    application.add_handler(
        ballondororder_handler
    )

    application.add_handler(
        ballondorwinner_handler
    )

    application.add_handler(
        clearballondor_handler
    )

    application.add_handler(
        ballondorhelp_handler
    )

    # ======================================================
    # RUN
    # ======================================================

    print(
        "🤖 Bot is running..."
    )

    application.run_polling()


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    import asyncio

    # Python 3.13 / Windows
    try:

        asyncio.get_event_loop()

    except RuntimeError:

        asyncio.set_event_loop(
            asyncio.new_event_loop()
        )

    main()