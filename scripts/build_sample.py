"""Construit l'échantillon publiable versionné dans le dépôt.

Le jeu Olist complet pèse 146 Mo : il est exclu par `.gitignore` et ne peut pas
partir sur GitHub. L'échantillon sert deux usages :

- un clone à froid démarre sans rien télécharger ;
- la démonstration en ligne tourne sur des données réelles, en volume réduit.

**On tire des clients, pas des commandes.** C'est la seule décision structurante
de ce script, et elle a deux raisons :

1. *Histoires complètes.* La RFM et le churn se calculent sur des récences. Tirer
   des commandes trouerait l'historique de chaque client et rendrait ces deux
   analyses fausses, pas seulement imprécises. En tirant des clients et en gardant
   toutes leurs commandes, chaque histoire retenue est intacte.
2. *Profondeur temporelle.* Le modèle de churn a besoin d'au moins 365 jours
   d'inactivité pour distinguer un client perdu d'un acheteur ponctuel — c'est le
   comportement normal sur une place de marché, où ~90 % des clients n'achètent
   qu'une fois. Une fenêtre plus courte ne produit qu'une seule classe : le modèle
   dégénère et rend un score nul pour tout le monde. L'échantillon couvre donc les
   25 mois du jeu, pas une tranche.

Le tirage est aléatoire mais à graine fixe : l'échantillon est reproductible, et
il respecte la distribution réelle du jeu. On ne sur-représente pas les clients
multi-commandes pour rendre la démonstration plus flatteuse — ce serait mentir sur
la donnée.

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

# Nombre de clients uniques retenus. Olist compte ~1,03 commande par client :
# 15 000 clients donnent ~15 500 commandes, soit ~4 Mo de parquet compressé.
NB_CLIENTS = 15_000

# Graine fixe : deux exécutions produisent le même échantillon, et une régression
# de chiffres dans la démonstration est donc imputable au code, jamais au tirage.
GRAINE = 42

CIBLE_OCTETS = 15e6


def _lire(nom: str) -> pd.DataFrame:
    chemin = RAW_DIR / nom
    if not chemin.exists():
        sys.exit(
            f"Fichier absent : {chemin}\n"
            "Lancez d'abord `python scripts/download_data.py` pour récupérer le jeu Olist."
        )
    return pd.read_csv(chemin)


def construire() -> dict[str, pd.DataFrame]:
    customers = _lire("olist_customers_dataset.csv")
    orders = _lire("olist_orders_dataset.csv")

    # `customer_id` identifie une commande, `customer_unique_id` identifie une
    # personne. C'est sur la personne qu'il faut tirer, sinon un client à trois
    # commandes a trois fois plus de chances d'entrer, avec une seule de ses
    # commandes retenue.
    personnes = customers["customer_unique_id"].drop_duplicates()
    retenues = set(
        personnes.sample(n=min(NB_CLIENTS, len(personnes)), random_state=GRAINE)
    )

    customers = customers[customers["customer_unique_id"].isin(retenues)]
    ids_clients = set(customers["customer_id"])

    orders = orders[orders["customer_id"].isin(ids_clients)]
    ids_commandes = set(orders["order_id"])

    items = _lire("olist_order_items_dataset.csv")
    items = items[items["order_id"].isin(ids_commandes)]

    payments = _lire("olist_order_payments_dataset.csv")
    payments = payments[payments["order_id"].isin(ids_commandes)]

    reviews = _lire("olist_order_reviews_dataset.csv")
    reviews = reviews[reviews["order_id"].isin(ids_commandes)]

    # Produits et vendeurs se déduisent des articles retenus, pas des commandes.
    products = _lire("olist_products_dataset.csv")
    products = products[products["product_id"].isin(set(items["product_id"]))]

    sellers = _lire("olist_sellers_dataset.csv")
    sellers = sellers[sellers["seller_id"].isin(set(items["seller_id"]))]

    # La géolocalisation pèse 1 000 000 de lignes et n'est utile que sur les codes
    # postaux effectivement présents.
    geo = _lire("olist_geolocation_dataset.csv")
    codes = set(customers["customer_zip_code_prefix"]) | set(sellers["seller_zip_code_prefix"])
    geo = geo[geo["geolocation_zip_code_prefix"].isin(codes)].drop_duplicates(
        "geolocation_zip_code_prefix"
    )

    traduction = _lire("product_category_name_translation.csv")

    return {
        "olist_orders_dataset": orders,
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
    orders = tables["olist_orders_dataset"]
    commandes = set(orders["order_id"])
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

    manquants = set(orders["customer_id"]) - clients
    if manquants:
        problemes.append(f"{len(manquants)} commandes sans client")

    sans_produit = set(articles["product_id"]) - set(tables["olist_products_dataset"]["product_id"])
    if sans_produit:
        problemes.append(f"{len(sans_produit)} articles sans produit")

    sans_vendeur = set(articles["seller_id"]) - set(tables["olist_sellers_dataset"]["seller_id"])
    if sans_vendeur:
        problemes.append(f"{len(sans_vendeur)} articles sans vendeur")

    # Le seuil de churn est de 365 jours : sans au moins deux ans d'amplitude,
    # aucun client ne peut être étiqueté perdu et le modèle rend un score nul
    # pour tout le monde. C'est le défaut qu'on ne veut pas publier.
    dates = pd.to_datetime(orders["order_purchase_timestamp"])
    jours = (dates.max() - dates.min()).days
    if jours < 500:
        problemes.append(
            f"amplitude temporelle de {jours} jours, insuffisante pour un seuil de churn de 365"
        )

    if problemes:
        sys.exit("Échantillon incohérent :\n  - " + "\n  - ".join(problemes))


def main() -> None:
    tables = construire()
    verifier(tables)

    orders = tables["olist_orders_dataset"]
    dates = pd.to_datetime(orders["order_purchase_timestamp"])
    print(
        f"Periode {dates.min().date()} -> {dates.max().date()} "
        f"({(dates.max() - dates.min()).days} jours)"
    )
    print(
        f"{tables['olist_customers_dataset']['customer_unique_id'].nunique()} clients uniques, "
        f"{len(orders)} commandes\n"
    )

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for nom, df in tables.items():
        chemin = SAMPLE_DIR / f"{nom}.parquet"
        df.to_parquet(chemin, index=False, compression="zstd")
        octets = chemin.stat().st_size
        total += octets
        print(f"  {nom:<40} {len(df):>7} lignes  {octets / 1e6:>6.2f} Mo")

    print(f"\nTotal : {total / 1e6:.2f} Mo dans {SAMPLE_DIR}/")
    if total > CIBLE_OCTETS:
        sys.exit(f"Echantillon trop lourd ({total / 1e6:.1f} Mo > 15 Mo). Baissez NB_CLIENTS.")


if __name__ == "__main__":
    main()
