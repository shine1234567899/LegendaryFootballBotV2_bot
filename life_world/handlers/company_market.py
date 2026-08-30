"""
MANUWORLD — COMPANY MARKET HANDLER

Commandes :

    /market
    /market <recherche>

Le système permet aux joueurs de consulter les produits
mis en vente par les entreprises et de les acheter.

IMPORTANT :
    Ce fichier ne modifie pas main.py.
    Le branchement du handler sera fait plus tard.
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
    buy_market_product,
    get_company_market,
    get_market_product,
    search_market,
)


# ============================================================
# CONSTANTES
# ============================================================

MARKET_PAGE_SIZE = 8


# ============================================================
# OUTILS
# ============================================================

async def get_actor(update: Update):
    """
    Retourne le personnage MANUWORLD du joueur actuel.
    """

    user = update.effective_user

    if user is None:
        return None

    return await get_life_character(user.id)


def format_money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ")


def display_product(product: dict[str, Any]) -> str:
    """
    Construit l'affichage d'un produit.
    """

    stock = int(product.get("stock") or 0)
    price = int(product.get("price") or 0)

    company_name = (
        product.get("company_name")
        or "Entreprise"
    )

    description = (
        str(product.get("description") or "").strip()
    )

    lines = [
        f"📦 {product.get('product_name', 'Produit')}",
        f"🏢 {company_name}",
        f"🏷️ Catégorie : {product.get('category', 'other')}",
        f"💰 Prix : {format_money(price)} FCFA",
        f"📦 Stock : {stock}",
    ]

    if description:
        lines.append(
            f"📝 {description[:300]}"
        )

    return "\n".join(lines)


def market_keyboard(
    products: list[dict[str, Any]],
    page: int = 0,
) -> InlineKeyboardMarkup:
    """
    Construit le clavier principal du marché.
    """

    total = len(products)

    if total == 0:
        return InlineKeyboardMarkup([])

    start = page * MARKET_PAGE_SIZE
    end = start + MARKET_PAGE_SIZE

    current = products[start:end]

    buttons: list[list[InlineKeyboardButton]] = []

    for product in current:
        offer_id = int(product["id"])
        name = str(
            product.get("product_name")
            or "Produit"
        )

        price = int(product.get("price") or 0)

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"📦 {name[:25]} — "
                        f"{format_money(price)} FCFA"
                    ),
                    callback_data=f"cm_view:{offer_id}",
                )
            ]
        )

    navigation: list[InlineKeyboardButton] = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"cm_page:{page - 1}",
            )
        )

    if end < total:
        navigation.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"cm_page:{page + 1}",
            )
        )

    if navigation:
        buttons.append(navigation)

    return InlineKeyboardMarkup(buttons)


def product_keyboard(
    offer_id: int,
) -> InlineKeyboardMarkup:
    """
    Clavier d'une offre.
    """

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🛒 Acheter x1",
                    callback_data=f"cm_buy:{offer_id}:1",
                ),
                InlineKeyboardButton(
                    text="🛒 Acheter x5",
                    callback_data=f"cm_buy:{offer_id}:5",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Acheter x10",
                    callback_data=f"cm_buy:{offer_id}:10",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Retour au marché",
                    callback_data="cm_back",
                )
            ],
        ]
    )


def confirmation_keyboard(
    offer_id: int,
    quantity: int,
) -> InlineKeyboardMarkup:
    """
    Confirmation d'achat.
    """

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="✅ Confirmer",
                    callback_data=(
                        f"cm_confirm:{offer_id}:{quantity}"
                    ),
                ),
                InlineKeyboardButton(
                    text="❌ Annuler",
                    callback_data=f"cm_view:{offer_id}",
                ),
            ]
        ]
    )


# ============================================================
# TEXTE DU MARCHÉ
# ============================================================

def market_header(
    search: str | None = None,
) -> str:
    text = (
        "🏪━━━━━━━━━━━━━━━━━━━━🏪\n"
        "       𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗠𝗔𝗥𝗞𝗘𝗧\n"
        "🏪━━━━━━━━━━━━━━━━━━━━🏪\n\n"
    )

    if search:
        text += (
            f"🔎 Recherche : `{search}`\n\n"
        )

    text += (
        "Voici les produits actuellement "
        "proposés par les entreprises.\n\n"
        "Sélectionne un produit pour voir "
        "ses détails et l'acheter."
    )

    return text


# ============================================================
# /MARKET
# ============================================================

async def market_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /market
    /market recherche
    """

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

    search = " ".join(
        context.args
    ).strip()

    if search:

        products = await search_market(
            search
        )

        context.user_data[
            "company_market_products"
        ] = products

        context.user_data[
            "company_market_search"
        ] = search

    else:

        products = await _get_market_products()

        context.user_data[
            "company_market_products"
        ] = products

        context.user_data[
            "company_market_search"
        ] = None

    if not products:

        if search:
            await message.reply_text(
                "🔎 Aucun produit trouvé pour "
                f"« {search} »."
            )
        else:
            await message.reply_text(
                "🏪 Le marché est actuellement vide."
            )

        return

    await message.reply_text(
        market_header(
            search or None
        ),
        reply_markup=market_keyboard(
            products,
            0,
        ),
        parse_mode="Markdown",
    )


# ============================================================
# RÉCUPÉRATION DU MARCHÉ
# ============================================================

async def _get_market_products():
    """
    Récupère les offres actives de toutes les entreprises.
    """

    # Il n'existe pas de fonction globale dans le système
    # pour cette lecture, donc on utilise une recherche large.
    #
    # Les recherches vides ne sont volontairement pas envoyées
    # au système.
    #
    # Cette fonction sera remplacée par une fonction globale
    # dédiée lorsqu'on développera les fonctions administratives
    # du marché.
    #
    # Pour l'instant, elle retourne les offres des entreprises
    # accessibles via la recherche générale.

    from sqlalchemy import text

    from life_world.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    m.id,
                    m.company_id,
                    m.product_name,
                    m.category,
                    m.price,
                    m.stock,
                    m.description,
                    m.active,
                    c.name AS company_name
                FROM life_company_market m
                INNER JOIN life_companies c
                    ON c.id = m.company_id
                WHERE m.active = TRUE
                  AND c.active = TRUE
                ORDER BY
                    m.category ASC,
                    m.product_name ASC,
                    m.id ASC
                LIMIT 100
                """
            )
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# AFFICHAGE D'UNE OFFRE
# ============================================================

async def show_product(
    query,
    offer_id: int,
):
    """
    Affiche les détails d'une offre.
    """

    product = await get_market_product(
        offer_id
    )

    if product is None:
        await query.edit_message_text(
            "❌ Cette offre n'est plus disponible."
        )
        return

    text = (
        "🏪━━━━━━━━━━━━━━━━━━━━🏪\n"
        "          𝗣𝗥𝗢𝗗𝗨𝗜𝗧\n"
        "🏪━━━━━━━━━━━━━━━━━━━━🏪\n\n"
        f"{display_product(product)}\n\n"
        "Choisis une quantité :"
    )

    await query.edit_message_text(
        text,
        reply_markup=product_keyboard(
            offer_id
        ),
    )


# ============================================================
# CONFIRMATION
# ============================================================

async def show_confirmation(
    query,
    offer_id: int,
    quantity: int,
):
    """
    Affiche la confirmation avant paiement.
    """

    product = await get_market_product(
        offer_id
    )

    if product is None:
        await query.edit_message_text(
            "❌ Cette offre n'est plus disponible."
        )
        return

    stock = int(product["stock"] or 0)
    price = int(product["price"] or 0)

    if stock < quantity:
        await query.edit_message_text(
            (
                "❌ Stock insuffisant.\n\n"
                f"📦 Disponible : {stock}\n"
                f"🛒 Demandé : {quantity}"
            ),
            reply_markup=product_keyboard(
                offer_id
            ),
        )
        return

    total = price * quantity

    text = (
        "🛒━━━━━━━━━━━━━━━━━━━━🛒\n"
        "       𝗖𝗢𝗡𝗙𝗜𝗥𝗠𝗔𝗧𝗜𝗢𝗡\n"
        "🛒━━━━━━━━━━━━━━━━━━━━🛒\n\n"
        f"📦 Produit : {product['product_name']}\n"
        f"🏢 Entreprise : "
        f"{product.get('company_name', 'Entreprise')}\n"
        f"🔢 Quantité : {quantity}\n"
        f"💰 Prix unitaire : "
        f"{format_money(price)} FCFA\n"
        f"💵 Total : "
        f"{format_money(total)} FCFA\n\n"
        "Confirmer l'achat ?"
    )

    await query.edit_message_text(
        text,
        reply_markup=confirmation_keyboard(
            offer_id,
            quantity,
        ),
    )


# ============================================================
# CALLBACKS
# ============================================================

async def company_market_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    data = query.data or ""

    # --------------------------------------------------------
    # PAGE
    # --------------------------------------------------------

    if data.startswith("cm_page:"):

        try:
            page = int(
                data.split(":", 1)[1]
            )
        except ValueError:
            return

        products = context.user_data.get(
            "company_market_products"
        )

        if not products:
            products = await _get_market_products()

        search = context.user_data.get(
            "company_market_search"
        )

        await query.edit_message_text(
            market_header(
                search
            ),
            reply_markup=market_keyboard(
                products,
                page,
            ),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # RETOUR
    # --------------------------------------------------------

    if data == "cm_back":

        products = context.user_data.get(
            "company_market_products"
        )

        if not products:
            products = await _get_market_products()

        search = context.user_data.get(
            "company_market_search"
        )

        await query.edit_message_text(
            market_header(
                search
            ),
            reply_markup=market_keyboard(
                products,
                0,
            ),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # VOIR PRODUIT
    # --------------------------------------------------------

    if data.startswith("cm_view:"):

        try:
            offer_id = int(
                data.split(":", 1)[1]
            )
        except ValueError:
            return

        await show_product(
            query,
            offer_id,
        )

        return

    # --------------------------------------------------------
    # ACHAT
    # --------------------------------------------------------

    if data.startswith("cm_buy:"):

        try:
            _, offer_id, quantity = data.split(":")
            offer_id = int(offer_id)
            quantity = int(quantity)
        except ValueError:
            return

        await show_confirmation(
            query,
            offer_id,
            quantity,
        )

        return

    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    if data.startswith("cm_confirm:"):

        try:
            _, offer_id, quantity = data.split(":")
            offer_id = int(offer_id)
            quantity = int(quantity)
        except ValueError:
            return

        user = query.from_user

        if user is None:
            return

        actor = await get_life_character(
            user.id
        )

        if actor is None:
            await query.edit_message_text(
                "❌ Personnage MANUWORLD introuvable."
            )
            return

        result = await buy_market_product(
            buyer_character_id=int(actor["id"]),
            offer_id=offer_id,
            quantity=quantity,
        )

        if not result.get("success"):
            await query.edit_message_text(
                result.get(
                    "message",
                    "❌ Achat impossible.",
                )
            )
            return

        await query.edit_message_text(
            result["message"]
        )

        return


# ============================================================
# REGISTRATION
# ============================================================

def register_company_market_handlers(
    application: Application,
) -> None:
    """
    Enregistre les handlers du marché des entreprises.

    Le branchement dans main.py sera effectué
    uniquement lors de la phase d'intégration finale.
    """

    application.add_handler(
        CommandHandler(
            "market",
            market_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            company_market_callback,
            pattern=r"^cm_",
        )
    )


__all__ = [
    "market_command",
    "company_market_callback",
    "register_company_market_handlers",
]