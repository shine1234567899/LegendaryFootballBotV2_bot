"""
Life World — Family Relationships

Gestion des relations familiales et sociales :

- demandes d'amitié ;
- plusieurs demandes simultanées ;
- accepter/refuser ;
- mariage ;
- adoption ;
- parent/enfant ;
- frères/sœurs ;
- conjoint ;
- vérification des relations ;
- recherche par @username ou réponse à un message.

IMPORTANT :
Ce module fonctionne avec les USERNAMES Telegram.
Les IDs Telegram ne sont pas utilisés comme identifiant
public du joueur dans les commandes Life World.

main.py sera raccordé à la fin.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "database" / "life_world.db"


# ============================================================
# CONNEXION
# ============================================================

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================
# TABLES
# ============================================================

def setup_family_database() -> None:

    conn = get_connection()

    # --------------------------------------------------------
    # AMITIÉS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_one TEXT NOT NULL,
            user_two TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'pending',

            requested_by TEXT NOT NULL,

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            accepted_at INTEGER,

            UNIQUE(user_one, user_two)
        )
        """
    )

    # --------------------------------------------------------
    # MARIAGES
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS marriages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            partner_one TEXT NOT NULL UNIQUE,
            partner_two TEXT NOT NULL UNIQUE,

            status TEXT NOT NULL DEFAULT 'active',

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            ended_at INTEGER
        )
        """
    )

    # --------------------------------------------------------
    # ADOPTIONS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS adoptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            parent_username TEXT NOT NULL,
            child_username TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'pending',

            requested_by TEXT NOT NULL,

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            accepted_at INTEGER,

            UNIQUE(parent_username, child_username)
        )
        """
    )

    # --------------------------------------------------------
    # RELATIONS PARENT/ENFANT
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS family_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            parent_username TEXT NOT NULL,
            child_username TEXT NOT NULL,

            relation_type TEXT NOT NULL DEFAULT 'parent',

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            UNIQUE(parent_username, child_username)
        )
        """
    )

    # --------------------------------------------------------
    # INDEX
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_friend_user_one
        ON friendships(user_one)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_friend_user_two
        ON friendships(user_two)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_adoption_parent
        ON adoptions(parent_username)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_adoption_child
        ON adoptions(child_username)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_family_parent
        ON family_relations(parent_username)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_family_child
        ON family_relations(child_username)
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# UTILITAIRES
# ============================================================

def normalize_username(username: str) -> str:
    username = str(username).strip()

    if username.startswith("@"):
        username = username[1:]

    username = username.lower()

    if not username:
        raise ValueError(
            "Username obligatoire."
        )

    return username


def normalize_pair(
    user_one: str,
    user_two: str,
) -> tuple[str, str]:

    user_one = normalize_username(user_one)
    user_two = normalize_username(user_two)

    if user_one == user_two:
        raise ValueError(
            "Un joueur ne peut pas être sa propre relation."
        )

    return tuple(
        sorted(
            [user_one, user_two]
        )
    )


# ============================================================
# AMITIÉ — DEMANDE
# ============================================================

def send_friend_request(
    requester: str,
    target: str,
) -> dict:

    requester = normalize_username(requester)
    target = normalize_username(target)

    if requester == target:
        return {
            "success": False,
            "reason": "self",
            "message": (
                "❌ Tu ne peux pas t'ajouter "
                "toi-même en ami."
            ),
        }

    user_one, user_two = normalize_pair(
        requester,
        target,
    )

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT *
        FROM friendships
        WHERE user_one = ?
          AND user_two = ?
        """,
        (
            user_one,
            user_two,
        ),
    ).fetchone()

    if existing:

        conn.close()

        if existing["status"] == "accepted":
            return {
                "success": False,
                "reason": "already_friends",
                "message": (
                    f"🤝 @{target} est déjà "
                    "ton ami."
                ),
            }

        if existing["status"] == "pending":
            return {
                "success": False,
                "reason": "pending",
                "message": (
                    "⏳ Une demande d'amitié "
                    "est déjà en attente."
                ),
            }

    conn.execute(
        """
        INSERT INTO friendships (
            user_one,
            user_two,
            status,
            requested_by
        )
        VALUES (?, ?, 'pending', ?)
        """,
        (
            user_one,
            user_two,
            requester,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "reason": "sent",
        "requester": requester,
        "target": target,
        "message": (
            f"🤝 Demande d'amitié envoyée à "
            f"@{target}."
        ),
    }


# ============================================================
# DEMANDES REÇUES
# ============================================================

def get_pending_friend_requests(
    username: str,
) -> list[dict]:

    username = normalize_username(username)

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM friendships
        WHERE (
            user_one = ?
            OR user_two = ?
        )
        AND status = 'pending'
        AND requested_by != ?
        ORDER BY created_at ASC
        """,
        (
            username,
            username,
            username,
        ),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# DEMANDES ENVOYÉES
# ============================================================

def get_sent_friend_requests(
    username: str,
) -> list[dict]:

    username = normalize_username(username)

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM friendships
        WHERE requested_by = ?
          AND status = 'pending'
        ORDER BY created_at ASC
        """,
        (username,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# ACCEPTER AMITIÉ
# ============================================================

def accept_friend_request(
    username: str,
    requester: str,
) -> dict:

    username = normalize_username(username)
    requester = normalize_username(requester)

    user_one, user_two = normalize_pair(
        username,
        requester,
    )

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM friendships
        WHERE user_one = ?
          AND user_two = ?
          AND status = 'pending'
          AND requested_by = ?
        """,
        (
            user_one,
            user_two,
            requester,
        ),
    ).fetchone()

    if row is None:
        conn.close()

        return {
            "success": False,
            "reason": "not_found",
            "message": (
                "❌ Cette demande n'existe plus."
            ),
        }

    conn.execute(
        """
        UPDATE friendships
        SET
            status = 'accepted',
            accepted_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE id = ?
        """,
        (row["id"],),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            f"🤝 Tu es maintenant ami avec "
            f"@{requester}."
        ),
    }


# ============================================================
# REFUSER
# ============================================================

def decline_friend_request(
    username: str,
    requester: str,
) -> bool:

    username = normalize_username(username)
    requester = normalize_username(requester)

    user_one, user_two = normalize_pair(
        username,
        requester,
    )

    conn = get_connection()

    cursor = conn.execute(
        """
        DELETE FROM friendships
        WHERE user_one = ?
          AND user_two = ?
          AND status = 'pending'
          AND requested_by = ?
        """,
        (
            user_one,
            user_two,
            requester,
        ),
    )

    conn.commit()
    conn.close()

    return cursor.rowcount > 0


# ============================================================
# LISTE DES AMIS
# ============================================================

def get_friends(
    username: str,
) -> list[str]:

    username = normalize_username(username)

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT user_one, user_two
        FROM friendships
        WHERE (
            user_one = ?
            OR user_two = ?
        )
        AND status = 'accepted'
        """,
        (
            username,
            username,
        ),
    ).fetchall()

    conn.close()

    friends = []

    for row in rows:

        if row["user_one"] == username:
            friends.append(
                row["user_two"]
            )
        else:
            friends.append(
                row["user_one"]
            )

    return sorted(
        set(friends)
    )


# ============================================================
# MARIAGE
# ============================================================

def get_spouse(
    username: str,
) -> Optional[str]:

    username = normalize_username(username)

    conn = get_connection()

    row = conn.execute(
        """
        SELECT partner_one, partner_two
        FROM marriages
        WHERE (
            partner_one = ?
            OR partner_two = ?
        )
        AND status = 'active'
        LIMIT 1
        """,
        (
            username,
            username,
        ),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    if row["partner_one"] == username:
        return row["partner_two"]

    return row["partner_one"]


def can_marry(
    user_one: str,
    user_two: str,
) -> tuple[bool, str]:

    user_one = normalize_username(user_one)
    user_two = normalize_username(user_two)

    if user_one == user_two:
        return (
            False,
            "❌ Tu ne peux pas te marier avec toi-même.",
        )

    if get_spouse(user_one):
        return (
            False,
            "❌ Tu es déjà marié.",
        )

    if get_spouse(user_two):
        return (
            False,
            f"❌ @{user_two} est déjà marié.",
        )

    return (
        True,
        "OK",
    )


def create_marriage(
    user_one: str,
    user_two: str,
) -> dict:

    user_one = normalize_username(user_one)
    user_two = normalize_username(user_two)

    allowed, reason = can_marry(
        user_one,
        user_two,
    )

    if not allowed:
        return {
            "success": False,
            "message": reason,
        }

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO marriages (
            partner_one,
            partner_two,
            status
        )
        VALUES (?, ?, 'active')
        """,
        (
            user_one,
            user_two,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            f"💍 @{user_one} et @{user_two} "
            "sont maintenant mariés."
        ),
    }


def divorce(
    username: str,
) -> dict:

    username = normalize_username(username)

    spouse = get_spouse(username)

    if not spouse:
        return {
            "success": False,
            "message": (
                "❌ Tu n'es actuellement pas marié."
            ),
        }

    conn = get_connection()

    conn.execute(
        """
        UPDATE marriages
        SET
            status = 'ended',
            ended_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE (
            partner_one = ?
            OR partner_two = ?
        )
        AND status = 'active'
        """,
        (
            username,
            username,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "spouse": spouse,
        "message": (
            f"💔 Le mariage avec @{spouse} "
            "est terminé."
        ),
    }


# ============================================================
# ADOPTION
# ============================================================

def can_adopt(
    parent: str,
    child: str,
) -> tuple[bool, str]:

    parent = normalize_username(parent)
    child = normalize_username(child)

    if parent == child:
        return (
            False,
            "❌ Tu ne peux pas t'adopter toi-même.",
        )

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT id
        FROM family_relations
        WHERE parent_username = ?
          AND child_username = ?
        LIMIT 1
        """,
        (
            parent,
            child,
        ),
    ).fetchone()

    conn.close()

    if existing:
        return (
            False,
            "❌ Cette relation familiale existe déjà.",
        )

    return (
        True,
        "OK",
    )


def send_adoption_request(
    parent: str,
    child: str,
) -> dict:

    parent = normalize_username(parent)
    child = normalize_username(child)

    allowed, reason = can_adopt(
        parent,
        child,
    )

    if not allowed:
        return {
            "success": False,
            "message": reason,
        }

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT id
        FROM adoptions
        WHERE parent_username = ?
          AND child_username = ?
          AND status = 'pending'
        LIMIT 1
        """,
        (
            parent,
            child,
        ),
    ).fetchone()

    if existing:
        conn.close()

        return {
            "success": False,
            "message": (
                "⏳ Une demande d'adoption "
                "est déjà en attente."
            ),
        }

    conn.execute(
        """
        INSERT INTO adoptions (
            parent_username,
            child_username,
            status,
            requested_by
        )
        VALUES (?, ?, 'pending', ?)
        """,
        (
            parent,
            child,
            "parent",
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            f"👨‍👩‍👦 Demande d'adoption envoyée "
            f"à @{child}."
        ),
    }


# ============================================================
# DEMANDES D'ADOPTION REÇUES
# ============================================================

def get_adoption_requests(
    username: str,
) -> list[dict]:

    username = normalize_username(username)

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM adoptions
        WHERE child_username = ?
          AND status = 'pending'
        ORDER BY created_at ASC
        """,
        (username,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# ACCEPTER ADOPTION
# ============================================================

def accept_adoption(
    child: str,
    parent: str,
) -> dict:

    child = normalize_username(child)
    parent = normalize_username(parent)

    conn = get_connection()

    request = conn.execute(
        """
        SELECT *
        FROM adoptions
        WHERE parent_username = ?
          AND child_username = ?
          AND status = 'pending'
        LIMIT 1
        """,
        (
            parent,
            child,
        ),
    ).fetchone()

    if request is None:
        conn.close()

        return {
            "success": False,
            "message": (
                "❌ Demande d'adoption introuvable."
            ),
        }

    conn.execute(
        """
        UPDATE adoptions
        SET
            status = 'accepted',
            accepted_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE id = ?
        """,
        (request["id"],),
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO family_relations (
            parent_username,
            child_username,
            relation_type
        )
        VALUES (?, ?, 'parent')
        """,
        (
            parent,
            child,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            f"👨‍👩‍👦 @{parent} est maintenant "
            f"le parent de @{child}."
        ),
    }


# ============================================================
# ENFANTS
# ============================================================

def get_children(
    parent: str,
) -> list[str]:

    parent = normalize_username(parent)

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT child_username
        FROM family_relations
        WHERE parent_username = ?
        ORDER BY child_username
        """,
        (parent,),
    ).fetchall()

    conn.close()

    return [
        row["child_username"]
        for row in rows
    ]


# ============================================================
# PARENTS
# ============================================================

def get_parents(
    child: str,
) -> list[str]:

    child = normalize_username(child)

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT parent_username
        FROM family_relations
        WHERE child_username = ?
        ORDER BY parent_username
        """,
        (child,),
    ).fetchall()

    conn.close()

    return [
        row["parent_username"]
        for row in rows
    ]


# ============================================================
# FRÈRES / SŒURS
# ============================================================

def get_siblings(
    username: str,
) -> list[str]:

    username = normalize_username(username)

    parents = get_parents(username)

    if not parents:
        return []

    conn = get_connection()

    placeholders = ",".join(
        "?" for _ in parents
    )

    rows = conn.execute(
        f"""
        SELECT DISTINCT child_username
        FROM family_relations
        WHERE parent_username IN ({placeholders})
          AND child_username != ?
        """,
        (
            *parents,
            username,
        ),
    ).fetchall()

    conn.close()

    return sorted(
        {
            row["child_username"]
            for row in rows
        }
    )


# ============================================================
# ARBRE GÉNÉALOGIQUE
# ============================================================

def get_family_tree(
    username: str,
) -> dict:

    username = normalize_username(username)

    spouse = get_spouse(username)
    parents = get_parents(username)
    children = get_children(username)
    siblings = get_siblings(username)

    return {
        "username": username,
        "spouse": spouse,
        "parents": parents,
        "children": children,
        "siblings": siblings,
    }


def format_family_tree(
    username: str,
) -> str:

    tree = get_family_tree(
        username
    )

    lines = [
        "🌳 <b>ARBRE GÉNÉALOGIQUE</b>",
        "",
        f"👤 <b>@{tree['username']}</b>",
        "",
    ]

    if tree["parents"]:
        lines.append("👨‍👩‍👦 <b>Parents</b>")

        for parent in tree["parents"]:
            lines.append(
                f"   └─ @{parent}"
            )

        lines.append("")

    if tree["spouse"]:
        lines.append("💍 <b>Conjoint(e)</b>")
        lines.append(
            f"   └─ @{tree['spouse']}"
        )
        lines.append("")

    if tree["siblings"]:
        lines.append("🧑‍🤝‍🧑 <b>Frères / Sœurs</b>")

        for sibling in tree["siblings"]:
            lines.append(
                f"   └─ @{sibling}"
            )

        lines.append("")

    if tree["children"]:
        lines.append("👶 <b>Enfants</b>")

        for child in tree["children"]:
            lines.append(
                f"   └─ @{child}"
            )

        lines.append("")

    if (
        not tree["parents"]
        and not tree["spouse"]
        and not tree["siblings"]
        and not tree["children"]
    ):
        lines.append(
            "🌱 Aucun lien familial enregistré."
        )

    return "\n".join(lines)


# ============================================================
# RECHERCHE DE CIBLE
# ============================================================

def resolve_target(
    username: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> Optional[str]:
    """
    Permet aux commandes d'accepter :

        /ami @username

    ou une réponse à un message.

    Si les deux sont fournis, le username explicite
    est prioritaire.
    """

    if username:
        return normalize_username(username)

    if replied_username:
        return normalize_username(
            replied_username
        )

    return None


# ============================================================
# INITIALISATION
# ============================================================

setup_family_database()