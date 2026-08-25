import random
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select, update

from database.database import AsyncSessionLocal
from database.models import User

# Liste d'équipes internationales
equipes = [
    "Paris SG", "Marseille", "Lyon", "Monaco", "Bordeaux", "Nantes", "Nice", "Lille",
    "Real Madrid", "FC Barcelona", "Atletico Madrid", "Sevilla", "Valencia",
    "Manchester United", "Liverpool", "Chelsea", "Arsenal", "Manchester City",
    "Juventus", "AC Milan", "Inter Milan", "AS Roma", "Napoli",
    "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen", "Schalke 04",
    "Benfica", "Porto", "Sporting CP",
    "Ajax", "PSV Eindhoven", "Feyenoord",
    "Boca Juniors", "River Plate", "Racing Club",
    "Flamengo", "Palmeiras", "Santos",
    "Zenit Saint Petersburg", "CSKA Moscow", "Spartak Moscow",
    "Galatasaray", "Fenerbahce", "Besiktas",
    "Club Brugge", "Anderlecht", "Standard Liège",
    "FC Basel", "Young Boys", "FC Zurich",
    "Celtic", "Rangers",
]

def _format_amount(value: int) -> str:
    return f"{int(value or 0):,}"

def _random_result():
    results = ["victoire", "nul", "defaite"]
    weights = [0.4, 0.3, 0.3]
    return random.choices(results, weights)[0]

def _generate_match():
    team1, team2 = random.sample(equipes, 2)
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

    matches = [_generate_match() for _ in range(3)]

    if len(context.args) == 0:
        text = "Matchs disponibles pour parier :\n\n"
        for i, match in enumerate(matches, 1):
            text += f"{i}. {match['teams']}\n"
            text += f"   Victoire: x{match['odds']['victoire']}\n"
            text += f"   Nul: x{match['odds']['nul']}\n"
            text += f"   Défaite: x{match['odds']['defaite']}\n\n"
        text += "Utilise la commande : /pari <numéro_match> <victoire|nul|defaite> <mise>"

        await message.reply_text(text)
        context.user_data["matches"] = matches
        return

    matches = context.user_data.get("matches")
    if matches is None:
        await message.reply_text("Tes matchs ont expiré. Envoie /pari pour voir les nouveaux matchs.")
        return

    if len(context.args) != 3:
        await message.reply_text("Usage : /pari <numéro_match> <victoire|nul|defaite> <mise>")
        return

    try:
        num_match = int(context.args[0])
        if num_match < 1 or num_match > len(matches):
            raise ValueError
    except ValueError:
        await message.reply_text("Le numéro du match est invalide.")
        return

    choix = context.args[1].lower()
    if choix not in ["victoire", "nul", "defaite"]:
        await message.reply_text("Choix invalide. Utilise victoire, nul ou defaite.")
        return

    try:
        mise = int(context.args[2])
        if mise <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("La mise doit être un nombre entier positif.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one_or_none()

        if db_user is None:
            await message.reply_text("Ton compte n'a pas été trouvé. Utilise /start.")
            return

        if db_user.coins < mise:
            await message.reply_text("Tu n'as pas assez de coins pour miser cette somme.")
            return

        new_coins = db_user.coins - mise

        resultat_reel = _random_result()

        cote = matches[num_match - 1]["odds"][choix]
        gain = 0
        gagne = False

        if resultat_reel == choix:
            gain = int(mise * cote)
            new_coins += gain
            gagne = True

        await session.execute(update(User).where(User.id == user.id).values(coins=new_coins))
        await session.commit()

        reponse = (
            f"Match : {matches[num_match -1]['teams']}\n"
            f"Résultat réel : {resultat_reel.capitalize()}\n"
            f"Tu as parié sur : {choix}\n"
            f"Mise : {mise} coins\n\n"
        )

        if gagne:
            reponse += f"Félicitations ! Tu as gagné {gain} coins.\n"
        else:
            reponse += "Désolé, tu as perdu ta mise.\n"

        reponse += f"Solde actuel : {_format_amount(new_coins)} coins."

        await message.reply_text(reponse)
        
pari_handler = CommandHandler("pari", pari)
