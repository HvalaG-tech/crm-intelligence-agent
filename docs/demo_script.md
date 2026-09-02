# Parcours de démonstration — les six questions

Ces six questions sont celles des boutons de la page d'accueil. Elles sont servies par le
mode démonstration : la narration est pré-enregistrée dans `data/demo_answers.json`, mais
les outils sont **réellement exécutés**, donc les tableaux et les graphiques sont calculés
sur les données du dépôt. Aucun appel au modèle, aucune clé requise.

L'ordre n'est pas décoratif : il va du cadrage général à la preuve que l'agent connaît ses
limites, en passant par le moment qui démontre la mémoire conversationnelle.

| # | Question | Outil exécuté | Ce que la réponse doit établir |
|---|---|---|---|
| 1 | Donne-moi une vue d'ensemble de la base clients. | `get_data_summary` | Le cadrage : 15 477 commandes, 15 000 clients, 2 436 149 R$, et le fait que 1,03 commande par client conditionne toutes les analyses suivantes |
| 2 | Segmente mes clients avec une analyse RFM. | `compute_rfm` | Les quatre segments et leur déséquilibre : les Champions, un client sur quatre, pèsent 2,5 fois les *At Risk* pourtant aussi nombreux |
| 3 | Quels clients risquent de partir ? | `predict_churn` | 64,8 % à risque, et surtout la justification du seuil de 365 jours sur une place de marché |
| 4 | Quelles catégories de produits génèrent le plus de chiffre d'affaires ? | `sql_query` | Cinq catégories resserrées, mais des rapports CA/volume très différents |
| 5 | Et ces catégories, elles vendent cher ou en volume ? | `sql_query` | **La mémoire.** « Ces catégories » n'a de sens que si le tour précédent est retenu. Montres-cadeaux vend cher et peu, linge de maison en volume et bon marché |
| 6 | Peux-tu lancer une campagne d'emailing sur les clients à risque ? | *aucun* | **Les limites.** L'agent analyse, il n'agit pas, et il l'explique au lieu de bricoler une réponse |

## Si l'on enregistre une démonstration animée

Trois battements suffisent, et il faut enregistrer **en mode démonstration** : les réponses
sont instantanées, donc pas de temps mort à couper, et elles sont identiques d'une prise à
l'autre.

1. La page au repos, indicateurs visibles — le contexte se comprend sans lire.
2. Question 4, puis question 5. C'est la paire qui vend : le suivi prouve ce qu'un tableau
   de bord ne sait pas faire.
3. Ouverture de « Comment j'ai obtenu ce résultat » : le SQL réellement exécuté apparaît.

La question 6 est un excellent argument, mais elle se lit mieux à l'écrit : à l'image, c'est
un bloc de texte sans graphique.

## Chiffres de référence

Ceux du tableau ci-dessus valent pour l'échantillon versionné (`data/samples/`), tel que
produit par `scripts/build_sample.py` avec ses réglages par défaut. Ils changent si
`NB_CLIENTS` ou la graine sont modifiés, et diffèrent du jeu Olist complet, qui compte
~99 000 commandes.
