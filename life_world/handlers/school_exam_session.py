"""
Life World — School Exam Session

Gestion de la session d'examen côté jeu :

- démarrage d'un examen ;
- conservation de la session ;
- récupération de la question actuelle ;
- réponses ;
- progression ;
- résultat final ;
- blocage des doubles réponses ;
- abandon propre de la session.

IMPORTANT :
Ce module ne branche PAS main.py.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# RÈGLES
# ============================================================

EXAM_RULES = {
    "cep": {
        "name": "CEP",
        "questions": 5,
        "required": 4,
        "domain_required": False,
    },
    "bepc": {
        "name": "BEPC",
        "questions": 7,
        "required": 5,
        "domain_required": True,
    },
    "probatoire": {
        "name": "PROBATOIRE",
        "questions": 10,
        "required": 8,
        "domain_required": True,
    },
    "bacc": {
        "name": "BACCALAURÉAT",
        "questions": 12,
        "required": 10,
        "domain_required": True,
    },
    "university": {
        "name": "UNIVERSITÉ",
        "questions": 15,
        "required": 15,
        "domain_required": True,
    },
}


# ============================================================
# QUESTION
# ============================================================

@dataclass
class SessionQuestion:
    number: int
    text: str
    answers: list[str]
    correct_index: int


# ============================================================
# SESSION
# ============================================================

@dataclass
class UserExamSession:
    username: str
    level: str
    domain: Optional[str]

    questions: list[SessionQuestion]

    current: int = 0
    score: int = 0

    answered: set[int] = field(
        default_factory=set
    )

    finished: bool = False

    passed: Optional[bool] = None


# ============================================================
# NORMALISATION
# ============================================================

def normalize_level(level: str) -> str:

    level = str(level).strip().lower()

    if level not in EXAM_RULES:
        raise ValueError(
            f"Niveau inconnu : {level}"
        )

    return level


# ============================================================
# CONVERSION
# ============================================================

def convert_question(
    raw,
    number: int,
) -> SessionQuestion:
    """
    Compatible avec plusieurs formats de banques.
    """

    if isinstance(raw, dict):

        text = raw.get(
            "question",
            raw.get("text"),
        )

        answers = raw.get(
            "answers",
            raw.get("options"),
        )

        correct = raw.get(
            "correct_answer",
            raw.get(
                "correct",
                raw.get("answer"),
            ),
        )

    elif isinstance(raw, (tuple, list)):

        if len(raw) < 3:
            raise ValueError(
                "Question invalide."
            )

        text = raw[0]
        answers = raw[1]
        correct = raw[2]

    else:

        text = getattr(
            raw,
            "question",
            getattr(
                raw,
                "text",
                None,
            ),
        )

        answers = getattr(
            raw,
            "answers",
            getattr(
                raw,
                "options",
                None,
            ),
        )

        correct = getattr(
            raw,
            "correct_index",
            getattr(
                raw,
                "correct_answer",
                getattr(
                    raw,
                    "correct",
                    None,
                ),
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
            "Réponse correcte absente."
        )

    answers = list(answers)

    correct = int(correct)

    if not (
        0 <= correct < len(answers)
    ):
        raise ValueError(
            "Index de réponse incorrect."
        )

    return SessionQuestion(
        number=number,
        text=str(text),
        answers=answers,
        correct_index=correct,
    )


# ============================================================
# CHARGEMENT DE LA BANQUE
# ============================================================

def _load_bank():

    try:
        from .domain_question_bank import ADVANCED
        return ADVANCED

    except ImportError:

        try:
            from domain_question_bank import ADVANCED
            return ADVANCED

        except ImportError as exc:

            raise ImportError(
                "domain_question_bank.py "
                "est introuvable."
            ) from exc


# ============================================================
# RÉCUPÉRATION DES QUESTIONS
# ============================================================

def get_questions(
    level: str,
    domain: Optional[str] = None,
) -> list:

    level = normalize_level(level)

    bank = _load_bank()

    rules = EXAM_RULES[level]

    # --------------------------------------------------------
    # CEP
    # --------------------------------------------------------

    if level == "cep":

        if isinstance(bank, dict):

            if "cep" in bank:
                source = bank["cep"]

            elif "basic" in bank:
                source = bank["basic"]

            else:
                raise RuntimeError(
                    "Banque CEP introuvable."
                )

        else:
            raise RuntimeError(
                "Format de banque invalide."
            )

    # --------------------------------------------------------
    # BEPC
    # --------------------------------------------------------

    elif level == "bepc":

        if not domain:
            raise ValueError(
                "Le domaine est obligatoire au BEPC."
            )

        domain = domain.lower().strip()

        if domain not in bank:
            raise RuntimeError(
                f"Domaine introuvable : {domain}"
            )

        domain_bank = bank[domain]

        if "bepc" not in domain_bank:
            raise RuntimeError(
                f"Banque BEPC absente : {domain}"
            )

        source = domain_bank["bepc"]

    # --------------------------------------------------------
    # PROBATOIRE / BACC / UNIVERSITÉ
    # --------------------------------------------------------

    else:

        if not domain:
            raise ValueError(
                f"Le domaine est obligatoire "
                f"pour {level}."
            )

        domain = domain.lower().strip()

        if domain not in bank:
            raise RuntimeError(
                f"Domaine introuvable : {domain}"
            )

        domain_bank = bank[domain]

        if level not in domain_bank:
            raise RuntimeError(
                f"Banque {level} absente : {domain}"
            )

        source = domain_bank[level]

    source = list(source)

    if len(source) < rules["questions"]:
        raise RuntimeError(
            f"Banque insuffisante : "
            f"{level}/{domain or 'general'}"
        )

    # Aucune question en double dans la session.
    return random.sample(
        source,
        rules["questions"],
    )


# ============================================================
# CRÉER UNE SESSION
# ============================================================

def create_session(
    username: str,
    level: str,
    domain: Optional[str] = None,
) -> UserExamSession:

    username = username.strip().lower()

    if not username:
        raise ValueError(
            "Username obligatoire."
        )

    level = normalize_level(level)

    rules = EXAM_RULES[level]

    if (
        rules["domain_required"]
        and not domain
    ):
        raise ValueError(
            f"Le domaine est obligatoire "
            f"pour {rules['name']}."
        )

    questions = get_questions(
        level,
        domain,
    )

    converted = [
        convert_question(
            question,
            index + 1,
        )
        for index, question
        in enumerate(questions)
    ]

    return UserExamSession(
        username=username,
        level=level,
        domain=(
            domain.lower().strip()
            if domain
            else None
        ),
        questions=converted,
    )


# ============================================================
# QUESTION ACTUELLE
# ============================================================

def current_question(
    session: UserExamSession,
) -> Optional[SessionQuestion]:

    if session.finished:
        return None

    if session.current >= len(
        session.questions
    ):
        return None

    return session.questions[
        session.current
    ]


# ============================================================
# INFORMATIONS SESSION
# ============================================================

def session_status(
    session: UserExamSession,
) -> dict:

    total = len(
        session.questions
    )

    return {
        "username": session.username,
        "level": session.level,
        "domain": session.domain,
        "current": session.current + 1
        if not session.finished
        else total,
        "answered": len(
            session.answered
        ),
        "score": session.score,
        "total": total,
        "finished": session.finished,
        "passed": session.passed,
    }


# ============================================================
# RÉPONDRE
# ============================================================

def submit_answer(
    session: UserExamSession,
    answer_index: int,
) -> dict:

    if session.finished:

        return {
            "success": False,
            "finished": True,
            "message": (
                "⚠️ Cet examen est terminé."
            ),
        }

    question = current_question(
        session
    )

    if question is None:

        return finish_session(
            session
        )

    if question.number in session.answered:

        return {
            "success": False,
            "finished": False,
            "message": (
                "⚠️ Cette question "
                "a déjà été répondue."
            ),
        }

    try:
        answer_index = int(
            answer_index
        )
    except (
        TypeError,
        ValueError,
    ):

        return {
            "success": False,
            "finished": False,
            "message": (
                "❌ Réponse invalide."
            ),
        }

    if not (
        0
        <= answer_index
        < len(question.answers)
    ):

        return {
            "success": False,
            "finished": False,
            "message": (
                "❌ Réponse invalide."
            ),
        }

    correct = (
        answer_index
        == question.correct_index
    )

    session.answered.add(
        question.number
    )

    if correct:
        session.score += 1

    session.current += 1

    if (
        session.current
        >= len(session.questions)
    ):

        result = finish_session(
            session
        )

        result["correct"] = correct

        return result

    next_question = current_question(
        session
    )

    return {
        "success": True,
        "finished": False,
        "correct": correct,
        "score": session.score,
        "answered": len(
            session.answered
        ),
        "total": len(
            session.questions
        ),
        "next_question": next_question,
    }


# ============================================================
# TERMINER
# ============================================================

def finish_session(
    session: UserExamSession,
) -> dict:

    if session.finished:

        return {
            "success": True,
            "finished": True,
            "passed": session.passed,
            "score": session.score,
            "total": len(
                session.questions
            ),
            "required": EXAM_RULES[
                session.level
            ]["required"],
        }

    session.finished = True

    required = EXAM_RULES[
        session.level
    ]["required"]

    session.passed = (
        session.score >= required
    )

    return {
        "success": True,
        "finished": True,
        "passed": session.passed,
        "score": session.score,
        "total": len(
            session.questions
        ),
        "required": required,
        "level": session.level,
        "domain": session.domain,
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_question(
    session: UserExamSession,
) -> str:

    question = current_question(
        session
    )

    if question is None:
        return (
            "🏁 <b>Examen terminé.</b>"
        )

    total = len(
        session.questions
    )

    return (
        f"📝 <b>Question "
        f"{question.number}/{total}</b>\n\n"
        f"{question.text}"
    )


def format_result(
    result: dict,
) -> str:

    level = result.get(
        "level",
        "examen",
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
        0,
    )

    if result.get("passed"):

        return (
            f"🎓 <b>{name}</b>\n\n"
            f"📊 Score : "
            f"<b>{score}/{total}</b>\n"
            f"🎯 Minimum : "
            f"<b>{required}/{total}</b>\n\n"
            "🎉 <b>ADMIS !</b>"
        )

    return (
        f"🎓 <b>{name}</b>\n\n"
        f"📊 Score : "
        f"<b>{score}/{total}</b>\n"
        f"🎯 Minimum : "
        f"<b>{required}/{total}</b>\n\n"
        "❌ <b>ÉCHEC</b>"
    )


# ============================================================
# ABANDON
# ============================================================

def abandon_session(
    session: UserExamSession,
) -> dict:

    session.finished = True
    session.passed = False

    return {
        "success": True,
        "finished": True,
        "abandoned": True,
        "passed": False,
        "score": session.score,
        "total": len(
            session.questions
        ),
    }