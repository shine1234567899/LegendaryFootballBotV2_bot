"""
Manu World — Wealth System

Calcul des éléments économiques personnels du joueur.

Gère :
- patrimoine estimé ;
- richesse liquide ;
- valeur des propriétés ;
- valeur des objets d'inventaire ;
- limites de catégorie ;
- classement de richesse ;
- résumé financier.

IMPORTANT :
Ce système ne retire ni n'ajoute directement d'argent.
Il calcule les valeurs à partir des autres systèmes.

main.py n'est PAS modifié ici.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "database" / "life_world.db"


# ============================================================
# VALEURS DE REFERENCE DES OBJETS
# ============================================================

ITEM_VALUES = {
    "basic_phone": 25_000,
    "smartphone": 100_000,
    "premium_phone": 300_000,
    "luxury_phone": 1_000_000,

    "watch": 50_000,
    "laptop": 400_000,
    "headphones": 75_000,
    "camera": 250_000,

    "car_key": 0,
    "gift_box": 10_000,
    "gold_watch": 500_000,
}


# ============================================================
# CONNEXION
# ============================================================

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# UTILITAIRES
# ============================================================

def normalize_username(username: str) -> str:
    username = str(username).strip()

    if username.startswith("@"):
        username = username[1:]

    username = username.lower()

    if not username:
        raise ValueError("Username obligatoire.")

    return username


# ============================================================
# SOLDE
# ============================================================

def get_cash_balance(username: str) -> int:
    """
    Recherche le solde dans les structures bancaires courantes
    de Manu World.

    Si le système bancaire n'est pas encore présent, retourne 0.
    Le système ne crée pas de table bancaire ici afin d'éviter
    de dupliquer le système bancaire déjà construit.
    """

    username = normalize_username(username)

    conn = get_connection()

    # Schéma principal possible.
    try:
        row = conn.execute(
            """
            SELECT balance
            FROM bank_accounts
            WHERE username = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        if row is not None:
            conn.close()
            return int(row["balance"] or 0)

    except sqlite3.OperationalError:
        pass

    # Schéma alternatif possible.
    try:
        row = conn.execute(
            """
            SELECT balance
            FROM accounts
            WHERE username = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        if row is not None:
            conn.close()
            return int(row["balance"] or 0)

    except sqlite3.OperationalError:
        pass

    conn.close()
    return 0


# ============================================================
# VALEUR DES PROPRIETES
# ============================================================

def get_property_value(
    username: str,
) -> int:

    username = normalize_username(username)

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT purchase_price
            FROM housing_properties
            WHERE username = ?
              AND ownership = 'owned'
            """,
            (username,),
        ).fetchall()

        conn.close()

        return sum(
            int(row["purchase_price"] or 0)
            for row in rows
        )

    except sqlite3.OperationalError:
        conn.close()
        return 0


# ============================================================
# VALEUR INVENTAIRE
# ============================================================

def get_inventory_value(
    username: str,
) -> int:

    username = normalize_username(username)

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT item_id, quantity
            FROM inventory_items
            WHERE username = ?
              AND quantity > 0
            """,
            (username,),
        ).fetchall()

        conn.close()

    except sqlite3.OperationalError:
        conn.close()
        return 0

    total = 0

    for row in rows:
        item_value = ITEM_VALUES.get(
            str(row["item_id"]).lower(),
            0,
        )

        total += (
            item_value
            * int(row["quantity"])
        )

    return total


# ============================================================
# VALEUR CARTES DE CREDIT
# ============================================================

def get_credit_exposure(
    username: str,
) -> int:

    """
    Dette actuellement utilisée sur les cartes de crédit.
    """

    username = normalize_username(username)

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT COALESCE(
                SUM(used_credit),
                0
            ) AS total
            FROM credit_cards
            WHERE username = ?
              AND status != 'cancelled'
            """,
            (username,),
        ).fetchone()

        conn.close()

        return int(row["total"] or 0)

    except sqlite3.OperationalError:
        conn.close()
        return 0


# ============================================================
# PATRIMOINE
# ============================================================

def calculate_wealth(
    username: str,
) -> dict:

    username = normalize_username(username)

    cash = get_cash_balance(
        username
    )

    properties = get_property_value(
        username
    )

    inventory = get_inventory_value(
        username
    )

    credit_debt = get_credit_exposure(
        username
    )

    gross_wealth = (
        cash
        + properties
        + inventory
    )

    net_wealth = max(
        0,
        gross_wealth - credit_debt,
    )

    return {
        "username": username,

        "cash": cash,

        "properties": properties,

        "inventory": inventory,

        "credit_debt": credit_debt,

        "gross_wealth": gross_wealth,

        "net_wealth": net_wealth,
    }


# ============================================================
# NIVEAU DE RICHESSE
# ============================================================

def wealth_level(
    net_wealth: int,
) -> str:

    net_wealth = int(net_wealth)

    if net_wealth >= 100_000_000:
        return "👑 Milliardaire du monde"

    if net_wealth >= 50_000_000:
        return "💎 Ultra riche"

    if net_wealth >= 20_000_000:
        return "🏆 Très riche"

    if net_wealth >= 10_000_000:
        return "💰 Riche"

    if net_wealth >= 5_000_000:
        return "💵 Aisé"

    if net_wealth >= 1_000_000:
        return "🙂 Stable"

    if net_wealth >= 250_000:
        return "🌱 En progression"

    return "🪙 Débutant"


# ============================================================
# FORMAT PATRIMOINE
# ============================================================

def format_wealth(
    username: str,
) -> str:

    data = calculate_wealth(
        username
    )

    level = wealth_level(
        data["net_wealth"]
    )

    return (
        "💰 <b>PATRIMOINE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 @{data['username']}\n"
        f"🏷️ Niveau : <b>{level}</b>\n\n"
        f"💵 Argent liquide : "
        f"<b>{data['cash']:,} FCFA</b>\n"
        f"🏠 Propriétés : "
        f"<b>{data['properties']:,} FCFA</b>\n"
        f"🎒 Inventaire : "
        f"<b>{data['inventory']:,} FCFA</b>\n"
        f"💳 Crédit utilisé : "
        f"<b>{data['credit_debt']:,} FCFA</b>\n\n"
        f"📊 Patrimoine brut : "
        f"<b>{data['gross_wealth']:,} FCFA</b>\n"
        f"💎 Patrimoine net : "
        f"<b>{data['net_wealth']:,} FCFA</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# COMPARAISON
# ============================================================

def compare_wealth(
    user_one: str,
    user_two: str,
) -> dict:

    first = calculate_wealth(
        user_one
    )

    second = calculate_wealth(
        user_two
    )

    difference = (
        first["net_wealth"]
        - second["net_wealth"]
    )

    return {
        "first": first,
        "second": second,
        "difference": difference,
        "leader": (
            first["username"]
            if difference > 0
            else second["username"]
            if difference < 0
            else None
        ),
    }


def format_wealth_comparison(
    user_one: str,
    user_two: str,
) -> str:

    data = compare_wealth(
        user_one,
        user_two,
    )

    first = data["first"]
    second = data["second"]

    if data["leader"] is None:
        result = "🤝 Égalité"

    else:
        result = (
            f"👑 @{data['leader']} "
            "est devant."
        )

    return (
        "💰 <b>COMPARAISON DE PATRIMOINE</b>\n\n"
        f"👤 @{first['username']} : "
        f"<b>{first['net_wealth']:,} FCFA</b>\n"
        f"👤 @{second['username']} : "
        f"<b>{second['net_wealth']:,} FCFA</b>\n\n"
        f"{result}"
    )


# ============================================================
# BOUTONS
# ============================================================

def wealth_buttons() -> list[
    list[tuple[str, str]]
]:

    return [
        [
            (
                "lw_wealth:view",
                "💰 Patrimoine",
            ),
            (
                "lw_wealth:compare",
                "⚖️ Comparer",
            ),
        ]
    ]


def parse_wealth_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 2:
        raise ValueError(
            "Callback patrimoine invalide."
        )

    if parts[0] != "lw_wealth":
        raise ValueError(
            "Callback patrimoine inconnu."
        )

    if parts[1] not in {
        "view",
        "compare",
    }:
        raise ValueError(
            "Action patrimoine inconnue."
        )

    return {
        "type": "wealth",
        "action": parts[1],
    }


# ============================================================
# AIDE
# ============================================================

def wealth_help() -> str:

    return (
        "💰 <b>PATRIMOINE</b>\n\n"
        "<code>/wealth</code>\n"
        "Affiche ton patrimoine estimé.\n\n"
        "<code>/wealth @username</code>\n"
        "Permettra plus tard de comparer "
        "les patrimoines."
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "ITEM_VALUES",
    "get_cash_balance",
    "get_property_value",
    "get_inventory_value",
    "get_credit_exposure",
    "calculate_wealth",
    "wealth_level",
    "format_wealth",
    "compare_wealth",
    "format_wealth_comparison",
    "wealth_buttons",
    "parse_wealth_callback",
    "wealth_help",
]
