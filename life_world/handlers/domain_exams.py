"""
MANUWORLD - domain_exams.py

Examens scolaires liés au domaine choisi.

Règles :
    CEP       : 5 questions faciles, réussite >= 4/5
    BEPC      : 7 questions moyennes, réussite >= 5/7
    Probatoire: 10 questions difficiles, réussite >= 8/10
    BACC      : 12 questions difficiles, réussite >= 10/12
    Université: 15 questions expertes, réussite = 15/15

À partir du collège, les questions sont sélectionnées selon
le domaine choisi par le joueur.

Domaines :
    Sciences
    Technologie & Informatique
    Économie & Gestion
    Droit
    Santé & Médecine
    Arts & Création
    Communication & Médias
    Ingénierie

Chaque niveau possède sa propre banque de questions.
Les questions ne sont donc pas les mêmes entre CEP, BEPC,
Probatoire, BACC et Université.
"""

from __future__ import annotations

import random
import uuid
from typing import Any
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from life_world.database import AsyncSessionLocal, get_life_character
from sqlalchemy import text


# ============================================================
# CONFIGURATION DES EXAMENS
# ============================================================

EXAMS = {
    "primary": {
        "name": "CEP",
        "count": 5,
        "required": 4,
        "difficulty": "Facile",
    },
    "college": {
        "name": "BEPC",
        "count": 7,
        "required": 5,
        "difficulty": "Moyenne",
    },
    "probatoire": {
        "name": "Probatoire",
        "count": 10,
        "required": 8,
        "difficulty": "Difficile",
    },
    "baccalaureat": {
        "name": "BACCALAURÉAT",
        "count": 12,
        "required": 10,
        "difficulty": "Difficile",
    },
    "university": {
        "name": "UNIVERSITÉ",
        "count": 15,
        "required": 15,
        "difficulty": "Expert",
    },
}


# ============================================================
# DOMAINES
# ============================================================

DOMAIN_NAMES = {
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
# BANQUE DE QUESTIONS
#
# Chaque niveau a une banque séparée.
# Les questions ne sont jamais copiées automatiquement d'un
# niveau vers un autre.
# ============================================================

QUESTIONS: dict[str, dict[str, list[dict[str, Any]]]] = {

    "primary": {
        "general": [
            {
                "question": "Combien font 7 + 8 ?",
                "answers": ["13", "14", "15", "16"],
                "correct": 2,
            },
            {
                "question": "Combien de jours compte une semaine ?",
                "answers": ["5", "6", "7", "8"],
                "correct": 2,
            },
            {
                "question": "Quelle est la capitale du Cameroun ?",
                "answers": ["Douala", "Yaoundé", "Bamenda", "Garoua"],
                "correct": 1,
            },
            {
                "question": "Quel est le pluriel de « cheval » ?",
                "answers": ["Chevals", "Chevaux", "Chevaus", "Chevales"],
                "correct": 1,
            },
            {
                "question": "Combien font 5 × 6 ?",
                "answers": ["25", "30", "35", "40"],
                "correct": 1,
            },
            {
                "question": "Combien de mois compte une année ?",
                "answers": ["10", "11", "12", "13"],
                "correct": 2,
            },
        ],
    },

    "college": {
        "science": [
            {
                "question": "Quel organe pompe le sang dans le corps humain ?",
                "answers": ["Le foie", "Le cœur", "Le rein", "Le poumon"],
                "correct": 1,
            },
            {
                "question": "Quelle planète est connue comme la planète rouge ?",
                "answers": ["Vénus", "Mars", "Jupiter", "Mercure"],
                "correct": 1,
            },
            {
                "question": "Quelle unité mesure une température ?",
                "answers": ["Mètre", "Kilogramme", "Degré Celsius", "Newton"],
                "correct": 2,
            },
            {
                "question": "Quel gaz est principalement utilisé par l'être humain pour respirer ?",
                "answers": ["Oxygène", "Hydrogène", "Hélium", "Méthane"],
                "correct": 0,
            },
            {
                "question": "Combien de côtés possède un triangle ?",
                "answers": ["2", "3", "4", "5"],
                "correct": 1,
            },
            {
                "question": "Quel état possède une matière qui conserve son propre volume et sa forme ?",
                "answers": ["Solide", "Liquide", "Gaz", "Plasma"],
                "correct": 0,
            },
            {
                "question": "Quel est le résultat de 12 × 8 ?",
                "answers": ["86", "96", "106", "116"],
                "correct": 1,
            },
        ],

        "technology": [
            {
                "question": "Que signifie l'abréviation CPU ?",
                "answers": [
                    "Central Processing Unit",
                    "Computer Personal User",
                    "Central Program Utility",
                    "Control Processing User",
                ],
                "correct": 0,
            },
            {
                "question": "Lequel est un langage de programmation ?",
                "answers": ["Python", "HTML", "Wi-Fi", "USB"],
                "correct": 0,
            },
            {
                "question": "Quel composant conserve les données même après extinction ?",
                "answers": ["SSD", "RAM", "Ventilateur", "Écran"],
                "correct": 0,
            },
            {
                "question": "Que représente généralement une adresse IP ?",
                "answers": [
                    "Un identifiant réseau",
                    "Une marque de téléphone",
                    "Un mot de passe",
                    "Une résolution d'écran",
                ],
                "correct": 0,
            },
            {
                "question": "Quel périphérique permet principalement de saisir du texte ?",
                "answers": ["Clavier", "Écran", "Haut-parleur", "Projecteur"],
                "correct": 0,
            },
            {
                "question": "Que signifie USB ?",
                "answers": [
                    "Universal Serial Bus",
                    "Universal System Base",
                    "User Serial Box",
                    "United Software Bus",
                ],
                "correct": 0,
            },
            {
                "question": "Quel système est un système d'exploitation ?",
                "answers": ["Linux", "Python", "HTML", "Bluetooth"],
                "correct": 0,
            },
        ],

        "economics": [
            {
                "question": "Que signifie épargner ?",
                "answers": [
                    "Dépenser immédiatement",
                    "Mettre de l'argent de côté",
                    "Emprunter",
                    "Créer une dette",
                ],
                "correct": 1,
            },
            {
                "question": "Que représente un salaire ?",
                "answers": [
                    "Une rémunération du travail",
                    "Une taxe",
                    "Une dette",
                    "Une amende",
                ],
                "correct": 0,
            },
            {
                "question": "Que se passe-t-il généralement quand une personne dépense plus que son revenu ?",
                "answers": [
                    "Son épargne augmente automatiquement",
                    "Elle peut créer un déficit",
                    "Elle gagne automatiquement de l'argent",
                    "Ses dépenses disparaissent",
                ],
                "correct": 1,
            },
            {
                "question": "Quel document présente généralement les revenus et dépenses prévus ?",
                "answers": ["Budget", "Passeport", "Diplôme", "Contrat de mariage"],
                "correct": 0,
            },
            {
                "question": "Qu'est-ce qu'un prix ?",
                "answers": [
                    "La valeur monétaire demandée pour un bien ou service",
                    "Un diplôme",
                    "Un salaire obligatoire",
                    "Une identité",
                ],
                "correct": 0,
            },
            {
                "question": "Que fait une banque avec un dépôt ?",
                "answers": [
                    "Elle le gère selon les conditions du compte",
                    "Elle détruit l'argent",
                    "Elle transforme toujours l'argent en or",
                    "Elle annule le dépôt",
                ],
                "correct": 0,
            },
            {
                "question": "Qu'est-ce qu'une entreprise ?",
                "answers": [
                    "Une organisation qui produit ou fournit des biens ou services",
                    "Un diplôme",
                    "Une école uniquement",
                    "Une monnaie",
                ],
                "correct": 0,
            },
        ],

        "law": [
            {
                "question": "À quoi sert principalement une loi ?",
                "answers": [
                    "À établir des règles de droit",
                    "À fixer les goûts musicaux",
                    "À choisir les vêtements",
                    "À distribuer des cadeaux",
                ],
                "correct": 0,
            },
            {
                "question": "Qui rend généralement une décision de justice ?",
                "answers": ["Un tribunal", "Un magasin", "Une banque", "Une école"],
                "correct": 0,
            },
            {
                "question": "Qu'est-ce qu'un contrat ?",
                "answers": [
                    "Un accord créant des obligations entre parties",
                    "Une carte bancaire",
                    "Un diplôme",
                    "Une monnaie",
                ],
                "correct": 0,
            },
            {
                "question": "Quel principe signifie qu'une personne est considérée innocente avant condamnation ?",
                "answers": [
                    "Présomption d'innocence",
                    "Secret bancaire",
                    "Propriété",
                    "Majorité",
                ],
                "correct": 0,
            },
            {
                "question": "Quel document peut constater une identité ?",
                "answers": [
                    "Carte d'identité",
                    "Ticket de caisse",
                    "Menu",
                    "Facture d'électricité uniquement",
                ],
                "correct": 0,
            },
            {
                "question": "Une personne peut-elle être soumise à des obligations prévues par un contrat qu'elle a valablement accepté ?",
                "answers": ["Oui", "Jamais", "Seulement le dimanche", "Uniquement à l'étranger"],
                "correct": 0,
            },
            {
                "question": "Quel domaine concerne principalement les relations entre citoyens et État ?",
                "answers": ["Droit public", "Cuisine", "Sport", "Astronomie"],
                "correct": 0,
            },
        ],

        "medicine": [
            {
                "question": "Quel organe est principalement associé à la circulation du sang ?",
                "answers": ["Cœur", "Estomac", "Oreille", "Peau"],
                "correct": 0,
            },
            {
                "question": "Quel organe permet principalement les échanges gazeux de la respiration ?",
                "answers": ["Poumons", "Reins", "Foie", "Pancréas"],
                "correct": 0,
            },
            {
                "question": "Quel élément du sang participe à la coagulation ?",
                "answers": ["Plaquettes", "Neurones", "Alvéoles", "Bile"],
                "correct": 0,
            },
            {
                "question": "Quelle pratique contribue à l'hygiène des mains ?",
                "answers": [
                    "Les laver régulièrement",
                    "Ne jamais les nettoyer",
                    "Les exposer à la poussière",
                    "Utiliser uniquement du parfum",
                ],
                "correct": 0,
            },
            {
                "question": "Quel organe filtre notamment le sang et produit l'urine ?",
                "answers": ["Rein", "Poumon", "Cœur", "Œil"],
                "correct": 0,
            },
            {
                "question": "Quelle substance est principalement transportée par les globules rouges ?",
                "answers": ["Oxygène", "Sable", "Bile", "Urine"],
                "correct": 0,
            },
            {
                "question": "Quelle discipline étudie le corps humain ?",
                "answers": ["Anatomie", "Astronomie", "Géologie uniquement", "Météorologie"],
                "correct": 0,
            },
        ],

        "arts": [
            {
                "question": "Quelle discipline utilise principalement les formes et les couleurs pour créer des œuvres visuelles ?",
                "answers": ["Peinture", "Comptabilité", "Chimie", "Droit"],
                "correct": 0,
            },
            {
                "question": "Qu'est-ce qu'une sculpture ?",
                "answers": [
                    "Une œuvre réalisée en travaillant une matière ou un volume",
                    "Un contrat",
                    "Une facture",
                    "Une loi",
                ],
                "correct": 0,
            },
            {
                "question": "Quel élément est fondamental en musique ?",
                "answers": ["Rythme", "Budget", "Tribunal", "Code fiscal"],
                "correct": 0,
            },
            {
                "question": "Quel art utilise principalement le corps en mouvement ?",
                "answers": ["Danse", "Architecture", "Comptabilité", "Chimie"],
                "correct": 0,
            },
            {
                "question": "Quel outil est couramment utilisé pour dessiner ?",
                "answers": ["Crayon", "Calculatrice", "Scanner médical", "Clé USB"],
                "correct": 0,
            },
            {
                "question": "Qu'est-ce qu'une œuvre artistique ?",
                "answers": [
                    "Une création destinée notamment à exprimer une idée ou une vision",
                    "Une dette",
                    "Une taxe",
                    "Une adresse IP",
                ],
                "correct": 0,
            },
            {
                "question": "Quel domaine étudie notamment les sons organisés musicalement ?",
                "answers": ["Musique", "Droit", "Médecine", "Finance"],
                "correct": 0,
            },
        ],

        "communication": [
            {
                "question": "Quel moyen permet de transmettre un message à distance ?",
                "answers": ["Téléphone", "Chaise", "Table", "Chaussure"],
                "correct": 0,
            },
            {
                "question": "Quel élément aide à identifier l'auteur d'un message ?",
                "answers": ["Signature", "Chaise", "Météo", "Prix"],
                "correct": 0,
            },
            {
                "question": "Qu'est-ce qu'une information ?",
                "answers": [
                    "Un élément communiqué pour informer",
                    "Une monnaie",
                    "Une maladie",
                    "Un bâtiment",
                ],
                "correct": 0,
            },
            {
                "question": "Quel média diffuse généralement des programmes audiovisuels ?",
                "answers": ["Télévision", "Calculatrice", "Banque", "Laboratoire"],
                "correct": 0,
            },
            {
                "question": "Quel réseau est principalement conçu pour relier des appareils et échanger des données ?",
                "answers": ["Réseau informatique", "Parking", "Bibliothèque", "Stade"],
                "correct": 0,
            },
            {
                "question": "Pourquoi vérifier une information avant de la partager ?",
                "answers": [
                    "Pour limiter la diffusion d'informations fausses",
                    "Pour augmenter automatiquement son prix",
                    "Pour supprimer Internet",
                    "Pour changer sa langue",
                ],
                "correct": 0,
            },
            {
                "question": "Quel élément structure généralement un article ?",
                "answers": ["Titre", "Mot de passe bancaire", "Carte SIM uniquement", "Clé de voiture"],
                "correct": 0,
            },
        ],

        "engineering": [
            {
                "question": "Quel domaine consiste notamment à concevoir des solutions techniques ?",
                "answers": ["Ingénierie", "Poésie", "Cuisine", "Danse"],
                "correct": 0,
            },
            {
                "question": "Quelle unité mesure une longueur ?",
                "answers": ["Mètre", "Newton", "Watt", "Joule"],
                "correct": 0,
            },
            {
                "question": "Quel matériau est un bon conducteur électrique ?",
                "answers": ["Cuivre", "Bois sec", "Caoutchouc", "Verre"],
                "correct": 0,
            },
            {
                "question": "Quel élément sert à transmettre une rotation dans une machine ?",
                "answers": ["Arbre mécanique", "Oreiller", "Livre", "Écran"],
                "correct": 0,
            },
            {
                "question": "Quel outil peut mesurer une longueur avec précision ?",
                "answers": ["Règle", "Microphone", "Boussole uniquement", "Haut-parleur"],
                "correct": 0,
            },
            {
                "question": "Que cherche notamment à faire une conception technique ?",
                "answers": [
                    "Répondre à un besoin avec une solution",
                    "Créer une dette",
                    "Changer une nationalité",
                    "Supprimer les mesures",
                ],
                "correct": 0,
            },
            {
                "question": "Quelle énergie est produite par un panneau photovoltaïque ?",
                "answers": [
                    "Électricité",
                    "Essence",
                    "Charbon",
                    "Bois",
                ],
                "correct": 0,
            },
        ],
    },

    # Les niveaux supérieurs disposent de banques distinctes.
    # Elles seront enrichies progressivement ; le moteur refuse
    # une session si le domaine ne possède pas assez de questions.
    "probatoire": {},
    "baccalaureat": {},
    "university": {},
}


EXAM_COOLDOWN_SECONDS = 24 * 60 * 60

# [MWL] /exam never requires school_xp to reach 100.
# /study is optional preparation. A successful exam itself changes class.


def _school_level_from_exam_type(exam_type: str) -> tuple[str, str, str | None]:
    mapping = {
        "primary": ("Collège", "3e", "BEPC"),
        "college": ("Lycée", "Première", "Probatoire"),
        "probatoire": ("Lycée", "Terminale", "Baccalauréat"),
        "baccalaureat": ("Études supérieures", "Université", None),
        "university": ("Études supérieures", "Université", None),
    }
    return mapping[exam_type]


async def _can_start_exam(character_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT school_last_exam_at FROM life_characters WHERE id=:id"), {"id": character_id})
        row = result.mappings().first()
        last = row["school_last_exam_at"] if row else None
    if last is None:
        return True, 0
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    remaining = EXAM_COOLDOWN_SECONDS - int((datetime.now(timezone.utc) - last).total_seconds())
    return remaining <= 0, max(0, remaining)


# ============================================================
# SESSION
# ============================================================

def get_exam_type(character) -> str:
    education = str(character.get("education_level") or "").lower()
    diploma = str(character.get("diploma_level") or "").lower()

    if "univers" in education or "supérieur" in education:
        return "university"

    if "terminal" in education:
        return "baccalaureat"

    if "lycée" in education or "lycee" in education:
        return "probatoire"

    if "collège" in education or "college" in education:
        return "college"

    return "primary"


def get_domain(character) -> str:
    value = (
        character.get("education_domain")
        or character.get("domain")
        or character.get("school_domain")
        or ""
    )

    value = str(value).strip().lower()

    if value in DOMAIN_NAMES:
        return value

    return "general"


def build_exam_questions(
    exam_type: str,
    domain: str,
) -> list[dict[str, Any]]:

    config = EXAMS[exam_type]

    if exam_type == "primary":
        pool = QUESTIONS["primary"]["general"]
    else:
        pool = QUESTIONS.get(exam_type, {}).get(domain, [])

    if len(pool) < config["count"]:
        raise ValueError(
            f"Banque insuffisante pour {exam_type}/{domain}: "
            f"{len(pool)}/{config['count']}"
        )

    return random.sample(pool, config["count"])


# ============================================================
# DÉBUT D'EXAMEN
# ============================================================

async def domain_exam_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    character = await get_life_character(
        update.effective_user.id
    )

    if character is None:
        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    exam_type = get_exam_type(character)
    domain = get_domain(character)

    allowed, remaining = await _can_start_exam(int(character["id"]))
    if not allowed:
        await message.reply_text(
            "⏳ **EXAMEN INDISPONIBLE**\n\n"
            f"Tu dois attendre **{remaining // 3600}h {(remaining % 3600) // 60:02d}min** avant de repasser un examen.",
            parse_mode="Markdown",
        )
        return

    if exam_type != "primary" and domain == "general":
        await message.reply_text(
            "❌ Tu dois d'abord choisir ton domaine avec "
            "`/schoolenroll`.",
            parse_mode="Markdown",
        )
        return

    try:
        questions = build_exam_questions(
            exam_type,
            domain,
        )
    except ValueError:
        await message.reply_text(
            "⚠️ La banque de questions de ce domaine et de ce "
            "niveau n'est pas encore suffisamment remplie.\n\n"
            "L'examen ne peut pas être lancé tant que les "
            "questions requises ne sont pas disponibles."
        )
        return

    sessions = context.user_data.setdefault(
        "domain_exam_sessions",
        {},
    )

    character_id = character["id"]

    if str(character_id) in sessions:
        await message.reply_text(
            "⏳ Tu as déjà un examen en cours."
        )
        return

    session_id = uuid.uuid4().hex[:12]

    sessions[str(character_id)] = {
        "session_id": session_id,
        "exam_type": exam_type,
        "domain": domain,
        "questions": questions,
        "current": 0,
        "correct": 0,
    }

    config = EXAMS[exam_type]

    await message.reply_text(
        "🎓 **EXAMEN MANUWORLD**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📜 Diplôme : **{config['name']}**\n"
        f"🎯 Difficulté : **{config['difficulty']}**\n"
        f"📚 Domaine : **{DOMAIN_NAMES.get(domain, 'Général')}**\n\n"
        f"📝 Questions : **{config['count']}**\n"
        f"✅ Réussite : **{config['required']}/{config['count']}**",
        parse_mode="Markdown",
    )

    await send_question(
        message,
        sessions[str(character_id)],
        character_id,
    )


# ============================================================
# QUESTION
# ============================================================

async def send_question(
    message,
    session: dict,
    character_id: int,
):
    index = session["current"]
    questions = session["questions"]

    if index >= len(questions):
        return

    question = questions[index]

    buttons = [
        [
            InlineKeyboardButton(
                answer,
                callback_data=(
                    f"dexam:{character_id}:{index}:{answer_index}"
                ),
            )
        ]
        for answer_index, answer
        in enumerate(question["answers"])
    ]

    await message.reply_text(
        f"📝 **Question {index + 1}/{len(questions)}**\n\n"
        f"❓ {question['question']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ============================================================
# RÉPONSE
# ============================================================

async def domain_exam_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        _, character_id_text, index_text, answer_text = (
            query.data.split(":")
        )

        character_id = int(character_id_text)
        index = int(index_text)
        answer_index = int(answer_text)

    except (ValueError, AttributeError):
        await query.edit_message_text(
            "❌ Réponse invalide."
        )
        return

    character = await get_life_character(
        update.effective_user.id
    )

    if character is None or character["id"] != character_id:
        await query.answer(
            "❌ Cet examen ne t'appartient pas.",
            show_alert=True,
        )
        return

    sessions = context.user_data.get(
        "domain_exam_sessions",
        {},
    )

    session = sessions.get(str(character_id))

    if not session:
        await query.edit_message_text(
            "❌ Cette session d'examen est terminée."
        )
        return

    if index != session["current"]:
        await query.answer(
            "⚠️ Cette question a déjà été traitée.",
            show_alert=True,
        )
        return

    question = session["questions"][index]

    if answer_index < 0 or answer_index >= len(question["answers"]):
        await query.answer(
            "Réponse invalide.",
            show_alert=True,
        )
        return

    if answer_index == question["correct"]:
        session["correct"] += 1
        result = "✅ Bonne réponse !"
    else:
        result = "❌ Mauvaise réponse."

    session["current"] += 1

    await query.edit_message_text(
        result
    )

    if session["current"] >= len(session["questions"]):
        await finish_exam(
            query.message,
            context,
            character_id,
        )
        return

    await send_question(
        query.message,
        session,
        character_id,
    )


# ============================================================
# FIN
# ============================================================

async def finish_exam(
    message,
    context: ContextTypes.DEFAULT_TYPE,
    character_id: int,
):
    sessions = context.user_data.get(
        "domain_exam_sessions",
        {},
    )

    session = sessions.pop(
        str(character_id),
        None,
    )

    if not session:
        return

    exam_type = session["exam_type"]
    config = EXAMS[exam_type]

    total = len(session["questions"])
    correct = session["correct"]
    required = config["required"]

    passed = correct >= required

    await message.reply_text(
        "🎓 **RÉSULTAT DE L'EXAMEN**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📜 {config['name']}\n"
        f"📚 Domaine : **"
        f"{DOMAIN_NAMES.get(session['domain'], 'Général')}**\n\n"
        f"✅ Bonnes réponses : **{correct}/{total}**\n"
        f"🎯 Minimum requis : **{required}/{total}**\n\n"
        + (
            "🏆 **EXAMEN RÉUSSI !**"
            if passed
            else "❌ **EXAMEN ÉCHOUÉ**"
        ),
        parse_mode="Markdown",
    )

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        await db.execute(
            text(
                """
                UPDATE life_characters
                SET school_last_exam_at=:now,
                    updated_at=NOW()
                WHERE id=:character_id
                """
            ),
            {"now": now, "character_id": character_id},
        )

        if passed:
            next_level, next_class, next_diploma = _school_level_from_exam_type(exam_type)

            if exam_type == "primary":
                current_level = "Collège"
            elif exam_type == "college":
                current_level = "Lycée"
            elif exam_type == "probatoire":
                current_level = "Lycée"
            elif exam_type == "baccalaureat":
                current_level = "Études supérieures"
            else:
                current_level = "Études supérieures"

            await db.execute(
                text(
                    """
                    UPDATE life_characters
                    SET education_level=CAST(:education_level AS VARCHAR(80)),
                        school_class=CAST(:school_class AS VARCHAR(80)),
                        current_diploma=CAST(:current_diploma AS VARCHAR(100)),
                        diploma_level=CAST(:current_diploma AS VARCHAR(100)),
                        school_xp=0,
                        school_xp_required=CASE
                            WHEN CAST(:education_level AS TEXT) ILIKE '%collège%' THEN 150
                            WHEN CAST(:education_level AS TEXT) ILIKE '%lycée%'
                                 AND CAST(:school_class AS TEXT)='Première' THEN 200
                            WHEN CAST(:education_level AS TEXT) ILIKE '%lycée%'
                                 AND CAST(:school_class AS TEXT)='Terminale' THEN 250
                            WHEN CAST(:education_level AS TEXT) ILIKE '%univers%' THEN 500
                            ELSE 100
                        END,
                        updated_at=NOW()
                    WHERE id=:character_id
                    """
                ),
                {
                    "education_level": next_level,
                    "school_class": next_class,
                    "current_diploma": next_diploma,
                    "character_id": character_id,
                },
            )

        await db.execute(
            text(
                """
                INSERT INTO life_transactions (
                    character_id,
                    type,
                    amount,
                    currency,
                    description
                )
                VALUES (
                    :character_id,
                    'education_exam',
                    0,
                    'coins',
                    :description
                )
                """
            ),
            {
                "character_id": character_id,
                "description": (
                    f"Examen {config['name']} - "
                    f"{correct}/{total} - "
                    f"{'réussi' if passed else 'échoué'}"
                ),
            },
        )

        if passed:
            # Synchronise l'historique scolaire avec les champs
            # canoniques de life_characters. /school ne restera plus
            # bloqué sur l'ancienne classe.
            await db.execute(
                text("""
                    UPDATE life_school_years
                    SET result='passed'
                    WHERE character_id=:character_id
                      AND result='in_progress'
                """),
                {"character_id": character_id},
            )
            await db.execute(
                text("""
                    INSERT INTO life_school_years (
                        character_id, class_name, academic_year, average, result
                    )
                    VALUES (
                        :character_id, CAST(:school_class AS VARCHAR(80)),
                        EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER,
                        0, 'in_progress'
                    )
                """),
                {"character_id": character_id, "school_class": next_class},
            )

        await db.commit()


# ============================================================
# REGISTRATION
# ============================================================

def register_domain_exam_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "exam",
            domain_exam_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            domain_exam_callback,
            pattern=r"^dexam:\d+:\d+:\d+$",
        )
    )
