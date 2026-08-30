"""
Manu World — Inventory System

Gestion de l'inventaire des joueurs.

Fonctions :
- ajouter un objet ;
- retirer un objet ;
- vérifier la quantité ;
- acheter/recevoir des objets via les systèmes externes ;
- utiliser un objet ;
- consulter l'inventaire ;
- offrir un objet à un autre joueur ;
- historique des cadeaux.

IMPORTANT :
Ce module ne branche pas main.py.
Le raccordement Telegram sera fait à la fin.
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

    return conn


# ============================================================
# BASE DE DONNÉES
# ============================================================

def setup_inventory_database() -> None:

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL,

            item_id TEXT NOT NULL,

            item_name TEXT NOT NULL,

            category TEXT NOT NULL DEFAULT 'general',

            quantity INTEGER NOT NULL DEFAULT 0,

            UNIQUE(username, item_id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sender TEXT NOT NULL,

            receiver TEXT NOT NULL,

            item_id TEXT NOT NULL,

            item_name TEXT NOT NULL,

            quantity INTEGER NOT NULL,

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            )
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_inventory_username
        ON inventory_items(username)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_inventory_gifts_receiver
        ON inventory_gifts(receiver)
        """
    )

    conn.commit()

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


def normalize_item_id(
    item_id: str,
) -> str:

    item_id = str(
        item_id
    ).strip().lower()

    if not item_id:
        raise ValueError(
            "Item ID obligatoire."
        )

    return item_id


# ============================================================
# CATALOGUE D'OBJETS
# ============================================================

ITEM_CATALOG = {

    # --------------------------------------------------------
    # TÉLÉPHONES
    # --------------------------------------------------------

    "basic_phone": {
        "name": "📱 Basic Phone",
        "category": "phone",
    },

    "smartphone": {
        "name": "📱 Smartphone",
        "category": "phone",
    },

    "premium_phone": {
        "name": "📱 Premium Phone",
        "category": "phone",
    },

    "luxury_phone": {
        "name": "📱 Luxury Phone",
        "category": "phone",
    },

    # --------------------------------------------------------
    # OBJETS DU QUOTIDIEN
    # --------------------------------------------------------

    "watch": {
        "name": "⌚ Montre",
        "category": "accessory",
    },

    "laptop": {
        "name": "💻 Ordinateur portable",
        "category": "electronics",
    },

    "headphones": {
        "name": "🎧 Casque audio",
        "category": "electronics",
    },

    "camera": {
        "name": "📷 Appareil photo",
        "category": "electronics",
    },

    # --------------------------------------------------------
    # VÉHICULES / ACCESSOIRES
    # --------------------------------------------------------

    "car_key": {
        "name": "🔑 Clé de voiture",
        "category": "vehicle",
    },

    # --------------------------------------------------------
    # DIVERS
    # --------------------------------------------------------

    "gift_box": {
        "name": "🎁 Coffret cadeau",
        "category": "general",
    },

    "gold_watch": {
        "name": "⌚ Montre en or",
        "category": "luxury",
    },
}


# ============================================================
# CATALOGUE
# ============================================================

def get_item_definition(
    item_id: str,
) -> Optional[dict]:

    item_id = normalize_item_id(
        item_id
    )

    definition = ITEM_CATALOG.get(
        item_id
    )

    if definition is None:
        return None

    return {
        "item_id": item_id,
        **definition,
    }


# ============================================================
# AJOUTER
# ============================================================

def add_item(
    username: str,
    item_id: str,
    quantity: int = 1,
    item_name: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:

    username = normalize_username(
        username
    )

    item_id = normalize_item_id(
        item_id
    )

    if quantity <= 0:

        return {
            "success": False,
            "message": (
                "❌ La quantité doit être "
                "supérieure à 0."
            ),
        }

    definition = get_item_definition(
        item_id
    )

    if definition:

        if item_name is None:
            item_name = definition["name"]

        if category is None:
            category = definition["category"]

    else:

        if item_name is None:
            item_name = item_id

        if category is None:
            category = "general"

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT quantity
        FROM inventory_items
        WHERE username = ?
          AND item_id = ?
        LIMIT 1
        """,
        (
            username,
            item_id,
        ),
    ).fetchone()

    if existing:

        new_quantity = (
            existing["quantity"]
            + quantity
        )

        conn.execute(
            """
            UPDATE inventory_items
            SET
                quantity = ?,
                item_name = ?,
                category = ?
            WHERE username = ?
              AND item_id = ?
            """,
            (
                new_quantity,
                item_name,
                category,
                username,
                item_id,
            ),
        )

    else:

        new_quantity = quantity

        conn.execute(
            """
            INSERT INTO inventory_items (
                username,
                item_id,
                item_name,
                category,
                quantity
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                item_id,
                item_name,
                category,
                quantity,
            ),
        )

    conn.commit()

    conn.close()

    return {
        "success": True,
        "username": username,
        "item_id": item_id,
        "item_name": item_name,
        "quantity": new_quantity,
        "message": (
            f"✅ {quantity}x {item_name} "
            "ajouté à l'inventaire."
        ),
    }


# ============================================================
# QUANTITÉ
# ============================================================

def get_item_quantity(
    username: str,
    item_id: str,
) -> int:

    username = normalize_username(
        username
    )

    item_id = normalize_item_id(
        item_id
    )

    conn = get_connection()

    row = conn.execute(
        """
        SELECT quantity
        FROM inventory_items
        WHERE username = ?
          AND item_id = ?
        LIMIT 1
        """,
        (
            username,
            item_id,
        ),
    ).fetchone()

    conn.close()

    if row is None:
        return 0

    return int(
        row["quantity"]
    )


# ============================================================
# VÉRIFIER
# ============================================================

def has_item(
    username: str,
    item_id: str,
    quantity: int = 1,
) -> bool:

    if quantity <= 0:
        return True

    return (
        get_item_quantity(
            username,
            item_id,
        )
        >= quantity
    )


# ============================================================
# RETIRER
# ============================================================

def remove_item(
    username: str,
    item_id: str,
    quantity: int = 1,
) -> dict:

    username = normalize_username(
        username
    )

    item_id = normalize_item_id(
        item_id
    )

    if quantity <= 0:

        return {
            "success": False,
            "message": (
                "❌ Quantité invalide."
            ),
        }

    current = get_item_quantity(
        username,
        item_id,
    )

    if current < quantity:

        return {
            "success": False,
            "reason": "insufficient_quantity",
            "message": (
                f"❌ Tu ne possèdes pas "
                f"{quantity}x {item_id}."
            ),
        }

    new_quantity = (
        current - quantity
    )

    conn = get_connection()

    if new_quantity == 0:

        conn.execute(
            """
            DELETE FROM inventory_items
            WHERE username = ?
              AND item_id = ?
            """,
            (
                username,
                item_id,
            ),
        )

    else:

        conn.execute(
            """
            UPDATE inventory_items
            SET quantity = ?
            WHERE username = ?
              AND item_id = ?
            """,
            (
                new_quantity,
                username,
                item_id,
            ),
        )

    conn.commit()

    conn.close()

    return {
        "success": True,
        "item_id": item_id,
        "removed": quantity,
        "remaining": new_quantity,
        "message": (
            f"✅ {quantity}x {item_id} "
            "retiré de l'inventaire."
        ),
    }


# ============================================================
# UTILISER
# ============================================================

def use_item(
    username: str,
    item_id: str,
    quantity: int = 1,
) -> dict:

    username = normalize_username(
        username
    )

    item_id = normalize_item_id(
        item_id
    )

    if not has_item(
        username,
        item_id,
        quantity,
    ):

        return {
            "success": False,
            "message": (
                "❌ Tu ne possèdes pas "
                "assez de cet objet."
            ),
        }

    result = remove_item(
        username,
        item_id,
        quantity,
    )

    if not result["success"]:
        return result

    return {
        "success": True,
        "item_id": item_id,
        "quantity": quantity,
        "message": (
            f"✅ {quantity}x {item_id} "
            "utilisé."
        ),
    }


# ============================================================
# INVENTAIRE
# ============================================================

def get_inventory(
    username: str,
) -> list[dict]:

    username = normalize_username(
        username
    )

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM inventory_items
        WHERE username = ?
          AND quantity > 0
        ORDER BY category ASC, item_name ASC
        """,
        (username,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# FORMAT INVENTAIRE
# ============================================================

def format_inventory(
    username: str,
) -> str:

    username = normalize_username(
        username
    )

    items = get_inventory(
        username
    )

    lines = [
        "🎒 <b>MON INVENTAIRE</b>",
        "",
        f"👤 @{username}",
        "",
    ]

    if not items:

        lines.append(
            "📭 Ton inventaire est vide."
        )

        return "\n".join(lines)

    current_category = None

    for item in items:

        category = item["category"]

        if category != current_category:

            current_category = category

            lines.extend(
                [
                    "",
                    f"📦 <b>{category.upper()}</b>",
                ]
            )

        lines.append(
            f"   └─ {item['item_name']} "
            f"x{item['quantity']}"
        )

    return "\n".join(lines)


# ============================================================
# CADEAUX
# ============================================================

def gift_item(
    sender: str,
    receiver: str,
    item_id: str,
    quantity: int = 1,
) -> dict:

    sender = normalize_username(
        sender
    )

    receiver = normalize_username(
        receiver
    )

    item_id = normalize_item_id(
        item_id
    )

    if sender == receiver:

        return {
            "success": False,
            "message": (
                "❌ Tu ne peux pas t'envoyer "
                "un cadeau à toi-même."
            ),
        }

    if quantity <= 0:

        return {
            "success": False,
            "message": (
                "❌ Quantité invalide."
            ),
        }

    if not has_item(
        sender,
        item_id,
        quantity,
    ):

        return {
            "success": False,
            "message": (
                "❌ Tu ne possèdes pas "
                "assez de cet objet."
            ),
        }

    definition = get_item_definition(
        item_id
    )

    item_name = (
        definition["name"]
        if definition
        else item_id
    )

    removed = remove_item(
        sender,
        item_id,
        quantity,
    )

    if not removed["success"]:
        return removed

    added = add_item(
        receiver,
        item_id,
        quantity,
        item_name=item_name,
        category=(
            definition["category"]
            if definition
            else "general"
        ),
    )

    if not added["success"]:

        # Sécurité : restituer les objets
        # si l'ajout au destinataire échoue.
        add_item(
            sender,
            item_id,
            quantity,
            item_name=item_name,
            category=(
                definition["category"]
                if definition
                else "general"
            ),
        )

        return {
            "success": False,
            "message": (
                "❌ Le cadeau n'a pas pu "
                "être transféré."
            ),
        }

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO inventory_gifts (
            sender,
            receiver,
            item_id,
            item_name,
            quantity
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            sender,
            receiver,
            item_id,
            item_name,
            quantity,
        ),
    )

    conn.commit()

    conn.close()

    return {
        "success": True,
        "sender": sender,
        "receiver": receiver,
        "item_id": item_id,
        "item_name": item_name,
        "quantity": quantity,
        "message": (
            f"🎁 {quantity}x {item_name} "
            f"envoyé à @{receiver}."
        ),
    }


# ============================================================
# HISTORIQUE DES CADEAUX
# ============================================================

def get_gift_history(
    username: str,
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

    rows = conn.execute(
        """
        SELECT *
        FROM inventory_gifts
        WHERE sender = ?
           OR receiver = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (
            username,
            username,
            limit,
        ),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# BOUTONS
# ============================================================

def inventory_buttons() -> list[
    list[tuple[str, str]]
]:

    return [
        [
            (
                "lw_inventory:list",
                "🎒 Inventaire",
            ),
            (
                "lw_inventory:gifts",
                "🎁 Cadeaux",
            ),
        ]
    ]


def item_action_buttons(
    item_id: str,
) -> list[list[tuple[str, str]]]:

    item_id = normalize_item_id(
        item_id
    )

    return [
        [
            (
                f"lw_inventory:use:{item_id}",
                "⚙️ Utiliser",
            ),
            (
                f"lw_inventory:gift:{item_id}",
                "🎁 Offrir",
            ),
        ]
    ]


# ============================================================
# CALLBACK
# ============================================================

def parse_inventory_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) < 2:

        raise ValueError(
            "Callback inventaire invalide."
        )

    if parts[0] != "lw_inventory":

        raise ValueError(
            "Callback inventaire inconnu."
        )

    action = parts[1]

    allowed = {
        "list",
        "gifts",
        "use",
        "gift",
    }

    if action not in allowed:

        raise ValueError(
            "Action inventaire inconnue."
        )

    result = {
        "type": "inventory",
        "action": action,
    }

    if len(parts) == 3:

        result["item_id"] = (
            normalize_item_id(parts[2])
        )

    return result


# ============================================================
# AIDE
# ============================================================

def inventory_help() -> str:

    return (
        "🎒 <b>INVENTAIRE</b>\n\n"

        "Voir ton inventaire :\n"
        "<code>/inventory</code>\n\n"

        "Offrir un objet :\n"
        "<code>/giftinventory @username "
        "item_id quantité</code>\n\n"

        "Exemple :\n"
        "<code>/giftinventory @Alex "
        "smartphone 1</code>"
    )


# ============================================================
# INITIALISATION
# ============================================================

setup_inventory_database()


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "ITEM_CATALOG",
    "setup_inventory_database",
    "get_item_definition",
    "add_item",
    "get_item_quantity",
    "has_item",
    "remove_item",
    "use_item",
    "get_inventory",
    "format_inventory",
    "gift_item",
    "get_gift_history",
    "inventory_buttons",
    "item_action_buttons",
    "parse_inventory_callback",
    "inventory_help",
]