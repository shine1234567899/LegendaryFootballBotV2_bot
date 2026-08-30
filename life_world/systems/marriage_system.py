"""
Life World — Marriage System

Gère le système de mariage :

- demande en mariage ;
- acceptation ;
- refus ;
- annulation d'une demande ;
- vérification du statut marital ;
- conjoint ;
- divorce ;
- historique des mariages.

Les joueurs sont identifiés par leur @username.

IMPORTANT :
- ce module ne branche pas main.py ;
- il utilise la base Life World existante ;
- le branchement Telegram sera fait à la fin.
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
    return conn


# ============================================================
# TABLE DES DEMANDES
# ============================================================

def setup_marriage_system() -> None:

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS marriage_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            requester TEXT NOT NULL,
            target TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'pending',

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            responded_at INTEGER,

            UNIQUE(requester, target)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_marriage_requests_target
        ON marriage_requests(target, status)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_marriage_requests_requester
        ON marriage_requests(requester, status)
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# UTILITAIRE USERNAME
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
# CONJOINT
# ============================================================

def get_spouse(
    username: str,
) -> Optional[str]:

    username = normalize_username(
        username
    )

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


def is_married(
    username: str,
) -> bool:

    return (
        get_spouse(username)
        is not None
    )


# ============================================================
# VÉRIFICATION MARIAGE
# ============================================================

def can_request_marriage(
    requester: str,
    target: str,
) -> tuple[bool, str]:

    requester = normalize_username(
        requester
    )

    target = normalize_username(
        target
    )

    if requester == target:
        return (
            False,
            "❌ Tu ne peux pas te demander "
            "en mariage toi-même.",
        )

    if is_married(requester):
        return (
            False,
            "❌ Tu es déjà marié.",
        )

    if is_married(target):
        return (
            False,
            f"❌ @{target} est déjà marié.",
        )

    return (
        True,
        "OK",
    )


# ============================================================
# ENVOYER UNE DEMANDE
# ============================================================

def send_marriage_request(
    requester: str,
    target: str,
) -> dict:

    requester = normalize_username(
        requester
    )

    target = normalize_username(
        target
    )

    allowed, reason = can_request_marriage(
        requester,
        target,
    )

    if not allowed:
        return {
            "success": False,
            "reason": "not_allowed",
            "message": reason,
        }

    conn = get_connection()

    # Une demande identique existe déjà.
    existing = conn.execute(
        """
        SELECT *
        FROM marriage_requests
        WHERE requester = ?
          AND target = ?
          AND status = 'pending'
        LIMIT 1
        """,
        (
            requester,
            target,
        ),
    ).fetchone()

    if existing:

        conn.close()

        return {
            "success": False,
            "reason": "already_pending",
            "message": (
                f"⏳ Une demande en mariage "
                f"est déjà envoyée à @{target}."
            ),
        }

    # On bloque également une demande inverse.
    reverse = conn.execute(
        """
        SELECT *
        FROM marriage_requests
        WHERE requester = ?
          AND target = ?
          AND status = 'pending'
        LIMIT 1
        """,
        (
            target,
            requester,
        ),
    ).fetchone()

    if reverse:

        conn.close()

        return {
            "success": False,
            "reason": "reverse_pending",
            "message": (
                f"💍 @{target} t'a déjà "
                "demandé en mariage."
            ),
        }

    conn.execute(
        """
        INSERT INTO marriage_requests (
            requester,
            target,
            status
        )
        VALUES (?, ?, 'pending')
        """,
        (
            requester,
            target,
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
            f"💍 Demande en mariage envoyée "
            f"à @{target}."
        ),
    }


# ============================================================
# DEMANDES REÇUES
# ============================================================

def get_marriage_requests(
    username: str,
) -> list[dict]:

    username = normalize_username(
        username
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM marriage_requests
        WHERE target = ?
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
# DEMANDES ENVOYÉES
# ============================================================

def get_sent_marriage_requests(
    username: str,
) -> list[dict]:

    username = normalize_username(
        username
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM marriage_requests
        WHERE requester = ?
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
# ACCEPTER
# ============================================================

def accept_marriage_request(
    target: str,
    requester: str,
) -> dict:

    target = normalize_username(
        target
    )

    requester = normalize_username(
        requester
    )

    if is_married(target):
        return {
            "success": False,
            "message": (
                "❌ Tu es déjà marié."
            ),
        }

    if is_married(requester):
        return {
            "success": False,
            "message": (
                f"❌ @{requester} est déjà marié."
            ),
        }

    conn = get_connection()

    request = conn.execute(
        """
        SELECT *
        FROM marriage_requests
        WHERE requester = ?
          AND target = ?
          AND status = 'pending'
        LIMIT 1
        """,
        (
            requester,
            target,
        ),
    ).fetchone()

    if request is None:

        conn.close()

        return {
            "success": False,
            "message": (
                "❌ Demande en mariage "
                "introuvable."
            ),
        }

    # Création du mariage.
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
            requester,
            target,
        ),
    )

    # Demande acceptée.
    conn.execute(
        """
        UPDATE marriage_requests
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

    # Les autres demandes deviennent invalides.
    conn.execute(
        """
        UPDATE marriage_requests
        SET
            status = 'cancelled',
            responded_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE status = 'pending'
          AND (
              requester = ?
              OR target = ?
              OR requester = ?
              OR target = ?
          )
        """,
        (
            requester,
            requester,
            target,
            target,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "spouse": requester,
        "message": (
            "💍 <b>MARIAGE</b>\n\n"
            f"💒 @{target} et @{requester} "
            "sont maintenant mariés !"
        ),
    }


# ============================================================
# REFUSER
# ============================================================

def decline_marriage_request(
    target: str,
    requester: str,
) -> dict:

    target = normalize_username(
        target
    )

    requester = normalize_username(
        requester
    )

    conn = get_connection()

    cursor = conn.execute(
        """
        UPDATE marriage_requests
        SET
            status = 'declined',
            responded_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE requester = ?
          AND target = ?
          AND status = 'pending'
        """,
        (
            requester,
            target,
        ),
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return {
            "success": False,
            "message": (
                "❌ Demande introuvable."
            ),
        }

    return {
        "success": True,
        "message": (
            f"❌ La demande de @{requester} "
            "a été refusée."
        ),
    }


# ============================================================
# ANNULER SA DEMANDE
# ============================================================

def cancel_marriage_request(
    requester: str,
    target: str,
) -> dict:

    requester = normalize_username(
        requester
    )

    target = normalize_username(
        target
    )

    conn = get_connection()

    cursor = conn.execute(
        """
        UPDATE marriage_requests
        SET
            status = 'cancelled',
            responded_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE requester = ?
          AND target = ?
          AND status = 'pending'
        """,
        (
            requester,
            target,
        ),
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return {
            "success": False,
            "message": (
                "❌ Demande introuvable."
            ),
        }

    return {
        "success": True,
        "message": (
            f"✅ Demande destinée à @{target} "
            "annulée."
        ),
    }


# ============================================================
# DIVORCE
# ============================================================

def divorce(
    username: str,
) -> dict:

    username = normalize_username(
        username
    )

    spouse = get_spouse(
        username
    )

    if spouse is None:
        return {
            "success": False,
            "message": (
                "❌ Tu n'es pas marié."
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
            f"💔 Ton mariage avec @{spouse} "
            "est terminé."
        ),
    }


# ============================================================
# HISTORIQUE
# ============================================================

def get_marriage_history(
    username: str,
) -> list[dict]:

    username = normalize_username(
        username
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM marriages
        WHERE partner_one = ?
           OR partner_two = ?
        ORDER BY created_at DESC
        """,
        (
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
# STATUT
# ============================================================

def marriage_status(
    username: str,
) -> dict:

    username = normalize_username(
        username
    )

    spouse = get_spouse(
        username
    )

    requests = get_marriage_requests(
        username
    )

    sent = get_sent_marriage_requests(
        username
    )

    return {
        "username": username,
        "married": spouse is not None,
        "spouse": spouse,
        "received_requests": requests,
        "sent_requests": sent,
    }


# ============================================================
# MESSAGE DU STATUT
# ============================================================

def format_marriage_status(
    username: str,
) -> str:

    data = marriage_status(
        username
    )

    lines = [
        "💍 <b>STATUT MATRIMONIAL</b>",
        "",
        f"👤 @{data['username']}",
        "",
    ]

    if data["married"]:

        lines.append(
            f"💑 Conjoint(e) : "
            f"<b>@{data['spouse']}</b>"
        )

    else:

        lines.append(
            "💔 Statut : <b>Célibataire</b>"
        )

    if data["received_requests"]:

        lines.append("")
        lines.append(
            "📨 <b>Demandes reçues</b>"
        )

        for request in data[
            "received_requests"
        ]:

            lines.append(
                f"💍 @{request['requester']}"
            )

    if data["sent_requests"]:

        lines.append("")
        lines.append(
            "📤 <b>Demandes envoyées</b>"
        )

        for request in data[
            "sent_requests"
        ]:

            lines.append(
                f"⏳ @{request['target']}"
            )

    return "\n".join(lines)


# ============================================================
# CALLBACKS
# ============================================================

def get_marriage_request_buttons(
    requester: str,
) -> list[tuple[str, str]]:

    requester = normalize_username(
        requester
    )

    return [
        (
            f"lw_marriage:accept:{requester}",
            "💍 Accepter",
        ),
        (
            f"lw_marriage:decline:{requester}",
            "❌ Refuser",
        ),
    ]


def parse_marriage_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 3:
        raise ValueError(
            "Callback mariage invalide."
        )

    if parts[0] != "lw_marriage":
        raise ValueError(
            "Callback mariage inconnu."
        )

    action = parts[1]
    username = normalize_username(
        parts[2]
    )

    if action not in {
        "accept",
        "decline",
    }:
        raise ValueError(
            "Action mariage inconnue."
        )

    return {
        "type": "marriage",
        "action": action,
        "username": username,
    }


# ============================================================
# INITIALISATION
# ============================================================

setup_marriage_system()
