"""
Life World — Family Tree

Gestion de l'affichage de l'arbre généalogique.

Relations :
- parents
- enfants
- conjoint(e)
- frères / sœurs

Les joueurs sont manipulés par @username.

IMPORTANT :
- aucune commande Telegram n'est enregistrée ici ;
- main.py sera raccordé à la fin ;
- ce module lit les relations déjà enregistrées
  dans family_relationships.py.
"""

from __future__ import annotations

from typing import Optional

try:
    from .family_relationships import (
        get_family_tree,
        get_parents,
        get_children,
        get_siblings,
        get_spouse,
        normalize_username,
    )
except ImportError:
    from family_relationships import (
        get_family_tree,
        get_parents,
        get_children,
        get_siblings,
        get_spouse,
        normalize_username,
    )


# ============================================================
# STRUCTURE
# ============================================================

def build_family_tree(
    username: str,
) -> dict:

    username = normalize_username(username)

    parents = get_parents(username)
    children = get_children(username)
    siblings = get_siblings(username)
    spouse = get_spouse(username)

    return {
        "username": username,
        "parents": parents,
        "siblings": siblings,
        "spouse": spouse,
        "children": children,
    }


# ============================================================
# NOEUD
# ============================================================

def make_person_node(
    username: str,
    relation: str,
) -> dict:

    return {
        "username": normalize_username(username),
        "relation": relation,
    }


# ============================================================
# ARBRE COMPLET
# ============================================================

def get_tree_data(
    username: str,
) -> dict:

    tree = build_family_tree(username)

    return {
        "self": make_person_node(
            tree["username"],
            "self",
        ),

        "parents": [
            make_person_node(
                parent,
                "parent",
            )
            for parent in tree["parents"]
        ],

        "siblings": [
            make_person_node(
                sibling,
                "sibling",
            )
            for sibling in tree["siblings"]
        ],

        "spouse": (
            make_person_node(
                tree["spouse"],
                "spouse",
            )
            if tree["spouse"]
            else None
        ),

        "children": [
            make_person_node(
                child,
                "child",
            )
            for child in tree["children"]
        ],
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_family_tree(
    username: str,
) -> str:

    tree = get_tree_data(username)

    lines = [
        "🌳 <b>ARBRE GÉNÉALOGIQUE</b>",
        "",
        "━━━━━━━━━━━━━━━━━━",
    ]

    # --------------------------------------------------------
    # PARENTS
    # --------------------------------------------------------

    if tree["parents"]:

        lines.append(
            "👨‍👩‍👦 <b>PARENTS</b>"
        )

        for parent in tree["parents"]:
            lines.append(
                f"   └── 👤 @{parent['username']}"
            )

        lines.append("")

    # --------------------------------------------------------
    # FRÈRES / SŒURS
    # --------------------------------------------------------

    if tree["siblings"]:

        lines.append(
            "🧑‍🤝‍🧑 <b>FRÈRES / SŒURS</b>"
        )

        for sibling in tree["siblings"]:
            lines.append(
                f"   └── 👤 @{sibling['username']}"
            )

        lines.append("")

    # --------------------------------------------------------
    # PERSONNE
    # --------------------------------------------------------

    lines.append(
        "👤 <b>TOI</b>"
    )

    lines.append(
        f"   └── @{tree['self']['username']}"
    )

    lines.append("")

    # --------------------------------------------------------
    # CONJOINT
    # --------------------------------------------------------

    if tree["spouse"]:

        lines.append(
            "💍 <b>CONJOINT(E)</b>"
        )

        lines.append(
            f"   └── 💑 @{tree['spouse']['username']}"
        )

        lines.append("")

    # --------------------------------------------------------
    # ENFANTS
    # --------------------------------------------------------

    if tree["children"]:

        lines.append(
            "👶 <b>ENFANTS</b>"
        )

        for child in tree["children"]:
            lines.append(
                f"   └── 👶 @{child['username']}"
            )

        lines.append("")

    lines.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    if (
        not tree["parents"]
        and not tree["siblings"]
        and not tree["spouse"]
        and not tree["children"]
    ):
        lines.append(
            "🌱 Aucun lien familial enregistré."
        )

    return "\n".join(lines)


# ============================================================
# VÉRIFICATION D'UNE RELATION
# ============================================================

def relationship_between(
    user_one: str,
    user_two: str,
) -> Optional[str]:

    user_one = normalize_username(user_one)
    user_two = normalize_username(user_two)

    if user_one == user_two:
        return "self"

    if user_two in get_parents(user_one):
        return "parent"

    if user_two in get_children(user_one):
        return "child"

    if user_two in get_siblings(user_one):
        return "sibling"

    if get_spouse(user_one) == user_two:
        return "spouse"

    return None


# ============================================================
# TEXTE DE RELATION
# ============================================================

RELATION_LABELS = {
    "self": "👤 Toi-même",
    "parent": "👨‍👩‍👦 Parent",
    "child": "👶 Enfant",
    "sibling": "🧑‍🤝‍🧑 Frère / Sœur",
    "spouse": "💍 Conjoint(e)",
}


def format_relationship(
    user_one: str,
    user_two: str,
) -> str:

    relation = relationship_between(
        user_one,
        user_two,
    )

    if relation is None:
        return (
            f"🔎 Aucun lien familial direct "
            f"entre @{normalize_username(user_one)} "
            f"et @{normalize_username(user_two)}."
        )

    label = RELATION_LABELS.get(
        relation,
        relation,
    )

    return (
        f"🔎 <b>RELATION</b>\n\n"
        f"👤 @{normalize_username(user_one)}\n"
        f"↕️ {label}\n"
        f"👤 @{normalize_username(user_two)}"
    )


# ============================================================
# CIBLE
# ============================================================

def resolve_tree_target(
    username: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> Optional[str]:

    if username:
        return normalize_username(username)

    if replied_username:
        return normalize_username(
            replied_username
        )

    return None


# ============================================================
# MESSAGE D'AIDE
# ============================================================

def family_tree_help() -> str:

    return (
        "🌳 <b>ARBRE GÉNÉALOGIQUE</b>\n\n"

        "Affiche ta famille avec :\n"
        "👨‍👩‍👦 Parents\n"
        "🧑‍🤝‍🧑 Frères / sœurs\n"
        "💍 Conjoint(e)\n"
        "👶 Enfants\n\n"

        "Exemple :\n"
        "<code>/familytree</code>\n\n"

        "Pour regarder l'arbre d'un autre joueur :\n"
        "<code>/familytree @username</code>\n\n"

        "Tu peux également répondre à son message "
        "puis utiliser la commande."
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "build_family_tree",
    "get_tree_data",
    "format_family_tree",
    "relationship_between",
    "format_relationship",
    "resolve_tree_target",
    "family_tree_help",
]