"""
Life World — Family Profile

Regroupe les informations familiales d'un joueur :

- conjoint(e)
- parents
- enfants
- frères / sœurs
- nombre d'amis
- demandes en attente

Ce module ne crée pas de nouvelles relations.
Il rassemble les systèmes déjà existants.

main.py sera raccordé à la fin.
"""

from __future__ import annotations

try:
    from .family_relationships import (
        normalize_username,
        get_friends,
        get_parents,
        get_children,
        get_siblings,
        get_spouse,
        get_pending_friend_requests,
    )
except ImportError:

    from family_relationships import (
        normalize_username,
        get_friends,
        get_parents,
        get_children,
        get_siblings,
        get_spouse,
        get_pending_friend_requests,
    )


# ============================================================
# PROFIL
# ============================================================

def get_family_profile(
    username: str,
) -> dict:

    username = normalize_username(
        username
    )

    friends = get_friends(
        username
    )

    parents = get_parents(
        username
    )

    children = get_children(
        username
    )

    siblings = get_siblings(
        username
    )

    spouse = get_spouse(
        username
    )

    friend_requests = (
        get_pending_friend_requests(
            username
        )
    )

    return {
        "username": username,

        "spouse": spouse,

        "parents": parents,

        "children": children,

        "siblings": siblings,

        "friends": friends,

        "friend_count": len(
            friends
        ),

        "parent_count": len(
            parents
        ),

        "child_count": len(
            children
        ),

        "sibling_count": len(
            siblings
        ),

        "pending_friend_requests": (
            friend_requests
        ),

        "pending_friend_request_count": (
            len(friend_requests)
        ),
    }


# ============================================================
# STATUT FAMILIAL
# ============================================================

def get_family_status(
    username: str,
) -> str:

    profile = get_family_profile(
        username
    )

    if profile["spouse"]:
        marriage = (
            f"💍 @{profile['spouse']}"
        )
    else:
        marriage = (
            "💔 Célibataire"
        )

    return marriage


# ============================================================
# RÉSUMÉ
# ============================================================

def format_family_profile(
    username: str,
) -> str:

    profile = get_family_profile(
        username
    )

    lines = [
        "👨‍👩‍👦 <b>PROFIL FAMILIAL</b>",
        "",
        f"👤 <b>@{profile['username']}</b>",
        "",
        f"💍 Statut : "
        f"{get_family_status(username)}",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"👨‍👩‍👦 Parents : "
        f"<b>{profile['parent_count']}</b>",
        f"👶 Enfants : "
        f"<b>{profile['child_count']}</b>",
        f"🧑‍🤝‍🧑 Frères / Sœurs : "
        f"<b>{profile['sibling_count']}</b>",
        f"🤝 Amis : "
        f"<b>{profile['friend_count']}</b>",
        "",
        "━━━━━━━━━━━━━━━━━━",
    ]

    return "\n".join(lines)


# ============================================================
# DÉTAILS
# ============================================================

def format_family_details(
    username: str,
) -> str:

    profile = get_family_profile(
        username
    )

    lines = [
        "👨‍👩‍👦 <b>DÉTAILS FAMILIAUX</b>",
        "",
        f"👤 @{profile['username']}",
        "",
    ]

    # --------------------------------------------------------
    # PARENTS
    # --------------------------------------------------------

    lines.append(
        "👨‍👩‍👦 <b>Parents</b>"
    )

    if profile["parents"]:

        for parent in profile["parents"]:
            lines.append(
                f"   └─ @{parent}"
            )

    else:

        lines.append(
            "   └─ Aucun"
        )

    lines.append("")

    # --------------------------------------------------------
    # CONJOINT
    # --------------------------------------------------------

    lines.append(
        "💍 <b>Conjoint(e)</b>"
    )

    if profile["spouse"]:

        lines.append(
            f"   └─ @{profile['spouse']}"
        )

    else:

        lines.append(
            "   └─ Aucun"
        )

    lines.append("")

    # --------------------------------------------------------
    # FRÈRES / SŒURS
    # --------------------------------------------------------

    lines.append(
        "🧑‍🤝‍🧑 <b>Frères / Sœurs</b>"
    )

    if profile["siblings"]:

        for sibling in profile["siblings"]:
            lines.append(
                f"   └─ @{sibling}"
            )

    else:

        lines.append(
            "   └─ Aucun"
        )

    lines.append("")

    # --------------------------------------------------------
    # ENFANTS
    # --------------------------------------------------------

    lines.append(
        "👶 <b>Enfants</b>"
    )

    if profile["children"]:

        for child in profile["children"]:
            lines.append(
                f"   └─ @{child}"
            )

    else:

        lines.append(
            "   └─ Aucun"
        )

    lines.append("")

    # --------------------------------------------------------
    # AMIS
    # --------------------------------------------------------

    lines.append(
        "🤝 <b>Amis</b>"
    )

    if profile["friends"]:

        for friend in profile["friends"]:
            lines.append(
                f"   └─ @{friend}"
            )

    else:

        lines.append(
            "   └─ Aucun"
        )

    lines.append("")

    # --------------------------------------------------------
    # DEMANDES
    # --------------------------------------------------------

    if profile[
        "pending_friend_request_count"
    ]:

        lines.append(
            "📨 <b>Demandes d'amitié</b>"
        )

        lines.append(
            f"   └─ "
            f"{profile['pending_friend_request_count']}"
        )

    return "\n".join(lines)


# ============================================================
# CIBLE
# ============================================================

def resolve_family_profile_target(
    requester: str,
    target: str | None = None,
    replied_username: str | None = None,
) -> str:

    if target:

        return normalize_username(
            target
        )

    if replied_username:

        return normalize_username(
            replied_username
        )

    return normalize_username(
        requester
    )


# ============================================================
# CALLBACKS
# ============================================================

def family_profile_buttons() -> list[
    list[tuple[str, str]]
]:

    return [
        [
            (
                "lw_family_profile:details",
                "👨‍👩‍👦 Détails",
            ),
        ],
        [
            (
                "lw_family_profile:tree",
                "🌳 Arbre généalogique",
            ),
        ],
    ]


def parse_family_profile_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 2:
        raise ValueError(
            "Callback profil familial invalide."
        )

    if parts[0] != "lw_family_profile":
        raise ValueError(
            "Callback familial inconnu."
        )

    action = parts[1]

    if action not in {
        "details",
        "tree",
    }:

        raise ValueError(
            "Action inconnue."
        )

    return {
        "type": "family_profile",
        "action": action,
    }


# ============================================================
# AIDE
# ============================================================

def family_profile_help() -> str:

    return (
        "👨‍👩‍👦 <b>PROFIL FAMILIAL</b>\n\n"

        "<code>/family</code>\n"
        "Affiche ton résumé familial.\n\n"

        "<code>/family @username</code>\n"
        "Affiche celui d'un autre joueur.\n\n"

        "↩️ Tu peux également répondre "
        "à son message."
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "get_family_profile",
    "get_family_status",
    "format_family_profile",
    "format_family_details",
    "resolve_family_profile_target",
    "family_profile_buttons",
    "parse_family_profile_callback",
    "family_profile_help",
]