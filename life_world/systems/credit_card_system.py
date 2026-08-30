"""
MANUWORLD — CREDIT CARD SYSTEM

Gestion des cartes de crédit.

Tables utilisées :

    life_credit_cards
    life_credit_card_transactions
    life_credit_card_payments

Aucun handler Telegram dans ce fichier.
"""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONSTANTES
# ============================================================

CARD_NUMBER_LENGTH = 16


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ")


def positive_amount(amount: Any) -> int:
    amount = int(amount)

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    return amount


def generate_card_number() -> str:
    """
    Génère un numéro de carte numérique de 16 chiffres.
    """

    return "".join(
        str(secrets.randbelow(10))
        for _ in range(CARD_NUMBER_LENGTH)
    )


# ============================================================
# CARTES
# ============================================================

async def get_credit_card(
    card_id: int,
) -> dict[str, Any] | None:
    """
    Retourne une carte de crédit.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    c.id,
                    c.bank_id,
                    c.character_id,
                    c.card_name,
                    c.card_number,
                    c.card_type,
                    c.credit_limit,
                    c.used_credit,
                    c.available_credit,
                    c.interest_rate,
                    c.annual_fee,
                    c.reward_rate,
                    c.credit_score,
                    c.status,
                    c.issued_at,
                    c.payment_due_at,
                    c.last_payment_at,
                    b.name AS bank_name
                FROM life_credit_cards c
                INNER JOIN life_banks b
                    ON b.id = c.bank_id
                WHERE c.id = :card_id
                LIMIT 1
                """
            ),
            {
                "card_id": int(card_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


async def get_character_credit_cards(
    character_id: int,
) -> list[dict[str, Any]]:
    """
    Retourne les cartes d'un personnage.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    c.id,
                    c.bank_id,
                    c.character_id,
                    c.card_name,
                    c.card_number,
                    c.card_type,
                    c.credit_limit,
                    c.used_credit,
                    c.available_credit,
                    c.interest_rate,
                    c.annual_fee,
                    c.reward_rate,
                    c.credit_score,
                    c.status,
                    c.issued_at,
                    c.payment_due_at,
                    c.last_payment_at,
                    b.name AS bank_name
                FROM life_credit_cards c
                INNER JOIN life_banks b
                    ON b.id = c.bank_id
                WHERE c.character_id = :character_id
                ORDER BY c.issued_at ASC
                """
            ),
            {
                "character_id": int(character_id),
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


async def get_credit_card_by_number(
    card_number: str,
) -> dict[str, Any] | None:
    """
    Recherche une carte par son numéro.
    """

    card_number = str(
        card_number or ""
    ).strip().replace(" ", "")

    if not card_number:
        return None

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    c.id,
                    c.bank_id,
                    c.character_id,
                    c.card_name,
                    c.card_number,
                    c.card_type,
                    c.credit_limit,
                    c.used_credit,
                    c.available_credit,
                    c.interest_rate,
                    c.annual_fee,
                    c.reward_rate,
                    c.credit_score,
                    c.status,
                    c.issued_at,
                    c.payment_due_at,
                    c.last_payment_at,
                    b.name AS bank_name
                FROM life_credit_cards c
                INNER JOIN life_banks b
                    ON b.id = c.bank_id
                WHERE c.card_number = :card_number
                LIMIT 1
                """
            ),
            {
                "card_number": card_number,
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# CRÉATION
# ============================================================

async def create_credit_card(
    character_id: int,
    bank_id: int,
    card_name: str,
    credit_limit: int,
    card_type: str = "standard",
    interest_rate: float = 0,
    annual_fee: int = 0,
    reward_rate: float = 0,
    credit_score: int = 500,
) -> dict[str, Any]:
    """
    Crée une carte de crédit pour un personnage.

    La carte commence avec :

        used_credit = 0
        available_credit = credit_limit
    """

    card_name = str(
        card_name or "MANUWORLD Card"
    ).strip()[:100]

    card_type = str(
        card_type or "standard"
    ).strip()[:40]

    try:
        credit_limit = positive_amount(
            credit_limit
        )
        annual_fee = max(
            0,
            int(annual_fee),
        )
        interest_rate = float(
            interest_rate
        )
        reward_rate = float(
            reward_rate
        )
        credit_score = max(
            0,
            min(1000, int(credit_score)),
        )
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Paramètres de carte invalides.",
        }

    if interest_rate < 0:
        return {
            "success": False,
            "message": "❌ Taux d'intérêt invalide.",
        }

    if reward_rate < 0:
        return {
            "success": False,
            "message": "❌ Taux de récompense invalide.",
        }

    async with AsyncSessionLocal() as session:

        # --------------------------------------------------------
        # PERSONNAGE
        # --------------------------------------------------------

        character_result = await session.execute(
            text(
                """
                SELECT id
                FROM life_characters
                WHERE id = :character_id
                LIMIT 1
                """
            ),
            {
                "character_id": int(character_id),
            },
        )

        if character_result.first() is None:
            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        # --------------------------------------------------------
        # BANQUE
        # --------------------------------------------------------

        bank_result = await session.execute(
            text(
                """
                SELECT id, name
                FROM life_banks
                WHERE id = :bank_id
                  AND active = TRUE
                LIMIT 1
                """
            ),
            {
                "bank_id": int(bank_id),
            },
        )

        bank = bank_result.mappings().first()

        if bank is None:
            return {
                "success": False,
                "message": "❌ Banque introuvable.",
            }

        # --------------------------------------------------------
        # NUMÉRO UNIQUE
        # --------------------------------------------------------

        card_number = None

        for _ in range(30):

            candidate = generate_card_number()

            existing = await session.execute(
                text(
                    """
                    SELECT 1
                    FROM life_credit_cards
                    WHERE card_number = :card_number
                    LIMIT 1
                    """
                ),
                {
                    "card_number": candidate,
                },
            )

            if existing.first() is None:
                card_number = candidate
                break

        if card_number is None:
            return {
                "success": False,
                "message": (
                    "❌ Impossible de générer "
                    "un numéro de carte."
                ),
            }

        # --------------------------------------------------------
        # CRÉATION
        # --------------------------------------------------------

        result = await session.execute(
            text(
                """
                INSERT INTO life_credit_cards (
                    bank_id,
                    character_id,
                    card_name,
                    card_number,
                    card_type,
                    credit_limit,
                    used_credit,
                    available_credit,
                    interest_rate,
                    annual_fee,
                    reward_rate,
                    credit_score,
                    status
                )
                VALUES (
                    :bank_id,
                    :character_id,
                    :card_name,
                    :card_number,
                    :card_type,
                    :credit_limit,
                    0,
                    :credit_limit,
                    :interest_rate,
                    :annual_fee,
                    :reward_rate,
                    :credit_score,
                    'active'
                )
                RETURNING id
                """
            ),
            {
                "bank_id": int(bank_id),
                "character_id": int(character_id),
                "card_name": card_name,
                "card_number": card_number,
                "card_type": card_type,
                "credit_limit": credit_limit,
                "interest_rate": interest_rate,
                "annual_fee": annual_fee,
                "reward_rate": reward_rate,
                "credit_score": credit_score,
            },
        )

        card_id = int(
            result.scalar_one()
        )

        await session.commit()

    return {
        "success": True,
        "card_id": card_id,
        "bank_id": int(bank_id),
        "bank_name": bank["name"],
        "card_name": card_name,
        "card_number": card_number,
        "credit_limit": credit_limit,
        "available_credit": credit_limit,
        "message": (
            "💳 CARTE CRÉÉE\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Banque : {bank['name']}\n"
            f"💳 Carte : {card_name}\n"
            f"🔢 Numéro : {card_number}\n"
            f"💰 Limite : "
            f"{format_money(credit_limit)} FCFA\n"
            f"📊 Disponible : "
            f"{format_money(credit_limit)} FCFA"
        ),
    }


# ============================================================
# UTILISATION
# ============================================================

async def use_credit_card(
    character_id: int,
    card_id: int,
    amount: int,
    merchant: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Utilise une carte de crédit.

    L'argent n'est pas retiré du portefeuille :
    il augmente simplement le crédit utilisé.

    Les achats restent enregistrés dans
    life_credit_card_transactions.
    """

    try:
        amount = positive_amount(amount)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Montant invalide.",
        }

    merchant = (
        str(merchant or "MANUWORLD")
        .strip()[:120]
    )

    description = (
        str(description or "Achat par carte")
        .strip()[:500]
    )

    async with AsyncSessionLocal() as session:

        card_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    bank_id,
                    character_id,
                    card_name,
                    credit_limit,
                    used_credit,
                    available_credit,
                    reward_rate,
                    status
                FROM life_credit_cards
                WHERE id = :card_id
                FOR UPDATE
                """
            ),
            {
                "card_id": int(card_id),
            },
        )

        card = card_result.mappings().first()

        if card is None:
            return {
                "success": False,
                "message": "❌ Carte introuvable.",
            }

        if int(card["character_id"]) != character_id:
            return {
                "success": False,
                "message": "❌ Cette carte ne t'appartient pas.",
            }

        if card["status"] != "active":
            return {
                "success": False,
                "message": "❌ Cette carte est inactive.",
            }

        available = int(
            card["available_credit"] or 0
        )

        if amount > available:
            return {
                "success": False,
                "message": (
                    "❌ Crédit insuffisant.\n"
                    f"💳 Disponible : "
                    f"{format_money(available)} FCFA\n"
                    f"🛒 Achat : "
                    f"{format_money(amount)} FCFA"
                ),
            }

        old_used = int(
            card["used_credit"] or 0
        )

        new_used = old_used + amount

        new_available = int(
            card["credit_limit"]
        ) - new_used

        reward_rate = float(
            card["reward_rate"] or 0
        )

        reward_earned = int(
            amount * reward_rate / 100
        )

        await session.execute(
            text(
                """
                UPDATE life_credit_cards
                SET used_credit = :used_credit,
                    available_credit = :available_credit
                WHERE id = :card_id
                """
            ),
            {
                "used_credit": new_used,
                "available_credit": new_available,
                "card_id": int(card_id),
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO life_credit_card_transactions (
                    card_id,
                    transaction_type,
                    amount,
                    balance_after,
                    merchant,
                    description,
                    reward_earned
                )
                VALUES (
                    :card_id,
                    'purchase',
                    :amount,
                    :balance_after,
                    :merchant,
                    :description,
                    :reward_earned
                )
                """
            ),
            {
                "card_id": int(card_id),
                "amount": amount,
                "balance_after": new_used,
                "merchant": merchant,
                "description": description,
                "reward_earned": reward_earned,
            },
        )

        await session.commit()

        return {
            "success": True,
            "amount": amount,
            "used_credit": new_used,
            "available_credit": new_available,
            "reward_earned": reward_earned,
            "message": (
                "💳 PAIEMENT ACCEPTÉ\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🏪 Marchand : {merchant}\n"
                f"💵 Montant : "
                f"{format_money(amount)} FCFA\n"
                f"💳 Crédit utilisé : "
                f"{format_money(new_used)} FCFA\n"
                f"📊 Crédit disponible : "
                f"{format_money(new_available)} FCFA"
            ),
        }


# ============================================================
# REMBOURSEMENT
# ============================================================

async def pay_credit_card(
    character_id: int,
    card_id: int,
    amount: int,
) -> dict[str, Any]:
    """
    Rembourse une dette de carte de crédit.

    L'argent est prélevé du portefeuille
    du personnage.
    """

    try:
        amount = positive_amount(amount)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Montant invalide.",
        }

    character_id = int(character_id)
    card_id = int(card_id)

    async with AsyncSessionLocal() as session:

        # --------------------------------------------------------
        # PERSONNAGE
        # --------------------------------------------------------

        character_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    balance
                FROM life_characters
                WHERE id = :character_id
                FOR UPDATE
                """
            ),
            {
                "character_id": character_id,
            },
        )

        character = character_result.mappings().first()

        if character is None:
            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        wallet = int(
            character["balance"] or 0
        )

        # --------------------------------------------------------
        # CARTE
        # --------------------------------------------------------

        card_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    character_id,
                    card_name,
                    credit_limit,
                    used_credit,
                    available_credit,
                    status
                FROM life_credit_cards
                WHERE id = :card_id
                FOR UPDATE
                """
            ),
            {
                "card_id": card_id,
            },
        )

        card = card_result.mappings().first()

        if card is None:
            return {
                "success": False,
                "message": "❌ Carte introuvable.",
            }

        if int(card["character_id"]) != character_id:
            return {
                "success": False,
                "message": "❌ Cette carte ne t'appartient pas.",
            }

        if card["status"] != "active":
            return {
                "success": False,
                "message": "❌ Cette carte est inactive.",
            }

        used = int(
            card["used_credit"] or 0
        )

        if used <= 0:
            return {
                "success": False,
                "message": "ℹ️ Aucun crédit à rembourser.",
            }

        if amount > used:
            amount = used

        if wallet < amount:
            return {
                "success": False,
                "message": (
                    "❌ Solde insuffisant.\n"
                    f"💰 Solde : "
                    f"{format_money(wallet)} FCFA\n"
                    f"💳 Remboursement : "
                    f"{format_money(amount)} FCFA"
                ),
            }

        new_used = used - amount

        credit_limit = int(
            card["credit_limit"]
        )

        new_available = (
            credit_limit - new_used
        )

        new_wallet = wallet - amount

        # --------------------------------------------------------
        # PORTEFEUILLE
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
                "balance": new_wallet,
                "character_id": character_id,
            },
        )

        # --------------------------------------------------------
        # CARTE
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                UPDATE life_credit_cards
                SET used_credit = :used_credit,
                    available_credit = :available_credit,
                    last_payment_at = NOW()
                WHERE id = :card_id
                """
            ),
            {
                "used_credit": new_used,
                "available_credit": new_available,
                "card_id": card_id,
            },
        )

        # --------------------------------------------------------
        # PAIEMENT
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                INSERT INTO life_credit_card_payments (
                    card_id,
                    amount,
                    previous_balance,
                    remaining_balance
                )
                VALUES (
                    :card_id,
                    :amount,
                    :previous_balance,
                    :remaining_balance
                )
                """
            ),
            {
                "card_id": card_id,
                "amount": amount,
                "previous_balance": used,
                "remaining_balance": new_used,
            },
        )

        # --------------------------------------------------------
        # TRANSACTION
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                INSERT INTO life_credit_card_transactions (
                    card_id,
                    transaction_type,
                    amount,
                    balance_after,
                    merchant,
                    description,
                    reward_earned
                )
                VALUES (
                    :card_id,
                    'payment',
                    :amount,
                    :balance_after,
                    NULL,
                    'Remboursement de carte',
                    0
                )
                """
            ),
            {
                "card_id": card_id,
                "amount": -amount,
                "balance_after": new_used,
            },
        )

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
                    'credit_card_payment',
                    :amount,
                    :balance_after,
                    'Remboursement carte de crédit',
                    :reference
                )
                """
            ),
            {
                "character_id": character_id,
                "amount": -amount,
                "balance_after": new_wallet,
                "reference": f"credit_card:{card_id}",
            },
        )

        await session.commit()

        return {
            "success": True,
            "amount": amount,
            "used_credit": new_used,
            "available_credit": new_available,
            "wallet_balance": new_wallet,
            "message": (
                "💳 REMBOURSEMENT EFFECTUÉ\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 Payé : "
                f"{format_money(amount)} FCFA\n"
                f"💳 Crédit restant : "
                f"{format_money(new_used)} FCFA\n"
                f"📊 Disponible : "
                f"{format_money(new_available)} FCFA\n"
                f"💰 Portefeuille : "
                f"{format_money(new_wallet)} FCFA"
            ),
        }


# ============================================================
# HISTORIQUE
# ============================================================

async def get_credit_card_transactions(
    card_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retourne l'historique d'une carte.
    """

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50

    limit = max(1, min(200, limit))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                f"""
                SELECT
                    id,
                    card_id,
                    transaction_type,
                    amount,
                    balance_after,
                    merchant,
                    description,
                    reward_earned,
                    created_at
                FROM life_credit_card_transactions
                WHERE card_id = :card_id
                ORDER BY created_at DESC
                LIMIT {limit}
                """
            ),
            {
                "card_id": int(card_id),
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# STATISTIQUES
# ============================================================

async def get_credit_card_stats(
    card_id: int,
) -> dict[str, Any]:
    """
    Retourne les statistiques d'une carte.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS transaction_count,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN transaction_type = 'purchase'
                                THEN amount
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_purchases,
                    COALESCE(
                        SUM(reward_earned),
                        0
                    ) AS total_rewards
                FROM life_credit_card_transactions
                WHERE card_id = :card_id
                """
            ),
            {
                "card_id": int(card_id),
            },
        )

        stats = result.mappings().first()

        card = await get_credit_card(
            card_id
        )

        if card is None:
            return {
                "success": False,
                "message": "❌ Carte introuvable.",
            }

        return {
            "success": True,
            "transaction_count": int(
                stats["transaction_count"] or 0
            ),
            "total_purchases": int(
                stats["total_purchases"] or 0
            ),
            "total_rewards": int(
                stats["total_rewards"] or 0
            ),
            "credit_limit": int(
                card["credit_limit"]
            ),
            "used_credit": int(
                card["used_credit"]
            ),
            "available_credit": int(
                card["available_credit"]
            ),
        }


# ============================================================
# STATUT
# ============================================================

async def set_credit_card_status(
    card_id: int,
    character_id: int,
    status: str,
) -> dict[str, Any]:
    """
    Modifie le statut d'une carte appartenant au joueur.

    Statuts autorisés :

        active
        blocked
        cancelled
    """

    status = str(
        status or ""
    ).strip().lower()

    allowed = {
        "active",
        "blocked",
        "cancelled",
    }

    if status not in allowed:
        return {
            "success": False,
            "message": "❌ Statut de carte invalide.",
        }

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                UPDATE life_credit_cards
                SET status = :status
                WHERE id = :card_id
                  AND character_id = :character_id
                RETURNING card_name
                """
            ),
            {
                "card_id": int(card_id),
                "character_id": int(character_id),
                "status": status,
            },
        )

        row = result.mappings().first()

        if row is None:
            return {
                "success": False,
                "message": "❌ Carte introuvable.",
            }

        await session.commit()

    return {
        "success": True,
        "status": status,
        "message": (
            f"✅ Carte « {row['card_name']} » "
            f"mise en statut `{status}`."
        ),
    }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_credit_card",
    "get_character_credit_cards",
    "get_credit_card_by_number",
    "create_credit_card",
    "use_credit_card",
    "pay_credit_card",
    "get_credit_card_transactions",
    "get_credit_card_stats",
    "set_credit_card_status",
]