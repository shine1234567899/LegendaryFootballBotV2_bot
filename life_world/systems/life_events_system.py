"""
MANUWORLD — LIFE EVENTS SYSTEM

Gestion des événements de vie du personnage.

Gère :
    - création d'événements
    - récupération de l'historique
    - événements récents
    - récompenses XP
    - variation financière
    - formatage
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONSTANTES
# ============================================================

DEFAULT_EVENT_TYPE = "life"
DEFAULT_XP_REWARD = 0
DEFAULT_MONEY_CHANGE = 0


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
# CRÉER UN ÉVÉNEMENT
# ============================================================

async def create_life_event(
    character_id: int,
    event_type: str,
    title: str,
    description: str = "",
    experience_reward: int = 0,
    money_change: int = 0,
    event_data: dict[str, Any] | None = None,
) -> dict[str, Any]:

    character_id = int(character_id)

    event_type = clean_text(
        event_type,
        DEFAULT_EVENT_TYPE,
        50,
    )

    title = clean_text(
        title,
        max_length=160,
    )

    description = clean_text(
        description,
        "",
        5000,
    )

    experience_reward = max(
        0,
        int(experience_reward),
    )

    money_change = int(
        money_change
    )

    event_data = (
        event_data
        if isinstance(event_data, dict)
        else {}
    )

    if not title:

        return {
            "success": False,
            "message": "❌ Le titre de l'événement est obligatoire.",
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
                "character_id": character_id,
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
                INSERT INTO life_events (
                    character_id,
                    event_type,
                    title,
                    description,
                    experience_reward,
                    money_change,
                    event_data
                )
                VALUES (
                    :character_id,
                    :event_type,
                    :title,
                    :description,
                    :experience_reward,
                    :money_change,
                    CAST(:event_data AS JSONB)
                )
                RETURNING *
                """
            ),
            {
                "character_id": character_id,
                "event_type": event_type,
                "title": title,
                "description": description,
                "experience_reward": experience_reward,
                "money_change": money_change,
                "event_data": __import__(
                    "json"
                ).dumps(
                    event_data,
                    ensure_ascii=False,
                ),
            },
        )

        event = dict(
            result.mappings().one()
        )

        await session.commit()

    return {
        "success": True,
        "event": event,
        "event_id": int(event["id"]),
    }


# ============================================================
# RÉCUPÉRER UN ÉVÉNEMENT
# ============================================================

async def get_life_event(
    event_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_events
                WHERE id = :event_id
                LIMIT 1
                """
            ),
            {
                "event_id": int(event_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# HISTORIQUE
# ============================================================

async def get_life_events(
    character_id: int,
    limit: int = 20,
    event_type: str | None = None,
) -> list[dict[str, Any]]:

    limit = max(
        1,
        min(
            100,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        if event_type:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_events
                    WHERE character_id = :character_id
                      AND event_type = :event_type
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "character_id": int(
                        character_id
                    ),
                    "event_type": clean_text(
                        event_type
                    ),
                    "limit": limit,
                },
            )

        else:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_events
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
# ÉVÉNEMENTS RÉCENTS
# ============================================================

async def get_recent_life_events(
    character_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:

    return await get_life_events(
        character_id=character_id,
        limit=limit,
    )


# ============================================================
# ÉVÉNEMENTS PAR TYPE
# ============================================================

async def get_events_by_type(
    character_id: int,
    event_type: str,
    limit: int = 20,
) -> list[dict[str, Any]]:

    return await get_life_events(
        character_id=character_id,
        limit=limit,
        event_type=event_type,
    )


# ============================================================
# SUPPRESSION
# ============================================================

async def delete_life_event(
    character_id: int,
    event_id: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                DELETE FROM life_events
                WHERE id = :event_id
                  AND character_id = :character_id
                RETURNING id
                """
            ),
            {
                "event_id": int(event_id),
                "character_id": int(character_id),
            },
        )

        row = result.first()

        if row is None:

            return {
                "success": False,
                "message": "❌ Événement introuvable.",
            }

        await session.commit()

    return {
        "success": True,
        "event_id": int(row[0]),
        "message": "✅ Événement supprimé.",
    }


# ============================================================
# STATISTIQUES
# ============================================================

async def get_event_statistics(
    character_id: int,
) -> dict[str, Any]:

    async with AsyncSessionLocal() as session:

        count_result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_events,
                    COALESCE(
                        SUM(experience_reward),
                        0
                    ) AS total_xp,
                    COALESCE(
                        SUM(money_change),
                        0
                    ) AS total_money
                FROM life_events
                WHERE character_id = :character_id
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        stats = dict(
            count_result.mappings().one()
        )

        type_result = await session.execute(
            text(
                """
                SELECT
                    event_type,
                    COUNT(*) AS count
                FROM life_events
                WHERE character_id = :character_id
                GROUP BY event_type
                ORDER BY count DESC
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        by_type = [
            dict(row)
            for row in type_result.mappings().all()
        ]

    return {
        "total_events": int(
            stats["total_events"] or 0
        ),
        "total_xp": int(
            stats["total_xp"] or 0
        ),
        "total_money": int(
            stats["total_money"] or 0
        ),
        "by_type": by_type,
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_life_event(
    event: dict[str, Any],
) -> str:

    event_type = event.get(
        "event_type",
        "life",
    )

    title = event.get(
        "title",
        "Événement",
    )

    description = event.get(
        "description"
    )

    xp = int(
        event.get(
            "experience_reward",
            0,
        )
        or 0
    )

    money = int(
        event.get(
            "money_change",
            0,
        )
        or 0
    )

    lines = [
        f"📌 **{title}**",
        f"🏷️ Type : `{event_type}`",
    ]

    if description:

        lines.extend(
            [
                "",
                f"📝 {description}",
            ]
        )

    if xp > 0:

        lines.append(
            f"✨ XP : +{xp}"
        )

    if money != 0:

        sign = "+" if money > 0 else ""

        lines.append(
            f"💰 Argent : "
            f"{sign}{format_money(money)} FCFA"
        )

    created_at = event.get(
        "created_at"
    )

    if created_at:

        lines.append(
            f"🕒 {created_at}"
        )

    return "\n".join(lines)


def format_event_history(
    events: list[dict[str, Any]],
) -> str:

    if not events:

        return (
            "📜 **HISTORIQUE DE VIE**\n\n"
            "Aucun événement enregistré."
        )

    lines = [
        "📜 **HISTORIQUE DE VIE**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for event in events:

        title = event.get(
            "title",
            "Événement",
        )

        event_type = event.get(
            "event_type",
            "life",
        )

        xp = int(
            event.get(
                "experience_reward",
                0,
            )
            or 0
        )

        money = int(
            event.get(
                "money_change",
                0,
            )
            or 0
        )

        line = (
            f"📌 **{title}**\n"
            f"   🏷️ {event_type}"
        )

        if xp:

            line += (
                f" • ✨ +{xp} XP"
            )

        if money:

            sign = "+" if money > 0 else ""

            line += (
                f" • 💰 {sign}"
                f"{format_money(money)}"
            )

        lines.extend(
            [
                line,
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "create_life_event",
    "get_life_event",
    "get_life_events",
    "get_recent_life_events",
    "get_events_by_type",
    "delete_life_event",
    "get_event_statistics",
    "format_life_event",
    "format_event_history",
]