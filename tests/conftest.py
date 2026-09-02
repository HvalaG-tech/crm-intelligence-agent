"""Fixtures partagées.

La fixture reproduit fidèlement le schéma d'Olist sur un point qui compte :
``customer_id`` est **réattribué à chaque commande**, tandis que ``customer_uid``
identifie la personne. Une fixture qui n'exposerait que ``customer_id`` laisserait
passer un groupement erroné dans la RFM, où chaque commande deviendrait un client
distinct et la fréquence vaudrait 1 pour tout le monde.

Vingt clients passent ici cinq commandes chacun : la fréquence est donc une
grandeur réellement testable.
"""

import pandas as pd
import pytest

NB_COMMANDES = 100
NB_CLIENTS = 20


@pytest.fixture
def sample_orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": [f"ord_{i}" for i in range(NB_COMMANDES)],
            # Un identifiant de commande, unique par ligne, comme chez Olist.
            "customer_id": [f"custorder_{i}" for i in range(NB_COMMANDES)],
            # L'identifiant de personne : 20 clients, 5 commandes chacun.
            "customer_uid": [f"cust_{i % NB_CLIENTS}" for i in range(NB_COMMANDES)],
            "purchase_date": pd.date_range("2023-01-01", periods=NB_COMMANDES, freq="3D"),
            "order_value": [50.0 + i * 10 for i in range(NB_COMMANDES)],
            "order_status": ["delivered"] * NB_COMMANDES,
            "customer_state": (["SP", "RJ", "MG"] * 34)[:NB_COMMANDES],
            "product_category_name": (["electronics", "fashion", "home"] * 34)[:NB_COMMANDES],
        }
    )


@pytest.fixture
def sample_customers(sample_orders) -> pd.DataFrame:
    """Agrégat par personne, avec ``customer_id`` portant la clé personne.

    C'est la convention de ``customers_enriched`` : le loader y renomme
    ``customer_uid`` en ``customer_id`` une fois l'agrégation faite.
    """
    return (
        sample_orders.groupby("customer_uid")
        .agg(
            total_orders=("order_id", "count"),
            total_revenue=("order_value", "sum"),
            avg_order_value=("order_value", "mean"),
            first_purchase=("purchase_date", "min"),
            last_purchase=("purchase_date", "max"),
            customer_state=("customer_state", "first"),
        )
        .reset_index()
        .rename(columns={"customer_uid": "customer_id"})
    )


@pytest.fixture
def sample_data(sample_orders, sample_customers) -> dict:
    return {"orders_enriched": sample_orders, "customers_enriched": sample_customers}
