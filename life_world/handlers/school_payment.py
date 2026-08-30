"""
Life World — School Payment

Gestion du paiement des inscriptions scolaires.

Ce module :
- vérifie le solde disponible ;
- calcule le prix d'inscription ;
- permet au joueur de payer lui-même ;
- permet à un parent de payer ;
- évite les doubles paiements ;
- prépare les informations nécessaires au branchement Telegram.

IMPORTANT :
Ce fichier ne modifie pas main.py.
Le branchement Telegram et les commandes seront faits à la fin.
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
# TABLE DES PAIEMENTS
# ============================================================

def setup_payment_database() -> None:
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS school_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_username TEXT NOT NULL,

            payer_username TEXT NOT NULL,

            school_id TEXT NOT NULL,

            level TEXT NOT NULL,

            amount INTEGER NOT NULL,

            payment_type TEXT NOT NULL DEFAULT 'enrollment',

            status TEXT NOT NULL DEFAULT 'completed',

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            )
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_school_payments_student
        ON school_payments(student_username)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_school_payments_payer
        ON school_payments(payer_username)
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# OUTILS ARGENT
# ============================================================

def _find_balance_table(conn: sqlite3.Connection):
    """
    Cherche une table de portefeuille courante.

    Le système essaie plusieurs noms afin de pouvoir être
    raccordé plus facilement au modèle financier existant.
    """

    candidates = [
        "wallets",
        "wallet",
        "accounts",
        "users",
        "players",
    ]

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    existing = {
        row["name"]
        for row in rows
    }

    for table in candidates:
        if table in existing:
            columns = conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()

            names = {
                column["name"]
                for column in columns
            }

            username_column = next(
                (
                    column
                    for column in (
                        "username",
                        "user_username",
                        "player_username"
                    )
                    if column in names
                ),
                None,
            )

            balance_column = next(
                (
                    column
                    for column in (
                        "balance",
                        "money",
                        "cash",
                        "coins"
                    )
                    if column in names
                ),
                None,
            )

            if username_column and balance_column:
                return (
                    table,
                    username_column,
                    balance_column,
                )

    return None


def get_balance(username: str) -> int:
    """
    Retourne le solde du joueur.

    Le module utilise la table financière existante si elle
    possède username + balance/money/cash/coins.
    """

    username = username.strip().lower()

    if not username:
        return 0

    conn = get_connection()

    wallet = _find_balance_table(conn)

    if not wallet:
        conn.close()
        raise RuntimeError(
            "Aucune table financière compatible trouvée. "
            "Elle sera raccordée au système financier final."
        )

    table, username_column, balance_column = wallet

    row = conn.execute(
        f"""
        SELECT {balance_column}
        FROM {table}
        WHERE LOWER({username_column}) = ?
        LIMIT 1
        """,
        (username,),
    ).fetchone()

    conn.close()

    if row is None or row[balance_column] is None:
        return 0

    return int(row[balance_column])


def has_enough_money(
    username: str,
    amount: int,
) -> bool:
    """Vérifie si le joueur possède suffisamment d'argent."""

    if amount < 0:
        return False

    return get_balance(username) >= amount


# ============================================================
# DÉBIT
# ============================================================

def debit_money(
    username: str,
    amount: int,
) -> None:
    """
    Débite l'argent du compte.

    Le débit est refusé si le solde est insuffisant.
    """

    username = username.strip().lower()

    if amount <= 0:
        raise ValueError(
            "Le montant doit être supérieur à zéro."
        )

    conn = get_connection()

    wallet = _find_balance_table(conn)

    if not wallet:
        conn.close()
        raise RuntimeError(
            "Table financière compatible introuvable."
        )

    table, username_column, balance_column = wallet

    cursor = conn.execute(
        f"""
        UPDATE {table}
        SET {balance_column} = {balance_column} - ?
        WHERE LOWER({username_column}) = ?
          AND {balance_column} >= ?
        """,
        (
            amount,
            username,
            amount,
        ),
    )

    if cursor.rowcount != 1:
        conn.rollback()
        conn.close()
        raise ValueError(
            "Solde insuffisant ou joueur introuvable."
        )

    conn.commit()
    conn.close()


# ============================================================
# PAIEMENT PARENT
# ============================================================

def is_parent_payment_allowed(
    student_username: str,
    payer_username: str,
) -> bool:
    """
    Vérifie que le payeur est différent de l'élève.

    La vérification du lien familial réel sera raccordée
    au système famille/adoption/mariage plus tard.
    """

    student = student_username.strip().lower()
    payer = payer_username.strip().lower()

    return bool(student and payer and student != payer)


# ============================================================
# DOUBLON
# ============================================================

def enrollment_already_paid(
    student_username: str,
    school_id: str,
) -> bool:
    """
    Empêche de payer deux fois la même inscription.
    """

    student_username = student_username.strip().lower()

    conn = get_connection()

    row = conn.execute(
        """
        SELECT id
        FROM school_payments
        WHERE student_username = ?
          AND school_id = ?
          AND payment_type = 'enrollment'
          AND status = 'completed'
        LIMIT 1
        """,
        (
            student_username,
            school_id,
        ),
    ).fetchone()

    conn.close()

    return row is not None


# ============================================================
# ENREGISTREMENT DU PAIEMENT
# ============================================================

def record_payment(
    student_username: str,
    payer_username: str,
    school_id: str,
    level: str,
    amount: int,
) -> int:
    """
    Enregistre le paiement après débit réussi.
    """

    conn = get_connection()

    cursor = conn.execute(
        """
        INSERT INTO school_payments (
            student_username,
            payer_username,
            school_id,
            level,
            amount,
            payment_type,
            status
        )
        VALUES (?, ?, ?, ?, ?, 'enrollment', 'completed')
        """,
        (
            student_username.strip().lower(),
            payer_username.strip().lower(),
            school_id,
            level.strip().lower(),
            amount,
        ),
    )

    payment_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return int(payment_id)


# ============================================================
# PAIEMENT COMPLET
# ============================================================

def pay_enrollment(
    student_username: str,
    payer_username: str,
    school_id: str,
    level: str,
    amount: int,
) -> dict:
    """
    Effectue un paiement complet de l'inscription.

    Étapes :
        1. vérification du montant ;
        2. vérification du doublon ;
        3. vérification du solde ;
        4. débit ;
        5. enregistrement du paiement.

    Retourne un dictionnaire exploitable par le handler.
    """

    student_username = student_username.strip().lower()
    payer_username = payer_username.strip().lower()

    if not student_username:
        return {
            "success": False,
            "reason": "student_invalid",
            "message": "❌ Élève invalide.",
        }

    if not payer_username:
        return {
            "success": False,
            "reason": "payer_invalid",
            "message": "❌ Payeur invalide.",
        }

    if not school_id:
        return {
            "success": False,
            "reason": "school_invalid",
            "message": "❌ Établissement invalide.",
        }

    if amount <= 0:
        return {
            "success": False,
            "reason": "amount_invalid",
            "message": "❌ Montant d'inscription invalide.",
        }

    if enrollment_already_paid(
        student_username,
        school_id,
    ):
        return {
            "success": False,
            "reason": "already_paid",
            "message": (
                "⚠️ Cette inscription a déjà été payée."
            ),
        }

    try:
        balance = get_balance(payer_username)
    except RuntimeError as exc:
        return {
            "success": False,
            "reason": "wallet_unavailable",
            "message": str(exc),
        }

    if balance < amount:
        return {
            "success": False,
            "reason": "insufficient_funds",
            "balance": balance,
            "required": amount,
            "missing": amount - balance,
            "message": (
                "❌ Solde insuffisant.\n\n"
                f"💰 Solde : {balance:,} FCFA\n"
                f"📚 Inscription : {amount:,} FCFA\n"
                f"📉 Manquant : {amount - balance:,} FCFA"
            ),
        }

    try:
        debit_money(
            payer_username,
            amount,
        )
    except ValueError:
        return {
            "success": False,
            "reason": "insufficient_funds",
            "message": (
                "❌ Le paiement a été refusé : "
                "solde insuffisant."
            ),
        }

    payment_id = record_payment(
        student_username=student_username,
        payer_username=payer_username,
        school_id=school_id,
        level=level,
        amount=amount,
    )

    return {
        "success": True,
        "payment_id": payment_id,
        "student": student_username,
        "payer": payer_username,
        "school_id": school_id,
        "level": level.lower(),
        "amount": amount,
        "message": (
            "✅ <b>INSCRIPTION PAYÉE</b>\n\n"
            f"👤 Élève : @{student_username}\n"
            f"💰 Montant : {amount:,} FCFA\n"
            f"🧾 Paiement : #{payment_id}"
        ),
    }


# ============================================================
# HISTORIQUE DES PAIEMENTS
# ============================================================

def get_payment_history(
    username: str,
) -> list[dict]:
    """
    Retourne les paiements liés à un élève ou à un payeur.
    """

    username = username.strip().lower()

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM school_payments
        WHERE student_username = ?
           OR payer_username = ?
        ORDER BY created_at DESC, id DESC
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
# INITIALISATION
# ============================================================

setup_payment_database()
