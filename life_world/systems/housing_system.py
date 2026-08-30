"""
Manu World — Housing System

Gestion des logements virtuels.

Types :
- chambre
- studio
- appartement
- villa
- manoir

Fonctions :
- louer un logement ;
- payer automatiquement le loyer quotidien ;
- acheter une propriété ;
- vérifier les conditions d'achat ;
- carte d'identité obligatoire pour acheter ;
- quitter un logement ;
- consulter son logement ;
- catalogue avec prix ;
- boutons préparés pour Telegram.

IMPORTANT :
main.py n'est PAS modifié ici.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "database" / "life_world.db"


# ============================================================
# CONFIGURATION DES LOGEMENTS
# ============================================================

HOUSING_TYPES = {
    "room": {
        "name": "🛏️ Chambre",
        "rent_daily": 2_000,
        "purchase_price": None,
        "requires_id": False,
    },
    "studio": {
        "name": "🏢 Studio",
        "rent_daily": 5_000,
        "purchase_price": 2_500_000,
        "requires_id": True,
    },
    "apartment": {
        "name": "🏠 Appartement",
        "rent_daily": 10_000,
        "purchase_price": 6_000_000,
        "requires_id": True,
    },
    "villa": {
        "name": "🏡 Villa",
        "rent_daily": 25_000,
        "purchase_price": 15_000_000,
        "requires_id": True,
    },
    "mansion": {
        "name": "🏰 Manoir",
        "rent_daily": 60_000,
        "purchase_price": 40_000_000,
        "requires_id": True,
    },
}


# ============================================================
# BASE DE DONNÉES
# ============================================================

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_housing_database() -> None:
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS housing_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL,

            housing_type TEXT NOT NULL,

            ownership TEXT NOT NULL DEFAULT 'rented',

            purchase_price INTEGER NOT NULL DEFAULT 0,

            daily_rent INTEGER NOT NULL DEFAULT 0,

            rent_due INTEGER NOT NULL DEFAULT 0,

            rent_last_paid INTEGER,

            created_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            UNIQUE(username)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_housing_username
        ON housing_properties(username)
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


def get_housing_type(
    housing_type: str,
) -> dict:

    key = str(
        housing_type
    ).strip().lower()

    if key not in HOUSING_TYPES:
        raise ValueError(
            f"Type de logement inconnu : {housing_type}"
        )

    return HOUSING_TYPES[key]


# ============================================================
# CARTE D'IDENTITÉ
# ============================================================

def has_identity_card(
    username: str,
) -> bool:
    """
    Vérifie si le joueur possède une carte d'identité.

    Le système accepte plusieurs schémas courants de Life World.
    Si aucune table d'identité n'existe encore, l'achat est refusé
    plutôt que de considérer automatiquement que la carte existe.
    """

    username = normalize_username(username)

    conn = get_connection()

    # Schéma principal attendu.
    try:
        row = conn.execute(
            """
            SELECT id
            FROM identity_cards
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        conn.close()

        return row is not None

    except sqlite3.OperationalError:
        pass

    # Schéma alternatif éventuel.
    try:
        row = conn.execute(
            """
            SELECT id
            FROM identity
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        conn.close()

        return row is not None

    except sqlite3.OperationalError:
        conn.close()
        return False


# ============================================================
# LOGEMENT ACTUEL
# ============================================================

def get_current_housing(
    username: str,
) -> Optional[dict]:

    username = normalize_username(username)

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM housing_properties
        WHERE username = ?
        LIMIT 1
        """,
        (username,),
    ).fetchone()

    conn.close()

    return dict(row) if row else None


# ============================================================
# VÉRIFICATION
# ============================================================

def can_get_housing(
    username: str,
) -> tuple[bool, str]:

    username = normalize_username(username)

    current = get_current_housing(username)

    if current is not None:
        return (
            False,
            "❌ Tu possèdes déjà un logement."
        )

    return True, "OK"


# ============================================================
# LOCATION
# ============================================================

def rent_housing(
    username: str,
    housing_type: str,
) -> dict:

    username = normalize_username(username)

    definition = get_housing_type(
        housing_type
    )

    allowed, reason = can_get_housing(
        username
    )

    if not allowed:
        return {
            "success": False,
            "message": reason,
        }

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO housing_properties (
            username,
            housing_type,
            ownership,
            purchase_price,
            daily_rent,
            rent_due,
            rent_last_paid
        )
        VALUES (?, ?, 'rented', 0, ?, ?, strftime('%s', 'now'))
        """,
        (
            username,
            housing_type,
            definition["rent_daily"],
            definition["rent_daily"],
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "ownership": "rented",
        "housing_type": housing_type,
        "rent_daily": definition["rent_daily"],
        "message": (
            f"🏠 Tu loues maintenant "
            f"{definition['name']}.\n\n"
            f"💰 Loyer quotidien : "
            f"{definition['rent_daily']:,} FCFA."
        ),
    }


# ============================================================
# ACHAT
# ============================================================

def buy_housing(
    username: str,
    housing_type: str,
    balance: int,
) -> dict:

    username = normalize_username(username)

    definition = get_housing_type(
        housing_type
    )

    allowed, reason = can_get_housing(
        username
    )

    if not allowed:
        return {
            "success": False,
            "message": reason,
        }

    price = definition["purchase_price"]

    if price is None:
        return {
            "success": False,
            "message": (
                "❌ Ce logement n'est pas disponible "
                "à l'achat."
            ),
        }

    if definition["requires_id"] and not has_identity_card(
        username
    ):
        return {
            "success": False,
            "reason": "identity_required",
            "message": (
                "🪪 Une carte d'identité est obligatoire "
                "pour acheter une propriété."
            ),
        }

    if balance < price:
        return {
            "success": False,
            "reason": "insufficient_funds",
            "message": (
                f"❌ Fonds insuffisants.\n"
                f"💰 Prix : {price:,} FCFA\n"
                f"💳 Solde : {balance:,} FCFA"
            ),
        }

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO housing_properties (
            username,
            housing_type,
            ownership,
            purchase_price,
            daily_rent,
            rent_due,
            rent_last_paid
        )
        VALUES (?, ?, 'owned', ?, 0, 0, strftime('%s', 'now'))
        """,
        (
            username,
            housing_type,
            price,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "ownership": "owned",
        "housing_type": housing_type,
        "purchase_price": price,
        "message": (
            f"🏡 Félicitations !\n\n"
            f"Tu es maintenant propriétaire de "
            f"{definition['name']}.\n"
            f"💰 Prix : {price:,} FCFA."
        ),
    }


# ============================================================
# PAIEMENT DU LOYER
# ============================================================

def get_rent_due(
    username: str,
) -> int:

    username = normalize_username(username)

    housing = get_current_housing(username)

    if housing is None:
        return 0

    if housing["ownership"] != "rented":
        return 0

    return int(
        housing["rent_due"]
    )


def calculate_days_since_payment(
    housing: dict,
    now: Optional[int] = None,
) -> int:

    import time

    if now is None:
        now = int(time.time())

    last_paid = housing.get(
        "rent_last_paid"
    )

    if not last_paid:
        return 1

    elapsed = max(
        0,
        now - int(last_paid),
    )

    return elapsed // 86_400


def calculate_rent_charge(
    username: str,
    now: Optional[int] = None,
) -> dict:

    housing = get_current_housing(
        username
    )

    if housing is None:
        return {
            "success": False,
            "days": 0,
            "amount": 0,
            "message": (
                "❌ Aucun logement."
            ),
        }

    if housing["ownership"] != "rented":
        return {
            "success": True,
            "days": 0,
            "amount": 0,
            "message": (
                "🏡 Propriété achetée : "
                "aucun loyer quotidien."
            ),
        }

    days = calculate_days_since_payment(
        housing,
        now,
    )

    amount = (
        days
        * int(housing["daily_rent"])
    )

    return {
        "success": True,
        "days": days,
        "amount": amount,
        "daily_rent": housing["daily_rent"],
    }


# ============================================================
# ENREGISTRER LE LOYER DÛ
# ============================================================

def accrue_rent(
    username: str,
    now: Optional[int] = None,
) -> dict:

    username = normalize_username(username)

    import time

    if now is None:
        now = int(time.time())

    housing = get_current_housing(
        username
    )

    if housing is None:
        return {
            "success": False,
            "amount": 0,
            "message": "❌ Aucun logement.",
        }

    if housing["ownership"] != "rented":
        return {
            "success": True,
            "amount": 0,
            "message": (
                "🏡 Propriétaire : aucun loyer."
            ),
        }

    days = calculate_days_since_payment(
        housing,
        now,
    )

    if days <= 0:
        return {
            "success": True,
            "amount": 0,
            "message": (
                "✅ Aucun nouveau loyer dû."
            ),
        }

    amount = (
        days
        * int(housing["daily_rent"])
    )

    conn = get_connection()

    conn.execute(
        """
        UPDATE housing_properties
        SET
            rent_due = rent_due + ?,
            rent_last_paid = ?
        WHERE username = ?
        """,
        (
            amount,
            now,
            username,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "days": days,
        "amount": amount,
        "message": (
            f"🧾 {amount:,} FCFA "
            f"de loyer ajouté."
        ),
    }


# ============================================================
# PAYER LE LOYER
# ============================================================

def pay_rent(
    username: str,
    balance: int,
) -> dict:

    username = normalize_username(username)

    accrue_rent(username)

    housing = get_current_housing(username)

    if housing is None:
        return {
            "success": False,
            "message": "❌ Aucun logement.",
        }

    due = int(
        housing["rent_due"]
    )

    if due <= 0:
        return {
            "success": True,
            "paid": 0,
            "remaining": 0,
            "message": (
                "✅ Aucun loyer à payer."
            ),
        }

    if balance < due:
        return {
            "success": False,
            "reason": "insufficient_funds",
            "message": (
                f"❌ Solde insuffisant.\n"
                f"🧾 Loyer dû : {due:,} FCFA\n"
                f"💰 Solde : {balance:,} FCFA"
            ),
        }

    conn = get_connection()

    conn.execute(
        """
        UPDATE housing_properties
        SET rent_due = 0
        WHERE username = ?
        """,
        (username,),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "paid": due,
        "remaining": 0,
        "message": (
            f"✅ Loyer de {due:,} FCFA payé."
        ),
    }


# ============================================================
# QUITTER / VENDRE
# ============================================================

def leave_housing(
    username: str,
) -> dict:

    username = normalize_username(username)

    housing = get_current_housing(username)

    if housing is None:
        return {
            "success": False,
            "message": (
                "❌ Tu n'as aucun logement."
            ),
        }

    if housing["ownership"] == "owned":
        return {
            "success": False,
            "reason": "owned_property",
            "message": (
                "❌ Tu es propriétaire de ce logement. "
                "Utilise la vente de propriété."
            ),
        }

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM housing_properties
        WHERE username = ?
        """,
        (username,),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            "🚪 Tu as quitté ton logement."
        ),
    }


# ============================================================
# VENDRE UNE PROPRIÉTÉ
# ============================================================

def sell_housing(
    username: str,
) -> dict:

    username = normalize_username(username)

    housing = get_current_housing(username)

    if housing is None:
        return {
            "success": False,
            "message": (
                "❌ Tu n'as aucun logement."
            ),
        }

    if housing["ownership"] != "owned":
        return {
            "success": False,
            "message": (
                "❌ Ce logement est loué."
            ),
        }

    purchase_price = int(
        housing["purchase_price"]
    )

    # Valeur de revente par défaut : 70 %.
    resale_value = int(
        purchase_price * 0.70
    )

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM housing_properties
        WHERE username = ?
        """,
        (username,),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "resale_value": resale_value,
        "message": (
            f"🏷️ Propriété vendue.\n"
            f"💰 Montant récupéré : "
            f"{resale_value:,} FCFA."
        ),
    }


# ============================================================
# CATALOGUE
# ============================================================

def housing_catalog() -> list[dict]:

    catalog = []

    for key, definition in HOUSING_TYPES.items():

        catalog.append(
            {
                "id": key,
                "name": definition["name"],
                "rent_daily": definition["rent_daily"],
                "purchase_price": (
                    definition["purchase_price"]
                ),
                "requires_id": (
                    definition["requires_id"]
                ),
            }
        )

    return catalog


def format_housing_catalog() -> str:

    lines = [
        "🏠 <b>CATALOGUE DES LOGEMENTS</b>",
        "",
    ]

    for item in housing_catalog():

        lines.append(
            f"{item['name']}"
        )

        lines.append(
            f"   💰 Location : "
            f"{item['rent_daily']:,} FCFA/jour"
        )

        if item["purchase_price"] is not None:

            lines.append(
                f"   🏡 Achat : "
                f"{item['purchase_price']:,} FCFA"
            )

        else:

            lines.append(
                "   🏡 Achat : indisponible"
            )

        if item["requires_id"]:

            lines.append(
                "   🪪 Carte d'identité requise"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# BOUTONS
# ============================================================

def housing_catalog_buttons() -> list[
    list[tuple[str, str]]
]:

    buttons = []

    for key, definition in HOUSING_TYPES.items():

        buttons.append(
            [
                (
                    f"lw_housing:view:{key}",
                    definition["name"],
                )
            ]
        )

    return buttons


def housing_action_buttons(
    housing_type: str,
) -> list[list[tuple[str, str]]]:

    housing_type = str(
        housing_type
    ).strip().lower()

    definition = get_housing_type(
        housing_type
    )

    buttons = [
        [
            (
                f"lw_housing:rent:{housing_type}",
                "🔑 Louer",
            )
        ]
    ]

    if definition["purchase_price"] is not None:

        buttons.append(
            [
                (
                    f"lw_housing:buy:{housing_type}",
                    "🏡 Acheter",
                )
            ]
        )

    return buttons


def current_housing_buttons() -> list[
    list[tuple[str, str]]
]:

    return [
        [
            (
                "lw_housing:payrent",
                "🧾 Payer le loyer",
            ),
        ],
        [
            (
                "lw_housing:leave",
                "🚪 Quitter",
            ),
        ],
    ]


# ============================================================
# CALLBACK
# ============================================================

def parse_housing_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) < 2:
        raise ValueError(
            "Callback logement invalide."
        )

    if parts[0] != "lw_housing":
        raise ValueError(
            "Callback logement inconnu."
        )

    action = parts[1]

    allowed = {
        "view",
        "rent",
        "buy",
        "payrent",
        "leave",
    }

    if action not in allowed:
        raise ValueError(
            "Action logement inconnue."
        )

    result = {
        "type": "housing",
        "action": action,
    }

    if len(parts) == 3:
        result["housing_type"] = parts[2]

    return result


# ============================================================
# RÉSUMÉ
# ============================================================

def format_current_housing(
    username: str,
) -> str:

    username = normalize_username(username)

    housing = get_current_housing(username)

    if housing is None:

        return (
            "🏠 <b>LOGEMENT</b>\n\n"
            "Tu n'as actuellement aucun logement."
        )

    definition = get_housing_type(
        housing["housing_type"]
    )

    ownership = (
        "🏡 Propriétaire"
        if housing["ownership"] == "owned"
        else "🔑 Locataire"
    )

    lines = [
        "🏠 <b>MON LOGEMENT</b>",
        "",
        f"🏠 Type : {definition['name']}",
        f"📌 Statut : {ownership}",
    ]

    if housing["ownership"] == "rented":

        lines.extend(
            [
                f"💰 Loyer quotidien : "
                f"{housing['daily_rent']:,} FCFA",
                f"🧾 Loyer dû : "
                f"{housing['rent_due']:,} FCFA",
            ]
        )

    else:

        lines.append(
            f"💵 Prix d'achat : "
            f"{housing['purchase_price']:,} FCFA"
        )

    return "\n".join(lines)


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "HOUSING_TYPES",
    "setup_housing_database",
    "has_identity_card",
    "get_current_housing",
    "can_get_housing",
    "rent_housing",
    "buy_housing",
    "get_rent_due",
    "calculate_rent_charge",
    "accrue_rent",
    "pay_rent",
    "leave_housing",
    "sell_housing",
    "housing_catalog",
    "format_housing_catalog",
    "housing_catalog_buttons",
    "housing_action_buttons",
    "current_housing_buttons",
    "parse_housing_callback",
    "format_current_housing",
]


setup_housing_database()
