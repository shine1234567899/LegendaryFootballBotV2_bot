"""
MANUWORLD — BUSINESS SYSTEM

Système complet de gestion des entreprises.

Fonctions :
    - création d'entreprise
    - consultation d'entreprise
    - trésorerie
    - dépôts / retraits
    - membres
    - employés réels
    - employés virtuels
    - grades
    - postes
    - actionnaires
    - réputation
    - crédibilité
    - offres d'emploi
    - candidatures
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text

from life_world.database import AsyncSessionLocal


# ============================================================
# CONSTANTES
# ============================================================

COMPANY_STATUS_ACTIVE = "active"
COMPANY_STATUS_CLOSED = "closed"

MEMBER_STATUS_ACTIVE = "active"
MEMBER_STATUS_INACTIVE = "inactive"

DEFAULT_GRADE = "employee"

DEFAULT_REPUTATION = 50
DEFAULT_CREDIBILITY = 50


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(
    amount: int | float | None,
) -> str:
    return f"{int(amount or 0):,}".replace(",", " ")


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


# ============================================================
# GRADES
# ============================================================

COMPANY_GRADES = {
    "owner": {
        "label": "👑 Owner",
        "level": 100,
    },
    "director": {
        "label": "🏛️ Director",
        "level": 80,
    },
    "manager": {
        "label": "💼 Manager",
        "level": 60,
    },
    "supervisor": {
        "label": "📋 Supervisor",
        "level": 40,
    },
    "employee": {
        "label": "👤 Employee",
        "level": 10,
    },
}


def get_grade_info(
    grade: str | None,
) -> dict[str, Any]:

    grade = clean_text(
        grade,
        DEFAULT_GRADE,
    ).lower()

    return COMPANY_GRADES.get(
        grade,
        COMPANY_GRADES[DEFAULT_GRADE],
    )


def grade_level(
    grade: str | None,
) -> int:

    return int(
        get_grade_info(grade)["level"]
    )


# ============================================================
# ENTREPRISE
# ============================================================

async def create_company(
    owner_character_id: int,
    name: str,
    company_type: str = "general",
    description: str = "",
    initial_capital: int = 0,
) -> dict[str, Any]:

    owner_character_id = int(
        owner_character_id
    )

    name = clean_text(
        name,
        max_length=100,
    )

    company_type = clean_text(
        company_type,
        "general",
        50,
    )

    description = clean_text(
        description,
        "",
        1000,
    )

    initial_capital = max(
        0,
        int(initial_capital),
    )

    if not name:
        return {
            "success": False,
            "message": "❌ Le nom de l'entreprise est obligatoire.",
        }

    async with AsyncSessionLocal() as session:

        character = await session.execute(
            text(
                """
                SELECT id, balance
                FROM life_characters
                WHERE id = :character_id
                FOR UPDATE
                """
            ),
            {
                "character_id": owner_character_id,
            },
        )

        character = character.mappings().first()

        if character is None:
            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        existing = await session.execute(
            text(
                """
                SELECT id
                FROM life_companies
                WHERE LOWER(name) = LOWER(:name)
                LIMIT 1
                """
            ),
            {
                "name": name,
            },
        )

        if existing.first() is not None:
            return {
                "success": False,
                "message": "❌ Une entreprise porte déjà ce nom.",
            }

        balance = int(
            character["balance"] or 0
        )

        if initial_capital > balance:

            return {
                "success": False,
                "message": (
                    "❌ Capital insuffisant.\n"
                    f"💰 Solde : "
                    f"{format_money(balance)} FCFA\n"
                    f"🏢 Capital : "
                    f"{format_money(initial_capital)} FCFA"
                ),
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_companies (
                    owner_character_id,
                    name,
                    company_type,
                    description,
                    treasury,
                    status,
                    reputation,
                    credibility
                )
                VALUES (
                    :owner_character_id,
                    :name,
                    :company_type,
                    :description,
                    :treasury,
                    :status,
                    :reputation,
                    :credibility
                )
                RETURNING id
                """
            ),
            {
                "owner_character_id": owner_character_id,
                "name": name,
                "company_type": company_type,
                "description": description,
                "treasury": initial_capital,
                "status": COMPANY_STATUS_ACTIVE,
                "reputation": DEFAULT_REPUTATION,
                "credibility": DEFAULT_CREDIBILITY,
            },
        )

        company_id = int(
            result.scalar_one()
        )

        if initial_capital > 0:

            await session.execute(
                text(
                    """
                    UPDATE life_characters
                    SET balance = balance - :amount,
                        updated_at = NOW()
                    WHERE id = :character_id
                    """
                ),
                {
                    "amount": initial_capital,
                    "character_id": owner_character_id,
                },
            )

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
                        'capital',
                        :amount,
                        :balance_after,
                        'Capital initial'
                    )
                    """
                ),
                {
                    "company_id": company_id,
                    "character_id": owner_character_id,
                    "amount": initial_capital,
                    "balance_after": initial_capital,
                },
            )

        await session.execute(
            text(
                """
                INSERT INTO life_company_members (
                    company_id,
                    character_id,
                    grade,
                    status
                )
                VALUES (
                    :company_id,
                    :character_id,
                    'owner',
                    'active'
                )
                """
            ),
            {
                "company_id": company_id,
                "character_id": owner_character_id,
            },
        )

        await session.commit()

    return {
        "success": True,
        "company_id": company_id,
        "message": (
            "🏢 ENTREPRISE CRÉÉE\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ Nom : {name}\n"
            f"📂 Type : {company_type}\n"
            f"💰 Capital : "
            f"{format_money(initial_capital)} FCFA\n"
            f"🆔 ID : {company_id}"
        ),
    }


# ============================================================
# CONSULTATION
# ============================================================

async def get_company(
    company_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


async def get_company_by_name(
    name: str,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_companies
                WHERE LOWER(name) = LOWER(:name)
                LIMIT 1
                """
            ),
            {
                "name": clean_text(name),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


async def get_character_companies(
    character_id: int,
) -> list[dict[str, Any]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT DISTINCT c.*
                FROM life_companies c
                INNER JOIN life_company_members m
                    ON m.company_id = c.id
                WHERE m.character_id = :character_id
                  AND m.status = 'active'
                ORDER BY c.created_at DESC
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
# PROPRIÉTAIRE
# ============================================================

async def is_company_owner(
    company_id: int,
    character_id: int,
) -> bool:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT 1
                FROM life_companies
                WHERE id = :company_id
                  AND owner_character_id = :character_id
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
# TRÉSORERIE
# ============================================================

async def get_company_treasury(
    company_id: int,
) -> int:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT treasury
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        value = result.scalar()

        return int(value or 0)


async def deposit_to_company(
    company_id: int,
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    amount = int(amount)

    if amount <= 0:
        return {
            "success": False,
            "message": "❌ Le montant doit être supérieur à 0.",
        }

    async with AsyncSessionLocal() as session:

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
                "character_id": int(character_id),
            },
        )

        character = character_result.mappings().first()

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
                "message": "❌ Solde personnel insuffisant.",
            }

        company_result = await session.execute(
            text(
                """
                SELECT treasury
                FROM life_companies
                WHERE id = :company_id
                FOR UPDATE
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = company_result.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        old_treasury = int(
            company["treasury"] or 0
        )

        new_treasury = (
            old_treasury + amount
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET balance = balance - :amount,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "amount": amount,
                "character_id": int(character_id),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_companies
                SET treasury = :treasury,
                    updated_at = NOW()
                WHERE id = :company_id
                """
            ),
            {
                "treasury": new_treasury,
                "company_id": int(company_id),
            },
        )

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
                    'deposit',
                    :amount,
                    :balance_after,
                    'Dépôt dans la trésorerie'
                )
                """
            ),
            {
                "company_id": int(company_id),
                "character_id": int(character_id),
                "amount": amount,
                "balance_after": new_treasury,
            },
        )

        await session.commit()

    return {
        "success": True,
        "amount": amount,
        "treasury": new_treasury,
        "message": (
            "💰 DÉPÔT EFFECTUÉ\n"
            f"💵 Montant : {format_money(amount)} FCFA\n"
            f"🏦 Trésorerie : "
            f"{format_money(new_treasury)} FCFA"
        ),
    }


async def withdraw_from_company(
    company_id: int,
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    amount = int(amount)

    if amount <= 0:
        return {
            "success": False,
            "message": "❌ Le montant doit être supérieur à 0.",
        }

    async with AsyncSessionLocal() as session:

        company_result = await session.execute(
            text(
                """
                SELECT
                    treasury,
                    owner_character_id
                FROM life_companies
                WHERE id = :company_id
                FOR UPDATE
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = company_result.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        if int(company["owner_character_id"]) != int(
            character_id
        ):
            return {
                "success": False,
                "message": "❌ Seul le propriétaire peut retirer de l'argent.",
            }

        treasury = int(
            company["treasury"] or 0
        )

        if treasury < amount:
            return {
                "success": False,
                "message": "❌ Trésorerie insuffisante.",
            }

        new_treasury = (
            treasury - amount
        )

        await session.execute(
            text(
                """
                UPDATE life_companies
                SET treasury = :treasury,
                    updated_at = NOW()
                WHERE id = :company_id
                """
            ),
            {
                "treasury": new_treasury,
                "company_id": int(company_id),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET balance = balance + :amount,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "amount": amount,
                "character_id": int(character_id),
            },
        )

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
                    'withdrawal',
                    :amount,
                    :balance_after,
                    'Retrait de trésorerie'
                )
                """
            ),
            {
                "company_id": int(company_id),
                "character_id": int(character_id),
                "amount": -amount,
                "balance_after": new_treasury,
            },
        )

        await session.commit()

    return {
        "success": True,
        "amount": amount,
        "treasury": new_treasury,
        "message": (
            "💸 RETRAIT EFFECTUÉ\n"
            f"💵 Montant : {format_money(amount)} FCFA\n"
            f"🏦 Trésorerie : "
            f"{format_money(new_treasury)} FCFA"
        ),
    }


# ============================================================
# MEMBRES
# ============================================================

async def get_company_members(
    company_id: int,
    active_only: bool = True,
) -> list[dict[str, Any]]:

    condition = (
        "AND m.status = 'active'"
        if active_only
        else ""
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                f"""
                SELECT
                    m.*,
                    c.username,
                    c.first_name,
                    c.last_name
                FROM life_company_members m
                INNER JOIN life_characters c
                    ON c.id = m.character_id
                WHERE m.company_id = :company_id
                {condition}
                ORDER BY m.joined_at ASC
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


async def get_company_member(
    company_id: int,
    character_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    m.*,
                    c.username,
                    c.first_name,
                    c.last_name
                FROM life_company_members m
                INNER JOIN life_characters c
                    ON c.id = m.character_id
                WHERE m.company_id = :company_id
                  AND m.character_id = :character_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
                "character_id": int(character_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# EMPLOYÉ RÉEL
# ============================================================

async def hire_character(
    company_id: int,
    character_id: int,
    target_character_id: int,
    grade: str = DEFAULT_GRADE,
    salary: int = 0,
) -> dict[str, Any]:

    grade = clean_text(
        grade,
        DEFAULT_GRADE,
    ).lower()

    if grade not in COMPANY_GRADES:
        grade = DEFAULT_GRADE

    salary = max(
        0,
        int(salary),
    )

    async with AsyncSessionLocal() as session:

        company = await session.execute(
            text(
                """
                SELECT owner_character_id, status
                FROM life_companies
                WHERE id = :company_id
                FOR UPDATE
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = company.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        if int(company["owner_character_id"]) != int(
            character_id
        ):
            return {
                "success": False,
                "message": "❌ Tu n'es pas propriétaire de cette entreprise.",
            }

        if company["status"] != COMPANY_STATUS_ACTIVE:
            return {
                "success": False,
                "message": "❌ Cette entreprise est fermée.",
            }

        target = await session.execute(
            text(
                """
                SELECT id
                FROM life_characters
                WHERE id = :character_id
                LIMIT 1
                """
            ),
            {
                "character_id": int(target_character_id),
            },
        )

        if target.first() is None:
            return {
                "success": False,
                "message": "❌ Personnage à recruter introuvable.",
            }

        existing = await session.execute(
            text(
                """
                SELECT id
                FROM life_company_members
                WHERE company_id = :company_id
                  AND character_id = :character_id
                  AND status = 'active'
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
                "character_id": int(target_character_id),
            },
        )

        if existing.first() is not None:
            return {
                "success": False,
                "message": "❌ Ce joueur est déjà membre.",
            }

        await session.execute(
            text(
                """
                INSERT INTO life_company_members (
                    company_id,
                    character_id,
                    grade,
                    salary,
                    status
                )
                VALUES (
                    :company_id,
                    :character_id,
                    :grade,
                    :salary,
                    'active'
                )
                """
            ),
            {
                "company_id": int(company_id),
                "character_id": int(target_character_id),
                "grade": grade,
                "salary": salary,
            },
        )

        await session.commit()

    return {
        "success": True,
        "message": (
            "👤 EMPLOYÉ RECRUTÉ\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 Grade : {grade}\n"
            f"💰 Salaire : {format_money(salary)} FCFA"
        ),
    }


# ============================================================
# EMPLOYÉS VIRTUELS
# ============================================================

async def add_virtual_employee(
    company_id: int,
    character_id: int,
    name: str,
    grade: str = DEFAULT_GRADE,
    salary: int = 0,
) -> dict[str, Any]:

    name = clean_text(
        name,
        max_length=100,
    )

    grade = clean_text(
        grade,
        DEFAULT_GRADE,
    ).lower()

    salary = max(
        0,
        int(salary),
    )

    if not name:
        return {
            "success": False,
            "message": "❌ Nom de l'employé obligatoire.",
        }

    async with AsyncSessionLocal() as session:

        company = await session.execute(
            text(
                """
                SELECT owner_character_id
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = company.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        if int(company["owner_character_id"]) != int(
            character_id
        ):
            return {
                "success": False,
                "message": "❌ Tu n'es pas propriétaire.",
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_virtual_employees (
                    company_id,
                    name,
                    grade,
                    salary,
                    status
                )
                VALUES (
                    :company_id,
                    :name,
                    :grade,
                    :salary,
                    'active'
                )
                RETURNING id
                """
            ),
            {
                "company_id": int(company_id),
                "name": name,
                "grade": grade,
                "salary": salary,
            },
        )

        employee_id = int(
            result.scalar_one()
        )

        await session.commit()

    return {
        "success": True,
        "employee_id": employee_id,
        "message": (
            "🤖 EMPLOYÉ VIRTUEL AJOUTÉ\n"
            f"👤 {name}\n"
            f"💼 Grade : {grade}\n"
            f"💰 Salaire : {format_money(salary)} FCFA"
        ),
    }


# ============================================================
# POSTES
# ============================================================

async def create_position(
    company_id: int,
    character_id: int,
    title: str,
    description: str = "",
    salary: int = 0,
    slots: int = 1,
) -> dict[str, Any]:

    title = clean_text(
        title,
        max_length=100,
    )

    description = clean_text(
        description,
        max_length=1000,
    )

    salary = max(
        0,
        int(salary),
    )

    slots = max(
        1,
        int(slots),
    )

    if not title:
        return {
            "success": False,
            "message": "❌ Titre du poste obligatoire.",
        }

    async with AsyncSessionLocal() as session:

        company = await session.execute(
            text(
                """
                SELECT owner_character_id
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = company.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        if int(company["owner_character_id"]) != int(
            character_id
        ):
            return {
                "success": False,
                "message": "❌ Tu n'es pas propriétaire.",
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_positions (
                    company_id,
                    title,
                    description,
                    salary,
                    slots,
                    status
                )
                VALUES (
                    :company_id,
                    :title,
                    :description,
                    :salary,
                    :slots,
                    'open'
                )
                RETURNING id
                """
            ),
            {
                "company_id": int(company_id),
                "title": title,
                "description": description,
                "salary": salary,
                "slots": slots,
            },
        )

        position_id = int(
            result.scalar_one()
        )

        await session.commit()

    return {
        "success": True,
        "position_id": position_id,
        "message": (
            "💼 POSTE CRÉÉ\n"
            f"🏷️ {title}\n"
            f"💰 Salaire : {format_money(salary)} FCFA\n"
            f"👥 Places : {slots}"
        ),
    }


# ============================================================
# ACTIONNAIRES
# ============================================================

async def add_shareholder(
    company_id: int,
    owner_character_id: int,
    shareholder_character_id: int,
    shares: int,
) -> dict[str, Any]:

    shares = int(shares)

    if shares <= 0:
        return {
            "success": False,
            "message": "❌ Nombre d'actions invalide.",
        }

    async with AsyncSessionLocal() as session:

        company = await session.execute(
            text(
                """
                SELECT owner_character_id
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = company.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        if int(company["owner_character_id"]) != int(
            owner_character_id
        ):
            return {
                "success": False,
                "message": "❌ Seul le propriétaire peut gérer les actionnaires.",
            }

        target = await session.execute(
            text(
                """
                SELECT id
                FROM life_characters
                WHERE id = :character_id
                LIMIT 1
                """
            ),
            {
                "character_id": int(
                    shareholder_character_id
                ),
            },
        )

        if target.first() is None:
            return {
                "success": False,
                "message": "❌ Actionnaire introuvable.",
            }

        existing = await session.execute(
            text(
                """
                SELECT id, shares
                FROM life_company_shareholders
                WHERE company_id = :company_id
                  AND character_id = :character_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
                "character_id": int(
                    shareholder_character_id
                ),
            },
        )

        row = existing.mappings().first()

        if row:

            await session.execute(
                text(
                    """
                    UPDATE life_company_shareholders
                    SET shares = shares + :shares
                    WHERE id = :id
                    """
                ),
                {
                    "shares": shares,
                    "id": int(row["id"]),
                },
            )

        else:

            await session.execute(
                text(
                    """
                    INSERT INTO life_company_shareholders (
                        company_id,
                        character_id,
                        shares
                    )
                    VALUES (
                        :company_id,
                        :character_id,
                        :shares
                    )
                    """
                ),
                {
                    "company_id": int(company_id),
                    "character_id": int(
                        shareholder_character_id
                    ),
                    "shares": shares,
                },
            )

        await session.commit()

    return {
        "success": True,
        "shares": shares,
        "message": (
            "📈 ACTIONNAIRE AJOUTÉ\n"
            f"📊 Actions : {shares}"
        ),
    }


async def get_shareholders(
    company_id: int,
) -> list[dict[str, Any]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    s.*,
                    c.username,
                    c.first_name,
                    c.last_name
                FROM life_company_shareholders s
                INNER JOIN life_characters c
                    ON c.id = s.character_id
                WHERE s.company_id = :company_id
                ORDER BY s.shares DESC
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
# STATISTIQUES
# ============================================================

async def update_company_stats(
    company_id: int,
    reputation_delta: int = 0,
    credibility_delta: int = 0,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT reputation, credibility
                FROM life_companies
                WHERE id = :company_id
                FOR UPDATE
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = result.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        reputation = max(
            0,
            min(
                100,
                int(company["reputation"] or 0)
                + int(reputation_delta),
            ),
        )

        credibility = max(
            0,
            min(
                100,
                int(company["credibility"] or 0)
                + int(credibility_delta),
            ),
        )

        await session.execute(
            text(
                """
                UPDATE life_companies
                SET reputation = :reputation,
                    credibility = :credibility,
                    updated_at = NOW()
                WHERE id = :company_id
                """
            ),
            {
                "reputation": reputation,
                "credibility": credibility,
                "company_id": int(company_id),
            },
        )

        await session.commit()

    return {
        "success": True,
        "reputation": reputation,
        "credibility": credibility,
    }


# ============================================================
# OFFRES D'EMPLOI
# ============================================================

async def create_job_ad(
    company_id: int,
    character_id: int,
    title: str,
    description: str = "",
    salary: int = 0,
) -> dict[str, Any]:

    title = clean_text(
        title,
        max_length=100,
    )

    description = clean_text(
        description,
        max_length=2000,
    )

    salary = max(
        0,
        int(salary),
    )

    async with AsyncSessionLocal() as session:

        company = await session.execute(
            text(
                """
                SELECT owner_character_id
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {
                "company_id": int(company_id),
            },
        )

        company = company.mappings().first()

        if company is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        if int(company["owner_character_id"]) != int(
            character_id
        ):
            return {
                "success": False,
                "message": "❌ Tu n'es pas propriétaire.",
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_job_ads (
                    company_id,
                    title,
                    description,
                    salary,
                    status
                )
                VALUES (
                    :company_id,
                    :title,
                    :description,
                    :salary,
                    'open'
                )
                RETURNING id
                """
            ),
            {
                "company_id": int(company_id),
                "title": title,
                "description": description,
                "salary": salary,
            },
        )

        job_id = int(
            result.scalar_one()
        )

        await session.commit()

    return {
        "success": True,
        "job_id": job_id,
        "message": (
            "📢 OFFRE PUBLIÉE\n"
            f"💼 {title}\n"
            f"💰 Salaire : {format_money(salary)} FCFA"
        ),
    }


async def get_job_ads(
    company_id: int,
    open_only: bool = True,
) -> list[dict[str, Any]]:

    condition = (
        "AND status = 'open'"
        if open_only
        else ""
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                f"""
                SELECT *
                FROM life_company_job_ads
                WHERE company_id = :company_id
                {condition}
                ORDER BY created_at DESC
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
# CANDIDATURES
# ============================================================

async def apply_to_job(
    job_id: int,
    character_id: int,
    message: str = "",
) -> dict[str, Any]:

    message = clean_text(
        message,
        max_length=2000,
    )

    async with AsyncSessionLocal() as session:

        job = await session.execute(
            text(
                """
                SELECT id, company_id, status
                FROM life_company_job_ads
                WHERE id = :job_id
                LIMIT 1
                """
            ),
            {
                "job_id": int(job_id),
            },
        )

        job = job.mappings().first()

        if job is None:
            return {
                "success": False,
                "message": "❌ Offre introuvable.",
            }

        if job["status"] != "open":
            return {
                "success": False,
                "message": "❌ Cette offre n'est plus ouverte.",
            }

        existing = await session.execute(
            text(
                """
                SELECT id
                FROM life_company_job_applications
                WHERE job_id = :job_id
                  AND character_id = :character_id
                LIMIT 1
                """
            ),
            {
                "job_id": int(job_id),
                "character_id": int(character_id),
            },
        )

        if existing.first() is not None:
            return {
                "success": False,
                "message": "❌ Tu as déjà candidaté à cette offre.",
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_job_applications (
                    job_id,
                    character_id,
                    message,
                    status
                )
                VALUES (
                    :job_id,
                    :character_id,
                    :message,
                    'pending'
                )
                RETURNING id
                """
            ),
            {
                "job_id": int(job_id),
                "character_id": int(character_id),
                "message": message,
            },
        )

        application_id = int(
            result.scalar_one()
        )

        await session.commit()

    return {
        "success": True,
        "application_id": application_id,
        "message": (
            "📨 CANDIDATURE ENVOYÉE\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⏳ Statut : En attente"
        ),
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_company(
    company: dict[str, Any],
) -> str:

    return (
        "🏢━━━━━━━━━━━━━━━━━━━━🏢\n"
        f"       {company.get('name', 'Entreprise')}\n"
        "🏢━━━━━━━━━━━━━━━━━━━━🏢\n\n"
        f"📂 Type : "
        f"{company.get('company_type', 'general')}\n"
        f"📊 Statut : "
        f"{company.get('status', 'unknown')}\n\n"
        f"💰 Trésorerie : "
        f"{format_money(company.get('treasury', 0))} FCFA\n"
        f"⭐ Réputation : "
        f"{company.get('reputation', 0)}/100\n"
        f"🛡️ Crédibilité : "
        f"{company.get('credibility', 0)}/100"
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "COMPANY_GRADES",
    "get_grade_info",
    "grade_level",
    "format_money",
    "format_company",
    "create_company",
    "get_company",
    "get_company_by_name",
    "get_character_companies",
    "is_company_owner",
    "get_company_treasury",
    "deposit_to_company",
    "withdraw_from_company",
    "get_company_members",
    "get_company_member",
    "hire_character",
    "add_virtual_employee",
    "create_position",
    "add_shareholder",
    "get_shareholders",
    "update_company_stats",
    "create_job_ad",
    "get_job_ads",
    "apply_to_job",
]