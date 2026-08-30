"""
MANUWORLD — SKILLS SYSTEM

Gestion des compétences des personnages.

Gère :
    - création automatique d'une compétence
    - consultation
    - ajout d'XP
    - progression de niveau
    - suppression
    - classement
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONFIGURATION
# ============================================================

BASE_XP = 100
XP_INCREMENT = 50
MAX_SKILL_LEVEL = 100


# ============================================================
# UTILITAIRES
# ============================================================

def normalize_skill_name(
    skill_name: str,
) -> str:

    skill_name = str(
        skill_name or ""
    ).strip()

    if not skill_name:
        raise ValueError(
            "Le nom de la compétence est obligatoire."
        )

    if len(skill_name) > 80:
        raise ValueError(
            "Le nom de la compétence est trop long."
        )

    return skill_name


def xp_required(
    level: int,
) -> int:

    level = max(
        1,
        int(level),
    )

    return BASE_XP + (
        (level - 1) * XP_INCREMENT
    )


def progress_bar(
    current: int,
    required: int,
    size: int = 10,
) -> str:

    if required <= 0:
        return "█" * size

    ratio = min(
        1.0,
        max(
            0.0,
            current / required,
        ),
    )

    filled = int(
        ratio * size
    )

    return (
        "█" * filled
        + "░" * (size - filled)
    )


# ============================================================
# CRÉATION / RÉCUPÉRATION
# ============================================================

async def get_skill(
    character_id: int,
    skill_name: str,
) -> dict[str, Any] | None:

    skill_name = normalize_skill_name(
        skill_name
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_skills
                WHERE character_id = :character_id
                  AND LOWER(skill_name) = LOWER(:skill_name)
                LIMIT 1
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
                "skill_name": skill_name,
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


async def create_skill(
    character_id: int,
    skill_name: str,
) -> dict[str, Any]:

    skill_name = normalize_skill_name(
        skill_name
    )

    existing = await get_skill(
        character_id,
        skill_name,
    )

    if existing:

        return {
            "success": True,
            "created": False,
            "skill": existing,
        }

    async with AsyncSessionLocal() as session:

        character = await session.execute(
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
                    character_id
                ),
            },
        )

        if character.first() is None:

            return {
                "success": False,
                "message": "❌ Personnage introuvable.",
            }

        result = await session.execute(
            text(
                """
                INSERT INTO life_skills (
                    character_id,
                    skill_name,
                    level,
                    experience
                )
                VALUES (
                    :character_id,
                    :skill_name,
                    1,
                    0
                )
                RETURNING *
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
                "skill_name": skill_name,
            },
        )

        skill = dict(
            result.mappings().one()
        )

        await session.commit()

    return {
        "success": True,
        "created": True,
        "skill": skill,
    }


# ============================================================
# LISTE
# ============================================================

async def get_character_skills(
    character_id: int,
) -> list[dict[str, Any]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_skills
                WHERE character_id = :character_id
                ORDER BY level DESC,
                         experience DESC,
                         skill_name ASC
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
# AJOUT D'XP
# ============================================================

async def add_skill_experience(
    character_id: int,
    skill_name: str,
    amount: int,
) -> dict[str, Any]:

    skill_name = normalize_skill_name(
        skill_name
    )

    amount = max(
        0,
        int(amount),
    )

    if amount <= 0:

        return {
            "success": False,
            "message": "❌ L'XP doit être supérieure à 0.",
        }

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_skills
                WHERE character_id = :character_id
                  AND LOWER(skill_name) = LOWER(:skill_name)
                FOR UPDATE
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
                "skill_name": skill_name,
            },
        )

        skill = result.mappings().first()

        if skill is None:

            await session.execute(
                text(
                    """
                    INSERT INTO life_skills (
                        character_id,
                        skill_name,
                        level,
                        experience
                    )
                    VALUES (
                        :character_id,
                        :skill_name,
                        1,
                        0
                    )
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                    "skill_name": skill_name,
                },
            )

            level = 1
            experience = 0

        else:

            level = int(
                skill["level"] or 1
            )

            experience = int(
                skill["experience"] or 0
            )

        experience += amount

        levels_gained = 0

        while (
            level < MAX_SKILL_LEVEL
            and experience >= xp_required(level)
        ):

            experience -= xp_required(
                level
            )

            level += 1

            levels_gained += 1

        if level >= MAX_SKILL_LEVEL:

            experience = min(
                experience,
                xp_required(
                    MAX_SKILL_LEVEL
                ) - 1,
            )

        await session.execute(
            text(
                """
                UPDATE life_skills
                SET level = :level,
                    experience = :experience
                WHERE character_id = :character_id
                  AND LOWER(skill_name) = LOWER(:skill_name)
                """
            ),
            {
                "level": level,
                "experience": experience,
                "character_id": int(
                    character_id
                ),
                "skill_name": skill_name,
            },
        )

        await session.commit()

    return {
        "success": True,
        "skill_name": skill_name,
        "level": level,
        "experience": experience,
        "levels_gained": levels_gained,
        "message": (
            f"🎯 {skill_name}\n"
            f"⭐ Niveau : {level}\n"
            f"✨ XP : {experience}/"
            f"{xp_required(level)}"
        ),
    }


# ============================================================
# NIVEAU
# ============================================================

async def set_skill_level(
    character_id: int,
    skill_name: str,
    level: int,
) -> dict[str, Any]:

    skill_name = normalize_skill_name(
        skill_name
    )

    level = max(
        1,
        min(
            MAX_SKILL_LEVEL,
            int(level),
        ),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                UPDATE life_skills
                SET level = :level,
                    experience = 0
                WHERE character_id = :character_id
                  AND LOWER(skill_name) = LOWER(:skill_name)
                RETURNING *
                """
            ),
            {
                "level": level,
                "character_id": int(
                    character_id
                ),
                "skill_name": skill_name,
            },
        )

        row = result.mappings().first()

        if row is None:

            await session.execute(
                text(
                    """
                    INSERT INTO life_skills (
                        character_id,
                        skill_name,
                        level,
                        experience
                    )
                    VALUES (
                        :character_id,
                        :skill_name,
                        :level,
                        0
                    )
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                    "skill_name": skill_name,
                    "level": level,
                },
            )

        await session.commit()

    return {
        "success": True,
        "level": level,
        "message": (
            f"🎯 {skill_name} est maintenant "
            f"au niveau {level}."
        ),
    }


# ============================================================
# SUPPRESSION
# ============================================================

async def delete_skill(
    character_id: int,
    skill_name: str,
) -> dict[str, Any]:

    skill_name = normalize_skill_name(
        skill_name
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                DELETE FROM life_skills
                WHERE character_id = :character_id
                  AND LOWER(skill_name) = LOWER(:skill_name)
                RETURNING skill_name
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
                "skill_name": skill_name,
            },
        )

        row = result.first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Compétence introuvable.",
            }

        await session.commit()

    return {
        "success": True,
        "message": (
            f"🗑️ Compétence supprimée : "
            f"{row[0]}"
        ),
    }


# ============================================================
# CLASSEMENT
# ============================================================

async def get_skill_leaderboard(
    skill_name: str,
    limit: int = 10,
) -> list[dict[str, Any]]:

    skill_name = normalize_skill_name(
        skill_name
    )

    limit = max(
        1,
        min(
            100,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    s.*,
                    c.username,
                    c.first_name,
                    c.last_name
                FROM life_skills s
                INNER JOIN life_characters c
                    ON c.id = s.character_id
                WHERE LOWER(s.skill_name)
                    = LOWER(:skill_name)
                ORDER BY s.level DESC,
                         s.experience DESC
                LIMIT :limit
                """
            ),
            {
                "skill_name": skill_name,
                "limit": limit,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# FORMATAGE
# ============================================================

def format_skill(
    skill: dict[str, Any],
) -> str:

    level = int(
        skill.get("level") or 1
    )

    experience = int(
        skill.get("experience") or 0
    )

    required = xp_required(
        level
    )

    return (
        f"🎯 **{skill.get('skill_name', 'Compétence')}**\n"
        f"⭐ Niveau : **{level}**\n"
        f"✨ XP : **{experience}/{required}**\n"
        f"{progress_bar(experience, required)}"
    )


def format_skills(
    skills: list[dict[str, Any]],
) -> str:

    if not skills:

        return (
            "🎯 **COMPÉTENCES**\n\n"
            "Aucune compétence enregistrée."
        )

    lines = [
        "🎯 **COMPÉTENCES**",
        "",
    ]

    for skill in skills:

        level = int(
            skill.get("level") or 1
        )

        experience = int(
            skill.get("experience") or 0
        )

        required = xp_required(
            level
        )

        lines.extend(
            [
                f"🎯 **{skill['skill_name']}**",
                f"⭐ Niveau : **{level}**",
                f"✨ XP : **{experience}/{required}**",
                progress_bar(
                    experience,
                    required,
                ),
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "BASE_XP",
    "XP_INCREMENT",
    "MAX_SKILL_LEVEL",
    "normalize_skill_name",
    "xp_required",
    "progress_bar",
    "get_skill",
    "create_skill",
    "get_character_skills",
    "add_skill_experience",
    "set_skill_level",
    "delete_skill",
    "get_skill_leaderboard",
    "format_skill",
    "format_skills",
]