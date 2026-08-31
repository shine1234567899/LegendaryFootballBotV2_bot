from __future__ import annotations

from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# MANUWORLD — COMPANY MARKET SYSTEM
# ============================================================
#
# Gestion du marché des entreprises :
#
# life_company_market
#       ↓
# produits / prix / stock
#       ↓
# achat
#       ↓
# life_company_market_sales
#       ↓
# trésorerie de l'entreprise
#
# Ce fichier ne contient volontairement aucun handler Telegram.
# Les handlers pourront être branchés plus tard.
# ============================================================


# ------------------------------------------------------------
# UTILITAIRES
# ------------------------------------------------------------

def _clean_text(value: Any, maximum: int) -> str:
    return str(value or "").strip()[:maximum]


def _positive_int(value: Any) -> int:
    value = int(value)

    if value <= 0:
        raise ValueError("Value must be positive.")

    return value


def _non_negative_int(value: Any) -> int:
    value = int(value)

    if value < 0:
        raise ValueError("Value cannot be negative.")

    return value



# ============================================================
# MARKET — CATALOGUE PERMANENT MANUWORLD
# ============================================================

DEFAULT_MARKET_PRODUCTS = [
    ("Apple iPhone 16", "smartphone", 850_000, 10, "Apple"),
    ("Samsung Galaxy S25", "smartphone", 780_000, 10, "Samsung"),
    ("Apple MacBook Air", "computer", 1_200_000, 8, "Apple"),
    ("Sony PlayStation 5", "gaming", 650_000, 10, "Sony"),
    ("JBL Headphones", "audio", 120_000, 15, "JBL"),
    ("Apple AirPods Pro", "audio", 180_000, 15, "Apple"),
    ("Apple Watch", "watch", 300_000, 10, "Apple"),
    ("Samsung Galaxy Watch", "watch", 220_000, 10, "Samsung"),
    ("Nike Air Max", "fashion", 150_000, 15, "Nike"),
    ("Adidas Originals", "fashion", 130_000, 15, "Adidas"),
    ("Puma Sneakers", "fashion", 110_000, 15, "Puma"),
    ("Lacoste Polo", "fashion", 90_000, 15, "Lacoste"),
    ("Ray-Ban Sunglasses", "accessory", 180_000, 10, "Ray-Ban"),
    ("Rolex Classic", "luxury", 8_000_000, 3, "Rolex"),
    ("Louis Vuitton Bag", "luxury", 1_800_000, 5, "Louis Vuitton"),
    ("Gucci Bag", "luxury", 1_500_000, 5, "Gucci"),
    ("Toyota Corolla", "vehicle", 12_000_000, 3, "Toyota"),
    ("Mercedes-Benz C-Class", "vehicle", 35_000_000, 2, "Mercedes-Benz"),
    ("Canon EOS Camera", "camera", 700_000, 6, "Canon"),
    ("Sony Bravia TV", "electronics", 900_000, 6, "Sony"),
]


async def seed_permanent_market() -> int:
    """
    [MWL] Ensures the permanent branded catalogue exists.
    Products are inserted only once and their stock is never reset.
    """

    async with AsyncSessionLocal() as session:
        # A nullable owner is supported by the database migration.
        company_result = await session.execute(
            text(
                """
                SELECT id
                FROM life_companies
                WHERE name = 'MANUWORLD OFFICIAL MARKET'
                LIMIT 1
                """
            )
        )
        company = company_result.first()

        if company is None:
            company_insert = await session.execute(
                text(
                    """
                    INSERT INTO life_companies (
                        name,
                        owner_character_id,
                        capital,
                        treasury,
                        reputation,
                        credibility,
                        health,
                        total_revenue,
                        active
                    )
                    VALUES (
                        'MANUWORLD OFFICIAL MARKET',
                        NULL,
                        0,
                        0,
                        100,
                        100,
                        100,
                        0,
                        TRUE
                    )
                    RETURNING id
                    """
                )
            )
            company_id = int(company_insert.scalar_one())
        else:
            company_id = int(company[0])

        inserted = 0

        for product_name, category, price, stock, brand in DEFAULT_MARKET_PRODUCTS:
            exists = await session.execute(
                text(
                    """
                    SELECT 1
                    FROM life_company_market
                    WHERE company_id = :company_id
                      AND product_name = :product_name
                    LIMIT 1
                    """
                ),
                {
                    "company_id": company_id,
                    "product_name": product_name,
                },
            )

            if exists.first() is not None:
                continue

            await session.execute(
                text(
                    """
                    INSERT INTO life_company_market (
                        company_id,
                        product_name,
                        category,
                        price,
                        stock,
                        description,
                        active
                    )
                    VALUES (
                        :company_id,
                        :product_name,
                        :category,
                        :price,
                        :stock,
                        :description,
                        TRUE
                    )
                    """
                ),
                {
                    "company_id": company_id,
                    "product_name": product_name,
                    "category": category,
                    "price": price,
                    "stock": stock,
                    "description": f"Produit de marque {brand}.",
                },
            )
            inserted += 1

        await session.commit()
        return inserted


# ============================================================
# ENTREPRISE
# ============================================================

async def get_company(company_id: int) -> dict[str, Any] | None:
    """
    Retourne une entreprise active.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    owner_character_id,
                    grade_id,
                    capital,
                    treasury,
                    reputation,
                    credibility,
                    health,
                    total_revenue,
                    active
                FROM life_companies
                WHERE id = :company_id
                  AND active = TRUE
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        row = result.mappings().first()

        if row is None:
            return None

        return dict(row)


async def get_company_owner(
    company_id: int,
) -> int | None:
    """
    Retourne le character_id du propriétaire de l'entreprise.
    """

    company = await get_company(company_id)

    if company is None:
        return None

    return int(company["owner_character_id"])


# ============================================================
# MARKET — LECTURE
# ============================================================

async def get_market_product(
    offer_id: int,
) -> dict[str, Any] | None:
    """
    Retourne une offre active du marché.
    """

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
                    m.created_at,
                    m.updated_at,
                    c.name AS company_name
                FROM life_company_market m
                INNER JOIN life_companies c
                    ON c.id = m.company_id
                WHERE m.id = :offer_id
                  AND m.active = TRUE
                  AND c.active = TRUE
                LIMIT 1
                """
            ),
            {
                "offer_id": int(offer_id),
            },
        )

        row = result.mappings().first()

        if row is None:
            return None

        return dict(row)

async def get_global_market(
    category: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Retourne les offres actives de toutes les entreprises.

    Cette fonction est utilisée par le handler /market afin que
    les handlers Telegram n'aient jamais besoin d'exécuter
    directement du SQL.
    """

    category = (
        _clean_text(category, 40)
        if category is not None
        else None
    )

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(200, limit))

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
                    m.created_at,
                    m.updated_at,
                    c.name AS company_name
                FROM life_company_market m
                INNER JOIN life_companies c
                    ON c.id = m.company_id
                WHERE m.active = TRUE
                  AND c.active = TRUE
                  AND m.stock > 0
                  AND (
                      :category IS NULL
                      OR LOWER(m.category) = LOWER(:category)
                  )
                ORDER BY
                    m.category ASC,
                    m.product_name ASC,
                    m.price ASC,
                    m.id ASC
                LIMIT :limit
                """
            ),
            {
                "category": category,
                "limit": limit,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]
async def get_company_market(
    company_id: int,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retourne toutes les offres actives d'une entreprise.
    """

    category = (
        _clean_text(category, 40)
        if category is not None
        else None
    )

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
                    m.created_at,
                    m.updated_at
                FROM life_company_market m
                INNER JOIN life_companies c
                    ON c.id = m.company_id
                WHERE m.company_id = :company_id
                  AND m.active = TRUE
                  AND c.active = TRUE
                  AND (
                      :category IS NULL
                      OR LOWER(m.category) = LOWER(:category)
                  )
                ORDER BY
                    m.category ASC,
                    m.product_name ASC,
                    m.id ASC
                """
            ),
            {
                "company_id": int(company_id),
                "category": category,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


async def search_market(
    search: str,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """
    Recherche globale dans le marché des entreprises.
    """

    search = _clean_text(search, 160)

    if not search:
        return []

    category = (
        _clean_text(category, 40)
        if category is not None
        else None
    )

    pattern = f"%{search}%"

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
                  AND (
                      m.product_name ILIKE :pattern
                      OR m.description ILIKE :pattern
                      OR m.category ILIKE :pattern
                      OR c.name ILIKE :pattern
                  )
                  AND (
                      :category IS NULL
                      OR LOWER(m.category) = LOWER(:category)
                  )
                ORDER BY
                    CASE
                        WHEN LOWER(m.product_name)
                            = LOWER(:search)
                        THEN 0
                        ELSE 1
                    END,
                    m.price ASC,
                    m.product_name ASC
                LIMIT 100
                """
            ),
            {
                "pattern": pattern,
                "search": search,
                "category": category,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# MARKET — CRÉATION D'UNE OFFRE
# ============================================================

async def create_market_product(
    company_id: int,
    product_name: str,
    price: int,
    stock: int,
    category: str = "other",
    description: str | None = None,
) -> dict[str, Any]:
    """
    Crée un nouveau produit dans le marché d'une entreprise.
    """

    product_name = _clean_text(product_name, 160)
    category = _clean_text(category, 40) or "other"
    description = (
        _clean_text(description, 2000)
        if description is not None
        else None
    )

    if not product_name:
        return {
            "success": False,
            "message": "❌ Nom du produit invalide.",
        }

    try:
        price = _positive_int(price)
        stock = _non_negative_int(stock)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Prix ou stock invalide.",
        }

    async with AsyncSessionLocal() as session:

        company_result = await session.execute(
            text(
                """
                SELECT id
                FROM life_companies
                WHERE id = :company_id
                  AND active = TRUE
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        if company_result.first() is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_market (
                    company_id,
                    product_name,
                    category,
                    price,
                    stock,
                    description,
                    active
                )
                VALUES (
                    :company_id,
                    :product_name,
                    :category,
                    :price,
                    :stock,
                    :description,
                    TRUE
                )
                RETURNING id
                """
            ),
            {
                "company_id": int(company_id),
                "product_name": product_name,
                "category": category,
                "price": price,
                "stock": stock,
                "description": description,
            },
        )

        offer_id = int(result.scalar_one())

        await session.commit()

    return {
        "success": True,
        "offer_id": offer_id,
        "message": (
            "✅ Produit ajouté au marché.\n"
            f"📦 Produit : {product_name}\n"
            f"💰 Prix : {price:,} FCFA\n"
            f"📦 Stock : {stock}"
        ),
    }


# ============================================================
# MARKET — MODIFICATION
# ============================================================

async def update_market_product(
    offer_id: int,
    company_id: int,
    price: int | None = None,
    stock: int | None = None,
    product_name: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Modifie une offre appartenant à une entreprise.

    Seuls les champs fournis sont modifiés.
    """

    changes: list[str] = []
    params: dict[str, Any] = {
        "offer_id": int(offer_id),
        "company_id": int(company_id),
    }

    if price is not None:
        try:
            price = _positive_int(price)
        except (TypeError, ValueError):
            return {
                "success": False,
                "message": "❌ Prix invalide.",
            }

        changes.append("price = :price")
        params["price"] = price

    if stock is not None:
        try:
            stock = _non_negative_int(stock)
        except (TypeError, ValueError):
            return {
                "success": False,
                "message": "❌ Stock invalide.",
            }

        changes.append("stock = :stock")
        params["stock"] = stock

    if product_name is not None:
        product_name = _clean_text(product_name, 160)

        if not product_name:
            return {
                "success": False,
                "message": "❌ Nom du produit invalide.",
            }

        changes.append("product_name = :product_name")
        params["product_name"] = product_name

    if category is not None:
        category = _clean_text(category, 40) or "other"

        changes.append("category = :category")
        params["category"] = category

    if description is not None:
        description = _clean_text(description, 2000)

        changes.append("description = :description")
        params["description"] = description

    if not changes:
        return {
            "success": False,
            "message": "❌ Aucune modification fournie.",
        }

    changes.append("updated_at = NOW()")

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                f"""
                UPDATE life_company_market
                SET {", ".join(changes)}
                WHERE id = :offer_id
                  AND company_id = :company_id
                  AND active = TRUE
                RETURNING id
                """
            ),
            params,
        )

        if result.first() is None:
            return {
                "success": False,
                "message": (
                    "❌ Offre introuvable ou "
                    "elle n'appartient pas à cette entreprise."
                ),
            }

        await session.commit()

    return {
        "success": True,
        "message": "✅ Produit mis à jour.",
    }


# ============================================================
# MARKET — DÉSACTIVATION
# ============================================================

async def deactivate_market_product(
    offer_id: int,
    company_id: int,
) -> dict[str, Any]:
    """
    Retire une offre du marché sans supprimer son historique.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                UPDATE life_company_market
                SET active = FALSE,
                    updated_at = NOW()
                WHERE id = :offer_id
                  AND company_id = :company_id
                  AND active = TRUE
                RETURNING product_name
                """
            ),
            {
                "offer_id": int(offer_id),
                "company_id": int(company_id),
            },
        )

        row = result.mappings().first()

        if row is None:
            return {
                "success": False,
                "message": "❌ Offre introuvable.",
            }

        await session.commit()

    return {
        "success": True,
        "message": (
            "✅ Produit retiré du marché.\n"
            f"📦 {row['product_name']}"
        ),
    }


# ============================================================
# MARKET — STOCK
# ============================================================

async def add_market_stock(
    offer_id: int,
    company_id: int,
    quantity: int,
) -> dict[str, Any]:
    """
    Ajoute du stock à une offre existante.
    """

    try:
        quantity = _positive_int(quantity)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Quantité invalide.",
        }

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                UPDATE life_company_market
                SET stock = stock + :quantity,
                    updated_at = NOW()
                WHERE id = :offer_id
                  AND company_id = :company_id
                  AND active = TRUE
                RETURNING stock
                """
            ),
            {
                "offer_id": int(offer_id),
                "company_id": int(company_id),
                "quantity": quantity,
            },
        )

        row = result.mappings().first()

        if row is None:
            return {
                "success": False,
                "message": "❌ Offre introuvable.",
            }

        await session.commit()

    return {
        "success": True,
        "stock": int(row["stock"]),
        "message": (
            "✅ Stock augmenté.\n"
            f"📦 Nouveau stock : {int(row['stock'])}"
        ),
    }


# ============================================================
# ACHAT — PRÉVISUALISATION
# ============================================================

async def preview_market_purchase(
    offer_id: int,
    quantity: int = 1,
) -> dict[str, Any]:
    """
    Vérifie une future commande sans modifier la base.
    """

    try:
        quantity = _positive_int(quantity)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Quantité invalide.",
        }

    offer = await get_market_product(offer_id)

    if offer is None:
        return {
            "success": False,
            "message": "❌ Produit introuvable.",
        }

    stock = int(offer["stock"])
    price = int(offer["price"])

    if stock < quantity:
        return {
            "success": False,
            "message": (
                "❌ Stock insuffisant.\n"
                f"📦 Disponible : {stock}\n"
                f"🛒 Demandé : {quantity}"
            ),
        }

    total = price * quantity

    return {
        "success": True,
        "offer_id": int(offer["id"]),
        "company_id": int(offer["company_id"]),
        "product_name": offer["product_name"],
        "price": price,
        "quantity": quantity,
        "stock": stock,
        "total": total,
        "company_name": offer["company_name"],
    }


# ============================================================
# ACHAT — EXÉCUTION
# ============================================================

async def buy_market_product(
    buyer_character_id: int,
    offer_id: int,
    quantity: int = 1,
) -> dict[str, Any]:
    """
    Effectue réellement un achat.

    Opérations atomiques :

    1. verrouillage du produit ;
    2. vérification du stock ;
    3. verrouillage du joueur ;
    4. vérification du solde ;
    5. retrait du montant ;
    6. diminution du stock ;
    7. ajout à la trésorerie de l'entreprise ;
    8. augmentation du chiffre d'affaires ;
    9. enregistrement de la vente ;
    10. ajout dans l'inventaire.

    Si une étape échoue, toute la transaction est annulée.
    """

    try:
        buyer_character_id = int(buyer_character_id)
        offer_id = int(offer_id)
        quantity = _positive_int(quantity)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Paramètres d'achat invalides.",
        }

    if buyer_character_id <= 0 or offer_id <= 0:
        return {
            "success": False,
            "message": "❌ Identifiant invalide.",
        }

    async with AsyncSessionLocal() as session:

        # --------------------------------------------------------
        # VERROUILLAGE DU PRODUIT
        # --------------------------------------------------------

        offer_result = await session.execute(
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
                    c.name AS company_name
                FROM life_company_market m
                INNER JOIN life_companies c
                    ON c.id = m.company_id
                WHERE m.id = :offer_id
                  AND m.active = TRUE
                  AND c.active = TRUE
                FOR UPDATE OF m
                """
            ),
            {
                "offer_id": offer_id,
            },
        )

        offer = offer_result.mappings().first()

        if offer is None:
            return {
                "success": False,
                "message": "❌ Produit introuvable ou indisponible.",
            }

        company_id = int(offer["company_id"])
        price = int(offer["price"])
        stock = int(offer["stock"])

        # --------------------------------------------------------
        # EMPÊCHE L'ENTREPRISE D'ACHETER SON PROPRE PRODUIT
        # --------------------------------------------------------

        owner_result = await session.execute(
            text(
                """
                SELECT owner_character_id
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": company_id,
            },
        )

        owner_id = owner_result.scalar_one_or_none()

        if owner_id is not None:
            if int(owner_id) == buyer_character_id:
                return {
                    "success": False,
                    "message": (
                        "❌ Tu ne peux pas acheter "
                        "ton propre produit."
                    ),
                }

        # --------------------------------------------------------
        # STOCK
        # --------------------------------------------------------

        if stock < quantity:
            return {
                "success": False,
                "message": (
                    "❌ Stock insuffisant.\n"
                    f"📦 Disponible : {stock}\n"
                    f"🛒 Demandé : {quantity}"
                ),
            }

        total_price = price * quantity

        # --------------------------------------------------------
        # VERROUILLAGE DU PERSONNAGE
        # --------------------------------------------------------

        buyer_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    telegram_id,
                    first_name,
                    last_name,
                    username,
                    balance
                FROM life_characters
                WHERE id = :character_id
                FOR UPDATE
                """
            ),
            {
                "character_id": buyer_character_id,
            },
        )

        buyer = buyer_result.mappings().first()

        if buyer is None:
            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        balance = int(buyer["balance"] or 0)

        # --------------------------------------------------------
        # SOLDE
        # --------------------------------------------------------

        if balance < total_price:
            return {
                "success": False,
                "message": (
                    "❌ Solde insuffisant.\n"
                    f"💰 Solde : {balance:,} FCFA\n"
                    f"🛒 Total : {total_price:,} FCFA"
                ),
            }

        new_balance = balance - total_price
        new_stock = stock - quantity

        # --------------------------------------------------------
        # RETRAIT DE L'ARGENT DU JOUEUR
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET balance = :balance,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "balance": new_balance,
                "character_id": buyer_character_id,
            },
        )

        # --------------------------------------------------------
        # DIMINUTION DU STOCK
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                UPDATE life_company_market
                SET stock = :stock,
                    updated_at = NOW()
                WHERE id = :offer_id
                """
            ),
            {
                "stock": new_stock,
                "offer_id": offer_id,
            },
        )

        # --------------------------------------------------------
        # TRÉSORERIE DE L'ENTREPRISE
        # --------------------------------------------------------

        treasury_result = await session.execute(
            text(
                """
                UPDATE life_companies
                SET treasury = treasury + :amount,
                    total_revenue = total_revenue + :amount,
                    updated_at = NOW()
                WHERE id = :company_id
                  AND active = TRUE
                RETURNING treasury, total_revenue
                """
            ),
            {
                "amount": total_price,
                "company_id": company_id,
            },
        )

        treasury = treasury_result.mappings().first()

        if treasury is None:
            raise RuntimeError(
                "Company became unavailable during purchase."
            )

        # --------------------------------------------------------
        # TRANSACTION ENTREPRISE
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                INSERT INTO life_company_transactions (
                    company_id,
                    character_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :company_id,
                    :character_id,
                    'market_sale',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "company_id": company_id,
                "character_id": buyer_character_id,
                "amount": total_price,
                "balance_after": int(treasury["treasury"]),
                "description": (
                    f"Vente de {quantity} x "
                    f"{offer['product_name']}"
                ),
            },
        )

        # --------------------------------------------------------
        # HISTORIQUE DE VENTE
        # --------------------------------------------------------

        sale_result = await session.execute(
            text(
                """
                INSERT INTO life_company_market_sales (
                    offer_id,
                    company_id,
                    buyer_character_id,
                    quantity,
                    unit_price,
                    total_price
                )
                VALUES (
                    :offer_id,
                    :company_id,
                    :buyer_character_id,
                    :quantity,
                    :unit_price,
                    :total_price
                )
                RETURNING id
                """
            ),
            {
                "offer_id": offer_id,
                "company_id": company_id,
                "buyer_character_id": buyer_character_id,
                "quantity": quantity,
                "unit_price": price,
                "total_price": total_price,
            },
        )

        sale_id = int(sale_result.scalar_one())

        # --------------------------------------------------------
        # INVENTAIRE DU JOUEUR
        # --------------------------------------------------------
        #
        # Le marché utilise le nom du produit comme item_name.
        # Si l'item existe déjà, sa quantité est augmentée.
        #

        await session.execute(
            text(
                """
                INSERT INTO life_inventory (
                    character_id,
                    item_name,
                    quantity,
                    item_data
                )
                VALUES (
                    :character_id,
                    :item_name,
                    :quantity,
                    CAST(:item_data AS JSONB)
                )
                ON CONFLICT (character_id, item_name)
                DO UPDATE SET
                    quantity =
                        life_inventory.quantity
                        + EXCLUDED.quantity,
                    item_data =
                        EXCLUDED.item_data
                """
            ),
            {
                "character_id": buyer_character_id,
                "item_name": offer["product_name"],
                "quantity": quantity,
                "item_data": (
                    "{"
                    f"\"source\":\"company_market\","
                    f"\"offer_id\":{offer_id},"
                    f"\"company_id\":{company_id},"
                    f"\"category\":"
                    f"\"{str(offer['category']).replace(chr(34), '')}\""
                    "}"
                ),
            },
        )

        # --------------------------------------------------------
        # TRANSACTION DU JOUEUR
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                INSERT INTO life_transactions (
                    character_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description,
                    reference
                )
                VALUES (
                    :character_id,
                    'market_purchase',
                    :amount,
                    :balance_after,
                    :description,
                    :reference
                )
                """
            ),
            {
                "character_id": buyer_character_id,
                "amount": -total_price,
                "balance_after": new_balance,
                "description": (
                    f"Achat de {quantity} x "
                    f"{offer['product_name']}"
                ),
                "reference": f"market_sale:{sale_id}",
            },
        )

        await session.commit()

        return {
            "success": True,
            "sale_id": sale_id,
            "offer_id": offer_id,
            "company_id": company_id,
            "company_name": offer["company_name"],
            "product_name": offer["product_name"],
            "quantity": quantity,
            "unit_price": price,
            "total_price": total_price,
            "remaining_stock": new_stock,
            "buyer_balance": new_balance,
            "company_treasury": int(
                treasury["treasury"]
            ),
            "company_total_revenue": int(
                treasury["total_revenue"]
            ),
            "message": (
                "✅ ACHAT RÉUSSI\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🏢 Entreprise : "
                f"{offer['company_name']}\n"
                f"📦 Produit : "
                f"{offer['product_name']}\n"
                f"🔢 Quantité : {quantity}\n"
                f"💰 Prix unitaire : "
                f"{price:,} FCFA\n"
                f"💵 Total : "
                f"{total_price:,} FCFA\n"
                f"📦 Stock restant : "
                f"{new_stock}\n"
                f"💳 Nouveau solde : "
                f"{new_balance:,} FCFA"
            ),
        }


# ============================================================
# HISTORIQUE DES VENTES
# ============================================================

async def get_company_sales(
    company_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retourne l'historique récent des ventes d'une entreprise.
    """

    limit = max(1, min(200, int(limit)))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                f"""
                SELECT
                    s.id,
                    s.offer_id,
                    s.company_id,
                    s.buyer_character_id,
                    s.quantity,
                    s.unit_price,
                    s.total_price,
                    s.created_at,
                    m.product_name,
                    c.first_name AS buyer_first_name,
                    c.last_name AS buyer_last_name,
                    c.username AS buyer_username
                FROM life_company_market_sales s
                LEFT JOIN life_company_market m
                    ON m.id = s.offer_id
                LEFT JOIN life_characters c
                    ON c.id = s.buyer_character_id
                WHERE s.company_id = :company_id
                ORDER BY s.created_at DESC
                LIMIT {limit}
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# STATISTIQUES DU MARCHÉ
# ============================================================

async def get_company_market_stats(
    company_id: int,
) -> dict[str, Any]:
    """
    Retourne les statistiques commerciales d'une entreprise.
    """

    async with AsyncSessionLocal() as session:

        offers_result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS offers,
                    COALESCE(SUM(stock), 0) AS stock
                FROM life_company_market
                WHERE company_id = :company_id
                  AND active = TRUE
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        sales_result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS sales_count,
                    COALESCE(SUM(quantity), 0) AS units_sold,
                    COALESCE(SUM(total_price), 0) AS revenue
                FROM life_company_market_sales
                WHERE company_id = :company_id
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company_result = await session.execute(
            text(
                """
                SELECT
                    treasury,
                    total_revenue
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        offers = offers_result.mappings().first()
        sales = sales_result.mappings().first()
        company = company_result.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        return {
            "success": True,
            "active_offers": int(
                offers["offers"] or 0
            ),
            "available_stock": int(
                offers["stock"] or 0
            ),
            "sales_count": int(
                sales["sales_count"] or 0
            ),
            "units_sold": int(
                sales["units_sold"] or 0
            ),
            "market_revenue": int(
                sales["revenue"] or 0
            ),
            "treasury": int(
                company["treasury"] or 0
            ),
            "total_revenue": int(
                company["total_revenue"] or 0
            ),
        }


# ============================================================
# VÉRIFICATION DU PROPRIÉTAIRE
# ============================================================

async def is_company_owner(
    character_id: int,
    company_id: int,
) -> bool:
    """
    Vérifie si un personnage est le propriétaire de l'entreprise.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT 1
                FROM life_companies
                WHERE id = :company_id
                  AND owner_character_id = :character_id
                  AND active = TRUE
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
                "character_id": int(character_id),
            },
        )

        return result.first() is not None


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_company",
    "get_company_owner",
    "get_market_product",
    "get_company_market",
    "search_market",
    "create_market_product",
    "update_market_product",
    "deactivate_market_product",
    "add_market_stock",
    "preview_market_purchase",
    "buy_market_product",
    "get_company_sales",
    "get_company_market_stats",
    "is_company_owner",
]