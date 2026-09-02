"""Mode démonstration — répondre sans appeler le modèle.

La démonstration est publique : sans garde-fou, chaque visiteur consommerait des
appels facturés sur la clé du propriétaire, et une page partagée sur LinkedIn
peut vider un budget en une soirée.

Le parti pris est de ne figer que **la narration**. Les outils listés dans
``data/demo_answers.json`` sont réellement exécutés à l'affichage : les tableaux
et les graphiques sont calculés sur les données du dépôt. Une réponse de
démonstration n'est donc pas une capture d'écran, c'est le vrai calcul avec un
commentaire pré-écrit. Ce qui est économisé, c'est uniquement le passage par le
modèle — la seule partie payante.

Une question libre, elle, sort du script : elle exige que le visiteur fournisse
sa propre clé.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHEMIN_REPONSES = Path("data/demo_answers.json")


@dataclass
class ReponseDemo:
    """Une réponse de démonstration, narration figée et figures recalculées."""

    texte: str
    figures: list[Any] = field(default_factory=list)
    etapes: list[dict] = field(default_factory=list)


def _normaliser(question: str) -> str:
    """Compare des questions sans se laisser arrêter par la forme.

    Le visiteur clique un bouton dans la quasi-totalité des cas, mais il peut
    aussi recopier la question à la main. On ramène donc casse, accents,
    apostrophes, traits d'union et ponctuation finale à une forme unique :
    « Donne-moi une vue d'ensemble. » et « donne moi une vue d ensemble »
    doivent tomber sur la même entrée.
    """
    sans_accent = "".join(
        c for c in unicodedata.normalize("NFD", question) if unicodedata.category(c) != "Mn"
    )
    lettres = [c if c.isalnum() else " " for c in sans_accent.lower()]
    return " ".join("".join(lettres).split())


class Demonstration:
    """Sert les réponses pré-enregistrées et exécute leurs outils."""

    def __init__(self, chemin: Path = CHEMIN_REPONSES) -> None:
        self._entrees: dict[str, dict] = {}
        self.questions: list[str] = []

        if not chemin.exists():
            logger.warning("Fichier de demonstration absent (%s) ; mode demo inactif.", chemin)
            return

        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        for entree in donnees.get("questions", []):
            self._entrees[_normaliser(entree["question"])] = entree
            self.questions.append(entree["question"])

    def __bool__(self) -> bool:
        return bool(self._entrees)

    def connait(self, question: str) -> bool:
        return _normaliser(question) in self._entrees

    def repondre(self, question: str, tools: list) -> ReponseDemo | None:
        """Rend la réponse pré-enregistrée, figures recalculées sur les données.

        Args:
            question: la question posée par le visiteur.
            tools: les tools initialisés sur les données chargées.

        Returns:
            La réponse, ou ``None`` si la question n'est pas au programme.
        """
        entree = self._entrees.get(_normaliser(question))
        if entree is None:
            return None

        par_nom = {t.name: t for t in tools}
        figures: list[Any] = []
        etapes: list[dict] = []

        for etape in entree.get("etapes", []):
            outil = par_nom.get(etape["tool"])
            if outil is None:
                logger.warning("Tool '%s' inconnu, etape ignoree.", etape["tool"])
                continue
            try:
                resultat, figure = outil.run(**etape.get("args", {}))
            except Exception:
                # Une démonstration ne doit jamais tomber en panne devant un
                # visiteur : on perd la figure, on garde la narration.
                logger.exception("Tool '%s' a echoue en mode demonstration.", etape["tool"])
                continue

            etapes.append(
                {"tool": etape["tool"], "args": etape.get("args", {}), "resultat": resultat}
            )
            if figure is not None:
                figures.append(figure)

        return ReponseDemo(texte=entree["reponse"], figures=figures, etapes=etapes)
