"""Évaluation du routage des outils.

Ce que le script mesure : sur une question donnée, l'agent appelle-t-il l'outil
attendu ? C'est la part du comportement que ce dépôt maîtrise, via le prompt
système et les descriptions d'outils. La qualité de la rédaction finale, elle,
dépend du modèle et se déplace à chaque version : la chiffrer donnerait un
nombre qui bouge sans qu'aucune ligne du dépôt n'ait changé.

Trois cas sont distingués :

- **routage attendu** : l'un des outils de ``tool_attendu`` a été appelé ;
- **hors périmètre** : aucun outil ne doit être appelé, l'agent doit décliner ;
- **assertion de contenu** : ``doit_contenir`` est cherché dans le résultat de
  l'outil, jamais dans la prose du modèle.

Usage, depuis n'importe quel répertoire :
    python -m eval.run_eval                 # exécution complète, nécessite OPENAI_API_KEY
    python -m eval.run_eval --dry-run       # valide le fichier de questions, sans appel
    python -m eval.run_eval --limit 5       # les cinq premières questions

La forme ``-m`` exige d'être lancée depuis la racine du dépôt, faute de quoi
Python ne trouve pas le paquet ``eval``. ``python eval/run_eval.py`` fonctionne
depuis n'importe où.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# core/loader.py résout ses chemins de données relativement au répertoire
# courant. Sans ce changement de répertoire, lancer l'évaluation depuis
# ailleurs que la racine trouverait bien le code, mais aucune donnée.
os.chdir(RACINE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import yaml  # noqa: E402

from core.agent import CRMAgent, ErreurAgent  # noqa: E402
from core.loader import OlistLoader  # noqa: E402
from tools import get_all_tools  # noqa: E402

CHEMIN_QUESTIONS = Path(__file__).parent / "questions.yaml"


def charger_questions() -> list[dict]:
    donnees = yaml.safe_load(CHEMIN_QUESTIONS.read_text(encoding="utf-8"))
    questions = donnees.get("questions", [])
    if not questions:
        sys.exit(f"Aucune question dans {CHEMIN_QUESTIONS}")
    return questions


def valider_fichier(questions: list[dict], noms_outils: set[str]) -> list[str]:
    """Contrôle le fichier sans rien appeler : utilisable en intégration continue."""
    problemes = []
    for i, q in enumerate(questions, 1):
        if "question" not in q:
            problemes.append(f"question {i} : champ 'question' manquant")
        attendus = q.get("tool_attendu", [])
        if not isinstance(attendus, list):
            problemes.append(f"question {i} : 'tool_attendu' doit être une liste")
            continue
        for nom in attendus:
            if nom not in noms_outils:
                problemes.append(f"question {i} : outil inconnu '{nom}'")
        if not attendus and not q.get("hors_perimetre"):
            problemes.append(
                f"question {i} : liste d'outils vide sans 'hors_perimetre: true'"
            )
    return problemes


def evaluer_une(agent: CRMAgent, cas: dict) -> dict:
    agent.reset()
    question = cas["question"]
    attendus = cas.get("tool_attendu", [])
    hors_perimetre = bool(cas.get("hors_perimetre"))

    try:
        agent.chat(question)
    except ErreurAgent as exc:
        return {"question": question, "appeles": [], "ok": False, "motif": str(exc)[:60]}

    appeles = [e["tool"] for e in agent.dernieres_etapes]

    if hors_perimetre:
        ok = not appeles
        motif = "" if ok else f"a appelé {', '.join(appeles)} au lieu de décliner"
    elif not appeles:
        ok, motif = False, "aucun outil appelé"
    else:
        ok = any(nom in attendus for nom in appeles)
        motif = "" if ok else f"attendu {'/'.join(attendus)}"

    if ok and (attendu_texte := cas.get("doit_contenir")):
        resultats = " ".join(e["resultat"] for e in agent.dernieres_etapes)
        if attendu_texte.lower() not in resultats.lower():
            ok, motif = False, f"'{attendu_texte}' absent du résultat"

    return {"question": question, "appeles": appeles, "ok": ok, "motif": motif}


def main() -> int:
    parseur = argparse.ArgumentParser(description="Évaluation du routage des outils.")
    parseur.add_argument("--dry-run", action="store_true", help="valide le fichier sans appeler le modèle")
    parseur.add_argument("--limit", type=int, default=0, help="n'évaluer que les N premières questions")
    args = parseur.parse_args()

    questions = charger_questions()
    if args.limit:
        questions = questions[: args.limit]

    loader = OlistLoader()
    data = loader.load_all()
    tools = get_all_tools(data)
    noms_outils = {t.name for t in tools}

    problemes = valider_fichier(questions, noms_outils)
    if problemes:
        print("Fichier de questions invalide :")
        for p in problemes:
            print(f"  - {p}")
        return 1

    if args.dry_run:
        print(f"{len(questions)} questions valides ({loader.source}). Aucun appel effectué.")
        return 0

    if not os.getenv("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY absente. Posez-la dans l'environnement, ou lancez\n"
            "  python -m eval.run_eval --dry-run\n"
            "pour valider le fichier de questions sans appeler le modèle."
        )
        return 1

    agent = CRMAgent(tools=tools)
    print(f"Source des données : {loader.source} · {len(questions)} questions\n")

    largeur = 62
    print(f"{'Question':<{largeur}} {'Outil appelé':<20} OK")
    print("-" * (largeur + 26))

    resultats = []
    for cas in questions:
        r = evaluer_une(agent, cas)
        resultats.append(r)
        appeles = ", ".join(r["appeles"]) or "(aucun)"
        marque = "oui" if r["ok"] else "NON"
        print(f"{r['question'][:largeur]:<{largeur}} {appeles[:20]:<20} {marque}")
        if not r["ok"] and r["motif"]:
            print(f"{'':<{largeur}} -> {r['motif']}")

    reussis = sum(1 for r in resultats if r["ok"])
    taux = reussis / len(resultats) * 100
    print("-" * (largeur + 26))
    print(f"\nTaux de reussite du routage : {reussis}/{len(resultats)} ({taux:.0f} %)")

    # Code de sortie non nul sous 80 % : utilisable comme garde-fou en CI.
    return 0 if taux >= 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
