"""
Life World — School Exam Engine

Gère les examens scolaires :

CEP         : 5 questions  → 4/5
BEPC        : 7 questions  → 5/7
Probatoire  : 10 questions → 8/10
BACC        : 12 questions → 10/12
Université  : 15 questions → 15/15

À partir du BEPC, les questions sont sélectionnées
dans la banque correspondant au domaine du joueur.

Exemple :
    Probatoire + Droit
        → uniquement questions de Droit

    BACC + Médecine
        → uniquement questions de Médecine

    Université + Technologie
        → uniquement questions de Technologie

IMPORTANT :
- aucune modification de main.py ;
- aucune question n'est inventée au moment de l'examen ;
- le moteur utilise les banques déjà préparées.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Optional


# ============================================================
# RÈGLES DES EXAMENS
# ============================================================

EXAM_RULES = {
    "cep": {
        "name": "CEP",
        "question_count": 5,
        "required_score": 4,
        "domain_required": False,
    },

    "bepc": {
        "name": "BEPC",
        "question_count": 7,
        "required_score": 5,
        "domain_required": True,
    },

    "probatoire": {
        "name": "PROBATOIRE",
        "question_count": 10,
        "required_score": 8,
        "domain_required": True,
    },

    "bacc": {
        "name": "BACCALAURÉAT",
        "question_count": 12,
        "required_score": 10,
        "domain_required": True,
    },

    "university": {
        "name": "UNIVERSITÉ",
        "question_count": 15,
        "required_score": 15,
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
# STRUCTURE D'UNE QUESTION
# ============================================================

@dataclass
class ExamQuestion:
    question_id: int
    text: str
    answers: list[str]
    correct_answer: int


@dataclass
class ExamSession:
    username: str
    level: str
    domain: Optional[str]

    questions: list[ExamQuestion]

    current_index: int = 0
    score: int = 0
    finished: bool = False


# ============================================================
# NORMALISATION
# ============================================================

def normalize_level(level: str) -> str:

    level = str(level).strip().lower()

    if level not in EXAM_RULES:
        raise ValueError(
            f"Niveau invalide : {level}"
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
# IMPORT DE LA BANQUE
# ============================================================

def load_question_bank():
    """
    Charge la banque existante.

    On essaie plusieurs chemins afin que le module
    reste compatible avec l'organisation actuelle
    de Life World.
    """

    try:
        from .domain_question_bank import ADVANCED

        return ADVANCED

    except ImportError:

        try:
            from domain_question_bank import ADVANCED

            return ADVANCED

        except ImportError as exc:
            raise ImportError(
                "Impossible de charger "
                "domain_question_bank.py"
            ) from exc


# ============================================================
# CONVERSION DES QUESTIONS
# ============================================================

def convert_question(
    raw_question: Any,
    question_id: int,
) -> ExamQuestion:
    """
    Convertit une question provenant de la banque
    vers le format utilisé par le moteur.
    """

    if isinstance(raw_question, dict):

        text = raw_question.get(
            "question",
            raw_question.get("text"),
        )

        answers = raw_question.get(
            "answers",
            raw_question.get("options"),
        )

        correct = raw_question.get(
            "correct",
            raw_question.get(
                "correct_answer",
                raw_question.get("answer"),
            ),
        )

    elif isinstance(raw_question, (tuple, list)):

        if len(raw_question) < 3:
            raise ValueError(
                "Format de question invalide."
            )

        text = raw_question[0]
        answers = raw_question[1]
        correct = raw_question[2]

    else:

        text = getattr(
            raw_question,
            "question",
            getattr(
                raw_question,
                "text",
                None,
            ),
        )

        answers = getattr(
            raw_question,
            "answers",
            getattr(
                raw_question,
                "options",
                None,
            ),
        )

        correct = getattr(
            raw_question,
            "correct_answer",
            getattr(
                raw_question,
                "correct",
                None,
            ),
        )

    if not text:
        raise ValueError(
            "Question sans texte."
        )

    if not answers:
        raise ValueError(
            "Question sans réponses."
        )

    if correct is None:
        raise ValueError(
            "Question sans réponse correcte."
        )

    return ExamQuestion(
        question_id=question_id,
        text=str(text),
        answers=list(answers),
        correct_answer=int(correct),
    )


# ============================================================
# RÉCUPÉRER LES QUESTIONS
# ============================================================

def get_raw_questions(
    level: str,
    domain: Optional[str] = None,
) -> list[Any]:

    level = normalize_level(level)
    domain = normalize_domain(domain)

    rules = EXAM_RULES[level]

    bank = load_question_bank()

    # CEP : banque générale.
    if level == "cep":

        if isinstance(bank, dict):

            if "cep" in bank:
                return list(bank["cep"])

            if "basic" in bank:
                return list(bank["basic"])

    # BEPC : banque du domaine.
    if level == "bepc":

        if not domain:
            raise ValueError(
                "Le domaine est obligatoire pour le BEPC."
            )

        if domain not in bank:
            raise ValueError(
                f"Banque introuvable pour : {domain}"
            )

        if isinstance(bank[domain], dict):

            if "bepc" not in bank[domain]:
                raise ValueError(
                    f"Banque BEPC absente : {domain}"
                )

            return list(
                bank[domain]["bepc"]
            )

    # Probatoire / BACC / Université :
    # banque spécialisée par domaine.
    if level in {
        "probatoire",
        "bacc",
        "university",
    }:

        if not domain:
            raise ValueError(
                "Le domaine est obligatoire "
                f"pour {rules['name']}."
            )

        if domain not in bank:
            raise ValueError(
                f"Domaine absent de la banque : "
                f"{domain}"
            )

        domain_bank = bank[domain]

        if level not in domain_bank:
            raise ValueError(
                f"Banque {level} absente "
                f"pour {domain}."
            )

        return list(
            domain_bank[level]
        )

    raise ValueError(
        f"Aucune banque disponible pour {level}."
    )


# ============================================================
# CONSTRUCTION D'UN EXAMEN
# ============================================================

def build_exam(
    username: str,
    level: str,
    domain: Optional[str] = None,
) -> ExamSession:

    username = str(username).strip().lower()

    if not username:
        raise ValueError(
            "Username obligatoire."
        )

    level = normalize_level(level)
    domain = normalize_domain(domain)

    rules = EXAM_RULES[level]

    if rules["domain_required"] and not domain:
        raise ValueError(
            f"Le domaine est obligatoire pour "
            f"{rules['name']}."
        )

    raw_questions = get_raw_questions(
        level,
        domain,
    )

    required_count = rules[
        "question_count"
    ]

    if len(raw_questions) < required_count:
        raise RuntimeError(
            f"Banque insuffisante pour "
            f"{level}/{domain or 'general'} : "
            f"{len(raw_questions)} disponibles, "
            f"{required_count} nécessaires."
        )

    # Sélection aléatoire sans doublon.
    selected = random.sample(
        raw_questions,
        required_count,
    )

    questions = [
        convert_question(
            raw,
            index + 1,
        )
        for index, raw in enumerate(selected)
    ]

    return ExamSession(
        username=username,
        level=level,
        domain=domain,
        questions=questions,
    )


# ============================================================
# QUESTION ACTUELLE
# ============================================================

def get_current_question(
    session: ExamSession,
) -> Optional[ExamQuestion]:

    if session.finished:
        return None

    if (
        session.current_index
        >= len(session.questions)
    ):
        return None

    return session.questions[
        session.current_index
    ]


# ============================================================
# VÉRIFICATION D'UNE RÉPONSE
# ============================================================

def answer_question(
    session: ExamSession,
    answer_index: int,
) -> dict:

    if session.finished:
        return {
            "success": False,
            "finished": True,
            "message": (
                "⚠️ Cet examen est déjà terminé."
            ),
        }

    question = get_current_question(
        session
    )

    if question is None:
        return finish_exam(session)

    try:
        answer_index = int(answer_index)
    except (TypeError, ValueError):

        return {
            "success": False,
            "finished": False,
            "message": "❌ Réponse invalide.",
        }

    if not (
        0
        <= answer_index
        < len(question.answers)
    ):

        return {
            "success": False,
            "finished": False,
            "message": "❌ Réponse invalide.",
        }

    correct = (
        answer_index
        == question.correct_answer
    )

    if correct:
        session.score += 1

    session.current_index += 1

    if (
        session.current_index
        >= len(session.questions)
    ):
        result = finish_exam(session)

        result["correct"] = correct

        return result

    next_question = get_current_question(
        session
    )

    return {
        "success": True,
        "finished": False,
        "correct": correct,
        "score": session.score,
        "answered": session.current_index,
        "total": len(session.questions),
        "next_question": next_question,
    }


# ============================================================
# FIN DE L'EXAMEN
# ============================================================

def finish_exam(
    session: ExamSession,
) -> dict:

    if session.finished:

        passed = (
            session.score
            >= EXAM_RULES[
                session.level
            ]["required_score"]
        )

        return {
            "success": True,
            "finished": True,
            "passed": passed,
            "score": session.score,
            "total": len(session.questions),
        }

    session.finished = True

    rules = EXAM_RULES[
        session.level
    ]

    passed = (
        session.score
        >= rules["required_score"]
    )

    return {
        "success": True,
        "finished": True,
        "passed": passed,
        "score": session.score,
        "total": len(session.questions),
        "required": rules[
            "required_score"
        ],
        "level": session.level,
        "domain": session.domain,
    }


# ============================================================
# RÉSULTAT AFFICHABLE
# ============================================================

def format_exam_result(
    result: dict,
) -> str:

    level = result.get(
        "level",
        "Examen",
    )

    rules = EXAM_RULES.get(
        level,
        {},
    )

    name = rules.get(
        "name",
        level.upper(),
    )

    score = result.get(
        "score",
        0,
    )

    total = result.get(
        "total",
        0,
    )

    required = result.get(
        "required",
        rules.get(
            "required_score",
            0,
        ),
    )

    if result.get("passed"):

        return (
            f"🎓 <b>{name}</b>\n\n"
            f"📊 Résultat : "
            f"<b>{score}/{total}</b>\n"
            f"🎯 Minimum : "
            f"<b>{required}/{total}</b>\n\n"
            "🎉 <b>ADMIS !</b>\n\n"
            "➡️ Tu peux poursuivre "
            "ton parcours scolaire."
        )

    return (
        f"🎓 <b>{name}</b>\n\n"
        f"📊 Résultat : "
        f"<b>{score}/{total}</b>\n"
        f"🎯 Minimum : "
        f"<b>{required}/{total}</b>\n\n"
        "❌ <b>ÉCHEC</b>\n\n"
        "Tu devras reprendre ce niveau."
    )


# ============================================================
# INFORMATIONS D'UNE QUESTION
# ============================================================

def format_question(
    question: ExamQuestion,
    number: int,
    total: int,
) -> str:

    return (
        f"📝 <b>Question {number}/{total}</b>\n\n"
        f"{question.text}"
    )


# ============================================================
# INFORMATIONS DE L'EXAMEN
# ============================================================

def exam_information(
    level: str,
    domain: Optional[str] = None,
) -> dict:

    level = normalize_level(level)
    domain = normalize_domain(domain)

    rules = EXAM_RULES[level]

    if (
        rules["domain_required"]
        and not domain
    ):
        raise ValueError(
            "Domaine obligatoire."
        )

    return {
        "level": level,
        "name": rules["name"],
        "domain": domain,
        "question_count": rules[
            "question_count"
        ],
        "required_score": rules[
            "required_score"
        ],
    }


# ============================================================
# VÉRIFICATION DES BANQUES
# ============================================================

def validate_specialized_banks() -> dict:
    """
    Vérifie les 24 banques spécialisées.

    8 domaines × :
        Probatoire = 10
        BACC = 12
        Université = 15
    """

    bank = load_question_bank()

    expected = {
        "probatoire": 10,
        "bacc": 12,
        "university": 15,
    }

    report = {}

    for domain in DOMAINS:

        if domain not in bank:
            report[domain] = {
                level: False
                for level in expected
            }
            continue

        report[domain] = {}

        for level, count in expected.items():

            actual = len(
                bank[domain].get(
                    level,
                    [],
                )
            )

            report[domain][level] = (
                actual >= count
            )

    return report


# ============================================================
# VÉRIFICATION FINALE
# ============================================================

def validate_configuration() -> None:

    for level, rules in EXAM_RULES.items():

        if rules["question_count"] <= 0:
            raise RuntimeError(
                f"Nombre de questions invalide : "
                f"{level}"
            )

        if (
            rules["required_score"]
            > rules["question_count"]
        ):
            raise RuntimeError(
                f"Seuil impossible : {level}"
            )

    if len(DOMAINS) != 8:
        raise RuntimeError(
            "Life World doit avoir 8 domaines."
        )


validate_configuration()