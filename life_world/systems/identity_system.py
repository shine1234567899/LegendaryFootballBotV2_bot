"""
Manu World — Identity System

Carte d'identité virtuelle du joueur.

Utilité :
- créer une identité ;
- consulter sa carte ;
- vérifier qu'un joueur possède une identité ;
- utiliser l'identité comme condition pour certains systèmes
  (ex. achat d'une propriété) ;
- conserver les informations d'identité ;
- boutons et callbacks préparés pour Telegram.

IMPORTANT :
main.py n'est PAS modifié ici.
"""

from __future__ import annotations

import random
import sqlite3
import string
import time
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
    return conn


# ============================================================
# BASE DE DONNÉES
# ============================================================

def setup_identity_database() -> None:
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS identity_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL UNIQUE,

            card_number TEXT NOT NULL UNIQUE,

            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,

            nationality TEXT NOT NULL DEFAULT 'Cameroon',

            birth_date TEXT,

            gender TEXT,

            address TEXT,

            issue_date INTEGER NOT NULL,

            status TEXT NOT NULL DEFAULT 'active'
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_identity_username
        ON identity_cards(username)
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


def clean_text(
    value: Optional[str],
    default: str = "",
) -> str:
    value = str(value or "").strip()

    return value if value else default


def generate_card_number() -> str:
    """
    Génère un numéro d'identité virtuel.

    Format :
    LW-XXXXXXXX-XXXX
    """

    first = "".join(
        random.choices(
            string.digits,
            k=8,
        )
    )

    second = "".join(
        random.choices(
            string.digits,
            k=4,
        )
    )

    return f"LW-{first}-{second}"


# ============================================================
# IDENTITÉ EXISTANTE
# ============================================================

def get_identity(
    username: str,
) -> Optional[dict]:

    username = normalize_username(username)

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM identity_cards
        WHERE username = ?
        LIMIT 1
        """,
        (username,),
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def has_identity_card(
    username: str,
) -> bool:
    return get_identity(username) is not None


# ============================================================
# CRÉATION
# ============================================================

def create_identity(
    username: str,
    first_name: str,
    last_name: str,
    nationality: str = "Cameroon",
    birth_date: Optional[str] = None,
    gender: Optional[str] = None,
    address: Optional[str] = None,
) -> dict:

    username = normalize_username(username)

    first_name = clean_text(first_name)
    last_name = clean_text(last_name)

    nationality = clean_text(
        nationality,
        "Cameroon",
    )

    birth_date = clean_text(
        birth_date
    )

    gender = clean_text(
        gender
    )

    address = clean_text(
        address
    )

    if not first_name:
        return {
            "success": False,
            "message": (
                "❌ Prénom obligatoire."
            ),
        }

    if not last_name:
        return {
            "success": False,
            "message": (
                "❌ Nom obligatoire."
            ),
        }

    existing = get_identity(
        username
    )

    if existing:
        return {
            "success": False,
            "reason": "already_exists",
            "identity": existing,
            "message": (
                "🪪 Tu possèdes déjà une "
                "carte d'identité."
            ),
        }

    conn = get_connection()

    card_number = generate_card_number()

    # Évite une collision extrêmement improbable.
    while conn.execute(
        """
        SELECT id
        FROM identity_cards
        WHERE card_number = ?
        LIMIT 1
        """,
        (card_number,),
    ).fetchone():

        card_number = generate_card_number()

    issue_date = int(
        time.time()
    )

    conn.execute(
        """
        INSERT INTO identity_cards (
            username,
            card_number,
            first_name,
            last_name,
            nationality,
            birth_date,
            gender,
            address,
            issue_date,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """,
        (
            username,
            card_number,
            first_name,
            last_name,
            nationality,
            birth_date,
            gender,
            address,
            issue_date,
        ),
    )

    conn.commit()

    row = conn.execute(
        """
        SELECT *
        FROM identity_cards
        WHERE username = ?
        LIMIT 1
        """,
        (username,),
    ).fetchone()

    conn.close()

    return {
        "success": True,
        "identity": dict(row),
        "message": (
            "🪪 <b>CARTE D'IDENTITÉ CRÉÉE</b>\n\n"
            f"👤 @{username}\n"
            f"🪪 N° : <code>{card_number}</code>"
        ),
    }


# ============================================================
# STATUT
# ============================================================

def identity_status(
    username: str,
) -> dict:

    identity = get_identity(
        username
    )

    if identity is None:
        return {
            "exists": False,
            "status": "missing",
        }

    return {
        "exists": True,
        "status": identity["status"],
        "identity": identity,
    }


def is_identity_active(
    username: str,
) -> bool:

    identity = get_identity(
        username
    )

    return bool(
        identity
        and identity["status"] == "active"
    )


# ============================================================
# BLOQUER / RÉACTIVER
# ============================================================

def set_identity_status(
    username: str,
    status: str,
) -> dict:

    username = normalize_username(username)

    status = str(
        status
    ).strip().lower()

    if status not in {
        "active",
        "blocked",
    }:
        return {
            "success": False,
            "message": (
                "❌ Statut d'identité invalide."
            ),
        }

    conn = get_connection()

    cursor = conn.execute(
        """
        UPDATE identity_cards
        SET status = ?
        WHERE username = ?
        """,
        (
            status,
            username,
        ),
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return {
            "success": False,
            "message": (
                "❌ Carte d'identité introuvable."
            ),
        }

    label = (
        "🟢 Active"
        if status == "active"
        else "🔴 Bloquée"
    )

    return {
        "success": True,
        "status": status,
        "message": (
            f"🪪 Carte d'identité : {label}."
        ),
    }


# ============================================================
# VÉRIFICATION POUR LES AUTRES SYSTÈMES
# ============================================================

def require_identity(
    username: str,
) -> tuple[bool, str]:

    username = normalize_username(username)

    identity = get_identity(
        username
    )

    if identity is None:
        return (
            False,
            "🪪 Une carte d'identité est requise.",
        )

    if identity["status"] != "active":
        return (
            False,
            "🔴 Ta carte d'identité est bloquée.",
        )

    return (
        True,
        "OK",
    )


# ============================================================
# FORMATAGE
# ============================================================

def format_identity(
    username: str,
) -> str:

    identity = get_identity(
        username
    )

    if identity is None:
        return (
            "🪪 <b>CARTE D'IDENTITÉ</b>\n\n"
            "❌ Aucune carte d'identité."
        )

    status = (
        "🟢 ACTIVE"
        if identity["status"] == "active"
        else "🔴 BLOQUÉE"
    )

    lines = [
        "🪪 <b>CARTE D'IDENTITÉ</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"👤 Nom : <b>{identity['last_name']}</b>",
        f"👤 Prénom : <b>{identity['first_name']}</b>",
        f"🌍 Nationalité : {identity['nationality']}",
    ]

    if identity["birth_date"]:
        lines.append(
            f"🎂 Date de naissance : "
            f"{identity['birth_date']}"
        )

    if identity["gender"]:
        lines.append(
            f"⚧ Genre : {identity['gender']}"
        )

    if identity["address"]:
        lines.append(
            f"🏠 Adresse : {identity['address']}"
        )

    lines.extend(
        [
            "",
            f"🪪 N° : "
            f"<code>{identity['card_number']}</code>",
            f"📌 Statut : {status}",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
    )

    return "\n".join(lines)


# ============================================================
# BOUTONS
# ============================================================

def identity_buttons() -> list[
    list[tuple[str, str]]
]:

    return [
        [
            (
                "lw_identity:view",
                "🪪 Ma carte",
            ),
        ],
        [
            (
                "lw_identity:status",
                "📌 Statut",
            ),
        ],
    ]


def identity_admin_buttons() -> list[
    list[tuple[str, str]]
]:

    return [
        [
            (
                "lw_identity:block",
                "🔒 Bloquer",
            ),
            (
                "lw_identity:activate",
                "🔓 Activer",
            ),
        ]
    ]


# ============================================================
# CALLBACK
# ============================================================

def parse_identity_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 2:
        raise ValueError(
            "Callback identité invalide."
        )

    if parts[0] != "lw_identity":
        raise ValueError(
            "Callback identité inconnu."
        )

    action = parts[1]

    allowed = {
        "view",
        "status",
        "block",
        "activate",
    }

    if action not in allowed:
        raise ValueError(
            "Action identité inconnue."
        )

    return {
        "type": "identity",
        "action": action,
    }


# ============================================================
# AIDE
# ============================================================

def identity_help() -> str:

    return (
        "🪪 <b>IDENTITÉ</b>\n\n"
        "Créer ta carte :\n"
        "<code>/identity create</code>\n\n"
        "Consulter ta carte :\n"
        "<code>/identity</code>\n\n"
        "La carte peut être demandée par "
        "certains systèmes de Manu World, "
        "notamment lors de l'achat d'une propriété."
    )


# ============================================================
# INITIALISATION
# ============================================================

setup_identity_database()


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "setup_identity_database",
    "normalize_username",
    "generate_card_number",
    "get_identity",
    "has_identity_card",
    "create_identity",
    "identity_status",
    "is_identity_active",
    "set_identity_status",
    "require_identity",
    "format_identity",
    "identity_buttons",
    "identity_admin_buttons",
    "parse_identity_callback",
    "identity_help",
]
