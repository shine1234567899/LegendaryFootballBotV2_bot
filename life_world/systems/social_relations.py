"""
Life World — Social Relations

Moteur commun permettant de déterminer la relation
entre deux joueurs.

Relations possibles :
- ami
- conjoint
- parent
- enfant
- frère / sœur
- aucune relation

Les commandes utilisent les @username.

IMPORTANT :
Ce fichier ne modifie pas main.py.
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
    )
except ImportError:
    from family_relationships import (
        normalize_username,
        get_friends,
        get_parents,
        get_children,
        get_siblings,
        get_spouse,
    )


# ============================================================
# RELATIONS
# ============================================================

RELATION_LABELS = {
    "self": "👤 Toi-même",
    "friend": "🤝 Ami(e)",
    "spouse": "💍 Conjoint(e)",
    "parent": "👨‍👩‍👦 Parent",
    "child": "👶 Enfant",
    "sibling": "🧑‍🤝‍🧑 Frère / Sœur",
    "none": "🌱 Aucune relation",
}


# ============================================================
# NORMALISATION
# ============================================================

def normalize_pair(
    user_one: str,
    user_two: str,
) -> tuple[str, str]:

    return (
        normalize_username(user_one),
        normalize_username(user_two),
    )


# ============================================================
# RELATION DIRECTE
# ============================================================

def get_direct_relationship(
    user_one: str,
    user_two: str,
) -> str:

    user_one, user_two = normalize_pair(
        user_one,
        user_two,
    )

    if user_one == user_two:
        return "self"

    # --------------------------------------------------------
    # CONJOINT
    # --------------------------------------------------------

    spouse = get_spouse(
        user_one
    )

    if spouse == user_two:
        return "spouse"

    # --------------------------------------------------------
    # PARENT
    # --------------------------------------------------------

    if user_two in get_parents(
        user_one
    ):
        return "parent"

    # --------------------------------------------------------
    # ENFANT
    # --------------------------------------------------------

    if user_two in get_children(
        user_one
    ):
        return "child"

    # --------------------------------------------------------
    # FRÈRE / SŒUR
    # --------------------------------------------------------

    if user_two in get_siblings(
        user_one
    ):
        return "sibling"

    # --------------------------------------------------------
    # AMI
    # --------------------------------------------------------

    if user_two in get_friends(
        user_one
    ):
        return "friend"

    return "none"


# ============================================================
# INFORMATIONS
# ============================================================

def relationship_info(
    user_one: str,
    user_two: str,
) -> dict:

    user_one, user_two = normalize_pair(
        user_one,
        user_two,
    )

    relation = get_direct_relationship(
        user_one,
        user_two,
    )

    return {
        "user_one": user_one,
        "user_two": user_two,
        "relation": relation,
        "label": RELATION_LABELS[
            relation
        ],
        "is_family": relation in {
            "spouse",
            "parent",
            "child",
            "sibling",
        },
        "is_friend": relation == "friend",
        "is_married": relation == "spouse",
    }


# ============================================================
# MESSAGE
# ============================================================

def format_relationship(
    user_one: str,
    user_two: str,
) -> str:

    info = relationship_info(
        user_one,
        user_two,
    )

    lines = [
        "🔎 <b>RELATION ENTRE JOUEURS</b>",
        "",
        f"👤 @{info['user_one']}",
        "↕️",
        f"👤 @{info['user_two']}",
        "",
        f"📌 Relation : "
        f"<b>{info['label']}</b>",
    ]

    return "\n".join(lines)


# ============================================================
# LISTE DES RELATIONS
# ============================================================

def get_all_relations(
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

    return {
        "username": username,
        "friends": friends,
        "parents": parents,
        "children": children,
        "siblings": siblings,
        "spouse": spouse,
    }


# ============================================================
# RÉSUMÉ SOCIAL
# ============================================================

def format_social_summary(
    username: str,
) -> str:

    data = get_all_relations(
        username
    )

    lines = [
        "👥 <b>RELATIONS SOCIALES</b>",
        "",
        f"👤 @{data['username']}",
        "",
    ]

    # --------------------------------------------------------
    # AMIS
    # --------------------------------------------------------

    lines.append(
        f"🤝 <b>Amis</b> "
        f"({len(data['friends'])})"
    )

    for friend in data["friends"]:
        lines.append(
            f"   └─ @{friend}"
        )

    if not data["friends"]:
        lines.append(
            "   └─ Aucun"
        )

    lines.append("")

    # --------------------------------------------------------
    # FAMILLE
    # --------------------------------------------------------

    lines.append(
        "👨‍👩‍👦 <b>Famille</b>"
    )

    if data["parents"]:

        for parent in data["parents"]:
            lines.append(
                f"   ├─ 👨‍👩‍👦 @{parent}"
            )

    if data["siblings"]:

        for sibling in data["siblings"]:
            lines.append(
                f"   ├─ 🧑‍🤝‍🧑 @{sibling}"
            )

    if data["spouse"]:

        lines.append(
            f"   ├─ 💍 @{data['spouse']}"
        )

    if data["children"]:

        for child in data["children"]:
            lines.append(
                f"   └─ 👶 @{child}"
            )

    if (
        not data["parents"]
        and not data["siblings"]
        and not data["spouse"]
        and not data["children"]
    ):
        lines.append(
            "   └─ Aucun"
        )

    return "\n".join(lines)


# ============================================================
# VÉRIFICATIONS RAPIDES
# ============================================================

def are_friends(
    user_one: str,
    user_two: str,
) -> bool:

    return (
        get_direct_relationship(
            user_one,
            user_two,
        )
        == "friend"
    )


def are_family(
    user_one: str,
    user_two: str,
) -> bool:

    return get_direct_relationship(
        user_one,
        user_two,
    ) in {
        "spouse",
        "parent",
        "child",
        "sibling",
    }


def are_married(
    user_one: str,
    user_two: str,
) -> bool:

    return (
        get_direct_relationship(
            user_one,
            user_two,
        )
        == "spouse"
    )


# ============================================================
# AUTORISATIONS SOCIALES
# ============================================================

def can_interact_as_family(
    user_one: str,
    user_two: str,
) -> bool:

    return are_family(
        user_one,
        user_two,
    )


def can_interact_as_friends(
    user_one: str,
    user_two: str,
) -> bool:

    return are_friends(
        user_one,
        user_two,
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "RELATION_LABELS",
    "get_direct_relationship",
    "relationship_info",
    "format_relationship",
    "get_all_relations",
    "format_social_summary",
    "are_friends",
    "are_family",
    "are_married",
    "can_interact_as_family",
    "can_interact_as_friends",
]