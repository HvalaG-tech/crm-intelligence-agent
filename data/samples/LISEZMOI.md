# Échantillon de données — provenance et licence

Les fichiers `.parquet` de ce dossier sont un **extrait** du jeu de données public
*Brazilian E-Commerce Public Dataset by Olist*, publié par Olist sur Kaggle.

- **Source** : https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- **Licence** : Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
  ([CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/))
- **Auteur** : Olist

## Ce que cela implique

La licence du jeu d'origine **suit ses extraits**. Ces fichiers restent donc sous
CC BY-NC-SA 4.0, y compris ici : la licence MIT du dépôt couvre le code, pas les
données. Quiconque les réutilise doit citer Olist, ne pas en faire un usage
commercial, et redistribuer ses propres dérivés sous la même licence.

## Comment cet extrait a été produit

`scripts/build_sample.py`, exécuté sur le jeu complet. Il tire 15 000 clients au
sort à graine fixe et conserve l'intégralité de leurs commandes, articles,
paiements et avis. Aucune valeur n'est modifiée, agrégée ni anonymisée : ce sont
les lignes d'origine, en nombre réduit.

Le jeu complet, 146 Mo, n'est pas versionné. Il se récupère avec
`python scripts/download_data.py`.
