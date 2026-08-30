"""
MANUWORLD — EXPENSES SYSTEM

Gestion des dépenses personnelles du personnage.

Gère :
    - ajout d'une dépense
    - récupération d'une dépense
    - historique
    - dépenses par catégorie
    - total des dépenses
    - statistiques
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONSTANTES
# ============================================================

DEFAULT_CATEGORY = "other"


# ============================================================
# UTILITAIRES
# ============================================================

def clean_text(
    value: Any,
    default: str = "",
    max_length: int | None = None,
) -> str:

    result = str(
        value if value is not None else default
    ).strip()

    if max_length is not None:
        result = result[:max_length]

    return result


def format_money(
    amount: int | float | None,
) -> str:

    return f"{int(amount or 0):,}".replace(",", " ")


# ============================================================
# AJOUT D'UNE DÉPENSE
# ============================================================

async def add_expense(
    character_id: int,
    category: str,
    description: str,
    amount: int,
) -> dict[str, Any]:

    character_id = int(character_id)

    category = clean_text(
        category,
        DEFAULT_CATEGORY,
        50,
    )

    description = clean_text(
        description,
        max_length=160,
    )

    amount = int(amount)

    if not description:

        return {
            "success": False,
            "message": "❌ La description est obligatoire.",
        }

    if amount <= 0:

        return {
            "success": False,
            "message": "❌ Le montant doit être supérieur à 0.",
        }

    async with AsyncSessionLocal() as session:

        character_result = await session.execute(
            text(
                """
                SELECT id, balance
                FROM life_characters
                WHERE id = :character_id
                FOR UPDATE
                """
            ),
            {
                "character_id": character_id,
            },
        )

        character = (
            character_result
            .mappings()
            .first()
        )

        if character is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        balance = int(
            character["balance"] or 0
        )

        if balance < amount:

            return {
                "success": False,
                "message": (
                    "❌ Solde insuffisant.\n"
                    f"💰 Solde : "
                    f"{format_money(balance)} FCFA\n"
                    f"💸 Dépense : "
                    f"{format_money(amount)} FCFA"
                ),
            }

        new_balance = balance - amount

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
                "character_id": character_id,
            },
        )

        result = await session.execute(
            text(
                """
                INSERT INTO life_expenses (
                    character_id,
                    category,
                    description,
                    amount
                )
                VALUES (
                    :character_id,
                    :category,
                    :description,
                    :amount
                )
                RETURNING *
                """
            ),
            {
                "character_id": character_id,
                "category": category,
                "description": description,
                "amount": amount,
            },
        )

        expense = dict(
            result.mappings().one()
        )

        await session.commit()

    return {
        "success": True,
        "expense": expense,
        "expense_id": int(
            expense["id"]
        ),
        "balance": new_balance,
        "message": (
            "💸 DÉPENSE ENREGISTRÉE\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 Catégorie : {category}\n"
            f"📝 {description}\n"
            f"💰 Montant : "
            f"{format_money(amount)} FCFA\n"
            f"💳 Solde restant : "
            f"{format_money(new_balance)} FCFA"
        ),
    }


# ============================================================
# RÉCUPÉRER UNE DÉPENSE
# ============================================================

async def get_expense(
    expense_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_expenses
                WHERE id = :expense_id
                LIMIT 1
                """
            ),
            {
                "expense_id": int(
                    expense_id
                ),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# HISTORIQUE
# ============================================================

async def get_expenses(
    character_id: int,
    limit: int = 20,
    category: str | None = None,
) -> list[dict[str, Any]]:

    limit = max(
        1,
        min(
            100,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        if category:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_expenses
                    WHERE character_id = :character_id
                      AND LOWER(category) = LOWER(:category)
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                    "category": clean_text(
                        category
                    ),
                    "limit": limit,
                },
            )

        else:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_expenses
                    WHERE character_id = :character_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                    "limit": limit,
                },
            )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# TOTAL
# ============================================================

async def get_total_expenses(
    character_id: int,
    category: str | None = None,
) -> int:

    async with AsyncSessionLocal() as session:

        if category:

            result = await session.execute(
                text(
                    """
                    SELECT COALESCE(
                        SUM(amount),
                        0
                    )
                    FROM life_expenses
                    WHERE character_id = :character_id
                      AND LOWER(category) = LOWER(:category)
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                    "category": clean_text(
                        category
                    ),
                },
            )

        else:

            result = await session.execute(
                text(
                    """
                    SELECT COALESCE(
                        SUM(amount),
                        0
                    )
                    FROM life_expenses
                    WHERE character_id = :character_id
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                },
            )

        return int(
            result.scalar() or 0
        )


# ============================================================
# STATISTIQUES
# ============================================================

async def get_expense_statistics(
    character_id: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        total_result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS count,
                    COALESCE(
                        SUM(amount),
                        0
                    ) AS total,
                    COALESCE(
                        AVG(amount),
                        0
                    ) AS average
                FROM life_expenses
                WHERE character_id = :character_id
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        totals = dict(
            total_result.mappings().one()
        )

        category_result = await session.execute(
            text(
                """
                SELECT
                    category,
                    COUNT(*) AS count,
                    COALESCE(
                        SUM(amount),
                        0
                    ) AS total
                FROM life_expenses
                WHERE character_id = :character_id
                GROUP BY category
                ORDER BY total DESC
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        by_category = [
            dict(row)
            for row in category_result
            .mappings()
            .all()
        ]

    return {
        "count": int(
            totals["count"] or 0
        ),
        "total": int(
            totals["total"] or 0
        ),
        "average": int(
            float(
                totals["average"] or 0
            )
        ),
        "by_category": by_category,
    }


# ============================================================
# SUPPRESSION
# ============================================================

async def delete_expense(
    character_id: int,
    expense_id: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                DELETE FROM life_expenses
                WHERE id = :expense_id
                  AND character_id = :character_id
                RETURNING *
                """
            ),
            {
                "expense_id": int(
                    expense_id
                ),
                "character_id": int(
                    character_id
                ),
            },
        )

        row = result.mappings().first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Dépense introuvable.",
            }

        await session.commit()

    return {
        "success": True,
        "expense": dict(row),
        "message": "✅ Dépense supprimée.",
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_expense(
    expense: dict[str, Any],
) -> str:

    amount = int(
        expense.get("amount") or 0
    )

    return (
        "💸 **DÉPENSE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📂 Catégorie : "
        f"{expense.get('category', DEFAULT_CATEGORY)}\n"
        f"📝 {expense.get('description', '')}\n"
        f"💰 Montant : "
        f"{format_money(amount)} FCFA"
    )


def format_expenses(
    expenses: list[dict[str, Any]],
) -> str:

    if not expenses:

        return (
            "💸 **DÉPENSES**\n\n"
            "Aucune dépense enregistrée."
        )

    total = sum(
        int(
            expense.get("amount") or 0
        )
        for expense in expenses
    )

    lines = [
        "💸 **HISTORIQUE DES DÉPENSES**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for expense in expenses:

        amount = int(
            expense.get("amount") or 0
        )

        lines.extend(
            [
                (
                    f"💸 {expense.get('description', '')}"
                ),
                (
                    f"   📂 "
                    f"{expense.get('category', DEFAULT_CATEGORY)}"
                ),
                (
                    f"   💰 "
                    f"{format_money(amount)} FCFA"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━━━",
            f"💵 Total affiché : "
            f"{format_money(total)} FCFA",
        ]
    )

    return "\n".join(lines)


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "DEFAULT_CATEGORY",
    "clean_text",
    "format_money",
    "add_expense",
    "get_expense",
    "get_expenses",
    "get_total_expenses",
    "get_expense_statistics",
    "delete_expense",
    "format_expense",
    "format_expenses",
]