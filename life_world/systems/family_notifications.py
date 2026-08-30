"""
Life World — Family Notifications

Prépare les notifications à envoyer lors des événements
familiaux :

- demande d'amitié ;
- acceptation/refus d'amitié ;
- demande en mariage ;
- acceptation/refus du mariage ;
- demande d'adoption ;
- acceptation/refus de l'adoption ;
- divorce.

Ce module ne fait PAS directement l'envoi Telegram.
Il produit des événements propres que main.py pourra envoyer
plus tard.

IMPORTANT :
main.py sera raccordé à la fin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ============================================================
# ÉVÉNEMENTS
# ============================================================

@dataclass
class FamilyNotification:

    recipient: str

    event_type: str

    title: str

    message: str

    sender: Optional[str] = None

    target: Optional[str] = None

    callback_data: Optional[str] = None


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

    if not username:
        raise ValueError(
            "Username obligatoire."
        )

    return username.lower()


# ============================================================
# AMITIÉ
# ============================================================

def friend_request_notification(
    requester: str,
    target: str,
) -> FamilyNotification:

    requester = normalize_username(
        requester
    )

    target = normalize_username(
        target
    )

    return FamilyNotification(
        recipient=target,
        sender=requester,
        target=target,
        event_type="friend_request",
        title="🤝 Nouvelle demande d'amitié",
        message=(
            f"🤝 <b>@{requester}</b> "
            "veut devenir ton ami(e).\n\n"
            "Choisis une option :"
        ),
        callback_data=(
            f"lw_friend:accept:{requester}"
        ),
    )


def friend_accepted_notification(
    accepter: str,
    requester: str,
) -> FamilyNotification:

    accepter = normalize_username(
        accepter
    )

    requester = normalize_username(
        requester
    )

    return FamilyNotification(
        recipient=requester,
        sender=accepter,
        target=requester,
        event_type="friend_accepted",
        title="🤝 Demande acceptée",
        message=(
            f"🤝 <b>@{accepter}</b> "
            "a accepté ta demande d'amitié."
        ),
    )


def friend_declined_notification(
    decliner: str,
    requester: str,
) -> FamilyNotification:

    decliner = normalize_username(
        decliner
    )

    requester = normalize_username(
        requester
    )

    return FamilyNotification(
        recipient=requester,
        sender=decliner,
        target=requester,
        event_type="friend_declined",
        title="❌ Demande refusée",
        message=(
            f"❌ <b>@{decliner}</b> "
            "a refusé ta demande d'amitié."
        ),
    )


# ============================================================
# MARIAGE
# ============================================================

def marriage_request_notification(
    requester: str,
    target: str,
) -> FamilyNotification:

    requester = normalize_username(
        requester
    )

    target = normalize_username(
        target
    )

    return FamilyNotification(
        recipient=target,
        sender=requester,
        target=target,
        event_type="marriage_request",
        title="💍 Demande en mariage",
        message=(
            f"💍 <b>@{requester}</b> "
            "t'a envoyé une demande en mariage.\n\n"
            "Tu peux accepter ou refuser."
        ),
        callback_data=(
            f"lw_marriage:accept:{requester}"
        ),
    )


def marriage_accepted_notification(
    accepter: str,
    requester: str,
) -> FamilyNotification:

    accepter = normalize_username(
        accepter
    )

    requester = normalize_username(
        requester
    )

    return FamilyNotification(
        recipient=requester,
        sender=accepter,
        target=requester,
        event_type="marriage_accepted",
        title="💍 Mariage accepté",
        message=(
            f"💍 <b>@{accepter}</b> "
            "a accepté la demande en mariage."
        ),
    )


def marriage_declined_notification(
    decliner: str,
    requester: str,
) -> FamilyNotification:

    decliner = normalize_username(
        decliner
    )

    requester = normalize_username(
        requester
    )

    return FamilyNotification(
        recipient=requester,
        sender=decliner,
        target=requester,
        event_type="marriage_declined",
        title="❌ Demande refusée",
        message=(
            f"❌ <b>@{decliner}</b> "
            "a refusé la demande en mariage."
        ),
    )


def divorce_notification(
    initiator: str,
    former_spouse: str,
) -> FamilyNotification:

    initiator = normalize_username(
        initiator
    )

    former_spouse = normalize_username(
        former_spouse
    )

    return FamilyNotification(
        recipient=former_spouse,
        sender=initiator,
        target=former_spouse,
        event_type="divorce",
        title="💔 Divorce",
        message=(
            f"💔 Le mariage avec "
            f"<b>@{initiator}</b> "
            "a pris fin."
        ),
    )


# ============================================================
# ADOPTION
# ============================================================

def adoption_request_notification(
    parent: str,
    child: str,
) -> FamilyNotification:

    parent = normalize_username(
        parent
    )

    child = normalize_username(
        child
    )

    return FamilyNotification(
        recipient=child,
        sender=parent,
        target=child,
        event_type="adoption_request",
        title="👨‍👩‍👦 Demande d'adoption",
        message=(
            f"👨‍👩‍👦 <b>@{parent}</b> "
            "souhaite t'adopter.\n\n"
            "Tu peux accepter ou refuser."
        ),
        callback_data=(
            f"lw_adoption:accept:{parent}"
        ),
    )


def adoption_accepted_notification(
    child: str,
    parent: str,
) -> FamilyNotification:

    child = normalize_username(
        child
    )

    parent = normalize_username(
        parent
    )

    return FamilyNotification(
        recipient=parent,
        sender=child,
        target=parent,
        event_type="adoption_accepted",
        title="👨‍👩‍👦 Adoption acceptée",
        message=(
            f"👶 <b>@{child}</b> "
            "a accepté ta demande d'adoption."
        ),
    )


def adoption_declined_notification(
    child: str,
    parent: str,
) -> FamilyNotification:

    child = normalize_username(
        child
    )

    parent = normalize_username(
        parent
    )

    return FamilyNotification(
        recipient=parent,
        sender=child,
        target=parent,
        event_type="adoption_declined",
        title="❌ Adoption refusée",
        message=(
            f"❌ <b>@{child}</b> "
            "a refusé ta demande d'adoption."
        ),
    )


# ============================================================
# LISTE DES ÉVÉNEMENTS
# ============================================================

def notification_to_dict(
    notification: FamilyNotification,
) -> dict:

    return {
        "recipient": notification.recipient,
        "event_type": notification.event_type,
        "title": notification.title,
        "message": notification.message,
        "sender": notification.sender,
        "target": notification.target,
        "callback_data": notification.callback_data,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_notification(
    notification: FamilyNotification,
) -> bool:

    if not notification.recipient:
        return False

    if not notification.event_type:
        return False

    if not notification.title:
        return False

    if not notification.message:
        return False

    return True


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "FamilyNotification",
    "friend_request_notification",
    "friend_accepted_notification",
    "friend_declined_notification",
    "marriage_request_notification",
    "marriage_accepted_notification",
    "marriage_declined_notification",
    "divorce_notification",
    "adoption_request_notification",
    "adoption_accepted_notification",
    "adoption_declined_notification",
    "notification_to_dict",
    "validate_notification",
]