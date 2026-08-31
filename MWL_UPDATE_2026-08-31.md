# MANUWORLD update — 2026-08-31

## Objectif
Version reconstruite à partir du ZIP `life_world(4).zip` et du `main.py` fourni.

## Corrections
- Entreprises : migration non destructive pour les colonnes manquantes (`company_type`, `description`, `status`, `grade`).
- Création d'entreprise : capital enregistré dans `capital` et `treasury`; membre Owner compatible avec le schéma réel.
- Recrutement : remplit `position` et `grade`, évitant l'erreur NOT NULL.
- École : `/school` se resynchronise avec les champs du personnage; un examen réussi change réellement de classe même si l'XP scolaire n'est pas à 100.
- Examen : correction du problème PostgreSQL `AmbiguousParameterError` par des casts explicites.
- Ciblage : une réponse à un message utilise directement le Telegram ID de l'auteur; un `@username` sert uniquement à retrouver le personnage, puis toutes les opérations utilisent le Telegram ID.
- `/paylife` accepte désormais `/paylife 500` en réponse à un message ou `/paylife @username 500`.
- Carte bancaire : depuis le détail d'une banque, le joueur peut demander la carte proposée par cette banque. Le système bancaire central (`bank_system.py`) n'a pas été réécrit.
- Marché permanent : initialisation automatique du catalogue de produits de marque au démarrage, sans remettre le stock à zéro.
- Hôpital et politique : modules branchés au démarrage.
- Menu Telegram : maintenu à 100 commandes.

## Fichiers ajoutés
- `life_world/systems/hospital_system.py`
- `life_world/handlers/hospital.py`
- `life_world/systems/politics_system.py`
- `life_world/handlers/politics.py`

## Fichiers principaux modifiés
- `main.py`
- `life_world/database.py`
- `life_world/systems/business_system.py`
- `life_world/handlers/business.py` (conservé et compatible avec le nouveau schéma)
- `life_world/handlers/education.py`
- `life_world/handlers/domain_exams.py`
- `life_world/handlers/economy.py`
- `life_world/utils/targeting.py`
- `life_world/handlers/bank.py` (uniquement l'ajout de la demande de carte depuis le menu banque)

## Validation
Tous les fichiers Python du pack passent une analyse de syntaxe Python.
