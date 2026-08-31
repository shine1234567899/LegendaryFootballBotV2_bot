# MANUWORLD V3 — refonte

## Principes
- Une seule source de vérité côté jeu : PostgreSQL.
- Les commandes ciblant un joueur utilisent une réponse Telegram ou `@username`.
- Les opérations d'argent sont atomiques et journalisées.
- Les systèmes sont idempotents : leurs migrations peuvent être relancées.
- Les boutons Telegram ne remplacent jamais les contrôles d'autorisation côté serveur.
- Le système bancaire est conservé séparément et n'est pas réécrit.

## Nouveautés
- Socle partagé `life_world/core.py`.
- Récompense quotidienne + série `/daily`.
- Réalisations `/achievements`.
- Notifications `/notifications`.
- Aide globale `/mwlhelp`.
- Politique V3 : partis, élections, candidatures, meetings.
- Entreprises : création, trésorerie, retrait PDG, paie, modification de salaire,
  licenciement, destruction avec confirmation.
- École : l'examen fait progresser de classe sans exiger `school_xp == 100`.
- Housing/lifestyle/wealth : migration des implémentations SQLite vers PostgreSQL.
- Targeting unifié : reply ou `@username`.

## Sécurité / cohérence
- Les actions d'entreprise vérifient le propriétaire côté serveur.
- Les retraits ne peuvent pas rendre une trésorerie négative.
- La paie vérifie la trésorerie avant de distribuer les salaires.
- La destruction rend la trésorerie restante au PDG avant suppression.
- Les opérations monétaires importantes écrivent dans `life_transactions`
  ou `life_company_transactions`.

## Banque
`life_world/systems/bank_system.py` n'est pas modifié dans cette refonte.
