"""Chargement du jeu Olist — produit les DataFrames canoniques utilisés par les tools.

Trois sources, essayées dans cet ordre :

1. ``data/processed/`` — cache parquet des DataFrames déjà assemblés, le plus rapide ;
2. ``data/raw/`` — le jeu Olist complet, 146 Mo, absent du dépôt ;
3. ``data/samples/`` — l'échantillon versionné, 2,7 Mo, seul disponible après un clone.

Les deux premières n'existent que sur une machine où ``scripts/download_data.py``
a tourné. La troisième garantit qu'un clone à froid démarre sans rien télécharger,
et c'est elle qui alimente la démonstration en ligne.
"""

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
SAMPLE_DIR = Path("data/samples")

# Les sept tables Olist utilisées, sans extension : le nom est identique en CSV
# et en parquet, seule la source change.
TABLES = (
    "olist_orders_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_customers_dataset",
    "olist_products_dataset",
    "olist_sellers_dataset",
    "olist_geolocation_dataset",
)


class OlistLoader:
    """Assemble les fichiers Olist en DataFrames canoniques.

    Sorties canoniques :

    - ``orders_enriched`` : une ligne par article de commande, enrichie du produit,
      du vendeur et du client ;
    - ``customers_enriched`` : une ligne par client, avec son historique agrégé ;
    - ``geo`` : la table de géolocalisation, autonome.

    Après un appel à ``load_all``, l'attribut ``source`` indique laquelle des trois
    sources a effectivement servi : ``cache``, ``complet`` ou ``echantillon``.
    """

    def __init__(self) -> None:
        self.source: str = "inconnue"

    def load_all(self) -> dict[str, pd.DataFrame]:
        """Charge les DataFrames canoniques depuis la première source disponible."""
        orders_path = PROCESSED_DIR / "orders_enriched.parquet"
        customers_path = PROCESSED_DIR / "customers_enriched.parquet"

        if orders_path.exists() and customers_path.exists():
            self.source = "cache"
            logger.info("Source des donnees : cache parquet (%s)", PROCESSED_DIR)
            return {
                "orders_enriched": pd.read_parquet(orders_path),
                "customers_enriched": pd.read_parquet(customers_path),
                "geo": self._charger_geo(),
            }

        if (RAW_DIR / "olist_orders_dataset.csv").exists():
            self.source = "complet"
            logger.info("Source des donnees : jeu Olist complet (%s)", RAW_DIR)
            # Le cache n'est écrit que depuis le jeu complet : le reconstituer à
            # partir de l'échantillon masquerait ensuite sa vraie provenance.
            return self._construire(self._lire(RAW_DIR, "csv"), ecrire_cache=True)

        if (SAMPLE_DIR / "olist_orders_dataset.parquet").exists():
            self.source = "echantillon"
            logger.info("Source des donnees : echantillon versionne (%s)", SAMPLE_DIR)
            return self._construire(self._lire(SAMPLE_DIR, "parquet"), ecrire_cache=False)

        raise FileNotFoundError(
            "Aucune source de donnees trouvee. Attendu l'un de :\n"
            f"  - {PROCESSED_DIR}/orders_enriched.parquet\n"
            f"  - {RAW_DIR}/olist_orders_dataset.csv (via `python scripts/download_data.py`)\n"
            f"  - {SAMPLE_DIR}/olist_orders_dataset.parquet (via `python scripts/build_sample.py`)"
        )

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def _lire(self, dossier: Path, extension: str) -> dict[str, pd.DataFrame]:
        lire = pd.read_csv if extension == "csv" else pd.read_parquet
        return {nom: lire(dossier / f"{nom}.{extension}") for nom in TABLES}

    def _charger_geo(self) -> pd.DataFrame:
        path = PROCESSED_DIR / "geo.parquet"
        if path.exists():
            return pd.read_parquet(path)

        for dossier, extension in ((RAW_DIR, "csv"), (SAMPLE_DIR, "parquet")):
            fichier = dossier / f"olist_geolocation_dataset.{extension}"
            if fichier.exists():
                brut = pd.read_csv(fichier) if extension == "csv" else pd.read_parquet(fichier)
                return self._normaliser_geo(brut)

        # La géolocalisation n'alimente aucun tool : mieux vaut une table vide
        # qu'un chargement qui échoue tout entier.
        logger.warning("Table de geolocalisation introuvable ; table vide utilisee.")
        return pd.DataFrame(columns=["zip_code", "lat", "lng", "city", "state"])

    @staticmethod
    def _normaliser_geo(brut: pd.DataFrame) -> pd.DataFrame:
        brut = brut.copy()
        brut.columns = ["zip_code", "lat", "lng", "city", "state"]
        return brut.drop_duplicates("zip_code")

    # ------------------------------------------------------------------
    # Assemblage
    # ------------------------------------------------------------------

    def _construire(
        self, tables: dict[str, pd.DataFrame], *, ecrire_cache: bool
    ) -> dict[str, pd.DataFrame]:
        orders = tables["olist_orders_dataset"]
        items = tables["olist_order_items_dataset"]
        payments = tables["olist_order_payments_dataset"]
        customers = tables["olist_customers_dataset"]
        products = tables["olist_products_dataset"]
        sellers = tables["olist_sellers_dataset"]

        # `orders.customer_id` identifie une commande, `customer_unique_id` identifie
        # une personne. Confondre les deux ferait de chaque commande un client
        # distinct, et la RFM comme le churn n'auraient plus de sens.
        customers_slim = customers[
            [
                "customer_id",
                "customer_unique_id",
                "customer_zip_code_prefix",
                "customer_city",
                "customer_state",
            ]
        ].copy()

        pay_agg = (
            payments.groupby("order_id")
            .agg(order_value=("payment_value", "sum"), payment_type=("payment_type", "first"))
            .reset_index()
        )

        orders_enriched = (
            orders.merge(items, on="order_id", how="left")
            .merge(pay_agg, on="order_id", how="left")
            .merge(customers_slim, on="customer_id", how="left")
            .merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
            .merge(sellers[["seller_id", "seller_city", "seller_state"]], on="seller_id", how="left")
        )
        orders_enriched = orders_enriched.rename(columns={"customer_unique_id": "customer_uid"})
        orders_enriched["purchase_date"] = pd.to_datetime(
            orders_enriched["order_purchase_timestamp"]
        )

        # `orders_enriched` porte une ligne par *article*, alors que `order_value`
        # est un montant par *commande* : agréger directement dessus compterait
        # une commande de trois articles trois fois. Le surcomptage mesuré était
        # de 26 % sur le chiffre d'affaires, et il se propageait au monétaire de
        # la RFM comme au CLV. On repasse donc au grain commande avant d'agréger.
        par_commande = orders_enriched.drop_duplicates("order_id")

        customers_enriched = (
            par_commande.groupby("customer_uid")
            .agg(
                total_orders=("order_id", "nunique"),
                total_revenue=("order_value", "sum"),
                avg_order_value=("order_value", "mean"),
                first_purchase=("purchase_date", "min"),
                last_purchase=("purchase_date", "max"),
                customer_city=("customer_city", "first"),
                customer_state=("customer_state", "first"),
            )
            .reset_index()
            .rename(columns={"customer_uid": "customer_id"})
        )

        geo = self._normaliser_geo(tables["olist_geolocation_dataset"])

        if ecrire_cache:
            PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
            orders_enriched.to_parquet(PROCESSED_DIR / "orders_enriched.parquet", index=False)
            customers_enriched.to_parquet(PROCESSED_DIR / "customers_enriched.parquet", index=False)
            self._ecrire_schema(orders_enriched, customers_enriched)

        return {
            "orders_enriched": orders_enriched,
            "customers_enriched": customers_enriched,
            "geo": geo,
        }

    def _ecrire_schema(self, orders: pd.DataFrame, customers: pd.DataFrame) -> None:
        schema = {
            "orders_enriched": {col: str(dtype) for col, dtype in orders.dtypes.items()},
            "customers_enriched": {col: str(dtype) for col, dtype in customers.dtypes.items()},
        }
        (PROCESSED_DIR / "schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
