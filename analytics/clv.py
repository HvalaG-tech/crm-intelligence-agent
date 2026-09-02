"""Estimation de la valeur vie client (CLV) sur 12 mois.

Modèle volontairement simple, mais pas naïf. La difficulté sur une place de
marché comme Olist est que **~90 % des clients n'achètent qu'une fois** : leur
fréquence d'achat individuelle est indéfinie, pas nulle.

Une première version extrapolait la fréquence de chaque client depuis son propre
historique, avec une ancienneté plancherisée à un mois. Pour un client à commande
unique, l'ancienneté vaut zéro jour, donc un mois après plancher, donc un rythme
apparent d'une commande par mois : son CLV valait douze fois son unique panier.
Le classement des « meilleurs clients » se remplissait alors d'acheteurs uniques
à gros panier, soit exactement l'inverse de ce qu'un CLV doit désigner, et le
total projeté valait douze fois le chiffre d'affaires réel.

Le modèle retenu sépare donc les deux populations :

- **Client à commandes multiples** : sa fréquence observée est réelle, on la
  reconduit. L'ancienneté est plancherisée à 30 jours, pas à un mois symbolique.
- **Client à commande unique** : on ne peut rien lire dans son historique. On lui
  applique l'espérance de la population — la probabilité de réachat observée,
  multipliée par la fréquence moyenne de ceux qui réachètent.

Le CLV rendu est la somme de la valeur déjà réalisée et de la valeur projetée sur
douze mois. Un client acquis vaut au moins ce qu'il a déjà dépensé.
"""

import pandas as pd

# Ancienneté minimale pour lire une fréquence dans l'historique d'un client.
# En dessous, deux commandes rapprochées produiraient un rythme aberrant.
ANCIENNETE_PLANCHER_JOURS = 30

HORIZON_MOIS = 12


def compute_clv(customers: pd.DataFrame) -> pd.DataFrame:
    """Estime le CLV à 12 mois de chaque client.

    Args:
        customers: DataFrame ``customers_enriched``.

    Returns:
        Le DataFrame enrichi de ``clv_estimated``, ``clv_future`` et
        ``freq_mensuelle``, trié par CLV décroissant.
    """
    df = customers.copy()

    anciennete_jours = (df["last_purchase"] - df["first_purchase"]).dt.days
    repeteurs = df["total_orders"] >= 2

    # --- Fréquence des clients qui ont réachété -------------------------------
    anciennete_mois = (anciennete_jours.clip(lower=ANCIENNETE_PLANCHER_JOURS) / 30.0)
    freq_observee = df["total_orders"] / anciennete_mois

    # --- Espérance appliquée aux clients à commande unique --------------------
    # Probabilité qu'un client de cette base réachète, et à quel rythme il le fait.
    taux_reachat = float(repeteurs.mean())
    freq_moyenne_repeteurs = float(freq_observee[repeteurs].mean()) if repeteurs.any() else 0.0
    freq_attendue_unique = taux_reachat * freq_moyenne_repeteurs

    df["freq_mensuelle"] = freq_observee.where(repeteurs, freq_attendue_unique)

    # --- Projection -----------------------------------------------------------
    df["clv_future"] = df["freq_mensuelle"] * df["avg_order_value"] * HORIZON_MOIS

    # Un client acquis vaut au moins ce qu'il a déjà dépensé : le CLV additionne
    # le réalisé et le projeté, il ne remplace pas l'un par l'autre.
    df["clv_estimated"] = df["total_revenue"] + df["clv_future"]

    return df.sort_values("clv_estimated", ascending=False)


def format_clv_summary(clv_df: pd.DataFrame, top_n: int = 15) -> str:
    total_clv = clv_df["clv_estimated"].sum()
    total_realise = clv_df["total_revenue"].sum()
    total_futur = clv_df["clv_future"].sum()
    repeteurs = int((clv_df["total_orders"] >= 2).sum())

    top = clv_df.head(top_n)[
        ["customer_id", "clv_estimated", "total_revenue", "total_orders"]
    ]
    top_pct = top["clv_estimated"].sum() / total_clv * 100 if total_clv else 0.0

    lines = [
        f"CLV Analysis — {len(clv_df):,} customers:",
        f"  Realised revenue to date: R$ {total_realise:,.0f}",
        f"  Projected {HORIZON_MOIS}-month value: R$ {total_futur:,.0f}",
        f"  Total CLV (realised + projected): R$ {total_clv:,.0f}",
        f"  Repeat buyers: {repeteurs:,} ({repeteurs / len(clv_df) * 100:.1f}%)",
        f"  Top {top_n} customers represent {top_pct:.1f}% of total CLV",
        f"\nTop {top_n} customers by CLV:",
        top.to_string(index=False, float_format=lambda x: f"{x:,.0f}"),
    ]
    return "\n".join(lines)
