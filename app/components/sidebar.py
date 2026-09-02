"""Barre latérale — clé API, état de la source de données, réinitialisation."""

import os

import streamlit as st

from core.config import settings


def render_sidebar(source_donnees: str = "inconnue") -> str | None:
    """Affiche la barre latérale et rend la clé OpenAI active, ou None.

    Args:
        source_donnees: ``cache``, ``complet`` ou ``echantillon``, tel que rapporté
            par le loader. Affiché au visiteur pour qu'il sache sur quoi il
            travaille : une démonstration en ligne tourne sur l'échantillon.
    """
    with st.sidebar:
        st.title("Configuration")

        if settings.demo_mode:
            st.info(
                "**Mode démonstration.** Les six questions proposées répondent "
                "immédiatement, sans clé et sans coût : seul le commentaire est "
                "pré-enregistré, les analyses et les graphiques sont calculés en direct.\n\n"
                "Pour poser vos propres questions, ajoutez votre clé OpenAI ci-dessous."
            )

        # La variable d'environnement prime : elle est posée avant le lancement.
        env_key = os.getenv("OPENAI_API_KEY", "")

        typed_key = st.text_input(
            "Clé API OpenAI",
            type="password",
            placeholder="sk-...",
            key="api_key_input",
            help=(
                "Votre clé n'est ni journalisée ni écrite sur disque. Elle reste en "
                "mémoire, le temps de votre session."
            ),
        )

        active_key = env_key or typed_key

        # Une clé changée doit recréer l'agent, sinon l'ancien client reste actif.
        if typed_key and typed_key != st.session_state.get("_last_api_key"):
            st.session_state.pop("agent", None)
            st.session_state["_last_api_key"] = typed_key

        if active_key:
            restant = settings.max_questions_session - st.session_state.get("questions_posees", 0)
            st.success("Clé chargée. Questions libres activées.")
            st.caption(f"{max(restant, 0)} question(s) libre(s) restante(s) sur cette session.")
        elif not settings.demo_mode:
            st.warning("Saisissez votre clé OpenAI pour utiliser l'agent.")

        st.divider()

        st.markdown("### Les données")
        libelles = {
            "echantillon": (
                "Échantillon public — 15 000 clients, 15 477 commandes, "
                "716 jours. C'est la source utilisée par la démonstration en ligne."
            ),
            "complet": "Jeu Olist complet — ~100 000 commandes, chargé depuis `data/raw/`.",
            "cache": "Cache local — DataFrames déjà assemblés depuis `data/processed/`.",
            "inconnue": "Source non déterminée.",
        }
        st.caption(libelles.get(source_donnees, libelles["inconnue"]))
        st.caption(
            "Jeu de données public **Olist** (place de marché brésilienne, 2016-2018). "
            "Aucune donnée client réelle."
        )

        st.divider()
        if st.button("Réinitialiser la conversation", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

    return active_key or None
