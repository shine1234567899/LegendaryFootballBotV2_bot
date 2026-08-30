"""
MANUWORLD — domain_question_bank.py

Banque de questions scolaires.

Règles :
- CEP          : 5 faciles, réussite 4/5
- BEPC         : 7 moyennes, réussite 5/7
- Probatoire   : 10 difficiles, réussite 8/10
- BACC         : 12 difficiles, réussite 10/12
- Université   : 15 expertes, réussite 15/15

À partir du collège, chaque examen dépend du domaine choisi.
Chaque niveau possède sa propre banque : aucune question d'un
niveau inférieur n'est automatiquement réutilisée.
"""

from __future__ import annotations

import random


EXAM_RULES = {
    "cep": {
        "name": "CEP",
        "count": 5,
        "required": 4,
        "difficulty": "Facile",
    },
    "bepc": {
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
    "bacc": {
        "name": "Baccalauréat",
        "count": 12,
        "required": 10,
        "difficulty": "Difficile",
    },
    "university": {
        "name": "Université",
        "count": 15,
        "required": 15,
        "difficulty": "Expert",
    },
}


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


def q(question, answers, correct):
    return {
        "question": question,
        "answers": answers,
        "correct": correct,
    }


# ============================================================
# CEP
# ============================================================

CEP_QUESTIONS = [
    q("Combien font 7 + 8 ?", ["13", "14", "15", "16"], 2),
    q("Combien de jours compte une semaine ?", ["5", "6", "7", "8"], 2),
    q("Quelle est la capitale du Cameroun ?", ["Douala", "Yaoundé", "Garoua", "Bafoussam"], 1),
    q("Quel est le pluriel de « cheval » ?", ["Chevals", "Chevaux", "Chevaus", "Chevales"], 1),
    q("Combien font 5 × 6 ?", ["25", "30", "35", "40"], 1),
    q("Combien de mois compte une année ?", ["10", "11", "12", "13"], 2),
    q("Quel animal est un mammifère ?", ["Chien", "Poulet", "Poisson", "Lézard"], 0),
    q("Combien font 20 - 7 ?", ["11", "12", "13", "14"], 2),
]


# ============================================================
# BEPC
# ============================================================

BEPC = {
    "science": [
        q("Quelle unité mesure une force ?", ["Joule", "Newton", "Watt", "Pascal"], 1),
        q("Quel organe pompe le sang ?", ["Foie", "Cœur", "Rein", "Poumon"], 1),
        q("Quelle planète est appelée planète rouge ?", ["Mars", "Vénus", "Jupiter", "Mercure"], 0),
        q("Quel gaz est nécessaire à la respiration ?", ["Azote", "Oxygène", "Hélium", "Hydrogène"], 1),
        q("Combien de côtés possède un hexagone ?", ["5", "6", "7", "8"], 1),
        q("Quel état possède une forme propre ?", ["Solide", "Liquide", "Gaz", "Plasma"], 0),
        q("Quel organe produit principalement l'urine ?", ["Cœur", "Rein", "Estomac", "Poumon"], 1),
    ],
    "technology": [
        q("Quel composant exécute principalement les instructions ?", ["CPU", "Écran", "Clavier", "Souris"], 0),
        q("Quel périphérique sert à saisir du texte ?", ["Clavier", "Écran", "Imprimante", "Haut-parleur"], 0),
        q("Que signifie USB ?", ["Universal Serial Bus", "United System Board", "User Storage Base", "Universal Software Box"], 0),
        q("Quel système est un système d'exploitation ?", ["Linux", "Python", "HTML", "Bluetooth"], 0),
        q("Quel stockage conserve les données sans alimentation ?", ["SSD", "RAM", "Cache", "Registre"], 0),
        q("Quelle unité mesure la capacité de stockage ?", ["Octet", "Volt", "Newton", "Ampère"], 0),
        q("Quel appareil relie généralement un réseau local à Internet ?", ["Routeur", "Clavier", "Microphone", "Scanner"], 0),
    ],
    "economics": [
        q("Qu'est-ce qu'un budget ?", ["Prévision de recettes et dépenses", "Un diplôme", "Une maladie", "Un sport"], 0),
        q("Que signifie épargner ?", ["Mettre de l'argent de côté", "Tout dépenser", "Emprunter", "Créer une dette"], 0),
        q("Qu'est-ce qu'un salaire ?", ["Rémunération du travail", "Une taxe", "Une amende", "Un prêt"], 0),
        q("Une entreprise produit généralement :", ["Des biens ou services", "Des diplômes uniquement", "Des lois uniquement", "Des monnaies"], 0),
        q("Qu'est-ce qu'un prix ?", ["Valeur monétaire demandée", "Un salaire", "Une dette", "Un diplôme"], 0),
        q("Une banque peut notamment :", ["Gérer des dépôts", "Fabriquer des voitures", "Décerner le BAC", "Construire des routes"], 0),
        q("Un bénéfice apparaît quand :", ["Les recettes dépassent les coûts", "Les coûts dépassent les recettes", "Il n'y a aucune vente", "L'entreprise ferme"], 0),
    ],
    "law": [
        q("Une loi établit principalement :", ["Des règles de droit", "Des prix", "Des salaires", "Des recettes"], 0),
        q("Un contrat est :", ["Un accord créant des obligations", "Une maladie", "Un diplôme", "Une monnaie"], 0),
        q("Un tribunal rend :", ["Des décisions de justice", "Des salaires", "Des factures", "Des diplômes"], 0),
        q("La présomption d'innocence signifie :", ["Être considéré innocent avant condamnation", "Être toujours coupable", "Ne jamais être jugé", "Être automatiquement condamné"], 0),
        q("Une carte d'identité sert notamment à :", ["Justifier son identité", "Payer une dette", "Passer le BAC", "Créer une entreprise"], 0),
        q("Le droit organise notamment :", ["Les relations sociales", "La météo", "La cuisine", "La musique"], 0),
        q("Une obligation juridique peut résulter :", ["D'un contrat ou de la loi", "D'une couleur", "D'un sport", "D'une chanson"], 0),
    ],
    "medicine": [
        q("Quel organe pompe le sang ?", ["Cœur", "Foie", "Rein", "Poumon"], 0),
        q("Quel organe permet les échanges gazeux ?", ["Poumons", "Reins", "Foie", "Estomac"], 0),
        q("Quel organe filtre le sang et produit l'urine ?", ["Rein", "Cœur", "Œil", "Peau"], 0),
        q("Les globules rouges transportent notamment :", ["Oxygène", "Bile", "Urine", "Salive"], 0),
        q("Les plaquettes participent :", ["À la coagulation", "À la digestion", "À la vision", "À l'audition"], 0),
        q("L'hygiène des mains aide à :", ["Réduire la transmission de microbes", "Augmenter la fièvre", "Changer le groupe sanguin", "Créer des os"], 0),
        q("Le cerveau appartient au système :", ["Nerveux", "Digestif", "Respiratoire", "Squelettique"], 0),
    ],
    "arts": [
        q("Quel art utilise principalement les couleurs sur une surface ?", ["Peinture", "Droit", "Comptabilité", "Chimie"], 0),
        q("La sculpture travaille principalement :", ["Le volume et la matière", "Les contrats", "Les réseaux", "Les budgets"], 0),
        q("La danse utilise principalement :", ["Le mouvement du corps", "Les équations", "Les lois", "Les médicaments"], 0),
        q("La musique organise notamment :", ["Les sons", "Les impôts", "Les contrats", "Les cellules"], 0),
        q("Quel outil est courant pour dessiner ?", ["Crayon", "Routeur", "Stéthoscope", "Calculatrice"], 0),
        q("Une photographie est une création :", ["Visuelle", "Juridique", "Médicale", "Comptable"], 0),
        q("Une scène de théâtre sert notamment à :", ["Représenter une œuvre dramatique", "Calculer une taxe", "Soigner", "Programmer"], 0),
    ],
    "communication": [
        q("Un message sert principalement à :", ["Transmettre une information", "Calculer un impôt", "Soigner", "Construire"], 0),
        q("Un titre résume généralement :", ["Le sujet d'un contenu", "Le salaire", "La température", "Le mot de passe"], 0),
        q("Vérifier une information permet de :", ["Limiter les fausses informations", "Augmenter une dette", "Changer une identité", "Supprimer Internet"], 0),
        q("Quel média diffuse des programmes audiovisuels ?", ["Télévision", "Banque", "Laboratoire", "École"], 0),
        q("Une interview consiste notamment à :", ["Poser des questions à une personne", "Créer une facture", "Mesurer un objet", "Programmer un robot"], 0),
        q("Une source est utile pour :", ["Identifier l'origine d'une information", "Augmenter le prix", "Changer une note", "Créer une maladie"], 0),
        q("La communication non verbale utilise notamment :", ["Gestes et expressions", "Uniquement des chiffres", "Des contrats", "Des factures"], 0),
    ],
    "engineering": [
        q("L'ingénierie vise notamment à :", ["Concevoir des solutions techniques", "Rédiger des lois", "Peindre", "Soigner"], 0),
        q("Quelle unité mesure une longueur ?", ["Mètre", "Newton", "Watt", "Joule"], 0),
        q("Le cuivre est connu pour être :", ["Conducteur électrique", "Isolant parfait", "Gaz", "Liquide"], 0),
        q("Un engrenage transmet notamment :", ["Un mouvement de rotation", "Une maladie", "Une information juridique", "Une note"], 0),
        q("Une règle mesure :", ["Une longueur", "Une température", "Une masse", "Une tension"], 0),
        q("Un moteur transforme notamment :", ["Une énergie en mouvement", "Une loi en salaire", "Une note en diplôme", "Une facture en argent"], 0),
        q("Un capteur sert à :", ["Mesurer ou détecter une grandeur", "Peindre", "Payer", "Juger"], 0),
    ],
}


# ============================================================
# NIVEAUX SUPÉRIEURS — SCIENCE
# ============================================================

ADVANCED = {
    "science": {
        "probatoire": [
            q("Selon la deuxième loi de Newton, la résultante des forces vaut :", ["mv", "ma", "m/a", "a/m"], 1),
            q("Quel organite produit principalement l'ATP ?", ["Ribosome", "Mitochondrie", "Noyau", "Lysosome"], 1),
            q("Une solution de pH 3 est :", ["Basique", "Neutre", "Acide", "Saturée"], 2),
            q("Quelle grandeur se mesure en ohms ?", ["Tension", "Résistance", "Puissance", "Charge"], 1),
            q("Lors d'une mitose, combien de cellules filles sont normalement produites ?", ["1", "2", "3", "4"], 1),
            q("Quel phénomène explique la déviation de la lumière entre deux milieux ?", ["Réfraction", "Fusion", "Conduction", "Évaporation"], 0),
            q("Quelle liaison résulte du partage d'électrons ?", ["Ionique", "Covalente", "Métallique", "Nucléaire"], 1),
            q("Quel est le rôle principal de l'ADN ?", ["Stocker l'information génétique", "Produire directement l'ATP", "Digérer les protéines", "Transporter l'oxygène"], 0),
            q("Dans un circuit série, le courant est :", ["Différent partout", "Le même partout", "Toujours nul", "Toujours alternatif"], 1),
            q("Quel mécanisme produit des gamètes à nombre chromosomique réduit ?", ["Mitose", "Méiose", "Diffusion", "Osmose"], 1),
        ],
        "bacc": [
            q("L'énergie cinétique d'un corps est :", ["mv", "1/2 mv²", "ma", "mgh²"], 1),
            q("À température constante, si le volume d'un gaz idéal diminue, sa pression :", ["Diminue", "Augmente", "Reste nulle", "Disparaît"], 1),
            q("Quelle structure contrôle les échanges entre cellule et milieu ?", ["Membrane plasmique", "Ribosome", "Nucléole", "Centrosome"], 0),
            q("Une lentille convergente possède généralement :", ["Un effet divergent", "Un foyer réel", "Aucun foyer", "Uniquement un foyer virtuel"], 1),
            q("Le pH est lié à :", ["La concentration en ions H+", "La masse uniquement", "La température uniquement", "La densité"], 0),
            q("Quel processus produit notamment du CO2 dans la respiration cellulaire ?", ["Cycle de Krebs", "Traduction", "Réplication", "Transcription"], 0),
            q("Une quantité conservée dans une réaction chimique est :", ["La charge totale", "La couleur", "Le volume du récipient", "La température"], 0),
            q("La fréquence d'une onde est l'inverse de :", ["La longueur", "La période", "L'amplitude", "La vitesse"], 1),
            q("Une réaction qui absorbe de la chaleur est :", ["Exothermique", "Endothermique", "Isotherme", "Catalytique"], 1),
            q("Quelle enzyme copie l'ADN lors de sa réplication ?", ["ADN polymérase", "Amylase", "Lipase", "Pepsine"], 0),
            q("Une oxydation correspond à :", ["Un gain d'électrons", "Une perte d'électrons", "Un gain de neutrons", "Une perte de protons"], 1),
            q("Quel pigment intervient principalement dans la photosynthèse ?", ["Hémoglobine", "Chlorophylle", "Mélanine", "Kératine"], 1),
        ],
        "university": [
            q("Dans Michaelis-Menten, Km correspond à la concentration pour laquelle la vitesse vaut :", ["Vmax", "Vmax/2", "2Vmax", "0"], 1),
            q("Le deuxième principe de la thermodynamique introduit notamment :", ["L'entropie", "La masse atomique", "La charge élémentaire", "Le pH"], 0),
            q("En mécanique quantique, une observable est représentée par :", ["Un opérateur", "Une constante uniquement", "Une matrice identité toujours", "Un scalaire imposé"], 0),
            q("La constante d'équilibre d'une réaction dépend principalement de :", ["La température", "La couleur", "La pression atmosphérique seulement", "La masse du récipient"], 0),
            q("Quelle structure cellulaire assure la traduction des ARNm ?", ["Ribosome", "Lysosome", "Peroxysome", "Centrioles"], 0),
            q("La PCR nécessite notamment :", ["Une ADN polymérase thermostable", "Une lipase", "Une hémoglobine", "Une amylase"], 0),
            q("La loi de Faraday concerne :", ["L'induction électromagnétique", "La gravitation", "La radioactivité alpha", "La conduction thermique"], 0),
            q("Une matrice hessienne contient :", ["Les dérivées secondes", "Les seules valeurs propres", "Les intégrales triples", "Les probabilités"], 0),
            q("Hardy-Weinberg suppose notamment :", ["Absence de sélection dans une population idéale", "Sélection maximale", "Mutation obligatoire", "Migration constante"], 0),
            q("La vitesse de réaction dépend notamment de :", ["La concentration et la température", "La couleur", "La forme du récipient", "Le nom du réactif"], 0),
            q("Le potentiel chimique est lié à :", ["L'énergie libre molaire partielle", "La masse uniquement", "La pression sonore", "La vitesse de la lumière"], 0),
            q("La spectroscopie RMN exploite principalement :", ["Les propriétés des noyaux dans un champ magnétique", "La gravité", "La pression acoustique", "La fluorescence uniquement"], 0),
            q("Un champ conservatif possède un travail indépendant :", ["Du chemin suivi", "De la masse", "Du temps uniquement", "De la température"], 0),
            q("En cinétique, une réaction d'ordre 1 possède une constante d'unité :", ["s⁻¹", "mol/L", "L/mol", "N"], 0),
            q("L'équation de Schrödinger décrit principalement :", ["L'évolution de l'état quantique", "La croissance bactérienne", "La pression atmosphérique", "Le bilan comptable"], 0),
        ],
    },
}


def get_questions(level: str, domain: str = "general") -> list[dict]:
    """
    Retourne la banque exacte du niveau et du domaine.

    Le moteur ne complète jamais une banque avec des questions
    provenant d'un autre niveau.
    """

    if level == "cep":
        return list(CEP_QUESTIONS)

    if level == "bepc":
        return list(BEPC.get(domain, []))

    return list(
        ADVANCED
        .get(domain, {})
        .get(level, [])
    )


def validate_bank(level: str, domain: str) -> tuple[bool, str]:
    if level not in EXAM_RULES:
        return False, "Niveau inconnu."

    expected = EXAM_RULES[level]["count"]
    available = len(get_questions(level, domain))

    if available < expected:
        return (
            False,
            f"Banque incomplète : {available}/{expected} questions.",
        )

    return True, "OK"


def create_exam(level: str, domain: str = "general") -> list[dict]:
    """
    Sélectionne les questions sans répétition pour une session.
    """

    valid, error = validate_bank(level, domain)

    if not valid:
        raise ValueError(error)

    count = EXAM_RULES[level]["count"]

    return random.sample(
        get_questions(level, domain),
        count,
    )


def exam_passed(level: str, correct_answers: int) -> bool:
    return correct_answers >= EXAM_RULES[level]["required"]


def exam_result(level: str, correct_answers: int) -> dict:
    config = EXAM_RULES[level]

    return {
        "name": config["name"],
        "difficulty": config["difficulty"],
        "correct": correct_answers,
        "total": config["count"],
        "required": config["required"],
        "passed": exam_passed(level, correct_answers),
    }

# ============================================================
# BANQUES SPÉCIALISÉES — PROBATOIRE / BACC / UNIVERSITÉ
# ============================================================
# 8 domaines × 3 niveaux.
# Sciences existe déjà dans ADVANCED et est conservé.
# Les 7 autres domaines sont ajoutés ici.
# Chaque banque est indépendante : aucune question d'un niveau
# n'est automatiquement reprise dans un autre niveau.

SPECIALIZED_ADVANCED = {
    "technology": {
        "probatoire": [
            q("Le protocole principalement utilisé pour consulter une page Web est :", ["HTTP/HTTPS", "SMTP", "DHCP", "Bluetooth"], 0),
            q("Une adresse IPv4 contient :", ["32 bits", "16 bits", "64 bits", "128 bits"], 0),
            q("Un octet contient :", ["8 bits", "4 bits", "16 bits", "32 bits"], 0),
            q("Le langage HTML sert principalement à :", ["Structurer le contenu d'une page Web", "Chiffrer un disque", "Mesurer une tension", "Gérer une batterie"], 0),
            q("Un routeur sert principalement à :", ["Acheminer des paquets entre réseaux", "Saisir du texte", "Afficher des pixels", "Stocker des photos"], 0),
            q("La RAM est une mémoire :", ["Volatile", "Toujours permanente", "Optique", "Mécanique"], 0),
            q("Une base de données sert notamment à :", ["Organiser et retrouver des données", "Refroidir un ordinateur", "Remplacer un écran", "Mesurer le courant"], 0),
            q("Un algorithme est :", ["Une suite d'étapes permettant de résoudre un problème", "Un câble réseau", "Une carte graphique", "Un fichier audio"], 0),
            q("Un antivirus cherche principalement à :", ["Détecter ou bloquer des logiciels malveillants", "Augmenter la RAM", "Créer une IP", "Produire de l'électricité"], 0),
            q("Une API permet notamment :", ["À des logiciels de communiquer selon une interface définie", "De remplacer un processeur", "De mesurer la température", "De fabriquer un écran"], 0),
        ],
        "bacc": [
            q("Une clé étrangère en base de données sert à :", ["Relier une table à une autre", "Créer un écran", "Compresser un processeur", "Mesurer le courant"], 0),
            q("La notation O(log n) décrit généralement :", ["Une croissance logarithmique du coût", "Une croissance exponentielle", "Un coût toujours nul", "Une mémoire physique"], 0),
            q("DNS permet principalement de :", ["Résoudre des noms de domaine", "Chiffrer tous les fichiers", "Créer une batterie", "Compiler du Python"], 0),
            q("Un processus est :", ["Un programme en cours d'exécution", "Un câble réseau", "Une base de données", "Un écran"], 0),
            q("Le chiffrement sert principalement à :", ["Protéger la confidentialité des données", "Augmenter la résolution", "Réduire la taille du CPU", "Créer une IP"], 0),
            q("Une pile suit le principe :", ["LIFO", "FIFO", "RANDOM", "DNS"], 0),
            q("Une file suit le principe :", ["FIFO", "LIFO", "HTTP", "SQL"], 0),
            q("Git sert principalement à :", ["Gérer les versions du code", "Mesurer une tension", "Créer une base électrique", "Remplacer un serveur"], 0),
            q("Le hameçonnage cherche notamment à :", ["Tromper un utilisateur pour obtenir des informations", "Refroidir un processeur", "Optimiser une requête", "Créer une image"], 0),
            q("Le principe du moindre privilège consiste à :", ["Accorder seulement les droits nécessaires", "Donner tous les droits", "Supprimer les comptes", "Désactiver la sécurité"], 0),
            q("Une transaction de base de données doit notamment préserver :", ["La cohérence des données", "La résolution d'écran", "La fréquence audio", "La puissance du GPU"], 0),
            q("Un compilateur transforme généralement :", ["Du code source en code cible ou intermédiaire", "Une IP en câble", "Une image en banque", "Une tension en texte"], 0),
        ],
        "university": [
            q("La complexité moyenne d'une recherche dans une table de hachage bien dimensionnée est :", ["O(1)", "O(n²)", "O(n!)", "O(log n) toujours"], 0),
            q("Dijkstra est utilisé pour :", ["Les plus courts chemins avec poids non négatifs", "Le tri d'images", "Le chiffrement", "La compression audio"], 0),
            q("Un mutex sert à :", ["Protéger une section critique", "Résoudre DNS", "Stocker une image", "Compiler du code"], 0),
            q("Le problème SAT est :", ["NP-complet", "Toujours linéaire", "Toujours indécidable", "Un protocole réseau"], 0),
            q("La normalisation relationnelle vise notamment à :", ["Réduire certaines redondances et anomalies", "Augmenter les doublons", "Supprimer les clés", "Créer des pixels"], 0),
            q("Un index B-tree sert notamment à :", ["Accélérer certaines recherches ordonnées", "Chiffrer un disque", "Créer un processus", "Mesurer une tension"], 0),
            q("TCP fournit notamment :", ["Une transmission fiable et ordonnée", "Uniquement du routage", "Des images", "Une base SQL"], 0),
            q("L'analyse lexicale d'un compilateur produit généralement :", ["Des unités lexicales ou tokens", "Des pixels", "Des paquets IP", "Des salaires"], 0),
            q("Le garbage collector gère principalement :", ["La mémoire devenue inaccessible", "Le réseau", "Le clavier", "Le DNS"], 0),
            q("CAP concerne notamment :", ["Cohérence, disponibilité et tolérance au partitionnement", "CPU, RAM et disque", "HTTP, FTP et SMTP", "SQL, HTML et CSS"], 0),
            q("Une fonction de hachage cryptographique doit être difficile à :", ["Inverser", "Calculer", "Stocker", "Appeler"], 0),
            q("La concurrence en programmation concerne :", ["Plusieurs tâches pouvant progresser de façon entrelacée ou parallèle", "Les couleurs", "Les imprimantes", "Les écrans"], 0),
            q("Une injection SQL exploite notamment :", ["Des entrées interprétées comme partie d'une requête", "La luminosité d'un écran", "La RAM physique", "Le son"], 0),
            q("La virtualisation permet notamment :", ["D'exécuter des environnements isolés sur une même machine physique", "De supprimer le processeur", "De remplacer Internet", "De créer de l'électricité"], 0),
            q("Une architecture distribuée utilise :", ["Plusieurs nœuds qui coopèrent", "Un seul transistor", "Aucun réseau", "Un seul fichier"], 0),
        ],
    },
    "economics": {
        "probatoire": [
            q("Le PIB mesure principalement :", ["La valeur des biens et services finaux produits", "Le patrimoine individuel", "Le nombre de banques", "Les salaires uniquement"], 0),
            q("L'inflation est :", ["Une hausse générale et durable du niveau des prix", "Une hausse d'un seul produit", "Une baisse du PIB", "Une hausse automatique des salaires"], 0),
            q("Épargner consiste à :", ["Mettre une partie du revenu de côté", "Tout dépenser", "Emprunter", "Créer une dette"], 0),
            q("Le salaire est :", ["Une rémunération du travail", "Une taxe", "Une amende", "Un prêt"], 0),
            q("Une entreprise produit généralement :", ["Des biens ou services", "Des diplômes uniquement", "Des lois", "Des monnaies"], 0),
            q("Un bénéfice apparaît quand :", ["Les recettes dépassent les coûts", "Les coûts dépassent les recettes", "Il n'y a aucune vente", "L'entreprise ferme"], 0),
            q("Le marché met notamment en relation :", ["L'offre et la demande", "Les médecins et patients uniquement", "Les élèves et professeurs uniquement", "Les tribunaux et banques uniquement"], 0),
            q("Un prix représente généralement :", ["Une valeur monétaire associée à un bien ou service", "Une note", "Une dette", "Un diplôme"], 0),
            q("Un emprunt est :", ["Une somme reçue avec obligation de remboursement selon les conditions", "Un cadeau", "Un salaire", "Une taxe"], 0),
            q("Une banque peut notamment :", ["Recevoir des dépôts et accorder des crédits", "Décerner le BACC", "Créer des lois", "Soigner les patients"], 0),
        ],
        "bacc": [
            q("L'élasticité-prix de la demande mesure :", ["La réaction de la quantité demandée à une variation du prix", "La taille d'une entreprise", "La dette", "Le nombre de salariés"], 0),
            q("Le coût d'opportunité est :", ["La meilleure alternative abandonnée lors d'un choix", "Une taxe", "Un salaire", "Une facture"], 0),
            q("Le seuil de rentabilité correspond au niveau où :", ["Le résultat est nul", "Le bénéfice est maximal", "Les coûts sont nuls", "Les ventes sont nulles"], 0),
            q("Une charge fixe :", ["Varie peu avec le niveau d'activité à court terme", "Est toujours nulle", "Est toujours un bénéfice", "Disparaît toujours avec les ventes"], 0),
            q("Le bilan comptable présente notamment :", ["Actif et passif", "Uniquement les ventes", "Uniquement les salaires", "Uniquement les impôts"], 0),
            q("Une obligation financière est généralement :", ["Un titre de créance", "Une action", "Un salaire", "Une facture client"], 0),
            q("La croissance économique désigne notamment :", ["Une augmentation durable de la production réelle", "Une hausse ponctuelle d'un prix", "Une baisse des salaires", "Une hausse de dette uniquement"], 0),
            q("La politique budgétaire concerne notamment :", ["Les recettes et dépenses publiques", "La médecine", "La programmation", "La photographie"], 0),
            q("La productivité mesure notamment :", ["La production rapportée aux facteurs utilisés", "La dette rapportée au salaire", "Le prix rapporté à la taxe", "La population rapportée au PIB"], 0),
            q("L'actualisation permet de :", ["Comparer des flux monétaires à des dates différentes", "Supprimer l'inflation automatiquement", "Créer de la monnaie", "Calculer une note"], 0),
            q("La solvabilité d'une entreprise concerne :", ["Sa capacité à honorer ses engagements", "Son nombre de clients uniquement", "Sa publicité", "Sa couleur"], 0),
            q("Une externalité est :", ["Un effet sur autrui non pleinement pris en compte par le marché", "Une dette bancaire", "Une action", "Une facture"], 0),
        ],
        "university": [
            q("La sélection adverse résulte notamment :", ["D'une asymétrie d'information avant le contrat", "D'une absence de prix", "D'une hausse automatique du PIB", "D'un excès de productivité"], 0),
            q("L'aléa moral apparaît notamment :", ["Après le contrat lorsque les comportements changent sous protection", "Avant toute transaction uniquement", "Quand tous ont la même information", "Quand les prix sont nuls"], 0),
            q("Le CAPM relie le rendement attendu notamment :", ["Au taux sans risque et au risque systématique", "Au nombre de salariés", "À la TVA uniquement", "À la couleur des actifs"], 0),
            q("Un équilibre de Nash est une situation où :", ["Aucun joueur n'a intérêt à dévier seul", "Tous ont le même revenu", "Un seul décide", "Les prix sont nuls"], 0),
            q("L'indice de Gini mesure notamment :", ["Les inégalités de distribution", "La croissance démographique", "Le taux directeur", "La productivité uniquement"], 0),
            q("Le risque systématique est :", ["Un risque non diversifiable", "Le risque propre à une seule entreprise", "Une erreur comptable", "Une taxe"], 0),
            q("Le coût d'agence provient notamment :", ["De divergences d'intérêts entre principal et agent", "De l'inflation uniquement", "D'un diplôme", "D'une couleur"], 0),
            q("L'efficience allocative en concurrence parfaite est associée à :", ["P = coût marginal", "P = 0 toujours", "Absence de demande", "Monopole obligatoire"], 0),
            q("La théorie des jeux étudie :", ["Les interactions stratégiques entre agents", "Les réactions chimiques", "Les réseaux informatiques", "Les maladies"], 0),
            q("L'asymétrie d'information signifie :", ["Que les agents disposent d'informations différentes", "Que tous savent tout", "Que personne ne sait rien", "Que les prix sont identiques"], 0),
            q("Une option financière confère généralement :", ["Un droit sans obligation d'exercer", "Une obligation absolue", "Un salaire", "Une dette publique"], 0),
            q("La diversification d'un portefeuille réduit surtout :", ["Le risque spécifique", "Le risque systématique à zéro", "Tous les risques", "L'inflation"], 0),
            q("Une politique monétaire restrictive vise généralement à :", ["Resserrer les conditions monétaires", "Rendre tous les crédits gratuits", "Supprimer la monnaie", "Augmenter automatiquement les salaires"], 0),
            q("Le taux d'actualisation sert notamment à :", ["Ramener des flux futurs à une valeur présente", "Calculer une taxe scolaire", "Mesurer la productivité physique", "Déterminer une nationalité"], 0),
            q("Une asymétrie d'information peut conduire à :", ["Des défaillances de marché", "Une concurrence toujours parfaite", "Une absence de risque", "Une production toujours maximale"], 0),
        ],
    },
    "law": {
        "probatoire": [
            ("Une loi établit principalement :", ["Des règles de droit", "Des prix", "Des salaires", "Des recettes"]),
            ("Un contrat est :", ["Un accord créant des obligations", "Une maladie", "Un diplôme", "Une monnaie"]),
            ("Un tribunal rend :", ["Des décisions de justice", "Des salaires", "Des factures", "Des diplômes"]),
            ("La présomption d'innocence signifie :", ["Être considéré innocent avant condamnation", "Être toujours coupable", "Ne jamais être jugé", "Être automatiquement condamné"]),
            ("Une carte d'identité sert notamment à :", ["Justifier son identité", "Payer une dette", "Passer le BAC", "Créer une entreprise"]),
            ("Le droit organise notamment :", ["Les relations sociales", "La météo", "La cuisine", "La musique"]),
            ("Une obligation juridique peut résulter :", ["D'un contrat ou de la loi", "D'une couleur", "D'un sport", "D'une chanson"]),
            ("La responsabilité civile vise notamment :", ["La réparation d'un dommage", "La création d'une monnaie", "La délivrance d'un diplôme", "La météo"]),
            ("Une personne morale peut être :", ["Une société", "Une température", "Une note", "Une maladie"]),
            ("Une sanction juridique est :", ["Une conséquence prévue par le droit", "Un cadeau", "Une note", "Un salaire"]),
        ],
        "bacc": [
            ("La responsabilité contractuelle peut résulter :", ["De l'inexécution d'une obligation contractuelle", "D'une couleur", "D'une température", "D'un diplôme"]),
            ("La nullité sanctionne notamment :", ["Un défaut affectant la validité d'un acte", "Une bonne exécution", "Une promotion", "Une publicité"]),
            ("Une règle impérative est :", ["Une règle à laquelle on ne peut normalement pas déroger librement", "Une règle facultative", "Une règle sportive", "Une règle sans effet"]),
            ("La hiérarchie des normes sert à :", ["Organiser les rapports entre normes", "Fixer les salaires", "Calculer les intérêts", "Créer des médicaments"]),
            ("Une société possède selon le régime applicable :", ["Une personnalité juridique distincte de ses membres", "Un corps humain", "Un groupe sanguin", "Aucun patrimoine"]),
            ("La charge de la preuve désigne :", ["La partie à laquelle incombe d'établir certains faits", "Le montant d'un salaire", "Le prix d'un contrat", "La durée d'un examen"]),
            ("Une clause contractuelle est :", ["Une stipulation convenue dans un contrat", "Une sanction pénale", "Un diplôme", "Une taxe"]),
            ("Un dommage peut être :", ["Matériel, corporel ou moral", "Uniquement financier", "Toujours pénal", "Toujours imaginaire"]),
            ("La jurisprudence regroupe notamment :", ["Des décisions de justice et leur interprétation", "Toutes les lois", "Tous les contrats privés", "Les règlements sportifs"]),
            ("Le principe du contradictoire permet notamment :", ["Aux parties de connaître et discuter les éléments pertinents", "De supprimer les preuves", "D'empêcher toute défense", "De fixer les prix"]),
            ("La capacité juridique concerne notamment :", ["L'aptitude à exercer certains droits et obligations", "La vitesse", "Le pH", "La mémoire informatique"]),
            ("Un recours permet notamment :", ["De contester une décision selon la procédure", "De créer une entreprise automatiquement", "De modifier la météo", "De changer une note"]),
        ],
        "university": [
            ("Le contrôle de constitutionnalité vise à :", ["Vérifier la conformité d'une norme à la Constitution", "Calculer le PIB", "Fixer un salaire", "Créer une entreprise"]),
            ("Le principe de proportionnalité cherche notamment à :", ["Adapter une mesure à l'objectif poursuivi", "Supprimer toute sanction", "Créer une monnaie", "Déterminer une note"]),
            ("Le droit international privé traite notamment :", ["Des rapports privés comportant un élément d'extranéité", "Des contrats purement internes uniquement", "De la médecine", "Des réseaux"]),
            ("Un conflit de lois concerne :", ["La détermination de la loi applicable à une situation internationale", "Le calcul d'une note", "La couleur d'un contrat", "La météo"]),
            ("Le droit des sociétés étudie notamment :", ["La constitution et le fonctionnement des sociétés", "Les réactions chimiques", "Les réseaux", "La physiologie"]),
            ("La sécurité juridique vise notamment :", ["La prévisibilité et la stabilité du droit", "L'augmentation des salaires", "La création monétaire", "La programmation"]),
            ("La force obligatoire du contrat signifie notamment :", ["Qu'un contrat valablement formé produit ses effets juridiques", "Que tout contrat est gratuit", "Qu'aucune obligation n'existe", "Que tout contrat est pénal"]),
            ("Le droit des obligations étudie notamment :", ["Les rapports entre créanciers et débiteurs", "Les pixels", "Les médicaments", "Les moteurs"]),
            ("La responsabilité pénale vise principalement :", ["La sanction d'une infraction", "La réparation de tout dommage civil", "La création d'un salaire", "La gestion d'une banque"]),
            ("La bonne foi peut intervenir notamment dans :", ["La formation ou l'exécution des obligations", "Le calcul du PIB", "La mesure d'une force", "Le routage"]),
            ("La personnalité morale implique notamment :", ["Une existence juridique distincte de celle des membres", "Une identité biologique", "Un corps physique", "L'absence de droits"]),
            ("Le droit de la preuve étudie notamment :", ["Les moyens et conditions permettant d'établir les faits", "Les taux bancaires", "Les moteurs", "Les maladies"]),
            ("La procédure civile encadre notamment :", ["Le déroulement des litiges civils", "La production agricole", "La fabrication de médicaments", "Le fonctionnement d'un CPU"]),
            ("La responsabilité du fait des produits concerne notamment :", ["Les dommages liés à des produits défectueux selon le régime applicable", "Les examens scolaires", "Les salaires", "Les réseaux"]),
            ("L'interprétation juridique consiste notamment à :", ["Déterminer le sens et la portée d'une règle", "Créer une nouvelle monnaie", "Mesurer une pression", "Programmer un routeur"]),
        ],
    },
    "medicine": {
        "probatoire": [
            ("Les globules rouges transportent principalement :", ["L'oxygène", "Les hormones uniquement", "Les os", "Les neurones"]),
            ("Les globules blancs participent principalement :", ["À la défense immunitaire", "À la digestion", "À la vision", "À la contraction cardiaque"]),
            ("Le cœur sert principalement à :", ["Propulser le sang", "Filtrer l'urine", "Produire la bile", "Digérer les protéines"]),
            ("Les reins participent notamment à :", ["La formation de l'urine et la régulation du milieu intérieur", "La respiration", "La vision", "La mastication"]),
            ("Les poumons assurent notamment :", ["Les échanges gazeux", "La digestion", "La filtration urinaire", "La coagulation"]),
            ("L'insuline participe à :", ["La régulation de la glycémie", "La vision", "La respiration mécanique", "La production des os"]),
            ("Une hormone est notamment :", ["Un messager chimique", "Un os", "Un globule rouge", "Un contrat"]),
            ("Les alvéoles pulmonaires permettent principalement :", ["Les échanges entre air et sang", "La digestion", "La filtration du sang", "La production d'urine"]),
            ("Le système nerveux central comprend :", ["Le cerveau et la moelle épinière", "Le foie et les reins", "Le cœur et les poumons", "Les muscles et les os"]),
            ("La vaccination vise notamment à :", ["Préparer une réponse immunitaire spécifique", "Remplacer les globules rouges", "Augmenter la taille", "Créer des os"]),
        ],
        "bacc": [
            ("Les anticorps sont produits notamment par :", ["Des lymphocytes B différenciés", "Les globules rouges", "Les plaquettes", "Les neurones"]),
            ("La filtration glomérulaire se déroule principalement :", ["Dans les reins", "Dans le foie", "Dans les poumons", "Dans le cœur"]),
            ("Le débit cardiaque dépend notamment :", ["De la fréquence cardiaque et du volume d'éjection", "Du nombre de reins", "Du volume pulmonaire uniquement", "De la taille des os"]),
            ("L'homéostasie désigne :", ["Le maintien relativement stable du milieu intérieur", "La digestion uniquement", "La croissance des os", "La production d'anticorps uniquement"]),
            ("Le foie participe notamment :", ["Au métabolisme et à la détoxification", "À la filtration glomérulaire", "À la production des neurones", "À l'audition"]),
            ("L'hémostase correspond aux mécanismes qui :", ["Limitent un saignement", "Digèrent les aliments", "Produisent l'urine", "Assurent la vision"]),
            ("Le pancréas possède une fonction :", ["Endocrine et digestive", "Uniquement respiratoire", "Uniquement nerveuse", "Uniquement osseuse"]),
            ("Une infection bactérienne est liée notamment :", ["À la présence et multiplication de bactéries pathogènes", "À une fracture", "À un contrat", "À une note"]),
            ("La pression artérielle correspond notamment :", ["À la pression exercée par le sang sur les parois artérielles", "À la pression de l'air", "À la pression osseuse", "À la pression de l'estomac"]),
            ("Le tissu épithélial recouvre notamment :", ["Des surfaces et cavités de l'organisme", "Uniquement les os", "Uniquement les neurones", "Uniquement les globules rouges"]),
            ("Le potentiel d'action neuronal dépend notamment :", ["De mouvements d'ions à travers la membrane", "Du nombre d'os", "De la bile", "Du salaire"]),
            ("Une enzyme biologique agit notamment en :", ["Accélérant une réaction en abaissant son énergie d'activation", "Créant des atomes", "Supprimant tous les réactifs", "Augmentant toujours la température"]),
        ],
        "university": [
            ("La pharmacocinétique étudie principalement :", ["Ce que l'organisme fait au médicament", "Ce que le médicament fait au marché", "La couleur du médicament", "Le prix uniquement"]),
            ("La pharmacodynamie étudie principalement :", ["Les effets du médicament sur l'organisme", "Le stockage comptable", "La fabrication des diplômes", "Le prix"]),
            ("La clairance rénale renseigne notamment sur :", ["L'élimination d'une substance par les reins", "Le volume pulmonaire", "La force musculaire", "La vision"]),
            ("Le potentiel de membrane au repos dépend notamment :", ["Des gradients ioniques et de la perméabilité membranaire", "Du nombre d'os", "De la bile", "Du salaire"]),
            ("La loi de Starling décrit notamment :", ["Les échanges de liquide à travers les capillaires", "La réplication de l'ADN", "La contraction osseuse", "La vision"]),
            ("L'apoptose correspond à :", ["Une mort cellulaire programmée", "Une division bactérienne", "Une inflammation obligatoire", "Une coagulation"]),
            ("Une mutation germinale peut être transmise :", ["À la descendance selon les conditions biologiques", "Toujours à tout individu", "Uniquement aux bactéries", "Jamais"]),
            ("La PCR permet notamment :", ["D'amplifier une séquence d'acide nucléique", "De mesurer directement la pression artérielle", "De remplacer toute imagerie", "De produire des globules rouges"]),
            ("L'immunité adaptative se caractérise notamment par :", ["Spécificité et mémoire", "Absence de cellules", "Réponse identique à tout agent", "Production de bile"]),
            ("L'équilibre acido-basique dépend notamment :", ["Des systèmes tampons, des poumons et des reins", "Des os uniquement", "De la peau uniquement", "Des muscles uniquement"]),
            ("L'ECG enregistre principalement :", ["L'activité électrique du cœur", "La pression osseuse", "La filtration rénale", "La température du foie"]),
            ("La spirométrie mesure notamment :", ["Des volumes et débits respiratoires", "La glycémie directement", "La pression intracrânienne", "La force musculaire"]),
            ("Une enzyme se caractérise notamment par :", ["Une activité catalytique et une certaine spécificité de substrat", "Une production obligatoire d'ATP", "Une absence de structure", "Une fonction uniquement mécanique"]),
            ("La perfusion tissulaire dépend notamment :", ["Du débit sanguin et des caractéristiques vasculaires", "Du nombre de cheveux", "Du salaire", "De la couleur des yeux"]),
            ("Une réponse immunitaire secondaire est généralement :", ["Plus rapide et plus efficace grâce à la mémoire immunitaire", "Toujours absente", "Identique à la première dans tous les cas", "Uniquement mécanique"]),
        ],
    },
    "arts": {
        "probatoire": [
            ("La composition visuelle concerne :", ["L'organisation des éléments dans une œuvre", "Le calcul d'un salaire", "La filtration du sang", "Le routage"]),
            ("La perspective linéaire sert notamment à :", ["Représenter la profondeur", "Calculer un impôt", "Mesurer un médicament", "Programmer"]),
            ("Le contraste désigne notamment :", ["Une différence perceptible entre éléments", "Un contrat", "Une facture", "Une adresse IP"]),
            ("Une palette chromatique est :", ["Un ensemble de couleurs utilisées dans une œuvre", "Une base de données", "Une ordonnance", "Un salaire"]),
            ("Le rythme visuel peut être créé par :", ["La répétition d'éléments", "Une dette", "Un médicament", "Un routeur"]),
            ("La texture visuelle évoque notamment :", ["L'aspect d'une surface", "Le prix", "La vitesse réseau", "Le rythme cardiaque"]),
            ("Le cadrage photographique détermine :", ["Ce qui entre dans le champ", "Le salaire", "Le pH", "Le protocole réseau"]),
            ("Une œuvre abstraite peut :", ["S'éloigner de la représentation réaliste", "Être obligatoirement une photographie", "Être uniquement juridique", "Être toujours musicale"]),
            ("Le storyboard sert notamment à :", ["Prévisualiser une œuvre audiovisuelle", "Calculer une dette", "Faire un diagnostic", "Créer une banque"]),
            ("La sculpture peut utiliser notamment :", ["La pierre, le bois ou le métal", "Uniquement des logiciels", "Uniquement du texte", "Uniquement du son"]),
        ],
        "bacc": [
            ("Le clair-obscur repose notamment sur :", ["Le contraste entre lumière et ombre", "La programmation", "La finance", "La biologie"]),
            ("La profondeur de champ concerne :", ["La zone de netteté d'une image", "La comptabilité", "La médecine", "Le droit"]),
            ("La perspective atmosphérique suggère la profondeur par :", ["Des variations de contraste et de couleur", "Des contrats", "Des factures", "Des adresses IP"]),
            ("Le montage cinématographique organise :", ["Des plans dans une séquence", "Des salaires", "Des médicaments", "Des lois"]),
            ("La direction artistique vise notamment à :", ["Définir une cohérence esthétique", "Calculer les impôts", "Diagnostiquer", "Administrer un serveur"]),
            ("Une installation artistique utilise notamment :", ["L'espace et plusieurs éléments", "Uniquement des tableaux", "Uniquement des contrats", "Uniquement des médicaments"]),
            ("Le symbolisme artistique utilise :", ["Des formes ou images porteuses de sens", "Des IP", "Des taxes", "Des enzymes"]),
            ("La théorie des couleurs étudie notamment :", ["Les relations entre couleurs", "Les contrats", "Les enzymes", "Les réseaux"]),
            ("La scénographie concerne notamment :", ["L'organisation spatiale et visuelle d'un dispositif scénique", "La comptabilité", "La pharmacologie", "Le routage"]),
            ("Une licence artistique peut définir :", ["Les conditions d'utilisation d'une œuvre", "Le taux d'intérêt", "Le groupe sanguin", "La puissance d'un moteur"]),
            ("Une narration visuelle organise :", ["Des images pour transmettre un récit ou une idée", "Des impôts", "Des médicaments", "Des IP"]),
            ("La composition équilibrée cherche notamment :", ["Une organisation visuelle cohérente", "Une dette minimale", "Une pression stable", "Une vitesse réseau"]),
        ],
        "university": [
            ("La sémiotique artistique étudie notamment :", ["Les signes et leur production de sens", "Les enzymes", "Les banques", "Les moteurs"]),
            ("La conservation-restauration vise notamment à :", ["Préserver et traiter les œuvres", "Créer des contrats", "Calculer le PIB", "Programmer"]),
            ("La Gestalt étudie notamment :", ["L'organisation perceptive des formes", "Les taux bancaires", "Les cellules", "Les lois"]),
            ("La propriété intellectuelle protège notamment :", ["Certaines créations et signes", "Le groupe sanguin", "Le Wi-Fi", "La température"]),
            ("L'art conceptuel met notamment l'accent sur :", ["L'idée ou le concept de l'œuvre", "Le salaire uniquement", "La vitesse", "Le pH"]),
            ("La muséographie concerne notamment :", ["La conception des espaces d'exposition", "La chirurgie", "Les banques", "Les réseaux"]),
            ("L'intertextualité artistique désigne :", ["Les relations entre œuvres et références", "Les taux d'intérêt", "Les réactions chimiques", "Les protocoles"]),
            ("La couleur additive concerne :", ["Le mélange de lumières colorées", "Le mélange de médicaments", "Les contrats", "Les impôts"]),
            ("Une démarche curatoriale concerne :", ["La sélection et mise en relation d'œuvres", "La programmation d'un CPU", "La médecine", "La finance"]),
            ("L'analyse formelle examine notamment :", ["Les éléments et relations visibles d'une œuvre", "Le salaire", "Le droit pénal", "Le réseau"]),
            ("Une œuvre multimédia combine :", ["Plusieurs médias ou formes d'expression", "Uniquement du texte juridique", "Uniquement des chiffres", "Uniquement des médicaments"]),
            ("La narration audiovisuelle organise notamment :", ["Images, sons et temporalité pour transmettre un récit", "Des contrats", "Des impôts", "Des IP"]),
            ("L'analyse iconographique étudie notamment :", ["Les sujets, motifs et significations représentés", "Les taux bancaires", "Les réseaux", "Les enzymes"]),
            ("La scénographie muséale cherche notamment à :", ["Organiser l'expérience spatiale du visiteur", "Créer des salaires", "Mesurer le pH", "Compiler un programme"]),
            ("La critique d'art peut notamment :", ["Interpréter et contextualiser une œuvre", "Déterminer une tension électrique", "Créer une banque", "Diagnostiquer une maladie"]),
        ],
    },
    "communication": {
        "probatoire": [
            ("La communication de masse vise :", ["Un public large", "Une seule cellule", "Un seul processeur", "Une seule banque"]),
            ("Une interview consiste notamment à :", ["Poser des questions à une personne", "Créer une facture", "Mesurer un objet", "Programmer un robot"]),
            ("Un communiqué de presse sert notamment à :", ["Transmettre une information officielle aux médias", "Créer un diplôme", "Calculer une dette", "Mesurer une force"]),
            ("L'audience désigne notamment :", ["Le public atteint par un média", "Un salaire", "Un médicament", "Un moteur"]),
            ("Une source permet notamment de :", ["Identifier l'origine d'une information", "Augmenter un prix", "Changer une note", "Créer une maladie"]),
            ("Le feedback correspond :", ["À une réaction au message", "À un salaire", "À une maladie", "À une adresse IP"]),
            ("La communication non verbale utilise notamment :", ["Gestes et expressions", "Uniquement des chiffres", "Des contrats", "Des factures"]),
            ("La communication institutionnelle présente notamment :", ["L'identité et les activités d'une organisation", "Le pH", "Un programme", "Un diagnostic"]),
            ("Vérifier une information permet de :", ["Limiter la diffusion d'informations fausses", "Augmenter une dette", "Supprimer Internet", "Changer une identité"]),
            ("Un titre sert généralement à :", ["Présenter ou résumer le sujet d'un contenu", "Calculer un salaire", "Mesurer la température", "Créer un mot de passe"]),
        ],
        "bacc": [
            ("L'agenda-setting concerne notamment :", ["L'influence sur l'importance accordée aux sujets", "La médecine", "La mécanique", "La comptabilité"]),
            ("La communication de crise vise notamment à :", ["Gérer l'information en situation sensible", "Créer une banque", "Faire un examen", "Mesurer une température"]),
            ("La segmentation d'audience consiste à :", ["Diviser un public en groupes pertinents", "Supprimer un public", "Changer une loi", "Créer une maladie"]),
            ("Le taux d'engagement mesure notamment :", ["Les interactions d'un public avec un contenu", "Le pH", "La vitesse", "La masse"]),
            ("Le storytelling utilise notamment :", ["La narration pour transmettre un message", "Des contrats", "Des enzymes", "Des routeurs"]),
            ("La communication interne concerne notamment :", ["Les échanges au sein d'une organisation", "Les échanges sanguins", "La météo", "La programmation"]),
            ("Une campagne de communication comprend notamment :", ["Objectifs, messages, publics et moyens", "Uniquement un salaire", "Un contrat seulement", "Un médicament"]),
            ("La réputation numérique dépend notamment :", ["Des informations et perceptions liées à une présence en ligne", "Du groupe sanguin", "Du pH", "Du nombre d'os"]),
            ("Une source secondaire :", ["Analyse ou rapporte des informations provenant de sources primaires", "Est toujours fausse", "Est toujours anonyme", "Est toujours officielle"]),
            ("La désinformation vise notamment :", ["À tromper ou induire en erreur", "À vérifier une source", "À corriger une faute", "À publier une étude"]),
            ("Le référencement vise notamment à :", ["Améliorer la visibilité dans les moteurs de recherche", "Créer une banque", "Mesurer la tension", "Produire des médicaments"]),
            ("Une stratégie éditoriale définit notamment :", ["Thèmes, formats et ligne de contenu", "Groupes sanguins", "Taux bancaires", "Moteurs"]),
        ],
        "university": [
            ("La théorie de la communication étudie notamment :", ["La production, transmission et réception des messages", "Les enzymes", "Les banques", "Les moteurs"]),
            ("L'analyse sémiotique étudie notamment :", ["Les signes, codes et significations", "Les taux d'intérêt", "La pression", "Les cellules"]),
            ("Le framing concerne notamment :", ["La sélection et mise en forme d'aspects d'un sujet", "La filtration du sang", "Le stockage", "La fiscalité"]),
            ("La communication organisationnelle étudie notamment :", ["Les flux d'information dans les organisations", "Les fractures", "Les moteurs", "Les banques uniquement"]),
            ("La communication interculturelle prend en compte :", ["Les différences de codes et contextes culturels", "Uniquement le prix", "Uniquement la météo", "Uniquement le processeur"]),
            ("L'analyse de sentiment cherche notamment à :", ["Identifier des tendances émotionnelles dans des contenus", "Calculer le PIB", "Diagnostiquer une fracture", "Mesurer une force"]),
            ("La communication scientifique cherche notamment à :", ["Rendre des connaissances scientifiques compréhensibles", "Remplacer les expériences", "Créer des contrats", "Calculer les salaires"]),
            ("Une stratégie multicanale utilise :", ["Plusieurs canaux coordonnés", "Un seul canal obligatoire", "Aucun média", "Uniquement des factures"]),
            ("La portée d'un contenu désigne notamment :", ["Le nombre de personnes potentiellement atteintes", "Le salaire", "La température", "La masse"]),
            ("Une crise réputationnelle peut nécessiter :", ["Une réponse rapide, cohérente et vérifiable", "Le silence obligatoire", "La suppression des preuves", "Un changement de diplôme"]),
            ("L'éthique journalistique concerne notamment :", ["Les principes encadrant la collecte et diffusion de l'information", "Les taux bancaires", "La mécanique", "La génétique"]),
            ("La vérification des faits vise notamment à :", ["Évaluer l'exactitude d'une affirmation", "Augmenter une dette", "Créer une entreprise", "Changer un diplôme"]),
            ("La communication politique peut mobiliser :", ["Des stratégies de persuasion et de cadrage", "Des enzymes", "Des batteries", "Des microscopes"]),
            ("L'archivage des contenus sert notamment à :", ["Conserver des traces pour référence", "Mesurer le pH", "Créer des os", "Augmenter la vitesse"]),
            ("Une stratégie de communication intégrée cherche notamment à :", ["Coordonner les messages sur plusieurs canaux", "Supprimer les publics", "Éviter toute cohérence", "Créer des médicaments"]),
        ],
    },
}

# Convertir les tuples des 4 domaines concernés en objets q().
for _domain in ("law", "medicine", "arts", "communication"):
    for _level, _rows in SPECIALIZED_ADVANCED[_domain].items():
        SPECIALIZED_ADVANCED[_domain][_level] = [
            q(question, answers, 0)
            for question, answers in _rows
        ]

# La conversion ci-dessus accepte aussi bien les tuples (question, answers)
# que les tuples (question, answers, correct). Pour la robustesse, vérifier
# ensuite toutes les banques.
if "ADVANCED" not in globals():
    ADVANCED = {}

for _domain, _levels in SPECIALIZED_ADVANCED.items():
    ADVANCED[_domain] = _levels

# ============================================================
# INGÉNIERIE — PROBATOIRE / BACC / UNIVERSITÉ
# ============================================================
SPECIALIZED_ADVANCED["engineering"] = {
    "probatoire": [
        q("La loi d'Ohm relie notamment :", ["Tension, courant et résistance", "Masse, volume et température", "Pression, temps et énergie", "Vitesse et salaire"], 0),
        q("Un moment de force dépend notamment :", ["De la force et du bras de levier", "Du pH", "Des pixels", "Du salaire"], 0),
        q("Un capteur sert à :", ["Mesurer ou détecter une grandeur", "Peindre", "Payer", "Juger"], 0),
        q("Un moteur transforme notamment :", ["Une énergie en mouvement", "Une loi en salaire", "Une note en diplôme", "Une facture en argent"], 0),
        q("La CAO signifie :", ["Conception assistée par ordinateur", "Comptabilité assistée par ordinateur", "Communication audio optimisée", "Contrôle administratif officiel"], 0),
        q("Un matériau conducteur permet notamment :", ["Le passage du courant électrique", "La suppression de toute tension", "La production d'un diplôme", "La mesure du pH"], 0),
        q("Une tolérance dimensionnelle indique :", ["Une variation admissible d'une dimension", "Une dette", "Un médicament", "Une adresse"], 0),
        q("Un système asservi utilise notamment :", ["Une boucle de rétroaction", "Un diplôme", "Une banque", "Un contrat"], 0),
        q("Un facteur de sécurité sert à :", ["Introduire une marge face aux incertitudes de conception", "Calculer un salaire", "Créer une IP", "Mesurer le pH"], 0),
        q("Un engrenage transmet notamment :", ["Un mouvement et un couple", "Une maladie", "Une information juridique", "Une note"], 0),
    ],
    "bacc": [
        q("La contrainte normale est liée notamment à :", ["Une force normale rapportée à une section", "Une température", "Un courant uniquement", "Un salaire"], 0),
        q("La résistance des matériaux étudie notamment :", ["Le comportement des structures sous charges", "Les médias", "Les banques", "Les contrats"], 0),
        q("Un système triphasé utilise :", ["Trois grandeurs électriques décalées en phase", "Trois processeurs", "Trois batteries obligatoires", "Trois moteurs identiques uniquement"], 0),
        q("La transformée de Laplace est utile notamment pour :", ["Analyser des systèmes dynamiques", "Mesurer une fracture", "Calculer un salaire", "Créer un contrat"], 0),
        q("Un automate programmable industriel sert notamment à :", ["Commander des procédés automatisés", "Créer une banque", "Diagnostiquer une maladie", "Rédiger une loi"], 0),
        q("Le rendement est le rapport entre :", ["Sortie utile et énergie ou puissance d'entrée", "Salaire et dette", "Prix et taxe", "Masse et température"], 0),
        q("La fatigue des matériaux concerne :", ["Les dommages sous chargements répétés", "La fatigue humaine uniquement", "Internet", "La comptabilité"], 0),
        q("Un échangeur thermique sert à :", ["Transférer de la chaleur", "Stocker des données", "Calculer un salaire", "Produire un diplôme"], 0),
        q("Une commande PID combine :", ["Actions proportionnelle, intégrale et dérivée", "Trois banques", "Trois médicaments", "Trois lois"], 0),
        q("Les éléments finis permettent notamment :", ["D'approximer le comportement de structures ou champs", "De calculer le PIB", "De vérifier une rumeur", "De diagnostiquer une maladie"], 0),
        q("La conductivité thermique mesure notamment :", ["La capacité d'un matériau à conduire la chaleur", "La vitesse Internet", "Le salaire", "Le pH"], 0),
        q("Une pompe transforme notamment :", ["Une énergie mécanique en énergie hydraulique selon le système", "Un diplôme en argent", "Une loi en médicament", "Un signal en salaire"], 0),
    ],
    "university": [
        q("Les équations de Navier-Stokes décrivent notamment :", ["Les écoulements de fluides", "Les marchés financiers uniquement", "Les contrats", "La génétique"], 0),
        q("La mécanique des milieux continus modélise notamment :", ["Le comportement de corps considérés comme continus", "Les médias", "Les banques", "Les diplômes"], 0),
        q("La transformée de Fourier permet notamment :", ["D'analyser un signal en fréquences", "De calculer un salaire", "De filtrer le sang", "De rédiger une loi"], 0),
        q("La stabilité d'un système dynamique concerne :", ["Son comportement après perturbation", "Son prix", "Sa couleur", "Son diplôme"], 0),
        q("L'analyse modale étudie notamment :", ["Les modes propres de vibration", "Les taux bancaires", "Les contrats", "Les groupes sanguins"], 0),
        q("La mécanique de la rupture étudie notamment :", ["L'initiation et propagation des fissures", "La publicité", "La comptabilité", "Le droit"], 0),
        q("L'optimisation sous contraintes cherche :", ["Une solution optimale respectant des contraintes", "Un salaire maximal sans modèle", "Une loi", "Un médicament"], 0),
        q("Un système non linéaire possède notamment :", ["Des relations non linéaires entre variables", "Une température fixe obligatoire", "Un seul état", "Aucun paramètre"], 0),
        q("La commande robuste cherche notamment à :", ["Maintenir les performances malgré certaines incertitudes", "Supprimer les capteurs", "Créer une banque", "Changer une identité"], 0),
        q("La mécatronique combine notamment :", ["Mécanique, électronique, informatique et commande", "Droit, médecine et art uniquement", "Banque et communication", "Biologie et droit"], 0),
        q("La thermodynamique hors équilibre étudie notamment :", ["Des systèmes avec flux et dissipation", "Les contrats", "Les salaires", "Les réseaux sociaux"], 0),
        q("La fiabilité d'un système concerne notamment :", ["La probabilité qu'il remplisse sa fonction", "Son prix uniquement", "Sa couleur", "Son diplôme"], 0),
        q("L'analyse dimensionnelle permet notamment de :", ["Vérifier la cohérence des unités", "Créer un médicament", "Déterminer une loi", "Calculer une audience"], 0),
        q("Un modèle multiphysique couple :", ["Plusieurs phénomènes physiques interdépendants", "Plusieurs salaires", "Plusieurs diplômes", "Plusieurs contrats uniquement"], 0),
        q("La conception optimale cherche notamment à :", ["Optimiser un ou plusieurs objectifs sous contraintes", "Éliminer toutes les contraintes", "Supprimer les mesures", "Éviter toute modélisation"], 0),
    ],
}

# Publier toutes les banques spécialisées dans le dictionnaire consommé par le moteur.
for _domain, _levels in SPECIALIZED_ADVANCED.items():
    ADVANCED[_domain] = _levels

SPECIALIZED_COUNTS = {"probatoire": 10, "bacc": 12, "university": 15}

def get_specialized_questions(level: str, domain: str) -> list[dict]:
    level = str(level).lower().strip()
    domain = str(domain).lower().strip()
    return list(ADVANCED.get(domain, {}).get(level, []))

def validate_specialized_banks() -> dict:
    result = {}
    for _domain in DOMAINS:
        for _level, _expected in SPECIALIZED_COUNTS.items():
            _count = len(get_specialized_questions(_level, _domain))
            result[(_domain, _level)] = (_count == _expected, _count, _expected)
    return result

for _key, (_ok, _count, _expected) in validate_specialized_banks().items():
    if not _ok:
        raise RuntimeError(f"Banque spécialisée incomplète: {_key}: {_count}/{_expected}")
