"""
Life World — School Progression

Gère le passage :
CEP → BEPC → Probatoire → BACC → Université

Règles :
CEP         : 5 questions  → 4/5
BEPC        : 7 questions  → 5/7
Probatoire  : 10 questions → 8/10
BACC        : 12 questions → 10/12
Université  : 15 questions → 15/15

À partir du BEPC :
- le joueur possède un domaine ;
- il peut continuer dans le même domaine ;
- ou changer de domaine.

IMPORTANT :
main.py sera connecté à la fin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ============================================================
# RÈGLES DES NIVEAUX
# ============================================================

LEVEL_RULES = {
    "cep": {
        "name": "CEP",
        "questions": 5,
        "required_score": 4,
        "next_level": "bepc",
        "domain_required": False,
    },

    "bepc": {
        "name": "BEPC",
        "questions": 7,
        "required_score": 5,
        "next_level": "probatoire",
        "domain_required": True,
    },

    "probatoire": {
        "name": "Probatoire",
        "questions": 10,
        "required_score": 8,
        "next_level": "bacc",
        "domain_required": True,
    },

    "bacc": {
        "name": "BACCALAUREAT",
        "questions": 12,
        "required_score": 10,
        "next_level": "university",
        "domain_required": True,
    },

    "university": {
        "name": "Université",
        "questions": 15,
        "required_score": 15,
        "next_level": None,
        "domain_required": True,
    },
}


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
# RÉSULTAT D'EXAMEN
# ============================================================

@dataclass
class ExamResult:
    level: str
    score: int
    total: int
    passed: bool
    required: int


# ============================================================
# NORMALISATION
# ============================================================

def normalize_level(level: str) -> str:
    level = str(level).strip().lower()

    if level not in LEVEL_RULES:
        raise ValueError(
            f"Niveau scolaire invalide : {level}"
        )

    return level


def normalize_domain(
    domain: Optional[str],
) -> Optional[str]:

    if domain is None:
        return None

    domain = str(domain).strip().lower()

    if domain not in DOMAINS:
        raise ValueError(
            f"Domaine invalide : {domain}"
        )

    return domain


# ============================================================
# INFORMATIONS NIVEAU
# ============================================================

def get_level_rules(level: str) -> dict:
    level = normalize_level(level)

    return dict(
        LEVEL_RULES[level]
    )


def get_question_count(level: str) -> int:
    return get_level_rules(level)["questions"]


def get_required_score(level: str) -> int:
    return get_level_rules(level)["required_score"]


def get_next_level(
    level: str,
) -> Optional[str]:

    return get_level_rules(level)["next_level"]


# ============================================================
# VALIDATION D'UN EXAMEN
# ============================================================

def evaluate_exam(
    level: str,
    score: int,
    total: Optional[int] = None,
) -> ExamResult:

    level = normalize_level(level)

    rules = LEVEL_RULES[level]

    expected_total = rules["questions"]

    if total is None:
        total = expected_total

    if total != expected_total:
        raise ValueError(
            f"Nombre de questions incorrect pour "
            f"{rules['name']} : {total}. "
            f"Attendu : {expected_total}."
        )

    score = int(score)

    if score < 0:
        score = 0

    if score > total:
        score = total

    required = rules["required_score"]

    return ExamResult(
        level=level,
        score=score,
        total=total,
        passed=score >= required,
        required=required,
    )


# ============================================================
# POURCENTAGE
# ============================================================

def exam_percentage(
    score: int,
    total: int,
) -> float:

    if total <= 0:
        return 0.0

    return round(
        (score / total) * 100,
        2,
    )


# ============================================================
# MESSAGE DE RÉSULTAT
# ============================================================

def format_exam_result(
    result: ExamResult,
) -> str:

    rules = LEVEL_RULES[result.level]

    percentage = exam_percentage(
        result.score,
        result.total,
    )

    if result.passed:
        status = "✅ ADMIS"
    else:
        status = "❌ ÉCHEC"

    return (
        f"🎓 <b>{rules['name']}</b>\n\n"
        f"📝 Note : "
        f"<b>{result.score}/{result.total}</b>\n"
        f"📊 Pourcentage : "
        f"<b>{percentage}%</b>\n"
        f"🎯 Minimum : "
        f"<b>{result.required}/{result.total}</b>\n\n"
        f"{status}"
    )


# ============================================================
# CONDITIONS D'ORIENTATION
# ============================================================

def domain_required(
    level: str,
) -> bool:

    return LEVEL_RULES[
        normalize_level(level)
    ]["domain_required"]


def validate_domain_for_progression(
    level: str,
    domain: Optional[str],
) -> bool:

    level = normalize_level(level)

    if not LEVEL_RULES[level]["domain_required"]:
        return True

    return normalize_domain(domain) is not None


# ============================================================
# PASSAGE AU NIVEAU SUIVANT
# ============================================================

def can_progress(
    level: str,
    score: int,
    domain: Optional[str] = None,
) -> tuple[bool, Optional[str], str]:

    level = normalize_level(level)

    result = evaluate_exam(level, score)

    if not result.passed:
        return (
            False,
            None,
            "❌ Le joueur n'a pas obtenu "
            "la note nécessaire.",
        )

    next_level = get_next_level(level)

    if next_level is None:
        return (
            True,
            None,
            "🏆 Le parcours scolaire est terminé.",
        )

    if domain_required(next_level):

        if not validate_domain_for_progression(
            next_level,
            domain,
        ):
            return (
                False,
                next_level,
                (
                    "🧭 Un domaine doit être choisi "
                    "avant de continuer."
                ),
            )

    return (
        True,
        next_level,
        (
            f"✅ Passage autorisé vers "
            f"<b>{LEVEL_RULES[next_level]['name']}</b>."
        ),
    )


# ============================================================
# ORIENTATION
# ============================================================

def continue_domain(
    current_domain: Optional[str],
) -> str:

    domain = normalize_domain(
        current_domain
    )

    if not domain:
        raise ValueError(
            "Aucun domaine actuel."
        )

    return domain


def change_domain(
    new_domain: str,
) -> str:

    return normalize_domain(
        new_domain
    )


def process_orientation(
    action: str,
    current_domain: Optional[str] = None,
    new_domain: Optional[str] = None,
) -> str:

    action = str(action).strip().lower()

    if action == "continue":

        return continue_domain(
            current_domain
        )

    if action == "change":

        if not new_domain:
            raise ValueError(
                "Nouveau domaine obligatoire."
            )

        return change_domain(
            new_domain
        )

    raise ValueError(
        f"Action inconnue : {action}"
    )


# ============================================================
# RÉSUMÉ DU PARCOURS
# ============================================================

def get_progression_summary(
    level: str,
    domain: Optional[str] = None,
) -> str:

    level = normalize_level(level)

    rules = LEVEL_RULES[level]

    lines = [
        "🎓 <b>PARCOURS SCOLAIRE</b>",
        "",
        f"📚 Niveau : <b>{rules['name']}</b>",
    ]

    if domain:
        domain = normalize_domain(domain)

        lines.append(
            f"🧭 Domaine : <b>{DOMAINS[domain]}</b>"
        )
    else:
        lines.append(
            "🧭 Domaine : <b>Non choisi</b>"
        )

    lines.extend(
        [
            "",
            f"📝 Questions au prochain examen : "
            f"<b>{rules['questions']}</b>",
            f"🎯 Note minimale : "
            f"<b>{rules['required_score']}/{rules['questions']}</b>",
        ]
    )

    next_level = rules["next_level"]

    if next_level:
        lines.append(
            f"➡️ Prochaine étape : "
            f"<b>{LEVEL_RULES[next_level]['name']}</b>"
        )
    else:
        lines.append(
            "🏆 Niveau final atteint."
        )

    return "\n".join(lines)


# ============================================================
# PARCOURS COMPLET
# ============================================================

def get_full_school_path() -> list[str]:

    return [
        "cep",
        "bepc",
        "probatoire",
        "bacc",
        "university",
    ]


# ============================================================
# VÉRIFICATION INTERNE
# ============================================================

def validate_configuration() -> None:

    expected = {
        "cep": (5, 4),
        "bepc": (7, 5),
        "probatoire": (10, 8),
        "bacc": (12, 10),
        "university": (15, 15),
    }

    for level, (
        questions,
        required,
    ) in expected.items():

        rules = LEVEL_RULES[level]

        if rules["questions"] != questions:
            raise RuntimeError(
                f"Nombre de questions incorrect : {level}"
            )

        if rules["required_score"] != required:
            raise RuntimeError(
                f"Seuil incorrect : {level}"
            )

    if len(DOMAINS) != 8:
        raise RuntimeError(
            "Le système doit contenir 8 domaines."
        )


validate_configuration()