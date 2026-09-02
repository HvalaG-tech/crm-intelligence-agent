"""Préparation du texte avant affichage."""


def texte_md(brut: str) -> str:
    """Neutralise les dollars avant un rendu markdown Streamlit.

    Streamlit interprète ``$...$`` comme du LaTeX. Or toutes les sommes de ce jeu
    de données sont en réaux brésiliens, notés « R$ » : la première occurrence
    ouvre une formule, la seconde la ferme, et toute la phrase entre les deux part
    en italique mathématique.

    Le défaut touche aussi bien les réponses pré-enregistrées du mode démonstration
    que celles rédigées par le modèle, qui écrit « R$ » de lui-même. On échappe donc
    au rendu plutôt que dans les sources : le texte stocké reste lisible, et rien
    n'oblige le modèle à connaître cette contrainte d'affichage.

    Aucune formule LaTeX n'est attendue dans les réponses ; échapper tous les
    dollars est donc sans effet de bord ici.
    """
    return brut.replace("$", r"\$")
