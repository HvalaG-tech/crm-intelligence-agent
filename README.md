# Agent d'analyse CRM

**Vos équipes marketing obtiennent leurs analyses clients sans passer par la data team.**

<!-- Démonstration animée : déposer docs/demo.gif et décommenter la ligne suivante.
![Démonstration de l'agent](docs/demo.gif)
-->

### ▶ Démonstration en ligne — `À_FOURNIR`

*Six questions répondent immédiatement, sans inscription et sans clé API.*

---

## Le problème

Dans la plupart des directions marketing, « qui sont nos meilleurs clients », « lesquels
risquent de partir » et « combien pèse cette catégorie » sont des questions à un ticket
Jira et deux semaines d'attente. Quand la réponse arrive, la campagne est partie sans elle.

Les données sont pourtant là, et les analyses sont connues. Ce qui manque, c'est le chemin
entre une question posée en français et le calcul qui y répond.

## Ce que ça fait

- **Répond en français à une question métier** en choisissant lui-même la bonne analyse :
  segmentation RFM, score de départ, valeur vie client, regroupement comportemental,
  ou requête SQL libre quand la question ne rentre dans aucune case.
- **Montre son raisonnement.** Chaque réponse ouvre sur les outils appelés, leurs
  paramètres et leur résultat brut. Rien n'est à croire sur parole.
- **Garde la mémoire de la conversation** : « et ces catégories, elles vendent cher ou
  en volume ? » fonctionne sans répéter le contexte.
- **Sait dire non.** Une demande d'action — envoyer un email, écrire dans le CRM — est
  déclinée avec son motif, au lieu d'être bricolée avec l'outil le plus proche.
- **Ne coûte rien à visiter.** Le parcours de démonstration sert des analyses réellement
  calculées, sans aucun appel au modèle.

## Résultats mesurés

| Ce qui est mesuré | Valeur |
|---|---|
| Routage vers le bon outil | **31/31 questions (100 %)** |
| Outils d'analyse exposés à l'agent | 7 |
| Tests automatisés, tous au vert | 33 |
| Requêtes SQL hostiles bloquées sous test | 11 |
| Coût d'une visite du parcours de démonstration | 0 appel au modèle |
| Échantillon embarqué dans le dépôt | 15 000 clients · 15 477 commandes · 716 jours · 4,2 Mo |
| Poids d'un clone, historique compris | 6,7 Mo |

**Routage des outils.** La suite `eval/questions.yaml` couvre 31 questions sur les 7 outils,
dont 3 hors périmètre et 5 volontairement ambiguës. Elle mesure le choix de l'outil, pas la
qualité de la rédaction : le premier dépend de ce dépôt, la seconde du modèle du jour.

```bash
export OPENAI_API_KEY=sk-...
python eval/run_eval.py            # taux de réussite chiffré
python eval/run_eval.py --dry-run  # valide la suite sans aucun appel
```

*La forme `python -m eval.run_eval` fonctionne aussi, mais seulement depuis la racine du
dépôt : ailleurs, Python ne trouve pas le paquet `eval`.*

**Dernière mesure : 31/31, le 2 septembre 2026, sur `gpt-4o`.** Deux réserves honnêtes sur
ce 100 % : les cinq questions ambiguës acceptent plusieurs routages défendables, et les
trois questions hors périmètre se valident par l'absence d'appel d'outil. La suite est donc
un garde-fou de non-régression — elle attrape un prompt système dégradé ou un changement de
modèle qui déplace le routage — plutôt qu'un classement de difficulté.

## Architecture

```
                      Question en français
                              │
                              ▼
                    ┌───────────────────┐
      mode démo ───►│    core/agent     │  boucle d'outils (function calling)
   (sans modèle)    │  + core/demo      │  5 itérations maximum
                    └─────────┬─────────┘
                              │ choisit un outil
      ┌───────────┬───────────┼───────────┬────────────┐
      ▼           ▼           ▼           ▼            ▼
  compute_rfm  predict_    run_kmeans  sql_query   compute_clv
               churn                   (verrouillé)   + 2 autres
      │           │           │           │            │
      └───────────┴─────┬─────┴───────────┴────────────┘
                        ▼
                 analytics/  (pandas · scikit-learn · Plotly)
                        │
                        ▼
                 core/loader   cache ▸ jeu complet ▸ échantillon
                        │
                        ▼
             Réponse rédigée + graphique + trace des étapes
```

Deux points de conception méritent d'être signalés.

**`sql_query` est traité comme une surface d'attaque**, puisqu'il exécute du texte produit
par un modèle. Les DataFrames sont matérialisés en tables, puis l'accès externe de DuckDB
est coupé et la configuration verrouillée — le moteur refuse alors de lui-même le disque,
le réseau et les extensions. Une liste blanche syntaxique s'y ajoute, non pour protéger
davantage, mais pour rendre un refus que l'agent sait expliquer.

**Le mode démonstration ne fige que la narration.** Les outils sont réellement exécutés à
l'affichage : les tableaux et les graphiques sont calculés sur les données du dépôt. Ce
n'est pas une maquette, c'est le vrai calcul avec un commentaire pré-écrit.

## Stack

| Rôle | Technologie |
|---|---|
| Orchestration de l'agent | OpenAI function calling |
| Analyse | pandas · scikit-learn |
| SQL analytique | DuckDB, en lecture seule verrouillée |
| Visualisation | Plotly |
| Interface | Streamlit |
| Configuration | pydantic-settings |
| Qualité | pytest · ruff · GitHub Actions |

## Installation

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

L'application démarre sur l'échantillon embarqué, sans clé et sans téléchargement. Pour
travailler sur le jeu Olist complet, lancez `python scripts/download_data.py` puis
`python scripts/preprocess.py`. Pour poser des questions libres, ajoutez votre clé OpenAI
dans la barre latérale, ou dans un fichier `.env` sur le modèle de `.env.example`.

## Limites connues

C'est la section qui doit être lue avant les autres.

- **Les données sont publiques, pas réelles.** Le jeu [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
  décrit une place de marché brésilienne entre 2016 et 2018. Aucune donnée client réelle
  n'entre dans ce dépôt.
- **La démonstration en ligne tourne sur un échantillon**, pas sur le jeu complet : 15 000
  clients tirés au sort avec toute leur histoire, contre ~99 000 commandes en local. Les
  ordres de grandeur diffèrent donc de ceux qu'on lit habituellement sur Olist.
- **Le churn est une règle d'inactivité, pas une résiliation observée.** Le seuil est fixé
  à 365 jours parce que ~97 % des clients de cette base n'achètent qu'une fois : plus court,
  on étiquetterait « perdu » un comportement d'achat parfaitement normal. Sur des données
  client réelles, cette étiquette se construit avec le métier, elle ne se devine pas.
- **Le score de départ sature.** Le modèle rend 1,00 pour tous les clients franchement
  inactifs, ce qui les met à égalité par milliers. C'est pourquoi le graphique classe par
  chiffre d'affaires à risque plutôt que par score : la question utile est « lesquels
  rappeler en premier », pas « lesquels ont le plus haut score ».
- **La valeur vie client est une estimation à 12 mois, volontairement simple.** Elle
  additionne le réalisé et une projection de fréquence ; pour les acheteurs uniques, cette
  fréquence est l'espérance de réachat de la population, faute de pouvoir lire quoi que ce
  soit dans un historique d'une seule ligne. Ce n'est pas un modèle BG/NBD.
- **L'agent analyse, il n'agit pas.** Aucune écriture, aucun envoi, aucun déclenchement.
  La séparation est délibérée : un agent qui analyse et agit dans le même mouvement est un
  agent dont on ne peut pas vérifier le raisonnement avant qu'il produise ses effets.
- **Le routage dépend du modèle.** Il est mesuré par `eval/`, mais un changement de modèle
  peut le déplacer sans qu'une ligne de ce dépôt ait bougé.

## Licence

MIT — voir [LICENSE](LICENSE).
