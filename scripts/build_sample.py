"""Construit l'échantillon publiable versionné dans le dépôt.

Le jeu Olist complet pèse 146 Mo : il est exclu par `.gitignore` et ne peut pas
partir sur GitHub. L'échantillon sert deux usages :

- un clone à froid démarre sans rien télécharger ;
- la démo en ligne tourne sur des données réelles, en volume réduit.

Deux règles gouvernent le tirage :

1. **Fenêtre temporelle continue**, jamais un tirage aléatoire. Le churn et la
   RFM se calculent sur des récences : un échantillon aléatoire troue l'histoire
   de chaque client et rend ces deux analyses fausses, pas seulement imprécises.
2. **Intégrité référentielle**, dans les deux sens. Toute commande retenue garde
   ses articles, paiements, avis, client, produits et vendeurs ; et aucune table
   ne conserve de ligne orpheline.

Usage :
    python scripts/build_sample.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# La console Windows par défaut est en cp1252 et ne sait pas encoder les
# caractères hors de cette page. Sans ceci, le script échoue à l'affichage
# après avoir fait tout le travail.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAW_DIR = Path("data/raw")
SAMPLE_DIR = Path("data/samples")

# Fenêtre retenue : douze mois pleins au cœur du jeu, là où le volume de
# commandes est stable. Les extrémités du jeu Olist sont clairsemées (montée en
# charge en 2016, coupure brutale fin 2018) et donneraient une saisonnalité
# trompeuse.
DEBUT = "2017-06-01"
FIN = "2018-06-01"

# Plafond de commandes. Au-delà, le parquet dépasse la cible de 15 Mo sans rien
# apporter à une démonstration.
MAX_COMMANDES = 10_000


def _lire(nom: str) -> pd.DataFrame:
    chemin = RAW_DIR / nom
    if not chemin.exists():
        sys.exit(
            f"Fichier absent : {chemin}\n"
            "Lancez d'abord `python scripts/download_data.py` pour récupérer le jeu Olist."
        )
    return pd.read_csv(chemin)


def construire() -> dict[str, pd.DataFrame]:
    orders = _lire("olist_orders_dataset.csv")
    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])

    fenetre = orders[
        (orders["order_purchase_timestamp"] >= DEBUT)
        & (orders["order_purchase_timestamp"] < FIN)
    ].copy()

    # Tronquer sur les plus anciennes : on garde une fenêtre continue qui commence
    # à DEBUT, plutôt que douze mois troués.
    fenetre = fenetre.sort_values("order_purchase_timestamp").head(MAX_COMMANDES)

    ids_commandes = set(fenetre["order_id"])
    ids_clients = set(fenetre["customer_id"])

    items = _lire("olist_order_items_dataset.csv")
    items = items[items["order_id"].isin(ids_commandes)]

    payments = _lire("olist_order_payments_dataset.csv")
    payments = payments[payments["order_id"].isin(ids_commandes)]

    reviews = _lire("olist_order_reviews_dataset.csv")
    reviews = reviews[reviews["order_id"].isin(ids_commandes)]

    customers = _lire("olist_customers_dataset.csv")
    customers = customers[customers["customer_id"].isin(ids_clients)]

    # Produits et vendeurs se déduisent des articles retenus, pas des commandes.
    products = _lire("olist_products_dataset.csv")
    products = products[products["product_id"].isin(set(items["product_id"]))]

    sellers = _lire("olist_sellers_dataset.csv")
    sellers = sellers[sellers["seller_id"].isin(set(items["seller_id"]))]

    # La géolocalisation est volumineuse (1 Mo compressé pour 1 000 000 de lignes)
    # et n'est utile que sur les codes postaux effectivement présents.
    geo = _lire("olist_geolocation_dataset.csv")
    codes = set(customers["customer_zip_code_prefix"]) | set(sellers["seller_zip_code_prefix"])
    geo = geo[geo["geolocation_zip_code_prefix"].isin(codes)].drop_duplicates(
        "geolocation_zip_code_prefix"
    )

    traduction = _lire("product_category_name_translation.csv")

    # La fenêtre est reposée en texte : le parquet garde le type datetime, mais
    # les tests de non-régression comparent des chaînes.
    fenetre["order_purchase_timestamp"] = fenetre["order_purchase_timestamp"].astype(str)

    return {
        "olist_orders_dataset": fenetre,
        "olist_order_items_dataset": items,
        "olist_order_payments_dataset": payments,
        "olist_order_reviews_dataset": reviews,
        "olist_customers_dataset": customers,
        "olist_products_dataset": products,
        "olist_sellers_dataset": sellers,
        "olist_geolocation_dataset": geo,
        "product_category_name_translation": traduction,
    }


def verifier(tables: dict[str, pd.DataFrame]) -> None:
    """Refuse un échantillon incohérent plutôt que de le publier."""
    commandes = set(tables["olist_orders_dataset"]["order_id"])
    clients = set(tables["olist_customers_dataset"]["customer_id"])
    articles = tables["olist_order_items_dataset"]

    problemes = []
    for nom in (
        "olist_order_items_dataset",
        "olist_order_payments_dataset",
        "olist_order_reviews_dataset",
    ):
        orphelines = set(tables[nom]["order_id"]) - commandes
        if orphelines:
            problemes.append(f"{nom} : {len(orphelines)} commandes inconnues")

    manquants = set(tables["olist_orders_dataset"]["customer_id"]) - clients
    if manquants:
        problemes.append(f"{len(manquants)} commandes sans client")

    sans_produit = set(articles["product_id"]) - set(tables["olist_products_dataset"]["product_id"])
    if sans_produit:
        problemes.append(f"{len(sans_produit)} articles sans produit")

    sans_vendeur = set(articles["seller_id"]) - set(tables["olist_sellers_dataset"]["seller_id"])
    if sans_vendeur:
        problemes.append(f"{len(sans_vendeur)} articles sans vendeur")

    if problemes:
        sys.exit("Échantillon incohérent :\n  - " + "\n  - ".join(problemes))


def main() -> None:
    tables = construire()
    verifier(tables)

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    print(f"Fenêtre {DEBUT} -> {FIN}")
    for nom, df in tables.items():
        chemin = SAMPLE_DIR / f"{nom}.parquet"
        df.to_parquet(chemin, index=False, compression="zstd")
        octets = chemin.stat().st_size
        total += octets
        print(f"  {nom:<40} {len(df):>7} lignes  {octets / 1e6:>6.2f} Mo")

    print(f"\nTotal : {total / 1e6:.2f} Mo dans {SAMPLE_DIR}/")
    if total > 15e6:
        sys.exit(f"Échantillon trop lourd ({total / 1e6:.1f} Mo > 15 Mo). Baissez MAX_COMMANDES.")


if __name__ == "__main__":
    main()
