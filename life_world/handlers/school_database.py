"""
Life World — School Database

Gestion des données scolaires du joueur :
- niveau scolaire ;
- domaine ;
- école actuelle ;
- historique des écoles ;
- financement de l'inscription ;
- progression vers le niveau suivant.

IMPORTANT :
Ce fichier ne branche aucun handler Telegram.
main.py sera relié à la fin.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "life_world.db"


# ============================================================
# CONNEXION
# ============================================================

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# CRÉATION DES TABLES
# ============================================================

def setup_school_database() -> None:
    """
    Crée les tables nécessaires au système scolaire.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS school_profiles (
            username TEXT PRIMARY KEY,

            education_level TEXT NOT NULL DEFAULT 'cep',

            domain TEXT,

            school_id INTEGER,

            enrollment_paid INTEGER NOT NULL DEFAULT 0,

            enrollment_payer TEXT,

            enrollment_year INTEGER,

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            updated_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            )
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS school_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL,

            education_level TEXT NOT NULL,

            domain TEXT,

            school_id INTEGER,

            school_name TEXT,

            enrollment_price INTEGER NOT NULL DEFAULT 0,

            payer TEXT,

            started_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            ended_at INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_school_history_username
        ON school_history(username)
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# PROFIL SCOLAIRE
# ============================================================

def create_school_profile(username: str) -> None:
    """
    Crée le profil scolaire s'il n'existe pas.
    """

    username = username.strip().lower()

    if not username:
        raise ValueError("Username obligatoire.")

    conn = get_connection()

    conn.execute(
        """
        INSERT OR IGNORE INTO school_profiles (
            username
        )
        VALUES (?)
        """,
        (username,),
    )

    conn.commit()
    conn.close()


def get_school_profile(
    username: str,
) -> Optional[dict]:
    """
    Retourne le profil scolaire du joueur.
    """

    username = username.strip().lower()

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM school_profiles
        WHERE username = ?
        """,
        (username,),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


# ============================================================
# NIVEAU SCOLAIRE
# ============================================================

def set_education_level(
    username: str,
    level: str,
) -> None:
    """
    Modifie le niveau scolaire actuel.
    """

    username = username.strip().lower()
    level = level.strip().lower()

    valid_levels = {
        "cep",
        "bepc",
        "probatoire",
        "bacc",
        "university",
    }

    if level not in valid_levels:
        raise ValueError(
            f"Niveau scolaire invalide : {level}"
        )

    create_school_profile(username)

    conn = get_connection()

    conn.execute(
        """
        UPDATE school_profiles
        SET
            education_level = ?,
            updated_at = CAST(strftime('%s', 'now') AS INTEGER)
        WHERE username = ?
        """,
        (level, username),
    )

    conn.commit()
    conn.close()


def get_education_level(
    username: str,
) -> Optional[str]:
    """
    Retourne le niveau actuel.
    """

    profile = get_school_profile(username)

    if not profile:
        return None

    return profile["education_level"]


# ============================================================
# DOMAINE
# ============================================================

def set_domain(
    username: str,
    domain: str,
) -> None:
    """
    Enregistre le domaine choisi.
    """

    username = username.strip().lower()
    domain = domain.strip().lower()

    create_school_profile(username)

    conn = get_connection()

    conn.execute(
        """
        UPDATE school_profiles
        SET
            domain = ?,
            updated_at = CAST(strftime('%s', 'now') AS INTEGER)
        WHERE username = ?
        """,
        (domain, username),
    )

    conn.commit()
    conn.close()


def get_domain(
    username: str,
) -> Optional[str]:
    """
    Retourne le domaine actuel.
    """

    profile = get_school_profile(username)

    if not profile:
        return None

    return profile["domain"]


# ============================================================
# ÉCOLE
# ============================================================

def set_school(
    username: str,
    school_id: int,
) -> None:
    """
    Enregistre l'école actuelle.
    """

    username = username.strip().lower()

    if school_id <= 0:
        raise ValueError("school_id invalide.")

    create_school_profile(username)

    conn = get_connection()

    conn.execute(
        """
        UPDATE school_profiles
        SET
            school_id = ?,
            enrollment_paid = 0,
            enrollment_payer = NULL,
            updated_at = CAST(strftime('%s', 'now') AS INTEGER)
        WHERE username = ?
        """,
        (school_id, username),
    )

    conn.commit()
    conn.close()


def get_school_id(
    username: str,
) -> Optional[int]:
    """
    Retourne l'identifiant de l'école actuelle.
    """

    profile = get_school_profile(username)

    if not profile:
        return None

    return profile["school_id"]


# ============================================================
# INSCRIPTION
# ============================================================

def set_enrollment_payment(
    username: str,
    payer: str,
) -> None:
    """
    Enregistre qui paie l'inscription.

    payer :
        self
        parent
    """

    username = username.strip().lower()
    payer = payer.strip().lower()

    if payer not in {
        "self",
        "parent",
    }:
        raise ValueError(
            "Le payeur doit être 'self' ou 'parent'."
        )

    create_school_profile(username)

    conn = get_connection()

    conn.execute(
        """
        UPDATE school_profiles
        SET
            enrollment_paid = 1,
            enrollment_payer = ?,
            updated_at = CAST(strftime('%s', 'now') AS INTEGER)
        WHERE username = ?
        """,
        (payer, username),
    )

    conn.commit()
    conn.close()


def enrollment_is_paid(
    username: str,
) -> bool:
    """
    Vérifie si l'inscription est payée.
    """

    profile = get_school_profile(username)

    if not profile:
        return False

    return bool(profile["enrollment_paid"])


def get_enrollment_payer(
    username: str,
) -> Optional[str]:
    profile = get_school_profile(username)

    if not profile:
        return None

    return profile["enrollment_payer"]


# ============================================================
# HISTORIQUE
# ============================================================

def add_school_history(
    username: str,
    education_level: str,
    domain: Optional[str],
    school_id: int,
    school_name: str,
    enrollment_price: int,
    payer: Optional[str],
) -> None:
    """
    Ajoute une école au parcours historique.
    """

    username = username.strip().lower()

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO school_history (
            username,
            education_level,
            domain,
            school_id,
            school_name,
            enrollment_price,
            payer
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            education_level.lower(),
            domain.lower() if domain else None,
            school_id,
            school_name,
            enrollment_price,
            payer,
        ),
    )

    conn.commit()
    conn.close()


def get_school_history(
    username: str,
) -> list[dict]:
    """
    Retourne tout l'historique scolaire.
    """

    username = username.strip().lower()

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM school_history
        WHERE username = ?
        ORDER BY started_at ASC, id ASC
        """,
        (username,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# CHANGEMENT D'ÉCOLE
# ============================================================

def change_school(
    username: str,
    new_school_id: int,
) -> None:
    """
    Change l'école actuelle.

    Le paiement de la nouvelle inscription
    devra être effectué avant validation définitive.
    """

    username = username.strip().lower()

    if new_school_id <= 0:
        raise ValueError(
            "Identifiant d'école invalide."
        )

    create_school_profile(username)

    conn = get_connection()

    conn.execute(
        """
        UPDATE school_profiles
        SET
            school_id = ?,
            enrollment_paid = 0,
            enrollment_payer = NULL,
            updated_at = CAST(strftime('%s', 'now') AS INTEGER)
        WHERE username = ?
        """,
        (new_school_id, username),
    )

    conn.commit()
    conn.close()


# ============================================================
# PASSAGE AU NIVEAU SUIVANT
# ============================================================

NEXT_LEVEL = {
    "cep": "bepc",
    "bepc": "probatoire",
    "probatoire": "bacc",
    "bacc": "university",
    "university": None,
}


def get_next_level(
    username: str,
) -> Optional[str]:
    """
    Retourne le prochain niveau scolaire.
    """

    current = get_education_level(username)

    if not current:
        return None

    return NEXT_LEVEL.get(current)


def promote_player(
    username: str,
) -> Optional[str]:
    """
    Fait passer le joueur au niveau suivant.

    Le domaine est conservé automatiquement.
    """

    current = get_education_level(username)

    if not current:
        raise ValueError(
            "Le joueur n'a pas de niveau scolaire."
        )

    next_level = NEXT_LEVEL.get(current)

    if not next_level:
        return None

    set_education_level(
        username,
        next_level,
    )

    return next_level


# ============================================================
# RÉINITIALISATION D'INSCRIPTION
# ============================================================

def reset_enrollment(
    username: str,
) -> None:
    """
    Remet l'inscription dans l'état non payé.
    """

    username = username.strip().lower()

    conn = get_connection()

    conn.execute(
        """
        UPDATE school_profiles
        SET
            enrollment_paid = 0,
            enrollment_payer = NULL,
            updated_at = CAST(strftime('%s', 'now') AS INTEGER)
        WHERE username = ?
        """,
        (username,),
    )

    conn.commit()
    conn.close()


# ============================================================
# INITIALISATION
# ============================================================

setup_school_database()