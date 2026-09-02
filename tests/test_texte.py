"""Non-régression sur l'échappement des montants.

Le bug d'origine : « pour 2 436 149 R$ de chiffre d'affaires et un panier moyen
de 157 R$ » s'affichait avec tout le milieu de phrase en italique mathématique,
Streamlit ayant lu les deux « $ » comme les bornes d'une formule LaTeX.
"""

from core.texte import texte_md


def test_un_montant_isole_est_echappe():
    assert texte_md("157 R$") == r"157 R\$"


def test_deux_montants_ne_forment_plus_une_formule():
    """Le cas réel : c'est la paire de dollars qui déclenchait le rendu LaTeX."""
    phrase = "pour 2 436 149 R$ de chiffre d'affaires et un panier moyen de 157 R$."
    rendu = texte_md(phrase)
    assert rendu.count(r"\$") == 2
    # Plus aucun « $ » non précédé d'une barre oblique inverse.
    assert "$" not in rendu.replace(r"\$", "")


def test_le_texte_sans_montant_est_intact():
    phrase = "Les Champions pèsent 2,5 fois les clients *At Risk*."
    assert texte_md(phrase) == phrase


def test_les_tableaux_markdown_restent_valides():
    ligne = "| beleza_saude | 189 548 R$ | 1 495 |"
    assert texte_md(ligne) == r"| beleza_saude | 189 548 R\$ | 1 495 |"
