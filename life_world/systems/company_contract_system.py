"""
Manu World — Company Contract System

Contrats, missions et commissions des entreprises.

Utilise les tables déjà prévues dans life_world/database.py :
- life_company_contracts
- life_company_tasks
- life_company_commissions
- life_company_members
- life_companies

Fonctions :
- créer un contrat ;
- accepter un contrat ;
- générer des tâches ;
- assigner une tâche à un employé ;
- terminer une tâche avec un score ;
- mettre à jour la préparation ;
- terminer un contrat ;
- créer des commissions ;
- consulter contrats, tâches et commissions.

IMPORTANT :
main.py n'est PAS modifié ici.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONFIGURATION
# ============================================================

DIFFICULTY = {
    "easy": {
        "label": "🟢 Facile",
        "preparation_required": 40,
        "base_reward": 100_000,
    },
    "medium": {
        "label": "🟡 Moyenne",
        "preparation_required": 60,
        "base_reward": 500_000,
    },
    "hard": {
        "label": "🔴 Difficile",
        "preparation_required": 75,
        "base_reward": 2_000_000,
    },
    "expert": {
        "label": "🟣 Expert",
        "preparation_required": 90,
        "base_reward": 10_000_000,
    },
}


def normalize_difficulty(
    difficulty: str,
) -> str:

    difficulty = str(
        difficulty
    ).strip().lower()

    aliases = {
        "easy": "easy",
        "facile": "easy",
        "medium": "medium",
        "moyenne": "medium",
        "normal": "medium",
        "hard": "hard",
        "difficile": "hard",
        "expert": "expert",
    }

    if difficulty not in aliases:
        raise ValueError(
            "Difficulté de contrat inconnue."
        )

    return aliases[difficulty]


# ============================================================
# CRÉER UN CONTRAT
# ============================================================

async def create_contract(
    company_id: int,
    title: str,
    client_name: str,
    difficulty: str,
    reward: Optional[int] = None,
    total_orders: int = 1,
    deadline_hours: int = 72,
) -> dict:

    title = str(title).strip()[:160]
    client_name = str(client_name).strip()[:120]
    difficulty = normalize_difficulty(difficulty)

    total_orders = max(
        1,
        int(total_orders),
    )

    deadline_hours = max(
        1,
        int(deadline_hours),
    )

    if not title or not client_name:
        return {
            "success": False,
            "message": (
                "❌ Titre et client sont obligatoires."
            ),
        }

    config = DIFFICULTY[difficulty]

    if reward is None:
        reward = (
            config["base_reward"]
            * total_orders
        )

    reward = max(
        0,
        int(reward),
    )

    async with AsyncSessionLocal() as session:

        company = await session.execute(
            text(
                """
                SELECT id, active
                FROM life_companies
                WHERE id = :company_id
                LIMIT 1
                """
            ),
            {"company_id": company_id},
        )

        if company.mappings().first() is None:
            return {
                "success": False,
                "message": "❌ Entreprise introuvable.",
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_contracts (
                    company_id,
                    title,
                    client_name,
                    difficulty,
                    reward,
                    total_orders,
                    virtual_orders,
                    real_orders,
                    completed_orders,
                    preparation_score,
                    status,
                    reminder_count,
                    deadline_at
                )
                VALUES (
                    :company_id,
                    :title,
                    :client_name,
                    :difficulty,
                    :reward,
                    :total_orders,
                    0,
                    0,
                    0,
                    0,
                    'offered',
                    0,
                    NOW() + (
                        :deadline_hours * INTERVAL '1 hour'
                    )
                )
                RETURNING id
                """
            ),
            {
                "company_id": company_id,
                "title": title,
                "client_name": client_name,
                "difficulty": difficulty,
                "reward": reward,
                "total_orders": total_orders,
                "deadline_hours": deadline_hours,
            },
        )

        contract_id = result.scalar_one()

        await session.commit()

    return {
        "success": True,
        "contract_id": contract_id,
        "message": (
            f"📑 <b>CONTRAT PROPOSÉ</b>\n"
            f"📌 {title}\n"
            f"🏢 Client : {client_name}\n"
            f"🎯 Difficulté : {config['label']}\n"
            f"📦 Commandes : {total_orders}\n"
            f"💰 Récompense : {reward:,} FCFA"
        ),
    }


# ============================================================
# RÉCUPÉRER UN CONTRAT
# ============================================================

async def get_contract(
    contract_id: int,
) -> Optional[dict]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_company_contracts
                WHERE id = :contract_id
                LIMIT 1
                """
            ),
            {"contract_id": contract_id},
        )

        row = result.mappings().first()

    return dict(row) if row else None


# ============================================================
# ACCEPTER UN CONTRAT
# ============================================================

async def accept_contract(
    contract_id: int,
) -> dict:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_company_contracts
                WHERE id = :contract_id
                FOR UPDATE
                """
            ),
            {"contract_id": contract_id},
        )

        contract = result.mappings().first()

        if contract is None:
            return {
                "success": False,
                "message": "❌ Contrat introuvable.",
            }

        if contract["status"] != "offered":
            return {
                "success": False,
                "message": (
                    "❌ Ce contrat n'est plus disponible."
                ),
            }

        difficulty = normalize_difficulty(
            contract["difficulty"]
        )

        await session.execute(
            text(
                """
                UPDATE life_company_contracts
                SET status = 'active',
                    accepted_at = NOW()
                WHERE id = :contract_id
                """
            ),
            {"contract_id": contract_id},
        )

        await session.commit()

    return {
        "success": True,
        "contract_id": contract_id,
        "difficulty": difficulty,
        "message": (
            "✅ Contrat accepté.\n"
            "📋 Les missions peuvent maintenant "
            "être préparées."
        ),
    }


# ============================================================
# GÉNÉRER UNE TÂCHE
# ============================================================

async def create_task(
    contract_id: int,
    task_type: str,
    title: str,
    difficulty: Optional[str] = None,
) -> dict:

    title = str(title).strip()[:160]
    task_type = str(task_type).strip()[:60]

    if not title or not task_type:
        return {
            "success": False,
            "message": "❌ Tâche invalide.",
        }

    async with AsyncSessionLocal() as session:

        contract_result = await session.execute(
            text(
                """
                SELECT difficulty, status
                FROM life_company_contracts
                WHERE id = :contract_id
                LIMIT 1
                """
            ),
            {"contract_id": contract_id},
        )

        contract = contract_result.mappings().first()

        if contract is None:
            return {
                "success": False,
                "message": "❌ Contrat introuvable.",
            }

        if contract["status"] not in {
            "offered",
            "active",
        }:
            return {
                "success": False,
                "message": (
                    "❌ Ce contrat ne peut plus recevoir "
                    "de mission."
                ),
            }

        if difficulty is None:
            difficulty = contract["difficulty"]
        else:
            difficulty = normalize_difficulty(
                difficulty
            )

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_tasks (
                    contract_id,
                    task_type,
                    title,
                    difficulty,
                    status
                )
                VALUES (
                    :contract_id,
                    :task_type,
                    :title,
                    :difficulty,
                    'pending'
                )
                RETURNING id
                """
            ),
            {
                "contract_id": contract_id,
                "task_type": task_type,
                "title": title,
                "difficulty": difficulty,
            },
        )

        task_id = result.scalar_one()

        await session.commit()

    return {
        "success": True,
        "task_id": task_id,
        "message": (
            f"📝 Mission créée : <b>{title}</b>"
        ),
    }


# ============================================================
# ASSIGNER UNE TÂCHE
# ============================================================

async def assign_task(
    task_id: int,
    member_id: int,
) -> dict:

    async with AsyncSessionLocal() as session:

        task_result = await session.execute(
            text(
                """
                SELECT
                    t.id,
                    t.contract_id,
                    t.status,
                    m.company_id,
                    m.status AS member_status
                FROM life_company_tasks t
                JOIN life_company_members m
                    ON m.id = :member_id
                JOIN life_company_contracts c
                    ON c.id = t.contract_id
                WHERE t.id = :task_id
                LIMIT 1
                """
            ),
            {
                "task_id": task_id,
                "member_id": member_id,
            },
        )

        row = task_result.mappings().first()

        if row is None:
            return {
                "success": False,
                "message": (
                    "❌ Mission ou employé introuvable."
                ),
            }

        if row["status"] != "pending":
            return {
                "success": False,
                "message": (
                    "❌ Cette mission n'est plus disponible."
                ),
            }

        if row["member_status"] != "active":
            return {
                "success": False,
                "message": (
                    "❌ Cet employé n'est plus actif."
                ),
            }

        # Vérifier que l'employé appartient bien
        # à la société du contrat.
        company_result = await session.execute(
            text(
                """
                SELECT company_id
                FROM life_company_tasks t
                JOIN life_company_contracts c
                    ON c.id = t.contract_id
                WHERE t.id = :task_id
                """
            ),
            {"task_id": task_id},
        )

        company_id = company_result.scalar_one()

        if int(company_id) != int(row["company_id"]):
            return {
                "success": False,
                "message": (
                    "❌ Cet employé n'appartient pas "
                    "à cette entreprise."
                ),
            }

        await session.execute(
            text(
                """
                UPDATE life_company_tasks
                SET
                    assigned_member_id = :member_id,
                    status = 'assigned'
                WHERE id = :task_id
                """
            ),
            {
                "member_id": member_id,
                "task_id": task_id,
            },
        )

        await session.commit()

    return {
        "success": True,
        "message": (
            "👔 Mission assignée à l'employé."
        ),
    }


# ============================================================
# TERMINER UNE TÂCHE
# ============================================================

async def complete_task(
    task_id: int,
    result_score: int,
) -> dict:

    result_score = max(
        0,
        min(100, int(result_score)),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    t.*,
                    c.company_id,
                    c.difficulty AS contract_difficulty,
                    c.total_orders,
                    c.completed_orders
                FROM life_company_tasks t
                JOIN life_company_contracts c
                    ON c.id = t.contract_id
                WHERE t.id = :task_id
                FOR UPDATE
                """
            ),
            {"task_id": task_id},
        )

        task = result.mappings().first()

        if task is None:
            return {
                "success": False,
                "message": "❌ Mission introuvable.",
            }

        if task["status"] == "completed":
            return {
                "success": False,
                "message": (
                    "❌ Cette mission est déjà terminée."
                ),
            }

        await session.execute(
            text(
                """
                UPDATE life_company_tasks
                SET
                    status = 'completed',
                    result_score = :score,
                    completed_at = NOW()
                WHERE id = :task_id
                """
            ),
            {
                "score": result_score,
                "task_id": task_id,
            },
        )

        # Une mission réussie contribue à la préparation.
        preparation_gain = max(
            1,
            result_score // 10,
        )

        await session.execute(
            text(
                """
                UPDATE life_company_contracts
                SET
                    preparation_score = LEAST(
                        100,
                        preparation_score + :gain
                    )
                WHERE id = :contract_id
                """
            ),
            {
                "gain": preparation_gain,
                "contract_id": task["contract_id"],
            },
        )

        await session.commit()

    return {
        "success": True,
        "score": result_score,
        "preparation_gain": preparation_gain,
        "message": (
            f"✅ Mission terminée avec "
            f"<b>{result_score}/100</b>.\n"
            f"📈 Préparation +{preparation_gain}."
        ),
    }


# ============================================================
# PRÉPARATION DU CONTRAT
# ============================================================

async def get_preparation(
    contract_id: int,
) -> dict:

    contract = await get_contract(
        contract_id
    )

    if contract is None:
        return {
            "success": False,
            "message": "❌ Contrat introuvable.",
        }

    difficulty = normalize_difficulty(
        contract["difficulty"]
    )

    required = DIFFICULTY[
        difficulty
    ]["preparation_required"]

    score = int(
        contract["preparation_score"]
    )

    return {
        "success": True,
        "score": score,
        "required": required,
        "ready": score >= required,
        "difficulty": difficulty,
    }


# ============================================================
# TERMINER LE CONTRAT
# ============================================================

async def complete_contract(
    contract_id: int,
) -> dict:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_company_contracts
                WHERE id = :contract_id
                FOR UPDATE
                """
            ),
            {"contract_id": contract_id},
        )

        contract = result.mappings().first()

        if contract is None:
            return {
                "success": False,
                "message": "❌ Contrat introuvable.",
            }

        difficulty = normalize_difficulty(
            contract["difficulty"]
        )

        required = DIFFICULTY[
            difficulty
        ]["preparation_required"]

        if contract["status"] != "active":
            return {
                "success": False,
                "message": (
                    "❌ Le contrat n'est pas actif."
                ),
            }

        if int(
            contract["preparation_score"]
        ) < required:
            return {
                "success": False,
                "message": (
                    f"❌ Préparation insuffisante.\n"
                    f"📈 Actuelle : "
                    f"{contract['preparation_score']}/100\n"
                    f"🎯 Requise : {required}/100"
                ),
            }

        if int(
            contract["completed_orders"]
        ) < int(
            contract["total_orders"]
        ):
            return {
                "success": False,
                "message": (
                    "❌ Toutes les commandes du contrat "
                    "ne sont pas terminées."
                ),
            }

        await session.execute(
            text(
                """
                UPDATE life_company_contracts
                SET
                    status = 'completed',
                    completed_at = NOW()
                WHERE id = :contract_id
                """
            ),
            {"contract_id": contract_id},
        )

        # Le revenu du contrat rejoint la société.
        await session.execute(
            text(
                """
                UPDATE life_companies
                SET
                    treasury = treasury + :reward,
                    total_revenue = total_revenue + :reward,
                    reputation = LEAST(100, reputation + 2),
                    credibility = LEAST(100, credibility + 2),
                    updated_at = NOW()
                WHERE id = :company_id
                """
            ),
            {
                "reward": int(contract["reward"]),
                "company_id": contract["company_id"],
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
                SELECT
                    c.company_id,
                    c.owner_character_id,
                    'contract_revenue',
                    :reward,
                    c.treasury,
                    :description
                FROM life_companies c
                WHERE c.id = :company_id
                """
            ),
            {
                "reward": int(contract["reward"]),
                "company_id": contract["company_id"],
                "description": (
                    f"Contrat #{contract_id} terminé"
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "reward": int(contract["reward"]),
        "message": (
            "🏆 <b>CONTRAT TERMINÉ</b>\n"
            f"💰 Revenu : "
            f"{int(contract['reward']):,} FCFA\n"
            "⭐ Réputation +2\n"
            "🔐 Crédibilité +2"
        ),
    }


# ============================================================
# COMMANDES
# ============================================================

async def increment_completed_orders(
    contract_id: int,
    virtual: bool = False,
) -> dict:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    completed_orders,
                    total_orders
                FROM life_company_contracts
                WHERE id = :contract_id
                FOR UPDATE
                """
            ),
            {"contract_id": contract_id},
        )

        contract = result.mappings().first()

        if contract is None:
            return {
                "success": False,
                "message": "❌ Contrat introuvable.",
            }

        if int(
            contract["completed_orders"]
        ) >= int(
            contract["total_orders"]
        ):
            return {
                "success": False,
                "message": (
                    "❌ Toutes les commandes sont déjà terminées."
                ),
            }

        if virtual:
            column = "virtual_orders"
        else:
            column = "real_orders"

        await session.execute(
            text(
                f"""
                UPDATE life_company_contracts
                SET
                    completed_orders =
                        completed_orders + 1,
                    {column} =
                        {column} + 1
                WHERE id = :contract_id
                """
            ),
            {"contract_id": contract_id},
        )

        await session.commit()

    return {
        "success": True,
        "message": (
            "📦 Commande enregistrée."
        ),
    }


# ============================================================
# COMMISSION
# ============================================================

async def create_commission(
    company_id: int,
    contract_id: Optional[int],
    member_id: Optional[int],
    character_id: Optional[int],
    amount: int,
) -> dict:

    amount = max(
        0,
        int(amount),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                INSERT INTO life_company_commissions (
                    company_id,
                    contract_id,
                    member_id,
                    character_id,
                    amount,
                    status
                )
                VALUES (
                    :company_id,
                    :contract_id,
                    :member_id,
                    :character_id,
                    :amount,
                    'pending'
                )
                RETURNING id
                """
            ),
            {
                "company_id": company_id,
                "contract_id": contract_id,
                "member_id": member_id,
                "character_id": character_id,
                "amount": amount,
            },
        )

        commission_id = result.scalar_one()

        await session.commit()

    return {
        "success": True,
        "commission_id": commission_id,
        "message": (
            f"💰 Commission de "
            f"{amount:,} FCFA créée."
        ),
    }


async def get_pending_commissions(
    company_id: int,
) -> list[dict]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_company_commissions
                WHERE company_id = :company_id
                  AND status = 'pending'
                ORDER BY created_at ASC
                """
            ),
            {"company_id": company_id},
        )

        rows = result.mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# LISTES
# ============================================================

async def get_company_contracts(
    company_id: int,
) -> list[dict]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_company_contracts
                WHERE company_id = :company_id
                ORDER BY created_at DESC
                """
            ),
            {"company_id": company_id},
        )

        rows = result.mappings().all()

    return [dict(row) for row in rows]


async def get_contract_tasks(
    contract_id: int,
) -> list[dict]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    t.*,
                    m.position,
                    m.virtual_name
                FROM life_company_tasks t
                LEFT JOIN life_company_members m
                    ON m.id = t.assigned_member_id
                WHERE t.contract_id = :contract_id
                ORDER BY t.created_at ASC
                """
            ),
            {"contract_id": contract_id},
        )

        rows = result.mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# FORMATAGE
# ============================================================

async def format_contract(
    contract_id: int,
) -> str:

    contract = await get_contract(
        contract_id
    )

    if contract is None:
        return "❌ Contrat introuvable."

    difficulty = normalize_difficulty(
        contract["difficulty"]
    )

    config = DIFFICULTY[difficulty]

    return (
        "📑 <b>CONTRAT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 {contract['title']}\n"
        f"🏢 Client : {contract['client_name']}\n"
        f"🎯 Difficulté : {config['label']}\n"
        f"📊 Préparation : "
        f"{contract['preparation_score']}/100\n"
        f"📦 Commandes : "
        f"{contract['completed_orders']}/"
        f"{contract['total_orders']}\n"
        f"💰 Récompense : "
        f"{int(contract['reward']):,} FCFA\n"
        f"📍 Statut : {contract['status']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "DIFFICULTY",
    "create_contract",
    "get_contract",
    "accept_contract",
    "create_task",
    "assign_task",
    "complete_task",
    "get_preparation",
    "complete_contract",
    "increment_completed_orders",
    "create_commission",
    "get_pending_commissions",
    "get_company_contracts",
    "get_contract_tasks",
    "format_contract",
]
