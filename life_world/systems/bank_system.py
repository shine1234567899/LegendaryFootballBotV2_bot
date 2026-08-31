"""
MANUWORLD — BANK SYSTEM

Système bancaire central.

Gère :
    - banques
    - comptes bancaires
    - ouverture de compte
    - dépôts
    - retraits
    - virements entre joueurs
    - frais
    - intérêts
    - historique des transactions
    - fermeture de compte

IMPORTANT :
    - utilise la base MANUWORLD existante ;
    - ne crée pas une nouvelle base ;
    - ne modifie pas main.py.
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_BANKS = [
    {
        "name": "Manuella First Bank",
        "bank_type": "premium",
        "interest_rate": Decimal("8.0000"),
        "account_fee": 0,
        "initial_deposit": 10_000_000,
        "transfer_fee": 100,
        "minimum_balance": 10_000_000,
        "maximum_balance": None,
        "prestige": 11,
        "card_name": "Manuella First Card",
        "card_type": "premium",
    },
    {
        "name": "Joy Joy Master",
        "bank_type": "elite",
        "interest_rate": Decimal("7.0000"),
        "account_fee": 0,
        "initial_deposit": 7_500_000,
        "transfer_fee": 150,
        "minimum_balance": 7_500_000,
        "maximum_balance": None,
        "prestige": 10,
        "card_name": "Joy Joy Master",
        "card_type": "elite",
    },
    {
        "name": "Tessia Bank",
        "bank_type": "premium",
        "interest_rate": Decimal("6.5000"),
        "account_fee": 0,
        "initial_deposit": 6_000_000,
        "transfer_fee": 200,
        "minimum_balance": 6_000_000,
        "maximum_balance": None,
        "prestige": 9,
        "card_name": "Tessia Premium",
        "card_type": "premium",
    },
    {
        "name": "Goat Bank",
        "bank_type": "premium",
        "interest_rate": Decimal("6.0000"),
        "account_fee": 0,
        "initial_deposit": 5_000_000,
        "transfer_fee": 250,
        "minimum_balance": 5_000_000,
        "maximum_balance": None,
        "prestige": 8,
        "card_name": "Goat Card",
        "card_type": "premium",
    },
    {
        "name": "Lili Bank",
        "bank_type": "premium",
        "interest_rate": Decimal("5.5000"),
        "account_fee": 0,
        "initial_deposit": 3_500_000,
        "transfer_fee": 300,
        "minimum_balance": 3_500_000,
        "maximum_balance": None,
        "prestige": 7,
        "card_name": "Lili Premium",
        "card_type": "premium",
    },
    {
        "name": "Elyra",
        "bank_type": "premium",
        "interest_rate": Decimal("5.2500"),
        "account_fee": 0,
        "initial_deposit": 3_000_000,
        "transfer_fee": 300,
        "minimum_balance": 3_000_000,
        "maximum_balance": None,
        "prestige": 6,
        "card_name": "Elyra Card",
        "card_type": "premium",
    },
    {
        "name": "Nénou Master",
        "bank_type": "card_bank",
        "interest_rate": Decimal("4.7500"),
        "account_fee": 0,
        "initial_deposit": 2_500_000,
        "transfer_fee": 350,
        "minimum_balance": 2_500_000,
        "maximum_balance": None,
        "prestige": 5,
        "card_name": "Nénou Master",
        "card_type": "master",
    },
    {
        "name": "Drav Visa",
        "bank_type": "card_bank",
        "interest_rate": Decimal("4.5000"),
        "account_fee": 0,
        "initial_deposit": 2_000_000,
        "transfer_fee": 350,
        "minimum_balance": 2_000_000,
        "maximum_balance": None,
        "prestige": 4,
        "card_name": "Drav Visa",
        "card_type": "visa",
    },
    {
        "name": "Asuna Pay",
        "bank_type": "payment_bank",
        "interest_rate": Decimal("4.2500"),
        "account_fee": 0,
        "initial_deposit": 1_750_000,
        "transfer_fee": 400,
        "minimum_balance": 1_750_000,
        "maximum_balance": None,
        "prestige": 3,
        "card_name": "Asuna Pay Card",
        "card_type": "payment",
    },
    {
        "name": "Luna Bank",
        "bank_type": "bank",
        "interest_rate": Decimal("4.0000"),
        "account_fee": 0,
        "initial_deposit": 1_500_000,
        "transfer_fee": 450,
        "minimum_balance": 1_500_000,
        "maximum_balance": None,
        "prestige": 2,
        "card_name": "Luna Card",
        "card_type": "standard",
    },
    {
        "name": "Yui Bank",
        "bank_type": "bank",
        "interest_rate": Decimal("3.5000"),
        "account_fee": 0,
        "initial_deposit": 750_000,
        "transfer_fee": 500,
        "minimum_balance": 750_000,
        "maximum_balance": None,
        "prestige": 1,
        "card_name": "Yui Card",
        "card_type": "standard",
    },
]

# ============================================================
# UTILITAIRES
# ============================================================

def format_money(
    amount: int | float | Decimal | None,
) -> str:

    return f"{int(amount or 0):,}".replace(
        ",",
        " ",
    )


def generate_account_number() -> str:

    digits = "".join(
        secrets.choice(
            string.digits
        )
        for _ in range(12)
    )

    return digits


def normalize_bank_name(
    name: str,
) -> str:

    name = str(
        name or ""
    ).strip()

    if not name:
        raise ValueError(
            "Le nom de la banque est obligatoire."
        )

    return name[:120]


def validate_amount(
    amount: int,
) -> int:

    amount = int(amount)

    if amount <= 0:

        raise ValueError(
            "Le montant doit être supérieur à 0."
        )

    return amount


# ============================================================
# BANQUES
# ============================================================

async def ensure_bank_catalog_schema() -> None:
    """[MWL] Add non-destructive fields required by the bank catalogue."""
    async with AsyncSessionLocal() as session:
        for statement in (
            "ALTER TABLE life_banks ADD COLUMN IF NOT EXISTS initial_deposit BIGINT NOT NULL DEFAULT 0",
            "ALTER TABLE life_banks ADD COLUMN IF NOT EXISTS card_name VARCHAR(100)",
            "ALTER TABLE life_banks ADD COLUMN IF NOT EXISTS card_type VARCHAR(40)",
        ):
            await session.execute(text(statement))
        await session.commit()



async def seed_default_banks() -> int:
    """
    Ajoute les banques par défaut sans modifier
    celles qui existent déjà.
    """

    await ensure_bank_catalog_schema()

    added = 0

    async with AsyncSessionLocal() as session:

        for bank in DEFAULT_BANKS:

            result = await session.execute(
                text(
                    """
                    SELECT id
                    FROM life_banks
                    WHERE LOWER(name) = LOWER(:name)
                    LIMIT 1
                    """
                ),
                {
                    "name": bank["name"],
                },
            )

            if result.first() is not None:
                continue

            await session.execute(
                text(
                    """
                    INSERT INTO life_banks (
                        name,
                        bank_type,
                        interest_rate,
                        account_fee,
                        transfer_fee,
                        minimum_balance,
                        maximum_balance,
                        prestige,
                        initial_deposit,
                        card_name,
                        card_type,
                        active
                    )
                    VALUES (
                        :name,
                        :bank_type,
                        :interest_rate,
                        :account_fee,
                        :transfer_fee,
                        :minimum_balance,
                        :maximum_balance,
                        :prestige,
                        :initial_deposit,
                        :card_name,
                        :card_type,
                        TRUE
                    )
                    """
                ),
                bank,
            )

            added += 1

        # Keep the public catalogue exactly aligned with MANUWORLD.
        # Disable legacy banks that are not part of the official catalogue.
        await session.execute(
            text(
                """
                UPDATE life_banks
                SET active = FALSE
                WHERE LOWER(name) NOT IN (
                    'manuella first bank',
                    'joy joy master',
                    'tessia bank',
                    'goat bank',
                    'lili bank',
                    'elyra',
                    'nénou master',
                    'drav visa',
                    'asuna pay',
                    'luna bank',
                    'yui bank'
                )
                """
            )
        )

        # Update existing desired banks without changing their IDs.
        for bank in DEFAULT_BANKS:
            await session.execute(
                text(
                    """
                    UPDATE life_banks
                    SET bank_type = :bank_type,
                        interest_rate = :interest_rate,
                        account_fee = :account_fee,
                        transfer_fee = :transfer_fee,
                        minimum_balance = :minimum_balance,
                        maximum_balance = :maximum_balance,
                        prestige = :prestige,
                        initial_deposit = :initial_deposit,
                        card_name = :card_name,
                        card_type = :card_type,
                        active = TRUE
                    WHERE LOWER(name) = LOWER(:name)
                    """
                ),
                bank,
            )

        await session.commit()

    return added


async def get_banks(
    active_only: bool = True,
) -> list[dict[str, Any]]:

    async with AsyncSessionLocal() as session:

        if active_only:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_banks
                    WHERE active = TRUE
                    ORDER BY prestige ASC,
                             name ASC
                    """
                )
            )

        else:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_banks
                    ORDER BY active DESC,
                             prestige ASC,
                             name ASC
                    """
                )
            )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


async def get_bank(
    bank_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_banks
                WHERE id = :bank_id
                LIMIT 1
                """
            ),
            {
                "bank_id": int(bank_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


async def get_bank_by_name(
    name: str,
) -> dict[str, Any] | None:

    name = normalize_bank_name(
        name
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_banks
                WHERE LOWER(name) = LOWER(:name)
                LIMIT 1
                """
            ),
            {
                "name": name,
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# COMPTE
# ============================================================

async def get_account(
    account_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name,
                    b.bank_type,
                    b.interest_rate,
                    b.account_fee,
                    b.transfer_fee,
                    b.minimum_balance,
                    b.maximum_balance,
                    b.prestige
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.id = :account_id
                LIMIT 1
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


async def get_character_account(
    character_id: int,
    bank_id: int | None = None,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        if bank_id is None:

            result = await session.execute(
                text(
                    """
                    SELECT
                        a.*,
                        b.name AS bank_name,
                        b.bank_type,
                        b.interest_rate,
                        b.account_fee,
                        b.transfer_fee,
                        b.minimum_balance,
                        b.maximum_balance,
                        b.prestige
                    FROM life_bank_accounts a
                    INNER JOIN life_banks b
                        ON b.id = a.bank_id
                    WHERE a.character_id = :character_id
                      AND a.status = 'active'
                    ORDER BY b.prestige ASC
                    LIMIT 1
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                },
            )

        else:

            result = await session.execute(
                text(
                    """
                    SELECT
                        a.*,
                        b.name AS bank_name,
                        b.bank_type,
                        b.interest_rate,
                        b.account_fee,
                        b.transfer_fee,
                        b.minimum_balance,
                        b.maximum_balance,
                        b.prestige
                    FROM life_bank_accounts a
                    INNER JOIN life_banks b
                        ON b.id = a.bank_id
                    WHERE a.character_id = :character_id
                      AND a.bank_id = :bank_id
                      AND a.status = 'active'
                    LIMIT 1
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                    "bank_id": int(
                        bank_id
                    ),
                },
            )

        row = result.mappings().first()

        return dict(row) if row else None


async def get_character_accounts(
    character_id: int,
) -> list[dict[str, Any]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name,
                    b.bank_type,
                    b.interest_rate,
                    b.account_fee,
                    b.transfer_fee,
                    b.minimum_balance,
                    b.maximum_balance,
                    b.prestige
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.character_id = :character_id
                ORDER BY
                    CASE
                        WHEN a.status = 'active'
                        THEN 0
                        ELSE 1
                    END,
                    b.prestige ASC
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# RECHERCHE PAR NUMÉRO DE COMPTE
# ============================================================

async def get_bank_account_by_number(
    account_number: str,
) -> dict[str, Any] | None:
    """
    Recherche un compte bancaire à partir de son numéro.
    """

    account_number = str(
        account_number or ""
    ).strip()

    if not account_number:
        return None

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name,
                    b.bank_type,
                    b.interest_rate,
                    b.account_fee,
                    b.transfer_fee,
                    b.minimum_balance,
                    b.maximum_balance,
                    b.prestige
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.account_number = :account_number
                LIMIT 1
                """
            ),
            {
                "account_number": account_number,
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# OUVERTURE DE COMPTE
# ============================================================

async def open_account(
    character_id: int,
    bank_id: int,
) -> dict[str, Any]:

    bank = await get_bank(
        bank_id
    )

    if bank is None:

        return {
            "success": False,
            "message": "❌ Banque introuvable.",
        }

    if not bank["active"]:

        return {
            "success": False,
            "message": "❌ Cette banque est actuellement fermée.",
        }

    existing = await get_character_account(
        character_id,
        bank_id,
    )

    if existing is not None:

        return {
            "success": False,
            "message": (
                "❌ Tu possèdes déjà un compte "
                f"chez {bank['name']}."
            ),
            "account": existing,
        }

    account_fee = int(bank["account_fee"] or 0)
    initial_deposit = int(bank.get("initial_deposit") or 0)
    required_upfront = account_fee + initial_deposit

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
                "character_id": int(
                    character_id
                ),
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

        if balance < required_upfront:

            return {
                "success": False,
                "message": (
                    "❌ Solde insuffisant pour ouvrir "
                    "ce compte.\n"
                    f"💰 Solde : {format_money(balance)} FCFA\n"
                    f"🏦 Dépôt initial : {format_money(initial_deposit)} FCFA\n"
                    f"🧾 Frais d'ouverture : {format_money(account_fee)} FCFA\n"
                    f"💵 Total nécessaire : {format_money(required_upfront)} FCFA"
                ),
            }

        account_number = None

        for _ in range(20):

            candidate = generate_account_number()

            check = await session.execute(
                text(
                    """
                    SELECT id
                    FROM life_bank_accounts
                    WHERE account_number = :account_number
                    LIMIT 1
                    """
                ),
                {
                    "account_number": candidate,
                },
            )

            if check.first() is None:

                account_number = candidate
                break

        if account_number is None:

            return {
                "success": False,
                "message": "❌ Impossible de générer le numéro du compte.",
            }

        new_balance = balance - required_upfront

        if required_upfront > 0:

            await session.execute(
                text(
                    """
                    UPDATE life_characters
                    SET
                        balance = :balance,
                        updated_at = NOW()
                    WHERE id = :character_id
                    """
                ),
                {
                    "balance": new_balance,
                    "character_id": int(
                        character_id
                    ),
                },
            )

        result = await session.execute(
            text(
                """
                INSERT INTO life_bank_accounts (
                    bank_id,
                    character_id,
                    account_number,
                    balance,
                    interest_accrued,
                    status
                )
                VALUES (
                    :bank_id,
                    :character_id,
                    :account_number,
                    0,
                    0,
                    'active'
                )
                RETURNING *
                """
            ),
            {
                "bank_id": int(
                    bank_id
                ),
                "character_id": int(
                    character_id
                ),
                "account_number": account_number,
                "initial_deposit": initial_deposit,
            },
        )

        account = dict(
            result.mappings().one()
        )

        if account_fee > 0:
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
                        'bank_account_fee',
                        :amount,
                        :balance_after,
                        :description,
                        :reference
                    )
                    """
                ),
                {
                    "character_id": int(character_id),
                    "amount": -account_fee,
                    "balance_after": new_balance,
                    "description": f"Frais d'ouverture {bank['name']}",
                    "reference": f"bank_account:{account['id']}",
                },
            )

        if initial_deposit > 0:
            await session.execute(
                text(
                    """
                    INSERT INTO life_bank_transactions (
                        account_id,
                        transaction_type,
                        amount,
                        balance_after,
                        description
                    )
                    VALUES (
                        :account_id,
                        'initial_deposit',
                        :amount,
                        :balance_after,
                        :description
                    )
                    """
                ),
                {
                    "account_id": int(account["id"]),
                    "amount": initial_deposit,
                    "balance_after": initial_deposit,
                    "description": f"Dépôt initial {bank['name']}",
                },
            )

        await session.commit()

    return {
        "success": True,
        "account": account,
        "bank": bank,
        "message": (
            "🏦 **COMPTE OUVERT**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Banque : **{bank['name']}**\n"
            f"🔢 Compte : `{account_number}`\n"
            f"💰 Solde : "
            f"{format_money(initial_deposit)} FCFA\n"
            f"💳 Carte : "
            f"{bank.get('card_name') or 'Aucune'}\n"
            f"📈 Intérêt : "
            f"{bank['interest_rate']} %"
        ),
    }


# ============================================================
# DÉPÔT
# ============================================================

async def deposit(
    character_id: int,
    account_id: int,
    amount: int,
) -> dict[str, Any]:

    try:
        amount = validate_amount(
            amount
        )
    except ValueError as exc:

        return {
            "success": False,
            "message": f"❌ {exc}",
        }

    async with AsyncSessionLocal() as session:

        account_result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name,
                    b.maximum_balance
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.id = :account_id
                  AND a.character_id = :character_id
                  AND a.status = 'active'
                FOR UPDATE
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
                "character_id": int(
                    character_id
                ),
            },
        )

        account = (
            account_result
            .mappings()
            .first()
        )

        if account is None:

            return {
                "success": False,
                "message": "❌ Compte bancaire introuvable.",
            }

        character_result = await session.execute(
            text(
                """
                SELECT balance
                FROM life_characters
                WHERE id = :character_id
                FOR UPDATE
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
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

        cash = int(
            character["balance"] or 0
        )

        if cash < amount:

            return {
                "success": False,
                "message": (
                    "❌ Argent liquide insuffisant.\n"
                    f"💵 Disponible : "
                    f"{format_money(cash)} FCFA"
                ),
            }

        old_balance = int(
            account["balance"] or 0
        )

        maximum = account.get(
            "maximum_balance"
        )

        if maximum is not None:

            maximum = int(
                maximum
            )

            if old_balance + amount > maximum:

                return {
                    "success": False,
                    "message": (
                        "❌ Le plafond du compte "
                        "serait dépassé."
                    ),
                }

        new_cash = (
            cash - amount
        )

        new_account_balance = (
            old_balance + amount
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET
                    balance = :balance,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "balance": new_cash,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET balance = :balance
                WHERE id = :account_id
                """
            ),
            {
                "balance": new_account_balance,
                "account_id": int(
                    account_id
                ),
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO life_bank_transactions (
                    account_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :account_id,
                    'deposit',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
                "amount": amount,
                "balance_after": new_account_balance,
                "description": "Dépôt bancaire",
            },
        )

        await session.commit()

    return {
        "success": True,
        "amount": amount,
        "balance": new_account_balance,
        "cash": new_cash,
        "message": (
            "🏦 **DÉPÔT EFFECTUÉ**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Dépôt : "
            f"+{format_money(amount)} FCFA\n"
            f"🏦 Solde bancaire : "
            f"{format_money(new_account_balance)} FCFA\n"
            f"💵 Argent liquide : "
            f"{format_money(new_cash)} FCFA"
        ),
    }


# ============================================================
# RETRAIT
# ============================================================

async def withdraw(
    character_id: int,
    account_id: int,
    amount: int,
) -> dict[str, Any]:

    try:
        amount = validate_amount(
            amount
        )
    except ValueError as exc:

        return {
            "success": False,
            "message": f"❌ {exc}",
        }

    async with AsyncSessionLocal() as session:

        account_result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name,
                    b.minimum_balance
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.id = :account_id
                  AND a.character_id = :character_id
                  AND a.status = 'active'
                FOR UPDATE
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
                "character_id": int(
                    character_id
                ),
            },
        )

        account = (
            account_result
            .mappings()
            .first()
        )

        if account is None:

            return {
                "success": False,
                "message": "❌ Compte bancaire introuvable.",
            }

        balance = int(
            account["balance"] or 0
        )

        minimum = int(
            account["minimum_balance"] or 0
        )

        if balance < amount:

            return {
                "success": False,
                "message": (
                    "❌ Solde bancaire insuffisant.\n"
                    f"🏦 Disponible : "
                    f"{format_money(balance)} FCFA"
                ),
            }

        new_balance = (
            balance - amount
        )

        if new_balance < minimum:

            return {
                "success": False,
                "message": (
                    "❌ Le solde minimum requis "
                    "serait dépassé.\n"
                    f"🔒 Minimum : "
                    f"{format_money(minimum)} FCFA"
                ),
            }

        character_result = await session.execute(
            text(
                """
                SELECT balance
                FROM life_characters
                WHERE id = :character_id
                FOR UPDATE
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
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

        cash = int(
            character["balance"] or 0
        )

        new_cash = (
            cash + amount
        )

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET balance = :balance
                WHERE id = :account_id
                """
            ),
            {
                "balance": new_balance,
                "account_id": int(
                    account_id
                ),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET
                    balance = :balance,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "balance": new_cash,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO life_bank_transactions (
                    account_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :account_id,
                    'withdraw',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
                "amount": -amount,
                "balance_after": new_balance,
                "description": "Retrait bancaire",
            },
        )

        await session.commit()

    return {
        "success": True,
        "amount": amount,
        "balance": new_balance,
        "cash": new_cash,
        "message": (
            "🏦 **RETRAIT EFFECTUÉ**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Retrait : "
            f"-{format_money(amount)} FCFA\n"
            f"🏦 Solde bancaire : "
            f"{format_money(new_balance)} FCFA\n"
            f"💵 Argent liquide : "
            f"{format_money(new_cash)} FCFA"
        ),
    }


# ============================================================
# VIREMENT
# ============================================================

async def transfer(
    sender_character_id: int,
    receiver_character_id: int,
    amount: int,
) -> dict[str, Any]:

    try:
        amount = validate_amount(
            amount
        )
    except ValueError as exc:

        return {
            "success": False,
            "message": f"❌ {exc}",
        }

    if (
        int(sender_character_id)
        == int(receiver_character_id)
    ):

        return {
            "success": False,
            "message": "❌ Impossible de faire un virement vers soi-même.",
        }

    async with AsyncSessionLocal() as session:

        sender_account_result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name,
                    b.transfer_fee
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.character_id = :character_id
                  AND a.status = 'active'
                ORDER BY b.prestige ASC
                LIMIT 1
                FOR UPDATE
                """
            ),
            {
                "character_id": int(
                    sender_character_id
                ),
            },
        )

        sender = (
            sender_account_result
            .mappings()
            .first()
        )

        if sender is None:

            return {
                "success": False,
                "message": "❌ L'expéditeur ne possède pas de compte bancaire.",
            }

        receiver_result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.character_id = :character_id
                  AND a.status = 'active'
                ORDER BY b.prestige ASC
                LIMIT 1
                FOR UPDATE
                """
            ),
            {
                "character_id": int(
                    receiver_character_id
                ),
            },
        )

        receiver = (
            receiver_result
            .mappings()
            .first()
        )

        if receiver is None:

            return {
                "success": False,
                "message": "❌ Le destinataire ne possède pas de compte bancaire.",
            }

        fee = int(
            sender["transfer_fee"] or 0
        )

        sender_balance = int(
            sender["balance"] or 0
        )

        total_debit = (
            amount + fee
        )

        if sender_balance < total_debit:

            return {
                "success": False,
                "message": (
                    "❌ Solde bancaire insuffisant.\n"
                    f"💸 Virement : "
                    f"{format_money(amount)} FCFA\n"
                    f"🏦 Frais : "
                    f"{format_money(fee)} FCFA\n"
                    f"💰 Disponible : "
                    f"{format_money(sender_balance)} FCFA"
                ),
            }

        receiver_balance = int(
            receiver["balance"] or 0
        )

        new_sender_balance = (
            sender_balance
            - total_debit
        )

        new_receiver_balance = (
            receiver_balance
            + amount
        )

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET balance = :balance
                WHERE id = :account_id
                """
            ),
            {
                "balance": new_sender_balance,
                "account_id": int(
                    sender["id"]
                ),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET balance = :balance
                WHERE id = :account_id
                """
            ),
            {
                "balance": new_receiver_balance,
                "account_id": int(
                    receiver["id"]
                ),
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO life_bank_transactions (
                    account_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :account_id,
                    'transfer_out',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "account_id": int(
                    sender["id"]
                ),
                "amount": -amount,
                "balance_after": new_sender_balance,
                "description": (
                    f"Virement vers compte "
                    f"{receiver['account_number']}"
                ),
            },
        )

        if fee > 0:

            await session.execute(
                text(
                    """
                    INSERT INTO life_bank_transactions (
                        account_id,
                        transaction_type,
                        amount,
                        balance_after,
                        description
                    )
                    VALUES (
                        :account_id,
                        'transfer_fee',
                        :amount,
                        :balance_after,
                        :description
                    )
                    """
                ),
                {
                    "account_id": int(
                        sender["id"]
                    ),
                    "amount": -fee,
                    "balance_after": new_sender_balance,
                    "description": "Frais de virement",
                },
            )

        await session.execute(
            text(
                """
                INSERT INTO life_bank_transactions (
                    account_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :account_id,
                    'transfer_in',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "account_id": int(
                    receiver["id"]
                ),
                "amount": amount,
                "balance_after": new_receiver_balance,
                "description": (
                    f"Virement depuis compte "
                    f"{sender['account_number']}"
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "amount": amount,
        "fee": fee,
        "sender_balance": new_sender_balance,
        "receiver_balance": new_receiver_balance,
        "message": (
            "💸 **VIREMENT EFFECTUÉ**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Montant : "
            f"{format_money(amount)} FCFA\n"
            f"🏦 Frais : "
            f"{format_money(fee)} FCFA\n"
            f"💳 Nouveau solde : "
            f"{format_money(new_sender_balance)} FCFA"
        ),
    }


# ============================================================
# INTÉRÊTS
# ============================================================

async def calculate_account_interest(
    account: dict[str, Any],
) -> int:

    balance = int(
        account.get("balance") or 0
    )

    rate = Decimal(
        str(
            account.get(
                "interest_rate"
            )
            or 0
        )
    )

    if balance <= 0 or rate <= 0:

        return 0

    # Intérêt annuel converti en intérêt journalier.
    interest = (
        Decimal(balance)
        * rate
        / Decimal("100")
        / Decimal("365")
    )

    return max(
        0,
        int(interest),
    )


async def apply_account_interest(
    account_id: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.interest_rate,
                    b.name AS bank_name
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.id = :account_id
                  AND a.status = 'active'
                FOR UPDATE
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
            },
        )

        account = result.mappings().first()

        if account is None:

            return {
                "success": False,
                "message": "❌ Compte introuvable.",
            }

        balance = int(
            account["balance"] or 0
        )

        rate = Decimal(
            str(
                account["interest_rate"]
                or 0
            )
        )

        if balance <= 0 or rate <= 0:

            return {
                "success": True,
                "interest": 0,
                "balance": balance,
                "message": "ℹ️ Aucun intérêt à appliquer.",
            }

        interest = max(
            0,
            int(
                Decimal(balance)
                * rate
                / Decimal("100")
                / Decimal("365")
            ),
        )

        if interest <= 0:

            return {
                "success": True,
                "interest": 0,
                "balance": balance,
            }

        new_balance = (
            balance + interest
        )

        previous_accrued = int(
            account["interest_accrued"] or 0
        )

        new_accrued = (
            previous_accrued
            + interest
        )

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET
                    balance = :balance,
                    interest_accrued = :interest_accrued,
                    last_interest_at = NOW()
                WHERE id = :account_id
                """
            ),
            {
                "balance": new_balance,
                "interest_accrued": new_accrued,
                "account_id": int(
                    account_id
                ),
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO life_bank_transactions (
                    account_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :account_id,
                    'interest',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
                "amount": interest,
                "balance_after": new_balance,
                "description": "Intérêt bancaire",
            },
        )

        await session.commit()

    return {
        "success": True,
        "interest": interest,
        "balance": new_balance,
        "message": (
            f"📈 Intérêt crédité : "
            f"+{format_money(interest)} FCFA\n"
            f"🏦 Nouveau solde : "
            f"{format_money(new_balance)} FCFA"
        ),
    }


# ============================================================
# HISTORIQUE
# ============================================================

async def get_bank_transactions(
    account_id: int,
    limit: int = 30,
) -> list[dict[str, Any]]:

    limit = max(
        1,
        min(
            200,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_bank_transactions
                WHERE account_id = :account_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
                "limit": limit,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# FERMETURE
# ============================================================

async def close_account(
    character_id: int,
    account_id: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.id = :account_id
                  AND a.character_id = :character_id
                  AND a.status = 'active'
                FOR UPDATE
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
                "character_id": int(
                    character_id
                ),
            },
        )

        account = result.mappings().first()

        if account is None:

            return {
                "success": False,
                "message": "❌ Compte bancaire introuvable.",
            }

        balance = int(
            account["balance"] or 0
        )

        if balance > 0:

            return {
                "success": False,
                "message": (
                    "❌ Le compte doit être vide "
                    "avant sa fermeture.\n"
                    f"🏦 Solde : "
                    f"{format_money(balance)} FCFA"
                ),
            }

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET status = 'closed'
                WHERE id = :account_id
                """
            ),
            {
                "account_id": int(
                    account_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "message": (
            f"✅ Compte {account['account_number']} "
            f"chez {account['bank_name']} fermé."
        ),
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_bank(
    bank: dict[str, Any],
) -> str:

    maximum = bank.get(
        "maximum_balance"
    )

    maximum_text = (
        "Illimité"
        if maximum is None
        else f"{format_money(maximum)} FCFA"
    )

    return (
        f"🏦 **{bank['name']}**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ Type : {bank.get('bank_type') or 'bank'}\n"
        f"📈 Intérêt : "
        f"{bank.get('interest_rate') or 0} %\n"
        f"💳 Frais de compte : "
        f"{format_money(bank.get('account_fee'))} FCFA\n"
        f"💸 Frais de virement : "
        f"{format_money(bank.get('transfer_fee'))} FCFA\n"
        f"🔒 Solde minimum : "
        f"{format_money(bank.get('minimum_balance'))} FCFA\n"
        f"📊 Plafond : {maximum_text}\n"
        f"⭐ Prestige : {bank.get('prestige') or 1}"
    )


def format_account(
    account: dict[str, Any],
) -> str:

    return (
        "🏦 **COMPTE BANCAIRE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏦 Banque : **{account.get('bank_name', '—')}**\n"
        f"🔢 Compte : `{account.get('account_number', '—')}`\n"
        f"💰 Solde : "
        f"**{format_money(account.get('balance'))} FCFA**\n"
        f"📈 Intérêts cumulés : "
        f"{format_money(account.get('interest_accrued'))} FCFA\n"
        f"📊 Statut : "
        f"{account.get('status', '—')}\n"
        f"⭐ Prestige : "
        f"{account.get('prestige') or 1}"
    )


def format_accounts(
    accounts: list[dict[str, Any]],
) -> str:

    if not accounts:

        return (
            "🏦 **MES COMPTES**\n\n"
            "Aucun compte bancaire."
        )

    lines = [
        "🏦 **MES COMPTES BANCAIRES**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for account in accounts:

        status = account.get(
            "status",
            "unknown",
        )

        icon = (
            "🟢"
            if status == "active"
            else "⚪"
        )

        lines.extend(
            [
                (
                    f"{icon} **{account.get('bank_name', '—')}**"
                ),
                (
                    f"   🔢 "
                    f"`{account.get('account_number', '—')}`"
                ),
                (
                    f"   💰 "
                    f"{format_money(account.get('balance'))} FCFA"
                ),
                "",
            ]
        )

    return "\n".join(lines)


def format_transactions(
    transactions: list[dict[str, Any]],
) -> str:

    if not transactions:

        return (
            "📜 **HISTORIQUE BANCAIRE**\n\n"
            "Aucune transaction."
        )

    lines = [
        "📜 **HISTORIQUE BANCAIRE**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    icons = {
        "deposit": "📥",
        "withdraw": "📤",
        "transfer_out": "↗️",
        "transfer_in": "↙️",
        "transfer_fee": "💸",
        "interest": "📈",
    }

    for transaction in transactions:

        transaction_type = transaction.get(
            "transaction_type",
            "transaction",
        )

        amount = int(
            transaction.get("amount") or 0
        )

        icon = icons.get(
            transaction_type,
            "💳",
        )

        sign = (
            "+"
            if amount > 0
            else ""
        )

        lines.extend(
            [
                (
                    f"{icon} **{transaction_type}**"
                ),
                (
                    f"   💰 {sign}"
                    f"{format_money(amount)} FCFA"
                ),
                (
                    f"   🏦 Solde : "
                    f"{format_money(transaction.get('balance_after'))} FCFA"
                ),
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================
# RÉSUMÉ BANCAIRE
# ============================================================

async def get_banking_summary(
    character_id: int,
) -> dict[str, Any]:

    accounts = await get_character_accounts(
        character_id
    )

    active_accounts = [
        account
        for account in accounts
        if account.get("status") == "active"
    ]

    total_balance = sum(
        int(
            account.get("balance") or 0
        )
        for account in active_accounts
    )

    total_interest = sum(
        int(
            account.get("interest_accrued") or 0
        )
        for account in active_accounts
    )

    return {
        "accounts": accounts,
        "active_accounts": active_accounts,
        "account_count": len(
            active_accounts
        ),
        "total_balance": total_balance,
        "total_interest": total_interest,
    }



# ============================================================
# COMPTE(S) DU PERSONNAGE — ALIAS HANDLER
# ============================================================

async def get_character_bank_accounts(
    character_id: int,
) -> list[dict[str, Any]]:
    """
    Retourne tous les comptes bancaires actifs du personnage.

    Nom utilisé par life_world/handlers/bank.py.
    """

    return await get_character_accounts(
        character_id
    )


async def transfer_bank_money(
    character_id: int,
    source_account_id: int,
    destination_account_number: str,
    amount: int,
) -> dict[str, Any]:
    """
    Effectue un virement depuis un compte précis vers un numéro
    de compte précis.

    Le système principal transfer() reste disponible pour les
    virements personnage-à-personnage.
    """

    try:
        amount = validate_amount(
            amount
        )
    except ValueError as exc:

        return {
            "success": False,
            "message": f"❌ {exc}",
        }

    destination = await get_bank_account_by_number(
        destination_account_number
    )

    if destination is None:

        return {
            "success": False,
            "message": "❌ Compte destinataire introuvable.",
        }

    async with AsyncSessionLocal() as session:

        source_result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name,
                    b.transfer_fee
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.id = :account_id
                  AND a.character_id = :character_id
                  AND a.status = 'active'
                FOR UPDATE
                """
            ),
            {
                "account_id": int(source_account_id),
                "character_id": int(character_id),
            },
        )

        source = source_result.mappings().first()

        if source is None:

            return {
                "success": False,
                "message": "❌ Compte source introuvable.",
            }

        if int(source["id"]) == int(destination["id"]):

            return {
                "success": False,
                "message": "❌ Impossible de transférer vers le même compte.",
            }

        destination_result = await session.execute(
            text(
                """
                SELECT
                    a.*,
                    b.name AS bank_name
                FROM life_bank_accounts a
                INNER JOIN life_banks b
                    ON b.id = a.bank_id
                WHERE a.id = :account_id
                  AND a.status = 'active'
                FOR UPDATE
                """
            ),
            {
                "account_id": int(destination["id"]),
            },
        )

        destination_row = destination_result.mappings().first()

        if destination_row is None:

            return {
                "success": False,
                "message": "❌ Compte destinataire fermé ou introuvable.",
            }

        fee = int(
            source["transfer_fee"] or 0
        )

        source_balance = int(
            source["balance"] or 0
        )

        total_debit = amount + fee

        if source_balance < total_debit:

            return {
                "success": False,
                "message": (
                    "❌ Solde bancaire insuffisant.\n"
                    f"💰 Disponible : "
                    f"{format_money(source_balance)} FCFA\n"
                    f"💸 Total nécessaire : "
                    f"{format_money(total_debit)} FCFA"
                ),
            }

        destination_balance = int(
            destination_row["balance"] or 0
        )

        new_source_balance = (
            source_balance - total_debit
        )

        new_destination_balance = (
            destination_balance + amount
        )

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET balance = :balance
                WHERE id = :account_id
                """
            ),
            {
                "balance": new_source_balance,
                "account_id": int(source["id"]),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_bank_accounts
                SET balance = :balance
                WHERE id = :account_id
                """
            ),
            {
                "balance": new_destination_balance,
                "account_id": int(destination_row["id"]),
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO life_bank_transactions (
                    account_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :account_id,
                    'transfer_out',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "account_id": int(source["id"]),
                "amount": -amount,
                "balance_after": new_source_balance,
                "description": (
                    f"Virement vers compte "
                    f"{destination_row['account_number']}"
                ),
            },
        )

        if fee > 0:

            await session.execute(
                text(
                    """
                    INSERT INTO life_bank_transactions (
                        account_id,
                        transaction_type,
                        amount,
                        balance_after,
                        description
                    )
                    VALUES (
                        :account_id,
                        'transfer_fee',
                        :amount,
                        :balance_after,
                        :description
                    )
                    """
                ),
                {
                    "account_id": int(source["id"]),
                    "amount": -fee,
                    "balance_after": new_source_balance,
                    "description": "Frais de virement",
                },
            )

        await session.execute(
            text(
                """
                INSERT INTO life_bank_transactions (
                    account_id,
                    transaction_type,
                    amount,
                    balance_after,
                    description
                )
                VALUES (
                    :account_id,
                    'transfer_in',
                    :amount,
                    :balance_after,
                    :description
                )
                """
            ),
            {
                "account_id": int(destination_row["id"]),
                "amount": amount,
                "balance_after": new_destination_balance,
                "description": (
                    f"Virement depuis compte "
                    f"{source['account_number']}"
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "amount": amount,
        "fee": fee,
        "source_balance": new_source_balance,
        "destination_balance": new_destination_balance,
        "message": (
            "✅ **VIREMENT EFFECTUÉ**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Montant : "
            f"{format_money(amount)} FCFA\n"
            f"🏦 Frais : "
            f"{format_money(fee)} FCFA\n"
            f"💳 Nouveau solde : "
            f"{format_money(new_source_balance)} FCFA"
        ),
    }


# ============================================================
# COMPATIBILITÉ AVEC BANK HANDLER
# ============================================================
#
# Le handler bancaire utilise les noms historiques ci-dessous.
# Le système conserve ses noms principaux (open_account, deposit,
# withdraw, transfer, etc.) et expose ces alias afin d'éviter de
# casser les imports existants.
# ============================================================

open_bank_account = open_account
deposit_to_bank = deposit
withdraw_from_bank = withdraw
transfer_between_accounts = transfer

get_bank_account = get_account
get_my_bank_account = get_character_account
get_my_bank_accounts = get_character_accounts

get_transactions = get_bank_transactions
close_bank_account = close_account

apply_interest = apply_account_interest


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "DEFAULT_BANKS",
    "format_money",
    "generate_account_number",
    "normalize_bank_name",
    "validate_amount",
    "seed_default_banks",
    "get_banks",
    "get_bank",
    "get_bank_by_name",
    "get_account",
    "get_character_account",
    "get_character_accounts",
    "open_account",
    "deposit",
    "withdraw",
    "transfer",
    "calculate_account_interest",
    "apply_account_interest",
    "get_bank_transactions",
    "close_account",
    "format_bank",
    "format_account",
    "format_accounts",
    "format_transactions",
    "get_banking_summary",
    "get_bank_account_by_number",
    "get_character_bank_accounts",
    "transfer_bank_money",

    # Compatibilité handler
    "open_bank_account",
    "deposit_to_bank",
    "withdraw_from_bank",
    "transfer_between_accounts",
    "get_bank_account",
    "get_my_bank_account",
    "get_my_bank_accounts",
    "get_transactions",
    "close_bank_account",
    "apply_interest",
]