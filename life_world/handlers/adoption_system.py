"""
Life World — Adoption System

Gestion de l'adoption :

- envoyer une demande ;
- accepter ;
- refuser ;
- annuler ;
- vérifier les demandes ;
- enregistrer le lien parent → enfant ;
- consulter les enfants ;
- consulter les parents.

Les joueurs sont identifiés par leur @username.

IMPORTANT :
Le système familial déjà créé reste la source des relations.
Ce fichier ne branche pas main.py.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = (
    BASE_DIR.parent
    / "database"
    / "life_world.db"
)


# ============================================================
# CONNEXION
# ============================================================

def get_connection() -> sqlite3.Connection:

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# ============================================================
# TABLE
# ============================================================

def setup_adoption_database() -> None:

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS adoption_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            parent_username TEXT NOT NULL,

            child_username TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'pending',

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            responded_at INTEGER,

            UNIQUE(parent_username, child_username)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_adoption_request_child
        ON adoption_requests(
            child_username,
            status
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_adoption_request_parent
        ON adoption_requests(
            parent_username,
            status
        )
        """
    )

    conn.commit()

    conn.close()


# ============================================================
# USERNAME
# ============================================================

def normalize_username(
    username: str,
) -> str:

    username = str(
        username
    ).strip()

    if username.startswith("@"):
        username = username[1:]

    username = username.lower()

    if not username:
        raise ValueError(
            "Username obligatoire."
        )

    return username


# ============================================================
# VÉRIFICATION
# ============================================================

def is_already_parent(
    parent: str,
    child: str,
) -> bool:

    parent = normalize_username(parent)
    child = normalize_username(child)

    conn = get_connection()

    row = conn.execute(
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

    return row is not None


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

    if is_already_parent(
        parent,
        child,
    ):

        return (
            False,
            "❌ Cette relation parent/enfant "
            "existe déjà.",
        )

    return (
        True,
        "OK",
    )


# ============================================================
# ENVOYER UNE DEMANDE
# ============================================================

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
            "reason": "not_allowed",
            "message": reason,
        }

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT *
        FROM adoption_requests
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
            "reason": "pending",
            "message": (
                f"⏳ Une demande d'adoption "
                f"est déjà envoyée à @{child}."
            ),
        }

    conn.execute(
        """
        INSERT INTO adoption_requests (
            parent_username,
            child_username,
            status
        )
        VALUES (?, ?, 'pending')
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
        "parent": parent,
        "child": child,
        "message": (
            f"👨‍👩‍👦 Demande d'adoption envoyée "
            f"à @{child}."
        ),
    }


# ============================================================
# DEMANDES REÇUES
# ============================================================

def get_received_requests(
    child: str,
) -> list[dict]:

    child = normalize_username(
        child
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM adoption_requests
        WHERE child_username = ?
          AND status = 'pending'
        ORDER BY created_at ASC
        """,
        (child,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# DEMANDES ENVOYÉES
# ============================================================

def get_sent_requests(
    parent: str,
) -> list[dict]:

    parent = normalize_username(
        parent
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM adoption_requests
        WHERE parent_username = ?
          AND status = 'pending'
        ORDER BY created_at ASC
        """,
        (parent,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# ACCEPTER
# ============================================================

def accept_adoption_request(
    child: str,
    parent: str,
) -> dict:

    child = normalize_username(
        child
    )

    parent = normalize_username(
        parent
    )

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

    request = conn.execute(
        """
        SELECT *
        FROM adoption_requests
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
                "❌ Demande d'adoption "
                "introuvable."
            ),
        }

    # --------------------------------------------------------
    # Ajouter la relation familiale.
    # --------------------------------------------------------

    conn.execute(
        """
        INSERT INTO family_relations (
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

    # --------------------------------------------------------
    # Marquer la demande comme acceptée.
    # --------------------------------------------------------

    conn.execute(
        """
        UPDATE adoption_requests
        SET
            status = 'accepted',
            responded_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE id = ?
        """,
        (
            request["id"],
        ),
    )

    conn.commit()

    conn.close()

    return {
        "success": True,
        "parent": parent,
        "child": child,
        "message": (
            "👨‍👩‍👦 <b>ADOPTION ACCEPTÉE</b>\n\n"
            f"👤 Parent : @{parent}\n"
            f"👶 Enfant : @{child}\n\n"
            "✅ Le lien familial est maintenant "
            "enregistré."
        ),
    }


# ============================================================
# REFUSER
# ============================================================

def decline_adoption_request(
    child: str,
    parent: str,
) -> dict:

    child = normalize_username(
        child
    )

    parent = normalize_username(
        parent
    )

    conn = get_connection()

    cursor = conn.execute(
        """
        UPDATE adoption_requests
        SET
            status = 'declined',
            responded_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE parent_username = ?
          AND child_username = ?
          AND status = 'pending'
        """,
        (
            parent,
            child,
        ),
    )

    conn.commit()

    conn.close()

    if cursor.rowcount == 0:

        return {
            "success": False,
            "message": (
                "❌ Demande d'adoption "
                "introuvable."
            ),
        }

    return {
        "success": True,
        "message": (
            f"❌ La demande de @{parent} "
            "a été refusée."
        ),
    }


# ============================================================
# ANNULER
# ============================================================

def cancel_adoption_request(
    parent: str,
    child: str,
) -> dict:

    parent = normalize_username(
        parent
    )

    child = normalize_username(
        child
    )

    conn = get_connection()

    cursor = conn.execute(
        """
        UPDATE adoption_requests
        SET
            status = 'cancelled',
            responded_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE parent_username = ?
          AND child_username = ?
          AND status = 'pending'
        """,
        (
            parent,
            child,
        ),
    )

    conn.commit()

    conn.close()

    if cursor.rowcount == 0:

        return {
            "success": False,
            "message": (
                "❌ Demande d'adoption "
                "introuvable."
            ),
        }

    return {
        "success": True,
        "message": (
            f"✅ Demande envoyée à @{child} "
            "annulée."
        ),
    }


# ============================================================
# ENFANTS
# ============================================================

def get_children(
    parent: str,
) -> list[str]:

    parent = normalize_username(
        parent
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT child_username
        FROM family_relations
        WHERE parent_username = ?
        ORDER BY child_username ASC
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

    child = normalize_username(
        child
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT parent_username
        FROM family_relations
        WHERE child_username = ?
        ORDER BY parent_username ASC
        """,
        (child,),
    ).fetchall()

    conn.close()

    return [
        row["parent_username"]
        for row in rows
    ]


# ============================================================
# STATUT ADOPTION
# ============================================================

def adoption_status(
    username: str,
) -> dict:

    username = normalize_username(
        username
    )

    return {
        "username": username,
        "parents": get_parents(username),
        "children": get_children(username),
        "received": get_received_requests(
            username
        ),
        "sent": get_sent_requests(
            username
        ),
    }


# ============================================================
# MESSAGE STATUT
# ============================================================

def format_adoption_status(
    username: str,
) -> str:

    data = adoption_status(
        username
    )

    lines = [
        "👨‍👩‍👦 <b>FAMILLE</b>",
        "",
        f"👤 @{data['username']}",
        "",
    ]

    if data["parents"]:

        lines.append(
            "👨‍👩‍👦 <b>PARENTS</b>"
        )

        for parent in data["parents"]:
            lines.append(
                f"   └─ @{parent}"
            )

        lines.append("")

    if data["children"]:

        lines.append(
            "👶 <b>ENFANTS</b>"
        )

        for child in data["children"]:
            lines.append(
                f"   └─ @{child}"
            )

        lines.append("")

    if data["received"]:

        lines.append(
            "📨 <b>DEMANDES REÇUES</b>"
        )

        for request in data["received"]:

            lines.append(
                f"   └─ @{request['parent_username']}"
            )

        lines.append("")

    if data["sent"]:

        lines.append(
            "📤 <b>DEMANDES ENVOYÉES</b>"
        )

        for request in data["sent"]:

            lines.append(
                f"   └─ @{request['child_username']}"
            )

    if (
        not data["parents"]
        and not data["children"]
        and not data["received"]
        and not data["sent"]
    ):

        lines.append(
            "🌱 Aucun lien d'adoption enregistré."
        )

    return "\n".join(lines)


# ============================================================
# BOUTONS
# ============================================================

def adoption_request_buttons(
    parent: str,
) -> list[tuple[str, str]]:

    parent = normalize_username(
        parent
    )

    return [
        (
            f"lw_adoption:accept:{parent}",
            "👨‍👩‍👦 Accepter",
        ),
        (
            f"lw_adoption:decline:{parent}",
            "❌ Refuser",
        ),
    ]


# ============================================================
# CALLBACK
# ============================================================

def parse_adoption_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 3:
        raise ValueError(
            "Callback adoption invalide."
        )

    if parts[0] != "lw_adoption":
        raise ValueError(
            "Callback adoption inconnu."
        )

    action = parts[1]

    if action not in {
        "accept",
        "decline",
    }:
        raise ValueError(
            "Action adoption inconnue."
        )

    return {
        "type": "adoption",
        "action": action,
        "username": normalize_username(
            parts[2]
        ),
    }


# ============================================================
# CIBLE
# ============================================================

def resolve_adoption_target(
    username: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> Optional[str]:

    if username:
        return normalize_username(
            username
        )

    if replied_username:
        return normalize_username(
            replied_username
        )

    return None


# ============================================================
# AIDE
# ============================================================

def adoption_help() -> str:

    return (
        "👨‍👩‍👦 <b>ADOPTION</b>\n\n"

        "Pour proposer une adoption :\n"
        "<code>/adopt @username</code>\n\n"

        "Ou réponds directement au message "
        "de la personne puis utilise :\n"
        "<code>/adopt</code>\n\n"

        "📨 Les demandes reçues peuvent être "
        "acceptées ou refusées avec les boutons."
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "send_adoption_request",
    "get_received_requests",
    "get_sent_requests",
    "accept_adoption_request",
    "decline_adoption_request",
    "cancel_adoption_request",
    "get_children",
    "get_parents",
    "adoption_status",
    "format_adoption_status",
    "adoption_request_buttons",
    "parse_adoption_callback",
    "resolve_adoption_target",
    "adoption_help",
]