"""
MANUWORLD — JOB SYSTEM

Système central des emplois et carrières.

Gère :
    - catalogue des métiers
    - création / initialisation des métiers
    - recherche de métiers
    - vérification des conditions
    - candidature / embauche
    - emploi actuel
    - démission
    - changement d'emploi
    - salaire
    - XP de carrière
    - historique des emplois

IMPORTANT :
    - utilise la base MANUWORLD existante ;
    - ne crée aucune nouvelle base ;
    - ne modifie pas main.py.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text

from database.database import AsyncSessionLocal


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_JOBS = [
    {
        "name": "Employé administratif",
        "description": "Travail administratif dans une entreprise.",
        "minimum_age": 18,
        "minimum_education": "Collège",
        "salary_min": 75_000,
        "salary_max": 150_000,
        "experience_reward": 10,
    },
    {
        "name": "Vendeur",
        "description": "Vente de produits et accueil des clients.",
        "minimum_age": 18,
        "minimum_education": "Collège",
        "salary_min": 80_000,
        "salary_max": 180_000,
        "experience_reward": 12,
    },
    {
        "name": "Comptable",
        "description": "Gestion des comptes et opérations financières.",
        "minimum_age": 21,
        "minimum_education": "Université",
        "salary_min": 200_000,
        "salary_max": 450_000,
        "experience_reward": 20,
    },
    {
        "name": "Développeur",
        "description": "Conception et développement de logiciels.",
        "minimum_age": 21,
        "minimum_education": "Université",
        "salary_min": 250_000,
        "salary_max": 700_000,
        "experience_reward": 25,
    },
    {
        "name": "Ingénieur",
        "description": "Conception, analyse et résolution de problèmes techniques.",
        "minimum_age": 23,
        "minimum_education": "Université",
        "salary_min": 350_000,
        "salary_max": 900_000,
        "experience_reward": 30,
    },
    {
        "name": "Médecin",
        "description": "Profession médicale spécialisée.",
        "minimum_age": 25,
        "minimum_education": "Université",
        "salary_min": 500_000,
        "salary_max": 1_500_000,
        "experience_reward": 35,
    },
    {
        "name": "Enseignant",
        "description": "Transmission des connaissances et formation des élèves.",
        "minimum_age": 21,
        "minimum_education": "Université",
        "salary_min": 180_000,
        "salary_max": 500_000,
        "experience_reward": 22,
    },
    {
        "name": "Journaliste",
        "description": "Recherche, vérification et présentation de l'information.",
        "minimum_age": 21,
        "minimum_education": "Université",
        "salary_min": 180_000,
        "salary_max": 450_000,
        "experience_reward": 20,
    },
    {
        "name": "Avocat",
        "description": "Profession juridique spécialisée dans la défense et le conseil.",
        "minimum_age": 25,
        "minimum_education": "Université",
        "salary_min": 400_000,
        "salary_max": 1_200_000,
        "experience_reward": 30,
    },
    {
        "name": "Architecte",
        "description": "Conception et planification de bâtiments.",
        "minimum_age": 23,
        "minimum_education": "Université",
        "salary_min": 300_000,
        "salary_max": 900_000,
        "experience_reward": 28,
    },
]


# ============================================================
# UTILITAIRES
# ============================================================

def normalize_job_name(
    name: str,
) -> str:

    name = str(
        name or ""
    ).strip()

    if not name:
        raise ValueError(
            "Le nom du métier est obligatoire."
        )

    return name[:100]


def normalize_education(
    education: Optional[str],
) -> Optional[str]:

    if education is None:
        return None

    education = str(
        education
    ).strip()

    return education[:80] if education else None


def format_money(
    amount: int | float | None,
) -> str:

    return f"{int(amount or 0):,}".replace(
        ",",
        " ",
    )


# ============================================================
# INITIALISATION DES MÉTIERS
# ============================================================

async def seed_default_jobs() -> int:
    """
    Ajoute les métiers par défaut qui n'existent pas encore.

    Les métiers existants ne sont jamais écrasés.
    """

    added = 0

    async with AsyncSessionLocal() as session:

        for job in DEFAULT_JOBS:

            existing = await session.execute(
                text(
                    """
                    SELECT id
                    FROM life_jobs
                    WHERE LOWER(name) = LOWER(:name)
                    LIMIT 1
                    """
                ),
                {
                    "name": job["name"],
                },
            )

            if existing.first() is not None:
                continue

            await session.execute(
                text(
                    """
                    INSERT INTO life_jobs (
                        name,
                        description,
                        minimum_age,
                        minimum_education,
                        salary_min,
                        salary_max,
                        experience_reward,
                        active
                    )
                    VALUES (
                        :name,
                        :description,
                        :minimum_age,
                        :minimum_education,
                        :salary_min,
                        :salary_max,
                        :experience_reward,
                        TRUE
                    )
                    """
                ),
                job,
            )

            added += 1

        await session.commit()

    return added


# ============================================================
# RÉCUPÉRER UN MÉTIER
# ============================================================

async def get_job(
    job_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_jobs
                WHERE id = :job_id
                LIMIT 1
                """
            ),
            {
                "job_id": int(job_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


async def get_job_by_name(
    name: str,
) -> dict[str, Any] | None:

    name = normalize_job_name(
        name
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_jobs
                WHERE LOWER(name) = LOWER(:name)
                LIMIT 1
                """
            ),
            {
                "name": name,
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# LISTE DES MÉTIERS
# ============================================================

async def get_jobs(
    active_only: bool = True,
    limit: int = 100,
) -> list[dict[str, Any]]:

    limit = max(
        1,
        min(
            500,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        if active_only:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_jobs
                    WHERE active = TRUE
                    ORDER BY minimum_age ASC,
                             salary_min ASC,
                             name ASC
                    LIMIT :limit
                    """
                ),
                {
                    "limit": limit,
                },
            )

        else:

            result = await session.execute(
                text(
                    """
                    SELECT *
                    FROM life_jobs
                    ORDER BY active DESC,
                             minimum_age ASC,
                             salary_min ASC,
                             name ASC
                    LIMIT :limit
                    """
                ),
                {
                    "limit": limit,
                },
            )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# RECHERCHE
# ============================================================

async def search_jobs(
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:

    query = str(
        query or ""
    ).strip()

    if not query:
        return []

    limit = max(
        1,
        min(
            100,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_jobs
                WHERE active = TRUE
                  AND (
                    name ILIKE :query
                    OR description ILIKE :query
                  )
                ORDER BY name ASC
                LIMIT :limit
                """
            ),
            {
                "query": f"%{query}%",
                "limit": limit,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# PERSONNAGE
# ============================================================

async def get_character_for_job(
    character_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    age,
                    education_level,
                    balance,
                    job_id,
                    workplace,
                    job_salary
                FROM life_characters
                WHERE id = :character_id
                LIMIT 1
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# EMPLOI ACTUEL
# ============================================================

async def get_current_employment(
    character_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    e.*,
                    j.name AS job_name,
                    j.description AS job_description,
                    j.minimum_age,
                    j.minimum_education,
                    j.experience_reward
                FROM life_employments e
                INNER JOIN life_jobs j
                    ON j.id = e.job_id
                WHERE e.character_id = :character_id
                  AND e.status = 'active'
                ORDER BY e.hired_at DESC
                LIMIT 1
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# HISTORIQUE DES EMPLOIS
# ============================================================

async def get_employment_history(
    character_id: int,
    limit: int = 20,
) -> list[dict[str, Any]]:

    limit = max(
        1,
        min(
            100,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    e.*,
                    j.name AS job_name,
                    j.description AS job_description
                FROM life_employments e
                INNER JOIN life_jobs j
                    ON j.id = e.job_id
                WHERE e.character_id = :character_id
                ORDER BY e.hired_at DESC
                LIMIT :limit
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
                "limit": limit,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# CONDITIONS D'ACCÈS
# ============================================================

def education_rank(
    education: Optional[str],
) -> int:

    value = str(
        education or ""
    ).lower()

    if (
        "univers" in value
        or "supérieur" in value
        or "superieur" in value
    ):
        return 4

    if (
        "terminal" in value
        or "lycée" in value
        or "lycee" in value
    ):
        return 3

    if (
        "collège" in value
        or "college" in value
    ):
        return 2

    if (
        "primaire" in value
        or "école" in value
        or "ecole" in value
    ):
        return 1

    return 0


def meets_education_requirement(
    current: Optional[str],
    required: Optional[str],
) -> bool:

    if not required:
        return True

    current_rank = education_rank(
        current
    )

    required_rank = education_rank(
        required
    )

    return current_rank >= required_rank


async def check_job_requirements(
    character_id: int,
    job_id: int,
) -> dict[str, Any]:

    character = await get_character_for_job(
        character_id
    )

    if character is None:

        return {
            "success": False,
            "eligible": False,
            "message": "❌ Personnage introuvable.",
        }

    job = await get_job(
        job_id
    )

    if job is None:

        return {
            "success": False,
            "eligible": False,
            "message": "❌ Métier introuvable.",
        }

    if not bool(job["active"]):

        return {
            "success": True,
            "eligible": False,
            "message": "❌ Ce métier n'est plus disponible.",
        }

    age = int(
        character["age"] or 0
    )

    minimum_age = int(
        job["minimum_age"] or 0
    )

    if age < minimum_age:

        return {
            "success": True,
            "eligible": False,
            "reason": "age",
            "message": (
                f"❌ Âge insuffisant.\n"
                f"🎂 Ton âge : {age} ans\n"
                f"🔒 Minimum : {minimum_age} ans"
            ),
            "character": character,
            "job": job,
        }

    current_education = (
        character.get(
            "education_level"
        )
    )

    required_education = (
        job.get(
            "minimum_education"
        )
    )

    if not meets_education_requirement(
        current_education,
        required_education,
    ):

        return {
            "success": True,
            "eligible": False,
            "reason": "education",
            "message": (
                "❌ Niveau d'études insuffisant.\n"
                f"🎓 Ton niveau : "
                f"{current_education or 'Inconnu'}\n"
                f"🔒 Requis : "
                f"{required_education}"
            ),
            "character": character,
            "job": job,
        }

    return {
        "success": True,
        "eligible": True,
        "message": "✅ Toutes les conditions sont remplies.",
        "character": character,
        "job": job,
    }


# ============================================================
# SALAIRE
# ============================================================

def calculate_salary(
    job: dict[str, Any],
    performance: int = 50,
) -> int:

    minimum = int(
        job.get("salary_min") or 0
    )

    maximum = int(
        job.get("salary_max") or minimum
    )

    performance = max(
        0,
        min(
            100,
            int(performance),
        ),
    )

    if maximum <= minimum:
        return minimum

    difference = maximum - minimum

    return minimum + int(
        difference
        * (
            performance
            / 100
        )
    )


# ============================================================
# EMBAUCHE
# ============================================================

async def hire_character(
    character_id: int,
    job_id: int,
    company_name: Optional[str] = None,
    salary: Optional[int] = None,
) -> dict[str, Any]:

    requirements = await check_job_requirements(
        character_id,
        job_id,
    )

    if not requirements.get(
        "eligible"
    ):

        return requirements

    character = requirements["character"]
    job = requirements["job"]

    current = await get_current_employment(
        character_id
    )

    if current is not None:

        return {
            "success": False,
            "message": (
                "❌ Tu as déjà un emploi actif.\n"
                f"💼 Poste : {current['job_name']}\n"
                f"🏢 Entreprise : "
                f"{current.get('company_name') or 'Indépendant'}"
            ),
        }

    if salary is None:

        salary = calculate_salary(
            job,
            performance=50,
        )

    salary = int(salary)

    salary = max(
        int(job["salary_min"] or 0),
        min(
            salary,
            int(job["salary_max"] or salary),
        ),
    )

    company_name = (
        str(company_name).strip()[:120]
        if company_name
        else None
    )

    async with AsyncSessionLocal() as session:

        employment_result = await session.execute(
            text(
                """
                INSERT INTO life_employments (
                    character_id,
                    job_id,
                    company_name,
                    salary,
                    status
                )
                VALUES (
                    :character_id,
                    :job_id,
                    :company_name,
                    :salary,
                    'active'
                )
                RETURNING *
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
                "job_id": int(
                    job_id
                ),
                "company_name": company_name,
                "salary": salary,
            },
        )

        employment = dict(
            employment_result
            .mappings()
            .one()
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET
                    job_id = :job_id,
                    workplace = :workplace,
                    job_salary = :salary,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "job_id": int(
                    job_id
                ),
                "workplace": company_name,
                "salary": salary,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "employment": employment,
        "job": job,
        "salary": salary,
        "message": (
            "✅ **EMBAUCHE RÉUSSIE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 Métier : {job['name']}\n"
            f"🏢 Entreprise : "
            f"{company_name or 'Indépendant'}\n"
            f"💰 Salaire : "
            f"{format_money(salary)} FCFA"
        ),
    }


# ============================================================
# DÉMISSION
# ============================================================

async def leave_job(
    character_id: int,
) -> dict[str, Any]:

    current = await get_current_employment(
        character_id
    )

    if current is None:

        return {
            "success": False,
            "message": "❌ Tu n'as aucun emploi actif.",
        }

    async with AsyncSessionLocal() as session:

        await session.execute(
            text(
                """
                UPDATE life_employments
                SET
                    status = 'left',
                    left_at = NOW()
                WHERE id = :employment_id
                """
            ),
            {
                "employment_id": int(
                    current["id"]
                ),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET
                    job_id = NULL,
                    workplace = NULL,
                    job_salary = 0,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "message": (
            "✅ Démission enregistrée.\n"
            f"💼 Ancien poste : {current['job_name']}"
        ),
    }


# ============================================================
# SALAIRE D'UN EMPLOI
# ============================================================

async def update_employment_salary(
    character_id: int,
    salary: int,
) -> dict[str, Any]:

    salary = max(
        0,
        int(salary),
    )

    current = await get_current_employment(
        character_id
    )

    if current is None:

        return {
            "success": False,
            "message": "❌ Aucun emploi actif.",
        }

    job = await get_job(
        int(current["job_id"])
    )

    if job is None:

        return {
            "success": False,
            "message": "❌ Métier introuvable.",
        }

    minimum = int(
        job["salary_min"] or 0
    )

    maximum = int(
        job["salary_max"] or salary
    )

    salary = max(
        minimum,
        min(
            maximum,
            salary,
        ),
    )

    async with AsyncSessionLocal() as session:

        await session.execute(
            text(
                """
                UPDATE life_employments
                SET salary = :salary
                WHERE id = :employment_id
                """
            ),
            {
                "salary": salary,
                "employment_id": int(
                    current["id"]
                ),
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET
                    job_salary = :salary,
                    updated_at = NOW()
                WHERE id = :character_id
                """
            ),
            {
                "salary": salary,
                "character_id": int(
                    character_id
                ),
            },
        )

        await session.commit()

    return {
        "success": True,
        "salary": salary,
        "message": (
            f"💰 Salaire actuel : "
            f"{format_money(salary)} FCFA"
        ),
    }


# ============================================================
# FORMATAGE
# ============================================================

def format_job(
    job: dict[str, Any],
) -> str:

    salary_min = int(
        job.get("salary_min") or 0
    )

    salary_max = int(
        job.get("salary_max") or 0
    )

    minimum_age = int(
        job.get("minimum_age") or 0
    )

    education = (
        job.get("minimum_education")
        or "Aucun"
    )

    return (
        f"💼 **{job.get('name', 'Métier')}**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 {job.get('description') or 'Aucune description.'}\n\n"
        f"🎂 Âge minimum : {minimum_age} ans\n"
        f"🎓 Études : {education}\n"
        f"💰 Salaire : "
        f"{format_money(salary_min)} — "
        f"{format_money(salary_max)} FCFA\n"
        f"✨ XP : "
        f"+{int(job.get('experience_reward') or 0)}"
    )


def format_jobs(
    jobs: list[dict[str, Any]],
) -> str:

    if not jobs:

        return (
            "💼 **MÉTIERS DISPONIBLES**\n\n"
            "Aucun métier disponible."
        )

    lines = [
        "💼 **MÉTIERS DISPONIBLES**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for job in jobs:

        minimum_age = int(
            job.get("minimum_age") or 0
        )

        salary_min = int(
            job.get("salary_min") or 0
        )

        salary_max = int(
            job.get("salary_max") or 0
        )

        lines.extend(
            [
                f"💼 **{job['name']}**",
                f"   🎂 {minimum_age} ans minimum",
                (
                    f"   🎓 "
                    f"{job.get('minimum_education') or 'Aucun'}"
                ),
                (
                    f"   💰 "
                    f"{format_money(salary_min)} — "
                    f"{format_money(salary_max)} FCFA"
                ),
                "",
            ]
        )

    return "\n".join(lines)


def format_employment(
    employment: dict[str, Any],
) -> str:

    salary = int(
        employment.get("salary") or 0
    )

    company = (
        employment.get("company_name")
        or "Indépendant"
    )

    status = (
        employment.get("status")
        or "active"
    )

    return (
        "💼 **EMPLOI ACTUEL**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👔 Poste : **{employment.get('job_name', '—')}**\n"
        f"🏢 Entreprise : {company}\n"
        f"💰 Salaire : "
        f"{format_money(salary)} FCFA\n"
        f"📊 Statut : {status}\n"
        f"📅 Embauche : "
        f"{employment.get('hired_at') or '—'}"
    )


def format_employment_history(
    history: list[dict[str, Any]],
) -> str:

    if not history:

        return (
            "📜 **HISTORIQUE PROFESSIONNEL**\n\n"
            "Aucun emploi enregistré."
        )

    lines = [
        "📜 **HISTORIQUE PROFESSIONNEL**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for employment in history:

        salary = int(
            employment.get("salary") or 0
        )

        company = (
            employment.get("company_name")
            or "Indépendant"
        )

        status = (
            employment.get("status")
            or "unknown"
        )

        lines.extend(
            [
                f"💼 **{employment.get('job_name', '—')}**",
                f"   🏢 {company}",
                f"   💰 {format_money(salary)} FCFA",
                f"   📊 {status}",
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================
# RÉSUMÉ CARRIÈRE
# ============================================================

async def get_career_summary(
    character_id: int,
) -> dict[str, Any]:

    character = await get_character_for_job(
        character_id
    )

    if character is None:

        return {
            "success": False,
            "message": "❌ Personnage introuvable.",
        }

    current = await get_current_employment(
        character_id
    )

    history = await get_employment_history(
        character_id,
        limit=100,
    )

    total_jobs = len(
        history
    )

    total_salary = sum(
        int(
            item.get("salary") or 0
        )
        for item in history
    )

    return {
        "success": True,
        "character": character,
        "current": current,
        "history": history,
        "total_jobs": total_jobs,
        "total_recorded_salary": total_salary,
    }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "DEFAULT_JOBS",
    "normalize_job_name",
    "normalize_education",
    "format_money",
    "seed_default_jobs",
    "get_job",
    "get_job_by_name",
    "get_jobs",
    "search_jobs",
    "get_character_for_job",
    "get_current_employment",
    "get_employment_history",
    "education_rank",
    "meets_education_requirement",
    "check_job_requirements",
    "calculate_salary",
    "hire_character",
    "leave_job",
    "update_employment_salary",
    "format_job",
    "format_jobs",
    "format_employment",
    "format_employment_history",
    "get_career_summary",
]