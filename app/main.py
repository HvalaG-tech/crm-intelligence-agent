"""Agent d'analyse CRM — point d'entrée Streamlit."""

import os
import sys

# Autoriser les imports depuis la racine du projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from app.components.metrics import render_kpi_cards
from app.components.sidebar import render_sidebar
from core.agent import CRMAgent, ErreurAgent
from core.config import settings
from core.demo import Demonstration
from core.loader import OlistLoader
from tools import get_all_tools

st.set_page_config(
    page_title="Agent d'analyse CRM",
    page_icon="📊",
    layout="wide",
)

# Libellés parlants pour la trace de raisonnement : le visiteur lit ce que
# l'agent fait, pas le nom interne de la fonction appelée.
LIBELLES_OUTILS = {
    "compute_rfm": "Je segmente les clients en RFM",
    "predict_churn": "Je score le risque de départ",
    "run_kmeans": "Je regroupe les clients par comportement",
    "sql_query": "J'interroge les données en SQL",
    "get_data_summary": "Je fais le tour de la base",
    "compute_clv": "J'estime la valeur vie client",
    "list_capabilities": "Je liste ce que je sais faire",
}


# ------------------------------------------------------------------
# Données (mises en cache — survivent aux réexécutions de Streamlit)
# ------------------------------------------------------------------
@st.cache_resource(show_spinner="Chargement des données…")
def charger_donnees() -> tuple[dict, str]:
    loader = OlistLoader()
    return loader.load_all(), loader.source


@st.cache_resource
def charger_demonstration() -> Demonstration:
    return Demonstration()


try:
    data, source_donnees = charger_donnees()
except Exception as exc:  # noqa: BLE001 — on veut une page utilisable quoi qu'il arrive
    data, source_donnees = None, "inconnue"
    st.error(
        "Les données n'ont pas pu être chargées. Sur une installation locale, lancez "
        "`python scripts/download_data.py` puis `python scripts/build_sample.py`."
    )
    st.caption(f"Détail technique : {type(exc).__name__}")

demo = charger_demonstration()
api_key = render_sidebar(source_donnees)

# ------------------------------------------------------------------
# En-tête — la valeur métier d'abord, la technique ensuite
# ------------------------------------------------------------------
st.title("Agent d'analyse CRM")
st.markdown(
    "**Vos équipes marketing obtiennent leurs analyses clients sans passer par la data team.** "
    "Posez une question en français : segmentation RFM, risque de départ, valeur vie client, "
    "ou requête libre sur les données."
)

if data is not None:
    render_kpi_cards(data)

st.divider()

# ------------------------------------------------------------------
# Parcours de démonstration — l'ordre raconte une histoire :
# vue d'ensemble, segmentation, risque, requête libre, question de suivi
# (qui prouve la mémoire), puis une demande hors périmètre (qui prouve
# que l'agent connaît ses limites).
# ------------------------------------------------------------------
if demo and settings.demo_mode:
    st.markdown("**Parcours de démonstration** — réponse immédiate, sans clé et sans coût :")
    for ligne in (demo.questions[:3], demo.questions[3:]):
        for col, question in zip(st.columns(len(ligne)), ligne):
            if col.button(question, use_container_width=True, key=f"demo_{question[:30]}"):
                st.session_state["question_posee"] = question

if "messages" not in st.session_state:
    st.session_state.messages = []
if "questions_posees" not in st.session_state:
    st.session_state.questions_posees = 0

# ------------------------------------------------------------------
# Historique
# ------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for fig in msg.get("figures", []):
            st.plotly_chart(fig, use_container_width=True)
        if msg.get("etapes"):
            with st.expander("Comment j'ai obtenu ce résultat"):
                for etape in msg["etapes"]:
                    titre = LIBELLES_OUTILS.get(etape["tool"], etape["tool"])
                    duree = f" · {etape['duree_s']} s" if etape.get("duree_s") else ""
                    st.markdown(f"**{titre}**{duree}")
                    if etape.get("args"):
                        st.code(str(etape["args"]), language="python")
                    st.code(etape["resultat"], language="text")

# ------------------------------------------------------------------
# Saisie
# ------------------------------------------------------------------
saisie = st.chat_input("Posez votre question sur vos clients…")
question = saisie or st.session_state.pop("question_posee", None)


def _memoriser(role: str, contenu: str, figures=None, etapes=None) -> None:
    st.session_state.messages.append(
        {"role": role, "content": contenu, "figures": figures or [], "etapes": etapes or []}
    )


if question and data is not None:
    _memoriser("user", question)
    with st.chat_message("user"):
        st.markdown(question)

    tools = get_all_tools(data)
    reponse_demo = demo.repondre(question, tools) if settings.demo_mode else None

    with st.chat_message("assistant"):
        # --- Voie 1 : question du parcours, servie sans appeler le modèle -----
        if reponse_demo is not None:
            st.markdown(reponse_demo.texte)
            for fig in reponse_demo.figures:
                st.plotly_chart(fig, use_container_width=True)
            if reponse_demo.etapes:
                with st.expander("Comment j'ai obtenu ce résultat"):
                    for etape in reponse_demo.etapes:
                        st.markdown(f"**{LIBELLES_OUTILS.get(etape['tool'], etape['tool'])}**")
                        if etape.get("args"):
                            st.code(str(etape["args"]), language="python")
                        st.code(etape["resultat"], language="text")
            _memoriser("assistant", reponse_demo.texte, reponse_demo.figures, reponse_demo.etapes)

        # --- Voie 2 : question libre, il faut une clé ------------------------
        elif not api_key:
            message = (
                "Cette question sort du parcours de démonstration, et y répondre demande "
                "un appel au modèle.\n\n"
                "**Ajoutez votre clé OpenAI dans la barre latérale** pour interroger l'agent "
                "librement, ou choisissez l'une des six questions proposées ci-dessus — "
                "elles répondent immédiatement et gratuitement."
            )
            st.info(message)
            _memoriser("assistant", message)

        elif st.session_state.questions_posees >= settings.max_questions_session:
            message = (
                f"Vous avez atteint la limite de {settings.max_questions_session} questions "
                "libres pour cette session. Réinitialisez la conversation depuis la barre "
                "latérale pour repartir."
            )
            st.warning(message)
            _memoriser("assistant", message)

        else:
            if "agent" not in st.session_state:
                st.session_state.agent = CRMAgent(tools=tools, api_key=api_key)

            agent = st.session_state.agent
            try:
                with st.status("J'analyse votre question…", expanded=True) as statut:

                    def montrer(tool: str, args: dict) -> None:
                        st.write(LIBELLES_OUTILS.get(tool, f"J'appelle `{tool}`") + "…")

                    reponse, figures = agent.chat(question, on_progress=montrer)
                    statut.update(label="Analyse terminée", state="complete", expanded=False)

                st.session_state.questions_posees += 1
                st.markdown(reponse)
                for fig in figures:
                    st.plotly_chart(fig, use_container_width=True)

                etapes = list(agent.dernieres_etapes)
                if etapes:
                    with st.expander("Comment j'ai obtenu ce résultat"):
                        for etape in etapes:
                            titre = LIBELLES_OUTILS.get(etape["tool"], etape["tool"])
                            st.markdown(f"**{titre}** · {etape['duree_s']} s")
                            if etape.get("args"):
                                st.code(str(etape["args"]), language="python")
                            st.code(etape["resultat"], language="text")

                _memoriser("assistant", reponse, figures, etapes)

            except ErreurAgent as exc:
                # Message déjà rédigé pour le visiteur par core/agent.py.
                st.error(str(exc))
                _memoriser("assistant", str(exc))
