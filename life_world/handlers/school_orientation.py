"""
Life World — School Orientation

Gère l'orientation scolaire à partir du collège :
- choix du domaine ;
- continuer dans le même domaine ;
- changer de domaine ;
- validation des domaines ;
- préparation du choix d'établissement.

IMPORTANT :
Ce fichier ne modifie pas main.py.
Les handlers seront branchés dans main.py à la fin du projet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ============================================================
# DOMAINES
# ============================================================

DOMAINS = {
    "science": "🔬 Sciences",
    "technology": "💻 Technologie & Informatique",
    "economics": "💰 Économie & Gestion",
    "law": "⚖️ Droit",
    "medicine": "🩺 Santé & Médecine",
    "arts": "🎨 Arts & Création",
    "communication": "🎙️ Communication & Médias",
    "engineering": "⚙️ Ingénierie",
}


# ============================================================
# NIVEAUX SCOLAIRES
# ============================================================

SCHOOL_LEVELS = {
    "cep": {
        "name": "CEP",
        "domain_required": False,
        "next": "bepc",
    },
    "bepc": {
        "name": "BEPC",
        "domain_required": True,
        "next": "probatoire",
    },
    "probatoire": {
        "name": "Probatoire",
        "domain_required": True,
        "next": "bacc",
    },
    "bacc": {
        "name": "Baccalauréat",
        "domain_required": True,
        "next": "university",
    },
    "university": {
        "name": "Université",
        "domain_required": True,
        "next": None,
    },
}


# ============================================================
# STRUCTURE DE L'ORIENTATION
# ============================================================

@dataclass
class OrientationResult:
    success: bool
    domain: Optional[str] = None
    action: Optional[str] = None
    message: str = ""


# ============================================================
# OUTILS DOMAINES
# ============================================================

def is_valid_domain(domain: Optional[str]) -> bool:
    """Vérifie qu'un domaine existe."""
    if not domain:
        return False

    return domain.lower().strip() in DOMAINS


def normalize_domain(domain: Optional[str]) -> Optional[str]:
    """Normalise le nom du domaine."""
    if not domain:
        return None

    domain = domain.lower().strip()

    if domain not in DOMAINS:
        return None

    return domain


def get_domain_name(domain: Optional[str]) -> str:
    """Retourne le nom affichable d'un domaine."""
    domain = normalize_domain(domain)

    if not domain:
        return "Aucun domaine"

    return DOMAINS[domain]


def get_domain_buttons() -> list[tuple[str, str]]:
    """
    Retourne les domaines sous forme :
    [(callback_data, texte), ...]
    """

    return [
        (domain, name)
        for domain, name in DOMAINS.items()
    ]


# ============================================================
# CHOIX DU DOMAINE
# ============================================================

def domain_required_for_level(level: str) -> bool:
    """
    À partir du BEPC, le domaine devient obligatoire.
    """

    level = level.lower().strip()

    if level not in SCHOOL_LEVELS:
        return False

    return SCHOOL_LEVELS[level]["domain_required"]


def get_orientation_message(
    level: str,
    current_domain: Optional[str] = None,
) -> str:
    """
    Message affiché au joueur pour choisir son orientation.
    """

    level = level.lower().strip()

    if level not in SCHOOL_LEVELS:
        raise ValueError("Niveau scolaire invalide.")

    if not SCHOOL_LEVELS[level]["domain_required"]:
        return (
            "🏫 <b>ORIENTATION SCOLAIRE</b>\n\n"
            "À ce niveau, aucun domaine spécialisé "
            "n'est encore nécessaire."
        )

    current_domain = normalize_domain(current_domain)

    if current_domain:
        return (
            "🎓 <b>ORIENTATION</b>\n\n"
            f"Ton domaine actuel est : "
            f"<b>{get_domain_name(current_domain)}</b>\n\n"
            "Que veux-tu faire pour la suite ?"
        )

    return (
        "🎓 <b>CHOISIS TON DOMAINE</b>\n\n"
        "À partir du collège, ton parcours dépend "
        "du domaine que tu choisis.\n\n"
        "Sélectionne le domaine dans lequel tu "
        "souhaites évoluer."
    )


# ============================================================
# CONTINUER OU CHANGER
# ============================================================

def get_continuation_options(
    current_domain: Optional[str],
) -> list[tuple[str, str]]:
    """
    Retourne les deux choix :
    - continuer dans le domaine actuel ;
    - changer de domaine.
    """

    current_domain = normalize_domain(current_domain)

    if not current_domain:
        return [
            (
                "change_domain",
                "🔄 Choisir un domaine",
            )
        ]

    return [
        (
            "continue_domain",
            f"➡️ Continuer : {get_domain_name(current_domain)}",
        ),
        (
            "change_domain",
            "🔄 Changer de domaine",
        ),
    ]


def continue_same_domain(
    current_domain: Optional[str],
) -> OrientationResult:
    """
    Le joueur conserve son domaine.
    """

    current_domain = normalize_domain(current_domain)

    if not current_domain:
        return OrientationResult(
            success=False,
            action="continue_domain",
            message=(
                "❌ Impossible de continuer : "
                "aucun domaine actuel n'est enregistré."
            ),
        )

    return OrientationResult(
        success=True,
        domain=current_domain,
        action="continue_domain",
        message=(
            "✅ Domaine conservé.\n\n"
            f"🎓 Domaine : {get_domain_name(current_domain)}"
        ),
    )


def change_domain(
    new_domain: Optional[str],
) -> OrientationResult:
    """
    Le joueur choisit un nouveau domaine.
    """

    new_domain = normalize_domain(new_domain)

    if not new_domain:
        return OrientationResult(
            success=False,
            action="change_domain",
            message="❌ Domaine invalide.",
        )

    return OrientationResult(
        success=True,
        domain=new_domain,
        action="change_domain",
        message=(
            "✅ Nouveau domaine enregistré.\n\n"
            f"🎓 Domaine : {get_domain_name(new_domain)}"
        ),
    )


# ============================================================
# ORIENTATION APRÈS EXAMEN
# ============================================================

def process_orientation(
    action: str,
    current_domain: Optional[str] = None,
    new_domain: Optional[str] = None,
) -> OrientationResult:
    """
    Traite le choix du joueur.

    action :
        continue_domain
        change_domain
    """

    action = action.lower().strip()

    if action == "continue_domain":
        return continue_same_domain(current_domain)

    if action == "change_domain":
        return change_domain(new_domain)

    return OrientationResult(
        success=False,
        action=action,
        message="❌ Action d'orientation inconnue.",
    )


# ============================================================
# PARCOURS SCOLAIRE
# ============================================================

def get_next_level(level: str) -> Optional[str]:
    """Retourne le niveau suivant."""

    level = level.lower().strip()

    if level not in SCHOOL_LEVELS:
        raise ValueError("Niveau scolaire invalide.")

    return SCHOOL_LEVELS[level]["next"]


def get_level_name(level: str) -> str:
    """Retourne le nom affichable du niveau."""

    level = level.lower().strip()

    if level not in SCHOOL_LEVELS:
        raise ValueError("Niveau scolaire invalide.")

    return SCHOOL_LEVELS[level]["name"]


# ============================================================
# VALIDATION DU PASSAGE AU NIVEAU SUIVANT
# ============================================================

def validate_progression(
    current_level: str,
    passed_exam: bool,
    current_domain: Optional[str] = None,
) -> dict:
    """
    Vérifie si le joueur peut passer au niveau suivant.

    À partir du BEPC, un domaine doit être présent.
    """

    current_level = current_level.lower().strip()

    if current_level not in SCHOOL_LEVELS:
        return {
            "success": False,
            "reason": "Niveau scolaire invalide.",
        }

    if not passed_exam:
        return {
            "success": False,
            "reason": "L'examen n'a pas été réussi.",
        }

    next_level = get_next_level(current_level)

    if next_level is None:
        return {
            "success": True,
            "finished": True,
            "next_level": None,
            "domain": normalize_domain(current_domain),
            "message": (
                "🎓 Félicitations !\n\n"
                "Tu as terminé ton parcours universitaire."
            ),
        }

    if SCHOOL_LEVELS[next_level]["domain_required"]:
        domain = normalize_domain(current_domain)

        if not domain:
            return {
                "success": False,
                "reason": (
                    "Un domaine doit être choisi "
                    "avant de continuer."
                ),
                "requires_domain": True,
                "next_level": next_level,
            }

    else:
        domain = normalize_domain(current_domain)

    return {
        "success": True,
        "finished": False,
        "next_level": next_level,
        "domain": domain,
        "message": (
            "✅ Examen réussi !\n\n"
            f"🎓 Prochain niveau : "
            f"<b>{get_level_name(next_level)}</b>"
        ),
    }


# ============================================================
# RÉSUMÉ DU PARCOURS
# ============================================================

def get_school_path_summary(
    level: str,
    domain: Optional[str] = None,
) -> str:
    """
    Produit un résumé simple du parcours actuel.
    """

    level_name = get_level_name(level)
    domain = normalize_domain(domain)

    lines = [
        "🎓 <b>PARCOURS SCOLAIRE</b>",
        "",
        f"📚 Niveau : <b>{level_name}</b>",
    ]

    if domain:
        lines.append(
            f"🧭 Domaine : <b>{get_domain_name(domain)}</b>"
        )
    else:
        lines.append("🧭 Domaine : <b>Non choisi</b>")

    next_level = get_next_level(level)

    if next_level:
        lines.append(
            f"➡️ Prochaine étape : "
            f"<b>{get_level_name(next_level)}</b>"
        )
    else:
        lines.append(
            "🏆 Parcours scolaire terminé."
        )

    return "\n".join(lines)