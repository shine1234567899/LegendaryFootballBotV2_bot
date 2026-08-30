"""
MANUWORLD — COMPANY CONTRACT HANDLER

Interface Telegram du système de contrats d'entreprise.

Commandes :
    /contracts
    /contract <id>
    /contract_accept <id>
    /contract_tasks <id>
    /contract_complete <id>

Fonctionnalités :
    - consulter les contrats d'une entreprise
    - consulter un contrat
    - accepter un contrat
    - consulter les tâches
    - terminer une tâche
    - consulter les commissions

IMPORTANT :
    main.py n'est pas modifié ici.
"""

from __future__ import annotations

from typing import Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from life_world.database import get_life_character

from life_world.systems.company_contract_system import (
    get_contract,
    accept_contract,
    get_company_contracts,
    get_contract_tasks,
    complete_task,
    complete_contract,
    get_pending_commissions,
    format_contract,
)


# ============================================================
# UTILITAIRES
# ============================================================

async def get_actor(
    update: Update,
) -> dict[str, Any] | None:

    user = update.effective_user

    if user is None:
        return None

    character = await get_life_character(
        user.id
    )

    if character is None:
        return None

    return dict(character)


def contract_keyboard(
    contract_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Tâches",
                    callback_data=(
                        f"contract:tasks:{contract_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Accepter",
                    callback_data=(
                        f"contract:accept:{contract_id}"
                    ),
                ),
                InlineKeyboardButton(
                    "🏁 Terminer",
                    callback_data=(
                        f"contract:complete:{contract_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Contrats",
                    callback_data="contract:list",
                )
            ],
        ]
    )


# ============================================================
# FORMATAGE DES CONTRATS
# ============================================================

def format_contracts(
    contracts: list[dict[str, Any]],
) -> str:

    if not contracts:

        return (
            "📑 **CONTRATS D'ENTREPRISE**\n\n"
            "Aucun contrat trouvé."
        )

    lines = [
        "📑 **CONTRATS D'ENTREPRISE**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for contract in contracts:

        contract_id = contract.get(
            "id",
            "—",
        )

        title = contract.get(
            "title",
            contract.get(
                "name",
                "Contrat",
            ),
        )

        status = contract.get(
            "status",
            "—",
        )

        difficulty = contract.get(
            "difficulty",
            "—",
        )

        reward = int(
            contract.get(
                "reward",
                contract.get(
                    "total_reward",
                    0,
                ),
            )
            or 0
        )

        lines.extend(
            [
                f"📑 **#{contract_id} — {title}**",
                f"   📊 Statut : {status}",
                f"   ⚔️ Difficulté : {difficulty}",
                (
                    f"   💰 Récompense : "
                    f"{reward:,} FCFA"
                ).replace(",", " "),
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================
# /CONTRACTS
# ============================================================

async def contracts_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:

        await message.reply_text(
            "❌ Tu n'as pas encore créé "
            "ton personnage MANUWORLD."
        )

        return

    contracts = await get_company_contracts(
        int(actor["id"])
    )

    await message.reply_text(
        format_contracts(contracts),
        parse_mode="Markdown",
    )


# ============================================================
# /CONTRACT
# ============================================================

async def contract_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    if len(context.args) != 1:

        await message.reply_text(
            "📑 **CONSULTER UN CONTRAT**\n\n"
            "Utilisation :\n"
            "`/contract <id>`\n\n"
            "Exemple :\n"
            "`/contract 12`",
            parse_mode="Markdown",
        )

        return

    try:

        contract_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ ID du contrat invalide."
        )

        return

    contract = await get_contract(
        contract_id
    )

    if contract is None:

        await message.reply_text(
            "❌ Contrat introuvable."
        )

        return

    await message.reply_text(
        format_contract(contract),
        reply_markup=contract_keyboard(
            contract_id
        ),
        parse_mode="Markdown",
    )


# ============================================================
# /CONTRACT_ACCEPT
# ============================================================

async def contract_accept_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:

        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )

        return

    if len(context.args) != 1:

        await message.reply_text(
            "Utilisation : `/contract_accept <id>`",
            parse_mode="Markdown",
        )

        return

    try:

        contract_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ ID du contrat invalide."
        )

        return

    result = await accept_contract(
        contract_id=contract_id,
        character_id=int(
            actor["id"]
        ),
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible d'accepter le contrat.",
        ),
        parse_mode="Markdown",
    )


# ============================================================
# TÂCHES
# ============================================================

async def show_tasks(
    query,
    contract_id: int,
):

    tasks = await get_contract_tasks(
        contract_id
    )

    if not tasks:

        text = (
            "📋 **TÂCHES DU CONTRAT**\n\n"
            "Aucune tâche enregistrée."
        )

    else:

        lines = [
            "📋 **TÂCHES DU CONTRAT**",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        for task in tasks:

            task_id = task.get(
                "id",
                "—",
            )

            title = task.get(
                "title",
                task.get(
                    "name",
                    "Tâche",
                ),
            )

            status = task.get(
                "status",
                "—",
            )

            reward = int(
                task.get(
                    "reward",
                    0,
                )
                or 0
            )

            lines.extend(
                [
                    (
                        f"📋 **#{task_id} — "
                        f"{title}**"
                    ),
                    f"   📊 {status}",
                    (
                        f"   💰 "
                        f"{reward:,} FCFA"
                    ).replace(",", " "),
                    "",
                ]
            )

        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Contrat",
                        callback_data=(
                            f"contract:view:{contract_id}"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# /CONTRACT_TASKS
# ============================================================

async def contract_tasks_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    if len(context.args) != 1:

        await message.reply_text(
            "Utilisation : `/contract_tasks <id>`",
            parse_mode="Markdown",
        )

        return

    try:

        contract_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ ID du contrat invalide."
        )

        return

    tasks = await get_contract_tasks(
        contract_id
    )

    if not tasks:

        await message.reply_text(
            "📋 Aucune tâche pour ce contrat."
        )

        return

    lines = [
        "📋 **TÂCHES DU CONTRAT**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for task in tasks:

        task_id = task.get(
            "id",
            "—",
        )

        title = task.get(
            "title",
            task.get(
                "name",
                "Tâche",
            ),
        )

        status = task.get(
            "status",
            "—",
        )

        lines.append(
            f"📋 #{task_id} — **{title}** — {status}"
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


# ============================================================
# /CONTRACT_COMPLETE
# ============================================================

async def contract_complete_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:

        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )

        return

    if len(context.args) != 1:

        await message.reply_text(
            "Utilisation : `/contract_complete <id>`",
            parse_mode="Markdown",
        )

        return

    try:

        contract_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ ID du contrat invalide."
        )

        return

    result = await complete_contract(
        contract_id=contract_id,
        character_id=int(
            actor["id"]
        ),
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible de terminer le contrat.",
        ),
        parse_mode="Markdown",
    )


# ============================================================
# COMMISSIONS
# ============================================================

async def show_commissions(
    query,
    character_id: int,
):

    commissions = await get_pending_commissions(
        character_id
    )

    if not commissions:

        text = (
            "💰 **COMMISSIONS EN ATTENTE**\n\n"
            "Aucune commission en attente."
        )

    else:

        lines = [
            "💰 **COMMISSIONS EN ATTENTE**",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        for commission in commissions:

            amount = int(
                commission.get(
                    "amount",
                    0,
                )
                or 0
            )

            status = commission.get(
                "status",
                "pending",
            )

            lines.append(
                f"💰 {amount:,} FCFA — {status}".replace(
                    ",",
                    " ",
                )
            )

        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Contrats",
                        callback_data="contract:list",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def contract_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    await query.answer()

    actor = await get_actor(update)

    if actor is None:

        await query.edit_message_text(
            "❌ Personnage MANUWORLD introuvable."
        )

        return

    character_id = int(
        actor["id"]
    )

    data = str(
        query.data or ""
    )

    parts = data.split(":")

    if len(parts) < 2:

        await query.edit_message_text(
            "❌ Action inconnue."
        )

        return

    action = parts[1]

    # --------------------------------------------------------
    # LISTE
    # --------------------------------------------------------

    if action == "list":

        contracts = await get_company_contracts(
            character_id
        )

        await query.edit_message_text(
            format_contracts(contracts),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💰 Commissions",
                            callback_data=(
                                "contract:commissions"
                            ),
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # COMMISSIONS
    # --------------------------------------------------------

    if action == "commissions":

        await show_commissions(
            query,
            character_id,
        )

        return

    # --------------------------------------------------------
    # ACTIONS AVEC ID
    # --------------------------------------------------------

    if action in {
        "view",
        "tasks",
        "accept",
        "complete",
    }:

        if len(parts) < 3:

            await query.edit_message_text(
                "❌ Contrat invalide."
            )

            return

        try:

            contract_id = int(
                parts[2]
            )

        except ValueError:

            await query.edit_message_text(
                "❌ ID du contrat invalide."
            )

            return

        contract = await get_contract(
            contract_id
        )

        if contract is None:

            await query.edit_message_text(
                "❌ Contrat introuvable."
            )

            return

        if action == "view":

            await query.edit_message_text(
                format_contract(contract),
                reply_markup=contract_keyboard(
                    contract_id
                ),
                parse_mode="Markdown",
            )

            return

        if action == "tasks":

            await show_tasks(
                query,
                contract_id,
            )

            return

        if action == "accept":

            result = await accept_contract(
                contract_id=contract_id,
                character_id=character_id,
            )

            await query.edit_message_text(
                result.get(
                    "message",
                    "❌ Impossible d'accepter le contrat.",
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⬅️ Contrat",
                                callback_data=(
                                    f"contract:view:{contract_id}"
                                ),
                            )
                        ]
                    ]
                ),
                parse_mode="Markdown",
            )

            return

        if action == "complete":

            result = await complete_contract(
                contract_id=contract_id,
                character_id=character_id,
            )

            await query.edit_message_text(
                result.get(
                    "message",
                    "❌ Impossible de terminer le contrat.",
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📑 Contrats",
                                callback_data="contract:list",
                            )
                        ]
                    ]
                ),
                parse_mode="Markdown",
            )

            return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_company_contract_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "contracts",
            contracts_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "contract",
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


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "contracts_command",
    "contract_command",
    "contract_accept_command",
    "contract_tasks_command",
    "contract_complete_command",
    "contract_callback",
    "register_company_contract_handlers",
]