import random
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select, update

from database.database import AsyncSessionLocal
from database.models import User

# Liste d'équipes possibles
equipes = [
    "Paris SG", "Marseille", "Real Madrid", "FC Barcelone", "Manchester city", "Arsenal",
    "liverpool", "Bayern munich", "Borussia dortmund", "Ac milan", "Inter Milan",
    "Brentford", "Newcastle", "Tottenham Hostpur", "Chelsea", "Atlético Madrid",
    "Lens", "Monaco",
]

def _format_amount(value: int) -> str:
    return f"{int(value or 0):,}"

def _random_result():
    results = ["victoire", "nul", "defaite"]
    weights = [0.4, 0.3, 0.3]
    return random.choices(results, weights)[0]

def _generate_match():
    # Choisit 2 équipes différentes au hasard
    team1, team2 = random.sample(equipes, 2)
    # Génère des cotes raisonnables pour chaque issue
    odds = {
        "victoire": round(random.uniform(1.5, 3.0), 2),
        "nul": round(random.uniform(2.5, 4.0), 2),
        "defaite": round(random.uniform(1.5, 3.0), 2),
    }
    return {
        "teams": f"{team1} vs {team2}",
        "odds": odds
    }

async def pari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    # Génère 3 matchs aléatoires à chaque appel
    matches = [_generate_match() for _ in range(3)]

    # Affichage des matchs si pas d'arguments
    if len(context.args) == 0:
        text = "🎲 *Matchs disponibles pour parier :*\n\n"
        for i, match in enumerate(matches, 1):
            text += f"{i}. {match['teams']}\n"
            text += f"   Victoire: x{match['odds']['victoire']}\n"
            text += f"   Nul: x{match['odds']['nul']}\n"
            text += f"   Défaite: x{match['odds']['defaite']}\n\n"
        text += "Utilise la commande : /pari <numéro_match> <victoire|nul|defaite> <mise>"
        await message.reply_text(text, parse_mode="Markdown")
        # Stocker les matchs pour cet utilisateur (optionnel, voir note ci-dessous)
        context.user_data["matches"] = matches
        return

    # Vérifier qu'à chaque pari on utilise les matchs affichés précédemment
    # On récupère les matchs sauvegardés (sinon on génère à nouveau)
    matches = context.user_data.get("matches")
    if matches is None:
        await message.reply_text("❌ Tes matchs ont expiré. Envoie /pari pour voir les nouveaux matchs.")
        return

    if len(context.args) != 3:
        await message.reply_text("❌ Usage : /pari <numéro_match> <victoire|nul|defaite> <mise>")
        return

    try:
        num_match = int(context.args[0])
        if num_match < 1 or num_match > len(matches):
            raise ValueError
    except ValueError:
        await message.reply_text("❌ Le numéro du match est invalide.")
        return

    choix = context.args[1].lower()
    if choix not in ["victoire", "nul", "defaite"]:
        await message.reply_text("❌ Choix invalide. Utilise victoire, nul ou defaite.")
        return

    try:
        mise = int(context.args[2])
        if mise <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("❌ La mise doit être un nombre entier positif.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one_or_none()

        if db_user is None:
            await message.reply_text("❌ Ton compte n'a pas été trouvé. Utilise /start.")
            return

        if db_user.coins < mise:
            await message.reply_text("❌ Tu n'as pas assez de coins pour miser cette somme.")
            return

        # Déduit la mise de la balance
        new_coins = db_user.coins - mise

        # Résultat simulé aléatoire
        resultat_reel = _random_result()

        cote = matches[num_match - 1]["odds"][choix]
        gain = 0
        gagne = False

        if resultat_reel == choix:
            gain = int(mise * cote)
            new_coins += gain
            gagne = True

        # Met à jour la base de données
        await session.execute(update(User).where(User.id == user.id).values(coins=new_coins))
        await session.commit()

        reponse = f"Match : {matches[num_match -1]['teams']}\n"
        reponse += f"Résultat réel : {resultat_reel.capitalize()}\n"
        reponse += f"Tu as parié sur : {choix}\n"
        reponse += f"Mise : {mise} coins\n\n"

        if gagne:
            reponse += f"🎉 Félicitations ! Tu as gagné {gain} coins.\n"
        else:
            reponse += "❌ Désolé, tu as perdu ta mise.\n"

        reponse += f"Solde actuel : {_format_amount(new_coins)} coins."

        await message.reply_text(reponse)

pari_handler = CommandHandler("pari", pari)
