"""
Life World — Friend Commands

Prépare la logique des commandes d'amitié.

Commandes prévues :

/friend @username
/acceptfriend @username
/declinefriend @username
/friends
/friendrequests

La cible peut également être récupérée depuis un message
auquel le joueur répond.

Exemples :

/friend @player

ou :

[réponse au message de @player]
/friend

IMPORTANT :
Ce fichier ne modifie pas main.py.
"""

from __future__ import annotations

from typing import Optional

try:
    from ..systems.family_relationships import (
        send_friend_request,
        accept_friend_request,
        decline_friend_request,
        get_friends,
        get_pending_friend_requests,
        get_sent_friend_requests,
        resolve_target,
    )
except ImportError:

    from ..systems.family_relationships import (
        send_friend_request,
        accept_friend_request,
        decline_friend_request,
        get_friends,
        get_pending_friend_requests,
        get_sent_friend_requests,
        resolve_target,
    )


# ============================================================
# CIBLE
# ============================================================

def resolve_friend_target(
    username: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> Optional[str]:

    return resolve_target(
        username=username,
        replied_username=replied_username,
    )


# ============================================================
# ENVOYER UNE DEMANDE
# ============================================================

def create_friend_request(
    requester: str,
    target: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    target = resolve_friend_target(
        username=target,
        replied_username=replied_username,
    )

    if not target:
        return {
            "success": False,
            "reason": "target_missing",
            "message": (
                "❌ Indique un @username ou "
                "réponds au message de la personne."
            ),
        }

    return send_friend_request(
        requester,
        target,
    )


# ============================================================
# ACCEPTER
# ============================================================

def accept_request(
    username: str,
    requester: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    requester = resolve_friend_target(
        username=requester,
        replied_username=replied_username,
    )

    if not requester:
        return {
            "success": False,
            "reason": "requester_missing",
            "message": (
                "❌ Indique le @username de la personne "
                "ou réponds à sa demande."
            ),
        }

    return accept_friend_request(
        username,
        requester,
    )


# ============================================================
# REFUSER
# ============================================================

def decline_request(
    username: str,
    requester: Optional[str] = None,
    replied_username: Optional[str] = None,
) -> dict:

    requester = resolve_friend_target(
        username=requester,
        replied_username=replied_username,
    )

    if not requester:
        return {
            "success": False,
            "reason": "requester_missing",
            "message": (
                "❌ Indique le @username de la personne "
                "ou réponds à sa demande."
            ),
        }

    deleted = decline_friend_request(
        username,
        requester,
    )

    if not deleted:
        return {
            "success": False,
            "reason": "not_found",
            "message": (
                "❌ Demande d'amitié introuvable."
            ),
        }

    return {
        "success": True,
        "message": (
            f"❌ Demande de @{requester} refusée."
        ),
    }


# ============================================================
# LISTE DES AMIS
# ============================================================

def friends_list(
    username: str,
) -> dict:

    friends = get_friends(
        username
    )

    if not friends:
        return {
            "success": True,
            "friends": [],
            "message": (
                "🤝 <b>MES AMIS</b>\n\n"
                "Tu n'as encore aucun ami."
            ),
        }

    lines = [
        "🤝 <b>MES AMIS</b>",
        "",
    ]

    for index, friend in enumerate(
        friends,
        start=1,
    ):
        lines.append(
            f"{index}. @{friend}"
        )

    return {
        "success": True,
        "friends": friends,
        "message": "\n".join(lines),
    }


# ============================================================
# DEMANDES REÇUES
# ============================================================

def incoming_requests(
    username: str,
) -> dict:

    requests = get_pending_friend_requests(
        username
    )

    if not requests:
        return {
            "success": True,
            "requests": [],
            "message": (
                "📨 <b>DEMANDES D'AMITIÉ</b>\n\n"
                "Aucune demande en attente."
            ),
        }

    result = []

    lines = [
        "📨 <b>DEMANDES D'AMITIÉ</b>",
        "",
    ]

    for request in requests:

        requester = request[
            "requested_by"
        ]

        result.append(
            {
                "requester": requester,
                "request_id": request["id"],
                "accept_callback": (
                    f"lw_friend:accept:"
                    f"{requester}"
                ),
                "decline_callback": (
                    f"lw_friend:decline:"
                    f"{requester}"
                ),
            }
        )

        lines.append(
            f"👤 @{requester}"
        )
        lines.append(
            f"   ├─ ✅ Accepter"
        )
        lines.append(
            f"   └─ ❌ Refuser"
        )
        lines.append("")

    return {
        "success": True,
        "requests": result,
        "message": "\n".join(lines),
    }


# ============================================================
# DEMANDES ENVOYÉES
# ============================================================

def outgoing_requests(
    username: str,
) -> dict:

    requests = get_sent_friend_requests(
        username
    )

    if not requests:
        return {
            "success": True,
            "requests": [],
            "message": (
                "📤 <b>DEMANDES ENVOYÉES</b>\n\n"
                "Aucune demande en attente."
            ),
        }

    lines = [
        "📤 <b>DEMANDES ENVOYÉES</b>",
        "",
    ]

    result = []

    for request in requests:

        target = (
            request["user_two"]
            if request["user_one"]
            == username
            else request["user_one"]
        )

        result.append(
            {
                "target": target,
                "request_id": request["id"],
            }
        )

        lines.append(
            f"⏳ @{target}"
        )

    return {
        "success": True,
        "requests": result,
        "message": "\n".join(lines),
    }


# ============================================================
# PLUSIEURS DEMANDES
# ============================================================

def send_multiple_friend_requests(
    requester: str,
    targets: list[str],
) -> dict:
    """
    Permet d'envoyer plusieurs demandes dans une seule
    commande.

    Exemple logique :

    /friend @A @B @C @D

    Chaque cible est traitée indépendamment.
    Une erreur sur une personne ne bloque pas
    les autres demandes.
    """

    if not targets:
        return {
            "success": False,
            "message": (
                "❌ Aucune cible fournie."
            ),
            "results": [],
        }

    results = []

    success_count = 0

    for target in targets:

        result = send_friend_request(
            requester,
            target,
        )

        results.append(
            {
                "target": target,
                "result": result,
            }
        )

        if result["success"]:
            success_count += 1

    lines = [
        "🤝 <b>DEMANDES D'AMITIÉ</b>",
        "",
        f"📨 Envoyées : "
        f"<b>{success_count}/{len(targets)}</b>",
        "",
    ]

    for item in results:

        target = item["target"]
        result = item["result"]

        if result["success"]:
            lines.append(
                f"✅ @{target}"
            )
        else:
            lines.append(
                f"❌ @{target} — "
                f"{result.get('message', 'Refusée')}"
            )

    return {
        "success": success_count > 0,
        "success_count": success_count,
        "total": len(targets),
        "results": results,
        "message": "\n".join(lines),
    }


# ============================================================
# CALLBACKS
# ============================================================

def parse_friend_callback(
    data: str,
) -> dict:

    parts = data.split(":")

    if len(parts) != 3:
        raise ValueError(
            "Callback amitié invalide."
        )

    if parts[0] != "lw_friend":
        raise ValueError(
            "Callback inconnu."
        )

    action = parts[1]
    username = parts[2]

    if action not in {
        "accept",
        "decline",
    }:
        raise ValueError(
            "Action d'amitié inconnue."
        )

    return {
        "type": "friend",
        "action": action,
        "username": username,
    }


# ============================================================
# BOUTONS DES DEMANDES
# ============================================================

def get_request_buttons(
    requester: str,
) -> list[tuple[str, str]]:

    requester = requester.strip().lstrip("@")

    return [
        (
            f"lw_friend:accept:{requester}",
            "✅ Accepter",
        ),
        (
            f"lw_friend:decline:{requester}",
            "❌ Refuser",
        ),
    ]


# ============================================================
# AIDE
# ============================================================

def friend_help() -> str:

    return (
        "🤝 <b>SYSTÈME D'AMITIÉ</b>\n\n"

        "📨 <b>Envoyer une demande</b>\n"
        "<code>/friend @username</code>\n\n"

        "👥 <b>Plusieurs personnes</b>\n"
        "<code>/friend @user1 @user2 @user3</code>\n\n"

        "↩️ <b>Depuis un message</b>\n"
        "Réponds au message puis utilise "
        "<code>/friend</code>\n\n"

        "📋 <b>Voir mes amis</b>\n"
        "<code>/friends</code>\n\n"

        "📨 <b>Demandes reçues</b>\n"
        "<code>/friendrequests</code>"
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "create_friend_request",
    "send_multiple_friend_requests",
    "accept_request",
    "decline_request",
    "friends_list",
    "incoming_requests",
    "outgoing_requests",
    "parse_friend_callback",
    "get_request_buttons",
    "friend_help",
]