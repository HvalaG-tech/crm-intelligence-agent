"""Le fichier de questions de référence doit rester valide.

La suite d'évaluation demande une clé OpenAI et ne tourne donc pas en intégration
continue. Sa partie vérifiable sans appel — les outils cités existent-ils, les
questions hors périmètre sont-elles bien marquées — l'est ici : un outil renommé
sans mise à jour du fichier casserait l'évaluation silencieusement, et on ne s'en
apercevrait qu'au moment de produire le chiffre pour le README.
"""

import pandas as pd
import pytest

yaml = pytest.importorskip("yaml", reason="pyyaml est une dépendance de développement")

from eval.run_eval import CHEMIN_QUESTIONS, valider_fichier  # noqa: E402
from tools import get_all_tools  # noqa: E402


@pytest.fixture
def noms_outils(sample_data) -> set[str]:
    donnees = dict(sample_data)
    donnees.setdefault("geo", pd.DataFrame(columns=["zip_code"]))
    return {t.name for t in get_all_tools(donnees)}


def test_fichier_questions_valide(noms_outils):
    questions = yaml.safe_load(CHEMIN_QUESTIONS.read_text(encoding="utf-8"))["questions"]
    assert valider_fichier(questions, noms_outils) == []


def test_couverture_des_outils(noms_outils):
    """Les sept outils doivent être couverts : une suite qui en oublie un ment."""
    questions = yaml.safe_load(CHEMIN_QUESTIONS.read_text(encoding="utf-8"))["questions"]
    cites = {nom for q in questions for nom in q.get("tool_attendu", [])}
    assert noms_outils <= cites, f"outils jamais évalués : {noms_outils - cites}"


def test_presence_de_cas_hors_perimetre():
    """Un agent qui ne sait pas dire non ne se met pas devant un métier."""
    questions = yaml.safe_load(CHEMIN_QUESTIONS.read_text(encoding="utf-8"))["questions"]
    assert sum(1 for q in questions if q.get("hors_perimetre")) >= 3
