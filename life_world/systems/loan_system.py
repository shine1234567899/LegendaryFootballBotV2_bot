"""
MANUWORLD — LOAN SYSTEM

Système de prêts bancaires.

Flux :

    joueur
       ↓
    demande de prêt
       ↓
    vérification banque
       ↓
    création du prêt
       ↓
    versement des fonds
       ↓
    remboursements
       ↓
    solde restant

Aucun handler Telegram dans ce fichier.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONSTANTES
# ============================================================

DEFAULT_DURATION_DAYS = 30
MAX_DURATION_DAYS = 365


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


def clamp_duration(days: Any) -> int:
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = DEFAULT_DURATION_DAYS

    return max(
        1,
        min(MAX_DURATION_DAYS, days),
    )


# ============================================================
# PRÊTS DU PERSONNAGE
# ============================================================

async def get_character_loans(
    character_id: int,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Retourne les prêts d'un personnage.
    """

    condition = ""

    if active_only:
        condition = """
            AND l.status IN (
                'active',
                'overdue'
            )
        """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                f"""
                SELECT
                    l.id,
                    l.bank_id,
                    l.character_id,
                    l.loan_type,
                    l.principal,
                    l.interest_rate,
                    l.total_interest,
                    l.total_due,
                    l.amount_paid,
                    l.remaining_balance,
                    l.duration_days,
                    l.issued_at,
                    l.due_at,
                    l.last_payment_at,
                    l.status,
                    b.name AS bank_name
                FROM life_loans l
                INNER JOIN life_banks b
                    ON b.id = l.bank_id
                WHERE l.character_id = :character_id
                {condition}
                ORDER BY l.issued_at DESC
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


# ============================================================
# DÉTAIL D'UN PRÊT
# ============================================================

async def get_loan(
    loan_id: int,
) -> dict[str, Any] | None:
    """
    Retourne un prêt.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    l.id,
                    l.bank_id,
                    l.character_id,
                    l.loan_type,
                    l.principal,
                    l.interest_rate,
                    l.total_interest,
                    l.total_due,
                    l.amount_paid,
                    l.remaining_balance,
                    l.duration_days,
                    l.issued_at,
                    l.due_at,
                    l.last_payment_at,
                    l.status,
                    b.name AS bank_name
                FROM life_loans l
                INNER JOIN life_banks b
                    ON b.id = l.bank_id
                WHERE l.id = :loan_id
                LIMIT 1
                """
            ),
            {
                "loan_id": int(loan_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# CALCUL D'INTÉRÊT
# ============================================================

def calculate_loan_interest(
    principal: int,
    interest_rate: float,
) -> int:
    """
    Calcule les intérêts simples du prêt.
    """

    principal = int(principal)
    interest_rate = float(interest_rate)

    return max(
        0,
        int(
            principal
            * interest_rate
            / 100
        ),
    )


# ============================================================
# DEMANDE DE PRÊT
# ============================================================

async def request_loan(
    character_id: int,
    bank_id: int,
    amount: int,
    duration_days: int = DEFAULT_DURATION_DAYS,
    loan_type: str = "personal",
) -> dict[str, Any]:
    """
    Demande et accorde un prêt.

    Les règles principales sont :

        - banque active ;
        - montant positif ;
        - aucun autre prêt actif ;
        - durée valide ;
        - limites déterminées par la banque.
    """

    try:
        amount = positive_amount(amount)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Montant du prêt invalide.",
        }

    duration_days = clamp_duration(
        duration_days
    )

    loan_type = str(
        loan_type or "personal"
    ).strip()[:40]

    character_id = int(character_id)
    bank_id = int(bank_id)

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

        # --------------------------------------------------------
        # BANQUE
        # --------------------------------------------------------

        bank_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    interest_rate,
                    maximum_balance
                FROM life_banks
                WHERE id = :bank_id
                  AND active = TRUE
                LIMIT 1
                """
            ),
            {
                "bank_id": bank_id,
            },
        )

        bank = bank_result.mappings().first()

        if bank is None:
            return {
                "success": False,
                "message": "❌ Banque introuvable.",
            }

        # --------------------------------------------------------
        # PRÊT ACTIF EXISTANT
        # --------------------------------------------------------

        active_result = await session.execute(
            text(
                """
                SELECT id
                FROM life_loans
                WHERE character_id = :character_id
                  AND status IN (
                      'active',
                      'overdue'
                  )
                LIMIT 1
                """
            ),
            {
                "character_id": character_id,
            },
        )

        if active_result.first() is not None:
            return {
                "success": False,
                "message": (
                    "❌ Tu possèdes déjà un prêt actif.\n"
                    "Rembourse-le avant d'en demander un nouveau."
                ),
            }

        # --------------------------------------------------------
        # INTÉRÊT
        # --------------------------------------------------------

        interest_rate = float(
            bank["interest_rate"] or 0
        )

        total_interest = calculate_loan_interest(
            amount,
            interest_rate,
        )

        total_due = (
            amount
            + total_interest
        )

        now = datetime.utcnow()

        # --------------------------------------------------------
        # DATE D'ÉCHÉANCE
        # --------------------------------------------------------

        due_at = (
            now
            + __import__(
                "datetime"
            ).timedelta(
                days=duration_days
            )
        )

        # --------------------------------------------------------
        # CRÉATION
        # --------------------------------------------------------

        result = await session.execute(
            text(
                """
                INSERT INTO life_loans (
                    bank_id,
                    character_id,
                    loan_type,
                    principal,
                    interest_rate,
                    total_interest,
                    total_due,
                    amount_paid,
                    remaining_balance,
                    duration_days,
                    issued_at,
                    due_at,
                    status
                )
                VALUES (
                    :bank_id,
                    :character_id,
                    :loan_type,
                    :principal,
                    :interest_rate,
                    :total_interest,
                    :total_due,
                    0,
                    :remaining_balance,
                    :duration_days,
                    :issued_at,
                    :due_at,
                    'active'
                )
                RETURNING id
                """
            ),
            {
                "bank_id": bank_id,
                "character_id": character_id,
                "loan_type": loan_type,
                "principal": amount,
                "interest_rate": interest_rate,
                "total_interest": total_interest,
                "total_due": total_due,
                "remaining_balance": total_due,
                "duration_days": duration_days,
                "issued_at": now,
                "due_at": due_at,
            },
        )

        loan_id = int(
            result.scalar_one()
        )

        # --------------------------------------------------------
        # VERSEMENT AU JOUEUR
        # --------------------------------------------------------

        old_balance = int(
            character["balance"] or 0
        )

        new_balance = (
            old_balance
            + amount
        )

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

        # --------------------------------------------------------
        # TRANSACTION FINANCIÈRE
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
                    'loan_received',
                    :amount,
                    :balance_after,
                    :description,
                    :reference
                )
                """
            ),
            {
                "character_id": character_id,
                "amount": amount,
                "balance_after": new_balance,
                "description": (
                    f"Prêt {loan_type} — {bank['name']}"
                ),
                "reference": f"loan:{loan_id}",
            },
        )

        await session.commit()

        return {
            "success": True,
            "loan_id": loan_id,
            "bank_name": bank["name"],
            "principal": amount,
            "interest_rate": interest_rate,
            "total_interest": total_interest,
            "total_due": total_due,
            "remaining_balance": total_due,
            "duration_days": duration_days,
            "due_at": due_at,
            "wallet_balance": new_balance,
            "message": (
                "🏦 PRÊT ACCORDÉ\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🏦 Banque : {bank['name']}\n"
                f"💰 Montant : "
                f"{format_money(amount)} FCFA\n"
                f"📈 Intérêts : "
                f"{format_money(total_interest)} FCFA\n"
                f"💵 Total à rembourser : "
                f"{format_money(total_due)} FCFA\n"
                f"📅 Durée : {duration_days} jours\n"
                f"💳 Échéance : "
                f"{due_at.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"💰 Nouveau solde : "
                f"{format_money(new_balance)} FCFA"
            ),
        }


# ============================================================
# REMBOURSEMENT
# ============================================================

async def repay_loan(
    character_id: int,
    loan_id: int,
    amount: int,
) -> dict[str, Any]:
    """
    Effectue un remboursement de prêt.
    """

    try:
        amount = positive_amount(amount)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "❌ Montant invalide.",
        }

    character_id = int(character_id)
    loan_id = int(loan_id)

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
        # PRÊT
        # --------------------------------------------------------

        loan_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    character_id,
                    remaining_balance,
                    amount_paid,
                    status
                FROM life_loans
                WHERE id = :loan_id
                FOR UPDATE
                """
            ),
            {
                "loan_id": loan_id,
            },
        )

        loan = loan_result.mappings().first()

        if loan is None:
            return {
                "success": False,
                "message": "❌ Prêt introuvable.",
            }

        if int(loan["character_id"]) != character_id:
            return {
                "success": False,
                "message": "❌ Ce prêt ne t'appartient pas.",
            }

        if loan["status"] not in (
            "active",
            "overdue",
        ):
            return {
                "success": False,
                "message": (
                    "❌ Ce prêt n'est plus remboursable."
                ),
            }

        remaining = int(
            loan["remaining_balance"] or 0
        )

        if remaining <= 0:
            return {
                "success": False,
                "message": "ℹ️ Ce prêt est déjà remboursé.",
            }

        if amount > remaining:
            amount = remaining

        if wallet < amount:
            return {
                "success": False,
                "message": (
                    "❌ Solde insuffisant.\n"
                    f"💰 Disponible : "
                    f"{format_money(wallet)} FCFA\n"
                    f"💵 Remboursement : "
                    f"{format_money(amount)} FCFA"
                ),
            }

        new_remaining = (
            remaining
            - amount
        )

        new_paid = (
            int(loan["amount_paid"] or 0)
            + amount
        )

        new_wallet = (
            wallet
            - amount
        )

        new_status = (
            "paid"
            if new_remaining <= 0
            else loan["status"]
        )

        # --------------------------------------------------------
        # PERSONNAGE
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
        # PRÊT
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                UPDATE life_loans
                SET amount_paid = :amount_paid,
                    remaining_balance = :remaining_balance,
                    last_payment_at = NOW(),
                    status = :status
                WHERE id = :loan_id
                """
            ),
            {
                "amount_paid": new_paid,
                "remaining_balance": new_remaining,
                "status": new_status,
                "loan_id": loan_id,
            },
        )

        # --------------------------------------------------------
        # HISTORIQUE
        # --------------------------------------------------------

        await session.execute(
            text(
                """
                INSERT INTO life_loan_payments (
                    loan_id,
                    character_id,
                    amount,
                    remaining_balance,
                    payment_type
                )
                VALUES (
                    :loan_id,
                    :character_id,
                    :amount,
                    :remaining_balance,
                    :payment_type
                )
                """
            ),
            {
                "loan_id": loan_id,
                "character_id": character_id,
                "amount": amount,
                "remaining_balance": new_remaining,
                "payment_type": (
                    "full"
                    if new_remaining <= 0
                    else "partial"
                ),
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
                    'loan_payment',
                    :amount,
                    :balance_after,
                    'Remboursement de prêt',
                    :reference
                )
                """
            ),
            {
                "character_id": character_id,
                "amount": -amount,
                "balance_after": new_wallet,
                "reference": f"loan:{loan_id}",
            },
        )

        await session.commit()

        status_text = (
            "✅ PRÊT ENTIÈREMENT REMBOURSÉ"
            if new_remaining <= 0
            else "💵 REMBOURSEMENT EFFECTUÉ"
        )

        return {
            "success": True,
            "amount": amount,
            "amount_paid": new_paid,
            "remaining_balance": new_remaining,
            "wallet_balance": new_wallet,
            "status": new_status,
            "message": (
                f"{status_text}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 Paiement : "
                f"{format_money(amount)} FCFA\n"
                f"📉 Dette restante : "
                f"{format_money(new_remaining)} FCFA\n"
                f"💰 Portefeuille : "
                f"{format_money(new_wallet)} FCFA"
            ),
        }


# ============================================================
# RETARD
# ============================================================

async def update_overdue_loans() -> int:
    """
    Marque les prêts arrivés à échéance comme overdue.

    Retourne le nombre de prêts concernés.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                UPDATE life_loans
                SET status = 'overdue'
                WHERE status = 'active'
                  AND due_at < NOW()
                  AND remaining_balance > 0
                """
            )
        )

        affected = int(
            result.rowcount or 0
        )

        await session.commit()

        return affected


# ============================================================
# STATISTIQUES
# ============================================================

async def get_loan_stats(
    character_id: int,
) -> dict[str, Any]:
    """
    Statistiques générales des prêts du personnage.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_loans,
                    COALESCE(
                        SUM(principal),
                        0
                    ) AS total_borrowed,
                    COALESCE(
                        SUM(amount_paid),
                        0
                    ) AS total_paid,
                    COALESCE(
                        SUM(remaining_balance),
                        0
                    ) AS total_remaining,
                    COALESCE(
                        SUM(total_interest),
                        0
                    ) AS total_interest
                FROM life_loans
                WHERE character_id = :character_id
                """
            ),
            {
                "character_id": int(character_id),
            },
        )

        row = result.mappings().first()

        active_result = await session.execute(
            text(
                """
                SELECT COUNT(*) AS count
                FROM life_loans
                WHERE character_id = :character_id
                  AND status IN (
                      'active',
                      'overdue'
                  )
                """
            ),
            {
                "character_id": int(character_id),
            },
        )

        active = active_result.mappings().first()

        return {
            "success": True,
            "total_loans": int(
                row["total_loans"] or 0
            ),
            "total_borrowed": int(
                row["total_borrowed"] or 0
            ),
            "total_paid": int(
                row["total_paid"] or 0
            ),
            "total_remaining": int(
                row["total_remaining"] or 0
            ),
            "total_interest": int(
                row["total_interest"] or 0
            ),
            "active_loans": int(
                active["count"] or 0
            ),
        }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_character_loans",
    "get_loan",
    "calculate_loan_interest",
    "request_loan",
    "repay_loan",
    "update_overdue_loans",
    "get_loan_stats",
]
