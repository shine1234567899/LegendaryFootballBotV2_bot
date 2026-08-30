"""
Life World — School Exam Keyboard

Prépare les textes et callback_data pour les boutons Telegram
du système scolaire.

Ce fichier ne branche aucun handler dans main.py.

Fonctions :
- boutons de domaines ;
- boutons de continuation/changement ;
- boutons de réponses ;
- bouton suivant/abandon ;
- affichage uniforme des examens.
"""

from __future__ import annotations

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
# RÈGLES
# ============================================================

LEVEL_RULES = {
    "cep": {
        "name": "CEP",
        "questions": 5,
        "required": 4,
    },
    "bepc": {
        "name": "BEPC",
        "questions": 7,
        "required": 5,
    },
    "probatoire": {
        "name": "PROBATOIRE",
        "questions": 10,
        "required": 8,
    },
    "bacc": {
        "name": "BACCALAURÉAT",
        "questions": 12,
        "required": 10,
    },
    "university": {
        "name": "UNIVERSITÉ",
        "questions": 15,
        "required": 15,
    },
}


# ============================================================
# OUTILS
# ============================================================

def normalize_level(level: str) -> str:
    level = str(level).strip().lower()

    if level not in LEVEL_RULES:
        raise ValueError(f"Niveau invalide : {level}")

    return level


def normalize_domain(domain: str) -> str:
    domain = str(domain).strip().lower()

    if domain not in DOMAINS:
        raise ValueError(f"Domaine invalide : {domain}")

    return domain


# ============================================================
# BOUTONS DOMAINES
# ============================================================

def get_domain_buttons() -> list[tuple[str, str]]:
    """
    Retourne :
        [(callback_data, texte), ...]

    Le handler Telegram pourra transformer ces données
    en InlineKeyboardButton.
    """

    return [
        (
            f"lw_domain:{domain}",
            name,
        )
        for domain, name in DOMAINS.items()
    ]


def get_domain_button_rows(
    per_row: int = 2,
) -> list[list[tuple[str, str]]]:
    """
    Organise les domaines par lignes.

    Par défaut :
        2 boutons par ligne.
    """

    if per_row <= 0:
        raise ValueError("per_row doit être supérieur à zéro.")

    buttons = get_domain_buttons()

    return [
        buttons[index:index + per_row]
        for index in range(0, len(buttons), per_row)
    ]


# ============================================================
# CONTINUER / CHANGER
# ============================================================

def get_orientation_buttons(
    current_domain: Optional[str],
) -> list[tuple[str, str]]:
    """
    Boutons affichés lorsqu'un joueur possède déjà
    un domaine.
    """

    buttons = []

    if current_domain:
        current_domain = normalize_domain(current_domain)

        buttons.append(
            (
                "lw_orientation:continue",
                f"➡️ Continuer : {DOMAINS[current_domain]}",
            )
        )

    buttons.append(
        (
            "lw_orientation:change",
            "🔄 Changer de domaine",
        )
    )

    return buttons


# ============================================================
# RÉPONSES
# ============================================================

def get_answer_buttons(
    level: str,
    question_number: int,
    answers: list[str],
) -> list[tuple[str, str]]:
    """
    Prépare les boutons de réponses.

    Exemple callback :
        lw_answer:probatoire:3:1

    Signification :
        niveau = probatoire
        question = 3
        réponse = index 1
    """

    level = normalize_level(level)

    if question_number <= 0:
        raise ValueError(
            "Le numéro de question doit être positif."
        )

    if not answers:
        raise ValueError(
            "La question doit avoir des réponses."
        )

    buttons = []

    letters = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
    ]

    for index, answer in enumerate(answers):

        label = (
            letters[index]
            if index < len(letters)
            else str(index + 1)
        )

        buttons.append(
            (
                f"lw_answer:{level}:{question_number}:{index}",
                f"{label}. {answer}",
            )
        )

    return buttons


def get_answer_button_rows(
    level: str,
    question_number: int,
    answers: list[str],
    per_row: int = 1,
) -> list[list[tuple[str, str]]]:
    """
    Organise les réponses en lignes.

    Une réponse par ligne par défaut pour garder
    une bonne lisibilité sur Telegram.
    """

    if per_row <= 0:
        raise ValueError(
            "per_row doit être supérieur à zéro."
        )

    buttons = get_answer_buttons(
        level,
        question_number,
        answers,
    )

    return [
        buttons[index:index + per_row]
        for index in range(0, len(buttons), per_row)
    ]


# ============================================================
# BOUTONS EXAMEN
# ============================================================

def get_exam_control_buttons(
    level: str,
) -> list[tuple[str, str]]:
    level = normalize_level(level)

    return [
        (
            f"lw_exam:quit:{level}",
            "🚪 Abandonner",
        ),
    ]


# ============================================================
# BOUTON CONFIRMATION ABANDON
# ============================================================

def get_abandon_confirmation_buttons(
    level: str,
) -> list[tuple[str, str]]:

    level = normalize_level(level)

    return [
        (
            f"lw_exam:quit_confirm:{level}",
            "✅ Oui, abandonner",
        ),
        (
            f"lw_exam:quit_cancel:{level}",
            "↩️ Continuer l'examen",
        ),
    ]


# ============================================================
# BOUTONS APRÈS EXAMEN
# ============================================================

def get_passed_buttons(
    level: str,
) -> list[tuple[str, str]]:

    level = normalize_level(level)

    return [
        (
            f"lw_school:continue:{level}",
            "🎓 Continuer le parcours",
        ),
    ]


def get_failed_buttons(
    level: str,
) -> list[tuple[str, str]]:

    level = normalize_level(level)

    return [
        (
            f"lw_exam:retry:{level}",
            "🔄 Repasser l'examen",
        ),
    ]


# ============================================================
# FORMATAGE QUESTION
# ============================================================

def format_exam_header(
    level: str,
    current: int,
    total: int,
    domain: Optional[str] = None,
) -> str:

    level = normalize_level(level)

    rules = LEVEL_RULES[level]

    if current < 1:
        current = 1

    if total <= 0:
        total = rules["questions"]

    lines = [
        f"🎓 <b>{rules['name']}</b>",
        "",
        f"📝 Question <b>{current}/{total}</b>",
    ]

    if domain:
        domain = normalize_domain(domain)
        lines.append(
            f"🧭 Domaine : <b>{DOMAINS[domain]}</b>"
        )

    lines.append("")

    return "\n".join(lines)


def format_exam_question(
    level: str,
    current: int,
    total: int,
    question_text: str,
    domain: Optional[str] = None,
) -> str:

    return (
        format_exam_header(
            level=level,
            current=current,
            total=total,
            domain=domain,
        )
        + question_text
    )


# ============================================================
# FORMATAGE RÉSULTAT
# ============================================================

def format_exam_result(
    level: str,
    score: int,
    total: int,
) -> str:

    level = normalize_level(level)

    rules = LEVEL_RULES[level]

    required = rules["required"]

    if score >= required:
        status = "🎉 <b>ADMIS</b>"
        extra = (
            "➡️ Tu peux continuer "
            "ton parcours scolaire."
        )
    else:
        status = "❌ <b>ÉCHEC</b>"
        extra = (
            "🔄 Tu devras repasser "
            "cet examen."
        )

    return (
        f"🎓 <b>{rules['name']}</b>\n\n"
        f"📊 Résultat : <b>{score}/{total}</b>\n"
        f"🎯 Minimum : <b>{required}/{total}</b>\n\n"
        f"{status}\n\n"
        f"{extra}"
    )


# ============================================================
# CALLBACK PARSING
# ============================================================

def parse_callback(data: str) -> dict:
    """
    Décode les callback_data produits par ce fichier.

    Retourne un dictionnaire simple exploitable par
    les futurs handlers.
    """

    parts = data.split(":")

    if not parts or parts[0] != "lw_":
        # Le préfixe réel est du type lw_answer.
        pass

    if data.startswith("lw_domain:"):
        return {
            "type": "domain",
            "domain": data.split(":", 1)[1],
        }

    if data.startswith("lw_orientation:"):
        return {
            "type": "orientation",
            "action": data.split(":", 1)[1],
        }

    if data.startswith("lw_answer:"):
        parts = data.split(":")

        if len(parts) != 4:
            raise ValueError(
                "Callback réponse invalide."
            )

        return {
            "type": "answer",
            "level": parts[1],
            "question": int(parts[2]),
            "answer": int(parts[3]),
        }

    if data.startswith("lw_exam:"):
        parts = data.split(":")

        if len(parts) < 3:
            raise ValueError(
                "Callback examen invalide."
            )

        return {
            "type": "exam",
            "action": parts[1],
            "level": parts[2],
        }

    if data.startswith("lw_school:"):
        parts = data.split(":")

        if len(parts) != 3:
            raise ValueError(
                "Callback scolaire invalide."
            )

        return {
            "type": "school",
            "action": parts[1],
            "level": parts[2],
        }

    raise ValueError(
        f"Callback Life World inconnu : {data}"
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_configuration() -> None:

    if len(DOMAINS) != 8:
        raise RuntimeError(
            "Life World doit contenir 8 domaines."
        )

    expected = {
        "cep": (5, 4),
        "bepc": (7, 5),
        "probatoire": (10, 8),
        "bacc": (12, 10),
        "university": (15, 15),
    }

    for level, (questions, required) in expected.items():

        rules = LEVEL_RULES[level]

        if rules["questions"] != questions:
            raise RuntimeError(
                f"Questions incorrectes pour {level}."
            )

        if rules["required"] != required:
            raise RuntimeError(
                f"Seuil incorrect pour {level}."
            )


validate_configuration()
