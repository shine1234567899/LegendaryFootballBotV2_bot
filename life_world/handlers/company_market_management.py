"""
MANUWORLD — COMPANY MARKET MANAGEMENT

Gestion du marché par le propriétaire d'une entreprise.

Ce module ne modifie pas main.py.
Le branchement des handlers sera effectué lors de
l'intégration finale.
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
from life_world.systems.company_market_system import (
    add_market_stock,
    create_market_product,
    deactivate_market_product,
    get_company_market,
    get_company_market_stats,
    get_company_sales,
    is_company_owner,
    update_market_product,
)


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ")


async def get_actor(
    update: Update,
) -> dict[str, Any] | None:
    """
    Retourne le personnage MANUWORLD correspondant
    au compte Telegram qui exécute la commande.
    """

    user = update.effective_user

    if user is None:
        return None

    character = await get_life_character(user.id)

    if character is None:
        return None

    return dict(character)


async def verify_owner(
    update: Update,
    company_id: int,
) -> dict[str, Any] | None:
    """
    Vérifie que l'utilisateur possède bien l'entreprise.
    """

    actor = await get_actor(update)

    if actor is None:
        message = update.effective_message

        if message:
            await message.reply_text(
                "❌ Tu n'as pas encore de personnage MANUWORLD."
            )

        return None

    if not await is_company_owner(
        int(actor["id"]),
        int(company_id),
    ):
        message = update.effective_message

        if message:
            await message.reply_text(
                "❌ Cette action est réservée au propriétaire "
                "de l'entreprise."
            )

        return None

    return actor


# ============================================================
# MENU
# ============================================================

def management_keyboard(
    company_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📦 Produits",
                    callback_data=f"cmm_products:{company_id}",
                ),
                InlineKeyboardButton(
                    "📊 Statistiques",
                    callback_data=f"cmm_stats:{company_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🧾 Ventes",
                    callback_data=f"cmm_sales:{company_id}",
                ),
            ],
        ]
    )


async def market_management_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /marketmanage <company_id>
    """

    message = update.effective_message

    if message is None:
        return

    if not context.args:
        await message.reply_text(
            "❌ Utilisation :\n"
            "/marketmanage <company_id>"
        )
        return

    try:
        company_id = int(context.args[0])
    except ValueError:
        await message.reply_text(
            "❌ ID entreprise invalide."
        )
        return

    actor = await verify_owner(
        update,
        company_id,
    )

    if actor is None:
        return

    await message.reply_text(
        (
            "🏪━━━━━━━━━━━━━━━━━━━━🏪\n"
            "      𝗠𝗔𝗥𝗞𝗘𝗧 𝗠𝗔𝗡𝗔𝗚𝗘𝗠𝗘𝗡𝗧\n"
            "🏪━━━━━━━━━━━━━━━━━━━━🏪\n\n"
            f"🏢 Entreprise ID : {company_id}\n\n"
            "Gère les produits et consulte les "
            "performances commerciales."
        ),
        reply_markup=management_keyboard(
            company_id
        ),
    )


# ============================================================
# PRODUITS
# ============================================================

async def show_company_products(
    query,
    company_id: int,
):
    products = await get_company_market(
        company_id
    )

    if not products:
        await query.edit_message_text(
            (
                "📦 Aucun produit actif.\n\n"
                "Ajoute ton premier produit "
                "au marché."
            )
        )
        return

    lines = [
        "🏪━━━━━━━━━━━━━━━━━━━━🏪",
        "       𝗧𝗘𝗦 𝗣𝗥𝗢𝗗𝗨𝗜𝗧𝗦",
        "🏪━━━━━━━━━━━━━━━━━━━━🏪",
        "",
    ]

    buttons = []

    for product in products:
        offer_id = int(product["id"])
        name = str(product["product_name"])
        price = int(product["price"])
        stock = int(product["stock"])

        lines.append(
            f"📦 {name}\n"
            f"   💰 {format_money(price)} FCFA\n"
            f"   📦 Stock : {stock}\n"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"⚙️ {name[:25]}",
                    callback_data=(
                        f"cmm_product:{offer_id}:{company_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Retour",
                callback_data=f"cmm_menu:{company_id}",
            )
        ]
    )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# ============================================================
# DÉTAIL PRODUIT
# ============================================================

async def show_product_management(
    query,
    offer_id: int,
    company_id: int,
):
    from life_world.systems.company_market_system import (
        get_market_product,
    )

    product = await get_market_product(
        offer_id
    )

    if product is None:
        await query.edit_message_text(
            "❌ Produit introuvable."
        )
        return

    if int(product["company_id"]) != company_id:
        await query.edit_message_text(
            "❌ Ce produit n'appartient pas à cette entreprise."
        )
        return

    text = (
        "⚙️━━━━━━━━━━━━━━━━━━━━⚙️\n"
        "       𝗚𝗘𝗦𝗧𝗜𝗢𝗡 𝗣𝗥𝗢𝗗𝗨𝗜𝗧\n"
        "⚙️━━━━━━━━━━━━━━━━━━━━⚙️\n\n"
        f"📦 Produit : {product['product_name']}\n"
        f"🏷️ Catégorie : {product['category']}\n"
        f"💰 Prix : "
        f"{format_money(product['price'])} FCFA\n"
        f"📦 Stock : {product['stock']}\n"
    )

    if product.get("description"):
        text += (
            f"\n📝 {product['description'][:500]}\n"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📦 + Stock",
                    callback_data=(
                        f"cmm_stock:{offer_id}:{company_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🗑️ Retirer",
                    callback_data=(
                        f"cmm_remove:{offer_id}:{company_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Produits",
                    callback_data=(
                        f"cmm_products:{company_id}"
                    ),
                ),
            ],
        ]
    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
    )


# ============================================================
# AJOUT DE STOCK
# ============================================================

async def request_stock(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    offer_id: int,
    company_id: int,
):
    """
    Demande une quantité via le prochain message texte.
    """

    context.user_data[
        "cmm_waiting_stock"
    ] = {
        "offer_id": offer_id,
        "company_id": company_id,
    }

    await query.edit_message_text(
        (
            "📦 AJOUT DE STOCK\n\n"
            "Envoie maintenant la quantité à ajouter.\n\n"
            "Exemple :\n"
            "`50`"
        ),
        parse_mode="Markdown",
    )


# ============================================================
# RETRAIT D'UNE OFFRE
# ============================================================

async def remove_product(
    query,
    offer_id: int,
    company_id: int,
):
    result = await deactivate_market_product(
        offer_id=offer_id,
        company_id=company_id,
    )

    await query.edit_message_text(
        result.get(
            "message",
            "❌ Impossible de retirer le produit.",
        )
    )


# ============================================================
# STATISTIQUES
# ============================================================

async def show_stats(
    query,
    company_id: int,
):
    stats = await get_company_market_stats(
        company_id
    )

    if not stats.get("success"):
        await query.edit_message_text(
            stats.get(
                "message",
                "❌ Impossible de récupérer les statistiques.",
            )
        )
        return

    text = (
        "📊━━━━━━━━━━━━━━━━━━━━📊\n"
        "       𝗠𝗔𝗥𝗞𝗘𝗧 𝗦𝗧𝗔𝗧𝗦\n"
        "📊━━━━━━━━━━━━━━━━━━━━📊\n\n"
        f"📦 Offres actives : "
        f"{stats['active_offers']}\n"
        f"📦 Stock disponible : "
        f"{stats['available_stock']}\n\n"
        f"🧾 Nombre de ventes : "
        f"{stats['sales_count']}\n"
        f"📦 Unités vendues : "
        f"{stats['units_sold']}\n"
        f"💰 Revenus du marché : "
        f"{format_money(stats['market_revenue'])} FCFA\n\n"
        f"🏦 Trésorerie : "
        f"{format_money(stats['treasury'])} FCFA\n"
        f"📈 Chiffre d'affaires total : "
        f"{format_money(stats['total_revenue'])} FCFA"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Retour",
                        callback_data=(
                            f"cmm_menu:{company_id}"
                        ),
                    )
                ]
            ]
        ),
    )


# ============================================================
# HISTORIQUE DES VENTES
# ============================================================

async def show_sales(
    query,
    company_id: int,
):
    sales = await get_company_sales(
        company_id,
        limit=20,
    )

    if not sales:
        await query.edit_message_text(
            "🧾 Cette entreprise n'a encore aucune vente."
        )
        return

    lines = [
        "🧾━━━━━━━━━━━━━━━━━━━━🧾",
        "       𝗗𝗘𝗥𝗡𝗜𝗘𝗥𝗘𝗦 𝗩𝗘𝗡𝗧𝗘𝗦",
        "🧾━━━━━━━━━━━━━━━━━━━━🧾",
        "",
    ]

    for sale in sales:

        buyer = (
            sale.get("buyer_username")
            or sale.get("buyer_first_name")
            or "Joueur"
        )

        product = (
            sale.get("product_name")
            or "Produit"
        )

        quantity = int(
            sale.get("quantity") or 0
        )

        total = int(
            sale.get("total_price") or 0
        )

        lines.append(
            f"📦 {product}\n"
            f"👤 Acheteur : {buyer}\n"
            f"🔢 Quantité : {quantity}\n"
            f"💰 Total : {format_money(total)} FCFA\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Retour",
                        callback_data=(
                            f"cmm_menu:{company_id}"
                        ),
                    )
                ]
            ]
        ),
    )


# ============================================================
# CALLBACKS
# ============================================================

async def company_market_management_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    data = query.data or ""

    # --------------------------------------------------------
    # MENU
    # --------------------------------------------------------

    if data.startswith("cmm_menu:"):

        try:
            company_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await query.edit_message_text(
            (
                "🏪━━━━━━━━━━━━━━━━━━━━🏪\n"
                "      𝗠𝗔𝗥𝗞𝗘𝗧 𝗠𝗔𝗡𝗔𝗚𝗘𝗠𝗘𝗡𝗧\n"
                "🏪━━━━━━━━━━━━━━━━━━━━🏪\n\n"
                f"🏢 Entreprise ID : {company_id}\n\n"
                "Choisis une section."
            ),
            reply_markup=management_keyboard(
                company_id
            ),
        )
        return

    # --------------------------------------------------------
    # PRODUITS
    # --------------------------------------------------------

    if data.startswith("cmm_products:"):

        try:
            company_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_company_products(
            query,
            company_id,
        )
        return

    # --------------------------------------------------------
    # PRODUIT
    # --------------------------------------------------------

    if data.startswith("cmm_product:"):

        try:
            _, offer_id, company_id = data.split(":")
            offer_id = int(offer_id)
            company_id = int(company_id)
        except ValueError:
            return

        await show_product_management(
            query,
            offer_id,
            company_id,
        )
        return

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    if data.startswith("cmm_stock:"):

        try:
            _, offer_id, company_id = data.split(":")
            offer_id = int(offer_id)
            company_id = int(company_id)
        except ValueError:
            return

        await request_stock(
            query,
            context,
            offer_id,
            company_id,
        )
        return

    # --------------------------------------------------------
    # RETRAIT
    # --------------------------------------------------------

    if data.startswith("cmm_remove:"):

        try:
            _, offer_id, company_id = data.split(":")
            offer_id = int(offer_id)
            company_id = int(company_id)
        except ValueError:
            return

        await remove_product(
            query,
            offer_id,
            company_id,
        )
        return

    # --------------------------------------------------------
    # STATS
    # --------------------------------------------------------

    if data.startswith("cmm_stats:"):

        try:
            company_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_stats(
            query,
            company_id,
        )
        return

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if data.startswith("cmm_sales:"):

        try:
            company_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_sales(
            query,
            company_id,
        )
        return


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_company_market_management_handlers(
    application: Application,
) -> None:
    """
    Enregistre les handlers de gestion du marché.

    À brancher dans main.py uniquement pendant
    l'intégration finale.
    """

    application.add_handler(
        CommandHandler(
            "marketmanage",
            market_management_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            company_market_management_callback,
            pattern=r"^cmm_",
        )
    )


__all__ = [
    "market_management_command",
    "company_market_management_callback",
    "register_company_market_management_handlers",
]