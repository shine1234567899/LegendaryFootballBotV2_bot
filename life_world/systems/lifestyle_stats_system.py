"""
Manu World — Lifestyle Stats System

Statistiques de vie du joueur.

Gère :
- ❤️ santé
- 😊 joie
- 😇 karma
- ⭐ réputation
- 💰 patrimoine calculable
- 📈 évolution des statistiques
- historique des variations

Les autres systèmes peuvent appeler modify_stat()
pour récompenser ou pénaliser un joueur.

Exemples :
- travail terminé -> réputation +
- bonne action -> karma +
- événement positif -> joie +
- sanction -> karma / réputation -

IMPORTANT :
main.py n'est PAS modifié ici.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_DIR = BASE_DIR.parent / "database"

DB_PATH = DB_DIR / "life_world.db"


# ============================================================
# LIMITES
# ============================================================

STAT_LIMITS = {
    "health": (0, 100),
    "joy": (0, 100),
    "karma": (-100, 100),
    "reputation": (0, 100),
}


STAT_LABELS = {
    "health": "❤️ Santé",
    "joy": "😊 Joie",
    "karma": "😇 Karma",
    "reputation": "⭐ Réputation",
}


# ============================================================
# CONNEXION
# ============================================================

def get_connection() -> sqlite3.Connection:
    """
    Ouvre la base SQLite de MANUWORLD.

    Le dossier database est créé automatiquement s'il
    n'existe pas encore.
    """

    DB_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    conn = sqlite3.connect(
        str(DB_PATH)
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# BASE DE DONNÉES
# ============================================================

def setup_lifestyle_database() -> None:

    # S'assure que le dossier existe avant toute
    # tentative d'ouverture de SQLite.
    DB_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    conn = get_connection()

    try:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lifestyle_stats (
                username TEXT PRIMARY KEY,

                health INTEGER NOT NULL DEFAULT 100,
                joy INTEGER NOT NULL DEFAULT 50,
                karma INTEGER NOT NULL DEFAULT 0,
                reputation INTEGER NOT NULL DEFAULT 0,

                updated_at INTEGER NOT NULL DEFAULT (
                    CAST(strftime('%s', 'now') AS INTEGER)
                )
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lifestyle_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL,

                stat_name TEXT NOT NULL,

                old_value INTEGER NOT NULL,
                new_value INTEGER NOT NULL,

                change_amount INTEGER NOT NULL,

                reason TEXT NOT NULL DEFAULT '',

                created_at INTEGER NOT NULL DEFAULT (
                    CAST(strftime('%s', 'now') AS INTEGER)
                )
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_lifestyle_history_user
            ON lifestyle_history(username, created_at)
            """
        )

        conn.commit()

    finally:

        conn.close()


# ============================================================
# UTILITAIRES
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


def validate_stat_name(
    stat_name: str,
) -> str:

    stat_name = str(
        stat_name
    ).strip().lower()

    if stat_name not in STAT_LIMITS:

        raise ValueError(
            f"Statistique inconnue : {stat_name}"
        )

    return stat_name


def clamp_stat(
    stat_name: str,
    value: int,
) -> int:

    stat_name = validate_stat_name(
        stat_name
    )

    minimum, maximum = STAT_LIMITS[
        stat_name
    ]

    return max(
        minimum,
        min(
            maximum,
            int(value),
        ),
    )


# ============================================================
# INITIALISATION D'UN JOUEUR
# ============================================================

def ensure_player_stats(
    username: str,
) -> dict:

    username = normalize_username(
        username
    )

    conn = get_connection()

    try:

        conn.execute(
            """
            INSERT OR IGNORE INTO lifestyle_stats (
                username,
                health,
                joy,
                karma,
                reputation
            )
            VALUES (?, 100, 50, 0, 0)
            """,
            (username,),
        )

        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM lifestyle_stats
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()

    finally:

        conn.close()

    if row is None:

        raise RuntimeError(
            "Impossible d'initialiser les statistiques du joueur."
        )

    return dict(row)


# ============================================================
# RÉCUPÉRER LES STATS
# ============================================================

def get_stats(
    username: str,
) -> dict:

    username = normalize_username(
        username
    )

    return ensure_player_stats(
        username
    )
# ============================================================
# COMPATIBILITÉ HANDLER
# ============================================================

def get_lifestyle_stats(
    username: str,
) -> dict:
    """
    Alias public utilisé par le handler lifestyle_stats.py.

    Conserve get_stats() comme fonction interne/principale
    tout en fournissant l'API attendue par le handler.
    """

    return get_stats(
        username
    )


def get_stat(
    username: str,
    stat_name: str,
) -> int:

    username = normalize_username(
        username
    )

    stat_name = validate_stat_name(
        stat_name
    )

    stats = get_stats(
        username
    )

    return int(
        stats[stat_name]
    )


# ============================================================
# MODIFIER UNE STAT
# ============================================================

def modify_stat(
    username: str,
    stat_name: str,
    amount: int,
    reason: str = "",
) -> dict:

    username = normalize_username(
        username
    )

    stat_name = validate_stat_name(
        stat_name
    )

    amount = int(amount)

    current = get_stat(
        username,
        stat_name,
    )

    new_value = clamp_stat(
        stat_name,
        current + amount,
    )

    actual_change = (
        new_value - current
    )

    conn = get_connection()

    try:

        conn.execute(
            f"""
            UPDATE lifestyle_stats
            SET
                {stat_name} = ?,
                updated_at = ?
            WHERE username = ?
            """,
            (
                new_value,
                int(time.time()),
                username,
            ),
        )

        if actual_change != 0:

            conn.execute(
                """
                INSERT INTO lifestyle_history (
                    username,
                    stat_name,
                    old_value,
                    new_value,
                    change_amount,
                    reason
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    stat_name,
                    current,
                    new_value,
                    actual_change,
                    reason,
                ),
            )

        conn.commit()

    finally:

        conn.close()

    return {
        "success": True,
        "username": username,
        "stat": stat_name,
        "old_value": current,
        "new_value": new_value,
        "change": actual_change,
        "reason": reason,
    }


# ============================================================
# DÉFINIR UNE STAT
# ============================================================

def set_stat(
    username: str,
    stat_name: str,
    value: int,
    reason: str = "",
) -> dict:

    username = normalize_username(
        username
    )

    stat_name = validate_stat_name(
        stat_name
    )

    value = clamp_stat(
        stat_name,
        value,
    )

    current = get_stat(
        username,
        stat_name,
    )

    return modify_stat(
        username,
        stat_name,
        value - current,
        reason,
    )


# ============================================================
# PLUSIEURS STATS
# ============================================================

def modify_stats(
    username: str,
    changes: dict[str, int],
    reason: str = "",
) -> dict:

    username = normalize_username(
        username
    )

    results = []

    for stat_name, amount in changes.items():

        results.append(
            modify_stat(
                username,
                stat_name,
                amount,
                reason,
            )
        )

    return {
        "success": True,
        "username": username,
        "changes": results,
    }


# ============================================================
# RÉPUTATION
# ============================================================

def add_reputation(
    username: str,
    amount: int,
    reason: str = "",
) -> dict:

    return modify_stat(
        username,
        "reputation",
        amount,
        reason,
    )


# ============================================================
# KARMA
# ============================================================

def add_karma(
    username: str,
    amount: int,
    reason: str = "",
) -> dict:

    return modify_stat(
        username,
        "karma",
        amount,
        reason,
    )


# ============================================================
# JOIE
# ============================================================

def add_joy(
    username: str,
    amount: int,
    reason: str = "",
) -> dict:

    return modify_stat(
        username,
        "joy",
        amount,
        reason,
    )


# ============================================================
# SANTÉ
# ============================================================

def add_health(
    username: str,
    amount: int,
    reason: str = "",
) -> dict:

    return modify_stat(
        username,
        "health",
        amount,
        reason,
    )


# ============================================================
# NIVEAUX
# ============================================================

def get_reputation_level(
    reputation: int,
) -> str:

    reputation = int(
        reputation
    )

    if reputation >= 90:
        return "👑 Légendaire"

    if reputation >= 75:
        return "💎 Exceptionnelle"

    if reputation >= 50:
        return "⭐ Respectée"

    if reputation >= 25:
        return "🙂 Correcte"

    if reputation >= 0:
        return "🌱 Débutante"

    return "⚠️ Mauvaise réputation"


def get_karma_level(
    karma: int,
) -> str:

    karma = int(
        karma
    )

    if karma >= 75:
        return "😇 Exemplaire"

    if karma >= 40:
        return "✨ Très bon"

    if karma >= 10:
        return "🙂 Positif"

    if karma >= -10:
        return "⚖️ Neutre"

    if karma >= -40:
        return "😈 Négatif"

    if karma >= -75:
        return "⚠️ Mauvais"

    return "☠️ Très mauvais"


# ============================================================
# HISTORIQUE
# ============================================================

def get_stat_history(
    username: str,
    stat_name: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:

    username = normalize_username(
        username
    )

    limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    conn = get_connection()

    try:

        if stat_name is None:

            rows = conn.execute(
                """
                SELECT *
                FROM lifestyle_history
                WHERE username = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (
                    username,
                    limit,
                ),
            ).fetchall()

        else:

            stat_name = validate_stat_name(
                stat_name
            )

            rows = conn.execute(
                """
                SELECT *
                FROM lifestyle_history
                WHERE username = ?
                  AND stat_name = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (
                    username,
                    stat_name,
                    limit,
                ),
            ).fetchall()

    finally:

        conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# FORMATAGE
# ============================================================

def format_lifestyle_stats(
    username: str,
) -> str:

    stats = get_stats(
        username
    )

    reputation_level = (
        get_reputation_level(
            stats["reputation"]
        )
    )

    karma_level = (
        get_karma_level(
            stats["karma"]
        )
    )

    return (
        "📊 <b>MES STATISTIQUES DE VIE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❤️ Santé : "
        f"<b>{stats['health']}/100</b>\n"
        f"😊 Joie : "
        f"<b>{stats['joy']}/100</b>\n"
        f"😇 Karma : "
        f"<b>{stats['karma']}/100</b>\n"
        f"   └─ {karma_level}\n"
        f"⭐ Réputation : "
        f"<b>{stats['reputation']}/100</b>\n"
        f"   └─ {reputation_level}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def format_stat_history(
    username: str,
    limit: int = 10,
) -> str:

    history = get_stat_history(
        username,
        limit=limit,
    )

    lines = [
        "📜 <b>HISTORIQUE DE VIE</b>",
        "",
    ]

    if not history:

        lines.append(
            "📭 Aucun changement enregistré."
        )

        return "\n".join(lines)

    for entry in history:

        change = entry["change_amount"]

        sign = (
            "+"
            if change > 0
            else ""
        )

        label = STAT_LABELS.get(
            entry["stat_name"],
            entry["stat_name"],
        )

        reason = (
            entry["reason"]
            or "Sans motif"
        )

        lines.append(
            f"{label} : "
            f"{entry['old_value']} → "
            f"{entry['new_value']} "
            f"({sign}{change})"
        )

        lines.append(
            f"   └─ {reason}"
        )

    return "\n".join(lines)


# ============================================================
# BOUTONS
# ============================================================

def lifestyle_buttons() -> list[
    list[tuple[str, str]]
]:

    return [
        [
            (
                "lw_stats:view",
                "📊 Mes stats",
            ),
            (
                "lw_stats:history",
                "📜 Historique",
            ),
        ]
    ]


def parse_lifestyle_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 2:

        raise ValueError(
            "Callback stats invalide."
        )

    if parts[0] != "lw_stats":

        raise ValueError(
            "Callback stats inconnu."
        )

    action = parts[1]

    if action not in {
        "view",
        "history",
    }:

        raise ValueError(
            "Action stats inconnue."
        )

    return {
        "type": "lifestyle_stats",
        "action": action,
    }


# ============================================================
# AIDE
# ============================================================

def lifestyle_help() -> str:

    return (
        "📊 <b>STATISTIQUES DE VIE</b>\n\n"
        "<code>/stats</code>\n"
        "Affiche tes statistiques.\n\n"
        "<code>/stats history</code>\n"
        "Affiche leur historique."
    )


# ============================================================
# INITIALISATION
# ============================================================

setup_lifestyle_database()


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "STAT_LIMITS",
    "STAT_LABELS",
    "setup_lifestyle_database",
    "ensure_player_stats",
    "get_stats",
    "get_stat",
    "modify_stat",
    "set_stat",
    "modify_stats",
    "add_reputation",
    "add_karma",
    "add_joy",
    "add_health",
    "get_reputation_level",
    "get_karma_level",
    "get_stat_history",
    "format_lifestyle_stats",
    "format_stat_history",
    "lifestyle_buttons",
    "parse_lifestyle_callback",
    "lifestyle_help",
]