"""
MANUWORLD — HEALTH SYSTEM

Gestion de la santé du personnage :
    - santé
    - énergie
    - faim
    - soif
    - récupération
    - dégâts
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from life_world.database import AsyncSessionLocal


# ============================================================
# CONSTANTES
# ============================================================

MAX_HEALTH = 100
MAX_ENERGY = 100
MAX_HUNGER = 100
MAX_THIRST = 100

DEFAULT_HEALTH = 100
DEFAULT_ENERGY = 100
DEFAULT_HUNGER = 100
DEFAULT_THIRST = 100


# ============================================================
# UTILITAIRES
# ============================================================

def clamp(
    value: int,
    minimum: int,
    maximum: int,
) -> int:

    return max(
        minimum,
        min(
            maximum,
            int(value),
        ),
    )


# ============================================================
# ÉTAT DU PERSONNAGE
# ============================================================

async def get_health_status(
    character_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    username,
                    health,
                    energy,
                    hunger,
                    thirst
                FROM life_characters
                WHERE id = :character_id
                LIMIT 1
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        row = result.mappings().first()

        if row is None:
            return None

        return dict(row)


# ============================================================
# INITIALISATION
# ============================================================

async def initialize_health(
    character_id: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                UPDATE life_characters
                SET
                    health = COALESCE(health, :health),
                    energy = COALESCE(energy, :energy),
                    hunger = COALESCE(hunger, :hunger),
                    thirst = COALESCE(thirst, :thirst),
                    updated_at = NOW()
                WHERE id = :character_id
                RETURNING
                    id,
                    health,
                    energy,
                    hunger,
                    thirst
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
                "health": DEFAULT_HEALTH,
                "energy": DEFAULT_ENERGY,
                "hunger": DEFAULT_HUNGER,
                "thirst": DEFAULT_THIRST,
            },
        )

        row = result.mappings().first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        await session.commit()

    return {
        "success": True,
        **dict(row),
    }


# ============================================================
# MODIFICATION DE SANTÉ
# ============================================================

async def change_health(
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT health
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

        row = result.mappings().first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        old_health = int(
            row["health"] or 0
        )

        new_health = clamp(
            old_health + int(amount),
            0,
            MAX_HEALTH,
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET health = :health,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "health": new_health,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "old_health": old_health,
        "health": new_health,
        "change": int(amount),
    }


# ============================================================
# DÉGÂTS
# ============================================================

async def damage_character(
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    amount = max(
        0,
        int(amount),
    )

    if amount <= 0:

        return {
            "success": False,
            "message": "❌ Les dégâts doivent être supérieurs à 0.",
        }

    result = await change_health(
        character_id,
        -amount,
    )

    if not result["success"]:
        return result

    health = int(
        result["health"]
    )

    return {
        **result,
        "knocked_out": health <= 0,
        "message": (
            f"❤️ Santé : {health}/{MAX_HEALTH}"
        ),
    }


# ============================================================
# SOINS
# ============================================================

async def heal_character(
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    amount = max(
        0,
        int(amount),
    )

    if amount <= 0:

        return {
            "success": False,
            "message": "❌ Les soins doivent être supérieurs à 0.",
        }

    result = await change_health(
        character_id,
        amount,
    )

    if not result["success"]:
        return result

    return {
        **result,
        "message": (
            f"❤️ Santé : "
            f"{result['health']}/{MAX_HEALTH}"
        ),
    }


# ============================================================
# ÉNERGIE
# ============================================================

async def change_energy(
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT energy
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

        row = result.mappings().first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        old_energy = int(
            row["energy"] or 0
        )

        new_energy = clamp(
            old_energy + int(amount),
            0,
            MAX_ENERGY,
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET energy = :energy,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "energy": new_energy,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "old_energy": old_energy,
        "energy": new_energy,
        "change": int(amount),
    }


# ============================================================
# FAIM
# ============================================================

async def change_hunger(
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT hunger
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

        row = result.mappings().first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        old_hunger = int(
            row["hunger"] or 0
        )

        new_hunger = clamp(
            old_hunger + int(amount),
            0,
            MAX_HUNGER,
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET hunger = :hunger,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "hunger": new_hunger,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "old_hunger": old_hunger,
        "hunger": new_hunger,
        "change": int(amount),
    }


# ============================================================
# SOIF
# ============================================================

async def change_thirst(
    character_id: int,
    amount: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT thirst
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

        row = result.mappings().first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        old_thirst = int(
            row["thirst"] or 0
        )

        new_thirst = clamp(
            old_thirst + int(amount),
            0,
            MAX_THIRST,
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET thirst = :thirst,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "thirst": new_thirst,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "old_thirst": old_thirst,
        "thirst": new_thirst,
        "change": int(amount),
    }


# ============================================================
# RÉCUPÉRATION
# ============================================================

async def recover_character(
    character_id: int,
    health: int = 0,
    energy: int = 0,
    hunger: int = 0,
    thirst: int = 0,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    health,
                    energy,
                    hunger,
                    thirst
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

        row = result.mappings().first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        new_health = clamp(
            int(row["health"] or 0) + int(health),
            0,
            MAX_HEALTH,
        )

        new_energy = clamp(
            int(row["energy"] or 0) + int(energy),
            0,
            MAX_ENERGY,
        )

        new_hunger = clamp(
            int(row["hunger"] or 0) + int(hunger),
            0,
            MAX_HUNGER,
        )

        new_thirst = clamp(
            int(row["thirst"] or 0) + int(thirst),
            0,
            MAX_THIRST,
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET
                    health = :health,
                    energy = :energy,
                    hunger = :hunger,
                    thirst = :thirst,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "health": new_health,
                "energy": new_energy,
                "hunger": new_hunger,
                "thirst": new_thirst,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "health": new_health,
        "energy": new_energy,
        "hunger": new_hunger,
        "thirst": new_thirst,
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_health_status(
    status: dict[str, Any],
) -> str:

    health = int(
        status.get("health") or 0
    )

    energy = int(
        status.get("energy") or 0
    )

    hunger = int(
        status.get("hunger") or 0
    )

    thirst = int(
        status.get("thirst") or 0
    )

    return (
        "❤️ **SANTÉ**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❤️ Santé : **{health}/{MAX_HEALTH}**\n"
        f"⚡ Énergie : **{energy}/{MAX_ENERGY}**\n"
        f"🍗 Faim : **{hunger}/{MAX_HUNGER}**\n"
        f"💧 Soif : **{thirst}/{MAX_THIRST}**"
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "MAX_HEALTH",
    "MAX_ENERGY",
    "MAX_HUNGER",
    "MAX_THIRST",
    "DEFAULT_HEALTH",
    "DEFAULT_ENERGY",
    "DEFAULT_HUNGER",
    "DEFAULT_THIRST",
    "clamp",
    "get_health_status",
    "initialize_health",
    "change_health",
    "damage_character",
    "heal_character",
    "change_energy",
    "change_hunger",
    "change_thirst",
    "recover_character",
    "format_health_status",
]