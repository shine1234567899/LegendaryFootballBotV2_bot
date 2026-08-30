"""
Life World — Family Commands

Prépare les commandes familiales :

/familytree
/familytree @username
/family @username
/spouse
/parents
/children
/siblings

La cible peut être :
    - @username
    - une réponse à un message

IMPORTANT :
Ce fichier prépare uniquement la logique des commandes.
Les handlers Telegram seront enregistrés dans main.py à la fin.
"""

from __future__ import annotations

from typing import Optional


try:
    from ..systems.family_tree import (
        format_family_tree,
        get_tree_data,
        resolve_tree_target,
    )

    from ..systems.family_relationships import (
        get_spouse,
        get_parents,
        get_children,
        get_siblings,
    )

except ImportError:

    from systems.family_tree import (
        format_family_tree,
        get_tree_data,
        resolve_tree_target,
    )

    from systems.family_relationships import (
        get_spouse,
        get_parents,
        get_children,
        get_siblings,
    )


# ============================================================
# CIBLE
# ============================================================

def resolve_family_target(
    username: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> Optional[str]:
    """
    Résout la cible d'une commande.

    Priorité :
        1. @username fourni directement
        2. username du message auquel on répond
    """

    return resolve_tree_target(
        username=username,
        replied_username=replied_username,
    )


# ============================================================
# ARBRE GÉNÉALOGIQUE
# ============================================================

def family_tree_command(
    requester: str,
    target: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    resolved = resolve_family_target(
        username=target,
        replied_username=replied_username,
    )

    if not resolved:
        resolved = requester

    message = format_family_tree(
        resolved
    )

    return {
        "success": True,
        "target": resolved,
        "message": message,
    }


# ============================================================
# CONJOINT
# ============================================================

def spouse_command(
    requester: str,
    target: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    resolved = resolve_family_target(
        username=target,
        replied_username=replied_username,
    )

    if not resolved:
        resolved = requester

    spouse = get_spouse(
        resolved
    )

    if spouse is None:

        return {
            "success": True,
            "target": resolved,
            "spouse": None,
            "message": (
                f"💍 @{resolved} "
                "n'est actuellement pas marié."
            ),
        }

    return {
        "success": True,
        "target": resolved,
        "spouse": spouse,
        "message": (
            f"💍 @{resolved} est marié à "
            f"@{spouse}."
        ),
    }


# ============================================================
# PARENTS
# ============================================================

def parents_command(
    requester: str,
    target: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    resolved = resolve_family_target(
        username=target,
        replied_username=replied_username,
    )

    if not resolved:
        resolved = requester

    parents = get_parents(
        resolved
    )

    if not parents:

        return {
            "success": True,
            "target": resolved,
            "parents": [],
            "message": (
                f"👨‍👩‍👦 @{resolved} "
                "n'a aucun parent enregistré."
            ),
        }

    lines = [
        f"👨‍👩‍👦 <b>PARENTS DE @{resolved}</b>",
        "",
    ]

    for parent in parents:
        lines.append(
            f"👤 @{parent}"
        )

    return {
        "success": True,
        "target": resolved,
        "parents": parents,
        "message": "\n".join(lines),
    }


# ============================================================
# ENFANTS
# ============================================================

def children_command(
    requester: str,
    target: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    resolved = resolve_family_target(
        username=target,
        replied_username=replied_username,
    )

    if not resolved:
        resolved = requester

    children = get_children(
        resolved
    )

    if not children:

        return {
            "success": True,
            "target": resolved,
            "children": [],
            "message": (
                f"👶 @{resolved} "
                "n'a aucun enfant enregistré."
            ),
        }

    lines = [
        f"👶 <b>ENFANTS DE @{resolved}</b>",
        "",
    ]

    for child in children:
        lines.append(
            f"👤 @{child}"
        )

    return {
        "success": True,
        "target": resolved,
        "children": children,
        "message": "\n".join(lines),
    }


# ============================================================
# FRÈRES / SŒURS
# ============================================================

def siblings_command(
    requester: str,
    target: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    resolved = resolve_family_target(
        username=target,
        replied_username=replied_username,
    )

    if not resolved:
        resolved = requester

    siblings = get_siblings(
        resolved
    )

    if not siblings:

        return {
            "success": True,
            "target": resolved,
            "siblings": [],
            "message": (
                f"🧑‍🤝‍🧑 @{resolved} "
                "n'a aucun frère ou sœur enregistré."
            ),
        }

    lines = [
        f"🧑‍🤝‍🧑 <b>FRÈRES / SŒURS DE @{resolved}</b>",
        "",
    ]

    for sibling in siblings:
        lines.append(
            f"👤 @{sibling}"
        )

    return {
        "success": True,
        "target": resolved,
        "siblings": siblings,
        "message": "\n".join(lines),
    }


# ============================================================
# RÉSUMÉ FAMILIAL
# ============================================================

def family_command(
    requester: str,
    target: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    resolved = resolve_family_target(
        username=target,
        replied_username=replied_username,
    )

    if not resolved:
        resolved = requester

    tree = get_tree_data(
        resolved
    )

    return {
        "success": True,
        "target": resolved,
        "family": tree,
        "message": format_family_tree(
            resolved
        ),
    }


# ============================================================
# BOUTONS
# ============================================================

def family_menu_buttons() -> list[list[tuple[str, str]]]:

    return [
        [
            (
                "lw_family:tree",
                "🌳 Arbre généalogique",
            ),
        ],
        [
            (
                "lw_family:parents",
                "👨‍👩‍👦 Parents",
            ),
            (
                "lw_family:children",
                "👶 Enfants",
            ),
        ],
        [
            (
                "lw_family:siblings",
                "🧑‍🤝‍🧑 Frères / Sœurs",
            ),
            (
                "lw_family:spouse",
                "💍 Conjoint(e)",
            ),
        ],
    ]


# ============================================================
# CALLBACKS
# ============================================================

def parse_family_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 2:
        raise ValueError(
            "Callback familial invalide."
        )

    if parts[0] != "lw_family":
        raise ValueError(
            "Callback familial inconnu."
        )

    action = parts[1]

    allowed = {
        "tree",
        "parents",
        "children",
        "siblings",
        "spouse",
    }

    if action not in allowed:
        raise ValueError(
            f"Action familiale inconnue : {action}"
        )

    return {
        "type": "family",
        "action": action,
    }


# ============================================================
# AIDE
# ============================================================

def family_help() -> str:

    return (
        "🌳 <b>SYSTÈME FAMILIAL</b>\n\n"

        "🌳 <code>/familytree</code>\n"
        "Voir ton arbre généalogique.\n\n"

        "🌳 <code>/familytree @username</code>\n"
        "Voir celui d'un autre joueur.\n\n"

        "💍 <code>/spouse</code>\n"
        "Voir ton conjoint.\n\n"

        "👨‍👩‍👦 <code>/parents</code>\n"
        "Voir tes parents.\n\n"

        "👶 <code>/children</code>\n"
        "Voir tes enfants.\n\n"

        "🧑‍🤝‍🧑 <code>/siblings</code>\n"
        "Voir tes frères et sœurs.\n\n"

        "↩️ Les commandes peuvent également "
        "utiliser une réponse à un message."
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "resolve_family_target",
    "family_tree_command",
    "family_command",
    "spouse_command",
    "parents_command",
    "children_command",
    "siblings_command",
    "family_menu_buttons",
    "parse_family_callback",
    "family_help",
]