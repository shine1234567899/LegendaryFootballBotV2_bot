"""
Life World — School Data

Catalogue des établissements scolaires et universitaires.

Le système permet :
- de proposer plusieurs écoles ;
- d'associer une école à un niveau ;
- d'associer une école à un domaine ;
- d'afficher les frais d'inscription ;
- de changer d'école ;
- de préparer les boutons Telegram.

IMPORTANT :
Ce fichier contient uniquement les données.
Aucun branchement dans main.py ici.
"""

from __future__ import annotations


# ============================================================
# STRUCTURE
# ============================================================

SCHOOLS = {

    # ========================================================
    # COLLÈGE — BEPC
    # ========================================================

    "college_general": {
        "name": "Collège Général Life World",
        "type": "college",
        "level": "bepc",
        "domains": [
            "science",
            "technology",
            "economics",
            "law",
            "medicine",
            "arts",
            "communication",
            "engineering",
        ],
        "enrollment_price": 25000,
        "monthly_price": 10000,
    },

    "college_science": {
        "name": "Collège Scientifique Life World",
        "type": "college",
        "level": "bepc",
        "domains": [
            "science",
            "medicine",
            "engineering",
            "technology",
        ],
        "enrollment_price": 35000,
        "monthly_price": 12000,
    },

    "college_tech": {
        "name": "Collège Numérique Life World",
        "type": "college",
        "level": "bepc",
        "domains": [
            "technology",
            "engineering",
        ],
        "enrollment_price": 40000,
        "monthly_price": 14000,
    },

    "college_business": {
        "name": "Collège Business Life World",
        "type": "college",
        "level": "bepc",
        "domains": [
            "economics",
            "communication",
        ],
        "enrollment_price": 30000,
        "monthly_price": 11000,
    },


    # ========================================================
    # LYCÉE — PROBATOIRE
    # ========================================================

    "lycee_sciences": {
        "name": "Lycée Scientifique Life World",
        "type": "lycee",
        "level": "probatoire",
        "domains": [
            "science",
            "medicine",
            "engineering",
        ],
        "enrollment_price": 50000,
        "monthly_price": 18000,
    },

    "lycee_technologie": {
        "name": "Lycée Technologie & Innovation",
        "type": "lycee",
        "level": "probatoire",
        "domains": [
            "technology",
            "engineering",
        ],
        "enrollment_price": 55000,
        "monthly_price": 20000,
    },

    "lycee_economie": {
        "name": "Lycée Économie & Gestion",
        "type": "lycee",
        "level": "probatoire",
        "domains": [
            "economics",
            "communication",
        ],
        "enrollment_price": 48000,
        "monthly_price": 17000,
    },

    "lycee_litteraire": {
        "name": "Lycée Arts & Communication",
        "type": "lycee",
        "level": "probatoire",
        "domains": [
            "arts",
            "communication",
            "law",
        ],
        "enrollment_price": 45000,
        "monthly_price": 16000,
    },


    # ========================================================
    # LYCÉE — BACC
    # ========================================================

    "lycee_sciences_bacc": {
        "name": "Institut Scientifique Life World",
        "type": "lycee",
        "level": "bacc",
        "domains": [
            "science",
            "medicine",
            "engineering",
        ],
        "enrollment_price": 65000,
        "monthly_price": 22000,
    },

    "lycee_tech_bacc": {
        "name": "Institut Technologie & Informatique",
        "type": "lycee",
        "level": "bacc",
        "domains": [
            "technology",
            "engineering",
        ],
        "enrollment_price": 70000,
        "monthly_price": 24000,
    },

    "lycee_business_bacc": {
        "name": "Institut Économie & Management",
        "type": "lycee",
        "level": "bacc",
        "domains": [
            "economics",
            "communication",
        ],
        "enrollment_price": 62000,
        "monthly_price": 21000,
    },

    "lycee_droit_bacc": {
        "name": "Institut Droit & Sciences Humaines",
        "type": "lycee",
        "level": "bacc",
        "domains": [
            "law",
            "communication",
            "arts",
        ],
        "enrollment_price": 60000,
        "monthly_price": 20000,
    },


    # ========================================================
    # UNIVERSITÉ
    # ========================================================

    "univ_sciences": {
        "name": "Université des Sciences Life World",
        "type": "university",
        "level": "university",
        "domains": [
            "science",
        ],
        "enrollment_price": 150000,
        "monthly_price": 0,
    },

    "univ_tech": {
        "name": "Université des Technologies Life World",
        "type": "university",
        "level": "university",
        "domains": [
            "technology",
            "engineering",
        ],
        "enrollment_price": 180000,
        "monthly_price": 0,
    },

    "univ_economics": {
        "name": "Université d'Économie & Gestion",
        "type": "university",
        "level": "university",
        "domains": [
            "economics",
        ],
        "enrollment_price": 160000,
        "monthly_price": 0,
    },

    "univ_law": {
        "name": "Université de Droit Life World",
        "type": "university",
        "level": "university",
        "domains": [
            "law",
        ],
        "enrollment_price": 155000,
        "monthly_price": 0,
    },

    "univ_medicine": {
        "name": "Université des Sciences de la Santé",
        "type": "university",
        "level": "university",
        "domains": [
            "medicine",
        ],
        "enrollment_price": 250000,
        "monthly_price": 0,
    },

    "univ_arts": {
        "name": "Université des Arts & Création",
        "type": "university",
        "level": "university",
        "domains": [
            "arts",
        ],
        "enrollment_price": 140000,
        "monthly_price": 0,
    },

    "univ_communication": {
        "name": "Université Communication & Médias",
        "type": "university",
        "level": "university",
        "domains": [
            "communication",
        ],
        "enrollment_price": 145000,
        "monthly_price": 0,
    },
}


# ============================================================
# RECHERCHE
# ============================================================

def get_school(school_id: str):
    """Retourne une école par son identifiant."""
    return SCHOOLS.get(school_id)


def get_schools_for_level(level: str) -> dict:
    """Retourne toutes les écoles correspondant au niveau."""
    level = level.lower().strip()

    return {
        school_id: school
        for school_id, school in SCHOOLS.items()
        if school["level"] == level
    }


def get_schools_for_domain(
    level: str,
    domain: str,
) -> dict:
    """
    Retourne uniquement les établissements
    compatibles avec le niveau et le domaine.
    """

    level = level.lower().strip()
    domain = domain.lower().strip()

    return {
        school_id: school
        for school_id, school in SCHOOLS.items()
        if (
            school["level"] == level
            and domain in school["domains"]
        )
    }


# ============================================================
# PRIX
# ============================================================

def get_enrollment_price(
    school_id: str,
) -> int:
    """Retourne le prix d'inscription."""

    school = get_school(school_id)

    if not school:
        raise ValueError("Établissement introuvable.")

    return school["enrollment_price"]


def get_monthly_price(
    school_id: str,
) -> int:
    """Retourne les frais mensuels."""

    school = get_school(school_id)

    if not school:
        raise ValueError("Établissement introuvable.")

    return school["monthly_price"]


# ============================================================
# VALIDATION
# ============================================================

def school_accepts_domain(
    school_id: str,
    domain: str,
) -> bool:
    """Vérifie qu'une école accepte le domaine."""

    school = get_school(school_id)

    if not school:
        return False

    return domain.lower().strip() in school["domains"]


def school_matches_level(
    school_id: str,
    level: str,
) -> bool:
    """Vérifie qu'une école correspond au niveau."""

    school = get_school(school_id)

    if not school:
        return False

    return school["level"] == level.lower().strip()


# ============================================================
# BOUTONS
# ============================================================

def get_school_buttons(
    level: str,
    domain: str,
) -> list[tuple[str, str]]:
    """
    Prépare les données nécessaires aux boutons Telegram.

    Retour :
        [
            ("school_id", "🏫 Nom — 50 000 FCFA"),
            ...
        ]
    """

    schools = get_schools_for_domain(
        level,
        domain,
    )

    buttons = []

    for school_id, school in schools.items():
        buttons.append(
            (
                school_id,
                (
                    f"🏫 {school['name']} — "
                    f"{school['enrollment_price']:,} FCFA"
                ),
            )
        )

    return buttons


# ============================================================
# RÉSUMÉ
# ============================================================

def school_summary(
    school_id: str,
) -> str:
    """Produit le résumé d'un établissement."""

    school = get_school(school_id)

    if not school:
        return "❌ Établissement introuvable."

    domains = ", ".join(
        school["domains"]
    )

    return (
        f"🏫 <b>{school['name']}</b>\n\n"
        f"🎓 Niveau : {school['level'].upper()}\n"
        f"🧭 Domaines : {domains}\n"
        f"💰 Inscription : "
        f"{school['enrollment_price']:,} FCFA\n"
        f"📅 Mensualité : "
        f"{school['monthly_price']:,} FCFA"
    )