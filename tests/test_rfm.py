"""Tests for analytics/rfm.py."""

from analytics.rfm import compute_rfm, format_rfm_summary


def test_compute_rfm_shape(sample_orders):
    rfm = compute_rfm(sample_orders)
    assert "customer_id" in rfm.columns
    assert "segment" in rfm.columns
    # Une ligne par *personne*, donc par customer_uid. Grouper sur customer_id
    # rendrait 100 lignes ici, une par commande.
    assert len(rfm) == sample_orders["customer_uid"].nunique()


def test_rfm_frequency_compte_les_commandes_par_personne(sample_orders):
    """Non-régression : la dimension F doit mesurer quelque chose.

    `customer_id` est réattribué à chaque commande chez Olist. Un groupement
    dessus faisait de chaque commande un client distinct, et la fréquence valait
    1 pour tout le monde : le F de la RFM ne discriminait plus rien.
    """
    rfm = compute_rfm(sample_orders)
    attendu = sample_orders.groupby("customer_uid")["order_id"].nunique()

    assert rfm["frequency"].min() > 1, "la frequence est degeneree a 1"
    assert rfm.set_index("customer_id")["frequency"].sort_index().equals(
        attendu.sort_index().rename("frequency").rename_axis("customer_id")
    )


def test_rfm_monetaire_ne_surcompte_pas_les_articles(sample_orders):
    """Le monétaire agrège des commandes, pas des lignes d'articles.

    `order_value` est un montant par commande : sommer la table au grain article
    comptait une commande de trois articles trois fois.
    """
    doublons = sample_orders.copy()
    doublons = doublons.loc[doublons.index.repeat(3)]  # 3 articles par commande

    assert compute_rfm(doublons)["monetary"].sum() == compute_rfm(sample_orders)["monetary"].sum()


def test_rfm_scores_range(sample_orders):
    rfm = compute_rfm(sample_orders, n_segments=4)
    for col in ["r_score", "f_score", "m_score"]:
        assert rfm[col].between(1, 4).all(), f"{col} out of [1, 4]"


def test_rfm_segments_are_known_labels(sample_orders):
    rfm = compute_rfm(sample_orders)
    valid = {"Champions", "Loyal Customers", "At Risk", "Lost"}
    assert set(rfm["segment"].unique()).issubset(valid)


def test_format_rfm_summary_under_2000(sample_orders):
    rfm = compute_rfm(sample_orders)
    summary = format_rfm_summary(rfm)
    assert len(summary) <= 2000
    assert "customers" in summary.lower()
