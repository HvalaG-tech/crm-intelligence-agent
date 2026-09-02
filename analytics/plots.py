"""Construction des figures Plotly — une seule identité visuelle pour tout le projet.

Trois décisions gouvernent ce module.

**Les segments sont ordonnés, pas nominaux.** Les segments RFM vont de Champions à
Lost, et les clusters KMeans sont numérotés par chiffre d'affaires décroissant :
dans les deux cas l'ordre porte du sens. Ils sont donc peints avec une *rampe
séquentielle à une teinte*, du clair au foncé, et non avec une palette
catégorielle. C'est l'encodage juste, et il évite au passage la limite des
palettes catégorielles, qui ne garantissent la lisibilité de toutes les paires
que jusqu'à trois séries — au-delà, deux couleurs finissent par se ressembler
pour un daltonien comme pour tout le monde.

**La couleur ne redouble jamais la longueur.** Sur les barres de churn et de CLV,
la longueur porte déjà la grandeur : les colorer par la même variable
n'ajouterait rien et coûterait une échelle à lire. Une seule teinte suffit.

**Le thème est choisi, pas inversé.** Les paliers sombres ne sont pas les paliers
clairs retournés : ce sont des paliers choisis pour le fond sombre, chacun validé
contre sa propre surface.

Les rampes ci-dessous ont été validées : monotonie de luminosité, écart entre
paliers, contraste de l'extrémité claire contre la surface, teinte unique.
"""


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --------------------------------------------------------------------------
# Jetons de couleur
# --------------------------------------------------------------------------

# Rampe ordinale bleue, quatre paliers, du moins au plus fort.
RAMPE_CLAIR = ["#86b6ef", "#3987e5", "#256abf", "#104281"]
RAMPE_SOMBRE = ["#cde2fb", "#86b6ef", "#3987e5", "#184f95"]

# Teinte unique, pour les graphiques où la longueur porte déjà la grandeur.
UNIE_CLAIR = "#2a78d6"
UNIE_SOMBRE = "#3987e5"

CHROME = {
    False: {  # thème clair
        "encre": "#0b0b0b",
        "encre_2": "#52514e",
        "muet": "#898781",
        "grille": "#e1e0d9",
        "axe": "#c3c2b7",
        "rampe": RAMPE_CLAIR,
        "unie": UNIE_CLAIR,
    },
    True: {  # thème sombre
        "encre": "#ffffff",
        "encre_2": "#c3c2b7",
        "muet": "#898781",
        "grille": "#2c2c2a",
        "axe": "#383835",
        "rampe": RAMPE_SOMBRE,
        "unie": UNIE_SOMBRE,
    },
}

# Le module ne dépend pas de Streamlit : l'application pose le thème une fois au
# démarrage, les outils continuent d'appeler les fonctions sans rien savoir.
_SOMBRE = False


def definir_theme(sombre: bool) -> None:
    """Fixe le thème utilisé par toutes les figures construites ensuite."""
    global _SOMBRE
    _SOMBRE = bool(sombre)


def _jetons() -> dict:
    return CHROME[_SOMBRE]


def _rampe_pour(n: int) -> list[str]:
    """Rend n couleurs prises dans la rampe, en conservant les extrêmes."""
    rampe = _jetons()["rampe"]
    if n <= 1:
        return [rampe[-2]]
    if n <= len(rampe):
        # Étaler sur toute l'amplitude plutôt que prendre les n premiers paliers :
        # deux segments doivent se distinguer autant que quatre.
        pas = (len(rampe) - 1) / (n - 1)
        return [rampe[round(i * pas)] for i in range(n)]
    # Au-delà de la rampe, on interpole plutôt que de recycler des teintes.
    return px.colors.sample_colorscale(
        px.colors.make_colorscale(rampe), [i / (n - 1) for i in range(n)]
    )


def _habiller(fig: go.Figure, titre: str, x: str, y: str) -> go.Figure:
    """Applique la charte commune : fonds transparents, grille discrète, survol.

    Les fonds sont transparents pour que la figure prenne celui de la page :
    une surface peinte en dur trahirait le thème dès que l'utilisateur bascule.
    """
    j = _jetons()
    fig.update_layout(
        # Le titre est ancré haut et la légende posée sous lui : à marge serrée,
        # les deux se chevauchaient.
        title={
            "text": titre,
            "font": {"size": 16, "color": j["encre"]},
            "x": 0,
            "xanchor": "left",
            "y": 0.97,
            "yanchor": "top",
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": 'system-ui, -apple-system, "Segoe UI", sans-serif', "color": j["encre_2"]},
        margin={"l": 10, "r": 10, "t": 92, "b": 10},
        hoverlabel={"font_size": 12},
        legend={
            "title": "",
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.04,
            "x": 0,
            "font": {"color": j["encre_2"]},
        },
    )
    commun = {
        "title_font": {"size": 12, "color": j["muet"]},
        "tickfont": {"size": 11, "color": j["muet"]},
        "linecolor": j["axe"],
        "zeroline": False,
    }
    # Grille horizontale seulement : des lignes verticales sous des barres
    # ajoutent du bruit sans aider à lire une valeur.
    fig.update_xaxes(title_text=x, showgrid=False, **commun)
    fig.update_yaxes(title_text=y, showgrid=True, gridcolor=j["grille"], gridwidth=1, **commun)
    return fig


def _arrondir_barres(fig: go.Figure) -> go.Figure:
    """Extrémités de barres arrondies, si la version de Plotly le permet."""
    try:
        fig.update_traces(marker_cornerradius=4)
    except Exception:
        pass
    return fig


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------

ORDRE_RFM = ["Champions", "Loyal Customers", "At Risk", "Lost"]


def plot_rfm_scatter(rfm: pd.DataFrame) -> go.Figure:
    """Nuage récence/montant, taille = fréquence, couleur = segment ordonné."""
    presents = [s for s in ORDRE_RFM if s in set(rfm["segment"])]
    couleurs = dict(zip(presents, reversed(_rampe_pour(len(presents)))))

    fig = px.scatter(
        rfm,
        x="recency_days",
        y="monetary",
        size="frequency",
        color="segment",
        category_orders={"segment": presents},
        color_discrete_map=couleurs,
        hover_data={"customer_id": True, "rfm_score": True, "frequency": True},
        custom_data=["customer_id"],
    )
    # Anneau de surface sur des marques qui se recouvrent : sans lui, un amas
    # dense devient une tache uniforme.
    # Des dizaines de milliers de clients se superposent : sans transparence, la
    # zone dense devient un aplat où l'on ne lit plus ni densité ni segment.
    # L'anneau de surface est conservé mais aminci, sinon il domine la marque.
    fig.update_traces(
        marker={
            "opacity": 0.6,
            "line": {"width": 0.5, "color": "rgba(255,255,255,0.45)"},
            "sizemin": 4,
        },
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Récence : %{x} jours<br>"
            "Montant cumulé : R$ %{y:,.0f}<extra></extra>"
        ),
    )
    return _habiller(
        fig,
        "Segmentation RFM — récence, montant et fréquence",
        "Récence (jours depuis le dernier achat)",
        "Montant cumulé (R$)",
    )


def plot_churn_risk(scored: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Barres horizontales : le chiffre d'affaires à risque, client par client.

    Le premier dessin classait les clients par score de départ. Il était illisible :
    le modèle sature à 1,00 sur tous les clients franchement inactifs, si bien que
    les vingt barres avaient la même longueur et que le graphique ne disait rien.

    La question à laquelle un responsable CRM veut une réponse n'est d'ailleurs pas
    « qui a le plus haut score », puisqu'ils sont des milliers à égalité, mais
    « lesquels rappeler en premier ». On classe donc les clients à risque par le
    chiffre d'affaires qu'ils ont déjà apporté : c'est lui qui est en jeu.
    """
    a_risque = scored[scored["churn_score"] >= 0.5]
    if a_risque.empty:  # aucun client au-dessus du seuil : on garde le haut du panier
        a_risque = scored

    top = a_risque.nlargest(top_n, "total_revenue").copy()
    top["label"] = top["customer_id"].astype(str).str[:10] + "…"

    fig = px.bar(
        top,
        x="total_revenue",
        y="label",
        orientation="h",
        custom_data=["customer_id", "recency_days", "churn_score"],
    )
    # Teinte unique : la longueur de la barre porte déjà la grandeur.
    fig.update_traces(
        marker_color=_jetons()["unie"],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Chiffre d'affaires à risque : R$ %{x:,.0f}<br>"
            "Inactif depuis : %{customdata[1]} jours<br>"
            "Score de départ : %{customdata[2]:.2f}<extra></extra>"
        ),
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    _habiller(
        fig,
        f"Chiffre d'affaires à risque — les {top_n} clients à rappeler en priorité",
        "Chiffre d'affaires déjà réalisé (R$)",
        "Client",
    )
    fig.update_xaxes(showgrid=True, gridcolor=_jetons()["grille"])
    fig.update_yaxes(showgrid=False)
    return _arrondir_barres(fig)


def plot_segments_scatter(segmented: pd.DataFrame) -> go.Figure:
    """Nuage commandes/chiffre d'affaires, couleur = segment classé par valeur."""
    presents = sorted(set(segmented["cluster_label"]))
    couleurs = dict(zip(presents, reversed(_rampe_pour(len(presents)))))

    fig = px.scatter(
        segmented,
        x="total_orders",
        y="total_revenue",
        color="cluster_label",
        category_orders={"cluster_label": presents},
        color_discrete_map=couleurs,
        custom_data=["customer_id", "avg_order_value"],
    )
    fig.update_traces(
        marker={"size": 9, "opacity": 0.65, "line": {"width": 0.5, "color": "rgba(255,255,255,0.45)"}},
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Commandes : %{x}<br>"
            "Chiffre d'affaires : R$ %{y:,.0f}<br>"
            "Panier moyen : R$ %{customdata[1]:,.0f}<extra></extra>"
        ),
    )
    return _habiller(
        fig,
        "Segments comportementaux (KMeans), classés par valeur",
        "Nombre de commandes",
        "Chiffre d'affaires cumulé (R$)",
    )


def plot_clv_bar(clv_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Barres horizontales : les n clients à plus forte valeur vie estimée."""
    top = clv_df.head(top_n).copy()
    top["label"] = top["customer_id"].astype(str).str[:10] + "…"

    fig = px.bar(
        top,
        x="clv_estimated",
        y="label",
        orientation="h",
        custom_data=["customer_id", "total_revenue", "total_orders"],
    )
    fig.update_traces(
        marker_color=_jetons()["unie"],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Valeur vie estimée : R$ %{x:,.0f}<br>"
            "Déjà dépensé : R$ %{customdata[1]:,.0f}<br>"
            "Commandes : %{customdata[2]}<extra></extra>"
        ),
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    _habiller(
        fig,
        f"Les {top_n} clients à plus forte valeur vie (12 mois)",
        "Valeur vie estimée (R$)",
        "Client",
    )
    fig.update_yaxes(showgrid=False)
    return _arrondir_barres(fig)


def auto_bar_chart(df: pd.DataFrame) -> go.Figure | None:
    """Barres pour un résultat SQL à deux colonnes : un libellé, une valeur."""
    if len(df.columns) < 2:
        return None
    try:
        libelle, valeur = df.columns[0], df.columns[1]
        if not pd.api.types.is_numeric_dtype(df[valeur]):
            return None

        fig = px.bar(df, x=libelle, y=valeur)
        fig.update_traces(
            marker_color=_jetons()["unie"],
            hovertemplate=f"<b>%{{x}}</b><br>{valeur} : %{{y:,.0f}}<extra></extra>",
        )
        # Le titre reprend les noms de colonnes de la requête : c'est le seul
        # libellé disponible, et il dit exactement ce qui est tracé.
        _habiller(fig, f"{valeur} par {libelle}", str(libelle), str(valeur))
        fig.update_xaxes(tickangle=-30)
        return _arrondir_barres(fig)
    except Exception:
        return None
