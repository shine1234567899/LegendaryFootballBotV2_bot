"""
Life World — School Exam Database

Stocke les sessions et résultats des examens scolaires.

Gère :
- examen en cours ;
- score ;
- questions répondues ;
- réussite/échec ;
- domaine ;
- historique des examens ;
- meilleur résultat par niveau.

IMPORTANT :
main.py sera branché à la fin.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "life_world.db"


# ============================================================
# CONNEXION
# ============================================================

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# TABLES
# ============================================================

def setup_exam_database() -> None:

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS school_exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL,

            level TEXT NOT NULL,

            domain TEXT,

            total_questions INTEGER NOT NULL,

            required_score INTEGER NOT NULL,

            score INTEGER NOT NULL DEFAULT 0,

            current_question INTEGER NOT NULL DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'active',

            passed INTEGER NOT NULL DEFAULT 0,

            started_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER)
            ),

            finished_at INTEGER
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS school_exam_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            session_id INTEGER NOT NULL,

            question_number INTEGER NOT NULL,

            answer_index INTEGER NOT NULL,

            correct INTEGER NOT NULL DEFAULT 0,

            answered_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s', 'now') AS INTEGER
            )),

            FOREIGN KEY(session_id)
                REFERENCES school_exam_sessions(id)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_exam_sessions_username
        ON school_exam_sessions(username)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_exam_answers_session
        ON school_exam_answers(session_id)
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# CRÉER UNE SESSION
# ============================================================

def create_exam_session(
    username: str,
    level: str,
    domain: Optional[str],
    total_questions: int,
    required_score: int,
) -> int:

    username = username.strip().lower()
    level = level.strip().lower()

    if not username:
        raise ValueError(
            "Username obligatoire."
        )

    if total_questions <= 0:
        raise ValueError(
            "Nombre de questions invalide."
        )

    if not (
        0 <= required_score <= total_questions
    ):
        raise ValueError(
            "Seuil de réussite invalide."
        )

    conn = get_connection()

    cursor = conn.execute(
        """
        INSERT INTO school_exam_sessions (
            username,
            level,
            domain,
            total_questions,
            required_score,
            score,
            current_question,
            status,
            passed
        )
        VALUES (?, ?, ?, ?, ?, 0, 0, 'active', 0)
        """,
        (
            username,
            level,
            domain.lower() if domain else None,
            total_questions,
            required_score,
        ),
    )

    session_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return int(session_id)


# ============================================================
# SESSION ACTIVE
# ============================================================

def get_active_session(
    username: str,
) -> Optional[dict]:

    username = username.strip().lower()

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM school_exam_sessions
        WHERE username = ?
          AND status = 'active'
        ORDER BY id DESC
        LIMIT 1
        """,
        (username,),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


# ============================================================
# RÉPONSE
# ============================================================

def save_answer(
    session_id: int,
    question_number: int,
    answer_index: int,
    correct: bool,
) -> None:

    conn = get_connection()

    session = conn.execute(
        """
        SELECT *
        FROM school_exam_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()

    if session is None:
        conn.close()
        raise ValueError(
            "Session d'examen introuvable."
        )

    if session["status"] != "active":
        conn.close()
        raise ValueError(
            "Cette session est déjà terminée."
        )

    # Empêche de répondre deux fois à la même question.
    already_answered = conn.execute(
        """
        SELECT id
        FROM school_exam_answers
        WHERE session_id = ?
          AND question_number = ?
        LIMIT 1
        """,
        (
            session_id,
            question_number,
        ),
    ).fetchone()

    if already_answered:
        conn.close()
        raise ValueError(
            "Cette question a déjà été répondue."
        )

    conn.execute(
        """
        INSERT INTO school_exam_answers (
            session_id,
            question_number,
            answer_index,
            correct
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id,
            question_number,
            answer_index,
            int(correct),
        ),
    )

    new_score = (
        session["score"]
        + (1 if correct else 0)
    )

    new_current = (
        session["current_question"]
        + 1
    )

    conn.execute(
        """
        UPDATE school_exam_sessions
        SET
            score = ?,
            current_question = ?
        WHERE id = ?
        """,
        (
            new_score,
            new_current,
            session_id,
        ),
    )

    conn.commit()
    conn.close()


# ============================================================
# TERMINER
# ============================================================

def finish_exam(
    session_id: int,
) -> dict:

    conn = get_connection()

    session = conn.execute(
        """
        SELECT *
        FROM school_exam_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()

    if session is None:
        conn.close()
        raise ValueError(
            "Session introuvable."
        )

    if session["status"] == "finished":

        conn.close()

        return dict(session)

    passed = (
        session["score"]
        >= session["required_score"]
    )

    conn.execute(
        """
        UPDATE school_exam_sessions
        SET
            status = 'finished',
            passed = ?,
            finished_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE id = ?
        """,
        (
            int(passed),
            session_id,
        ),
    )

    conn.commit()

    result = conn.execute(
        """
        SELECT *
        FROM school_exam_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()

    conn.close()

    return dict(result)


# ============================================================
# ABANDONNER
# ============================================================

def cancel_exam(
    session_id: int,
) -> None:

    conn = get_connection()

    conn.execute(
        """
        UPDATE school_exam_sessions
        SET
            status = 'cancelled',
            finished_at =
                CAST(strftime('%s', 'now') AS INTEGER)
        WHERE id = ?
          AND status = 'active'
        """,
        (session_id,),
    )

    conn.commit()
    conn.close()


# ============================================================
# HISTORIQUE
# ============================================================

def get_exam_history(
    username: str,
) -> list[dict]:

    username = username.strip().lower()

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM school_exam_sessions
        WHERE username = ?
          AND status = 'finished'
        ORDER BY id DESC
        """,
        (username,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# MEILLEUR RÉSULTAT
# ============================================================

def get_best_result(
    username: str,
    level: str,
) -> Optional[dict]:

    username = username.strip().lower()
    level = level.strip().lower()

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM school_exam_sessions
        WHERE username = ?
          AND level = ?
          AND status = 'finished'
        ORDER BY
            passed DESC,
            score DESC,
            id DESC
        LIMIT 1
        """,
        (
            username,
            level,
        ),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


# ============================================================
# STATISTIQUES
# ============================================================

def get_exam_statistics(
    username: str,
) -> dict:

    username = username.strip().lower()

    conn = get_connection()

    total = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM school_exam_sessions
        WHERE username = ?
          AND status = 'finished'
        """,
        (username,),
    ).fetchone()["count"]

    passed = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM school_exam_sessions
        WHERE username = ?
          AND status = 'finished'
          AND passed = 1
        """,
        (username,),
    ).fetchone()["count"]

    failed = total - passed

    conn.close()

    return {
        "total_exams": total,
        "passed": passed,
        "failed": failed,
    }


# ============================================================
# QUESTIONS RÉPONDUES
# ============================================================

def get_session_answers(
    session_id: int,
) -> list[dict]:

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM school_exam_answers
        WHERE session_id = ?
        ORDER BY question_number ASC
        """,
        (session_id,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# SUPPRIMER UNE SESSION INCOMPLÈTE
# ============================================================

def delete_active_session(
    username: str,
) -> None:

    username = username.strip().lower()

    conn = get_connection()

    sessions = conn.execute(
        """
        SELECT id
        FROM school_exam_sessions
        WHERE username = ?
          AND status = 'active'
        """,
        (username,),
    ).fetchall()

    for session in sessions:

        conn.execute(
            """
            DELETE FROM school_exam_answers
            WHERE session_id = ?
            """,
            (session["id"],),
        )

        conn.execute(
            """
            DELETE FROM school_exam_sessions
            WHERE id = ?
            """,
            (session["id"],),
        )

    conn.commit()
    conn.close()


# ============================================================
# INITIALISATION
# ============================================================

setup_exam_database()