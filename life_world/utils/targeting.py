"""
MANUWORLD V3 — TARGETING

Règle globale : une commande visant un autre joueur accepte uniquement :
1) une réponse au message de ce joueur ;
2) @username.
Les IDs Telegram ne sont jamais demandés aux joueurs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from life_world.database import get_life_character, get_life_character_by_username


@dataclass
class TargetResult:
    character: dict[str, Any] | None
    telegram_id: int | None = None
    error: str | None = None
    source: str | None = None


def normalize_username(value: str | None) -> str:
    return str(value or "").strip().lstrip("@").lower()


def get_target_username(update) -> str | None:
    msg=update.effective_message
    if not msg:return None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        u=msg.reply_to_message.from_user
        return u.username
    entities=msg.entities or []
    for entity in entities:
        if entity.type=="mention":
            try:
                return msg.text[entity.offset:entity.offset+entity.length]
            except Exception:
                pass
    if getattr(update,"effective_user",None):
        # /command @username amount => second token is the target.
        text=msg.text or ""
        parts=text.split()
        if len(parts)>=2 and parts[1].startswith("@"):
            return parts[1]
    return None


async def resolve_target(update, *, allow_self: bool=False) -> TargetResult:
    msg=update.effective_message
    actor_user=update.effective_user
    if not msg or not actor_user:
        return TargetResult(None,error="❌ Message invalide.")

    target_user=None
    source=None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user=msg.reply_to_message.from_user
        source="reply"
    else:
        parts=(msg.text or "").split()
        if len(parts)>=2 and parts[1].startswith("@"):
            username=normalize_username(parts[1])
            if username:
                character=await get_life_character_by_username(username)
                if character:
                    tid=int(character["telegram_id"])
                    if not allow_self and tid==int(actor_user.id):
                        return TargetResult(None,error="❌ Tu ne peux pas te cibler toi-même.")
                    return TargetResult(dict(character),tid,None,"username")
                return TargetResult(None,error="❌ Aucun personnage avec ce @username.")
        return TargetResult(
            None,
            error="❌ Cible manquante. Réponds au message du joueur ou utilise `@username`.",
        )

    tid=int(target_user.id)
    if not allow_self and tid==int(actor_user.id):
        return TargetResult(None,error="❌ Tu ne peux pas te cibler toi-même.")
    character=await get_life_character(tid)
    if not character:
        return TargetResult(None,tid,"❌ Ce joueur n'a pas encore de personnage MANUWORLD.",source)
    return TargetResult(dict(character),tid,None,source)


async def require_target(update, *, allow_self: bool=False) -> TargetResult:
    result=await resolve_target(update,allow_self=allow_self)
    if result.character is None and result.error:
        return result
    return result


async def get_actor_character(update) -> dict[str,Any] | None:
    u=update.effective_user
    if not u:return None
    row=await get_life_character(u.id)
    return dict(row) if row else None
