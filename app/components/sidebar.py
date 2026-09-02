"""Sidebar component — API key input and settings."""

import os

import streamlit as st


def render_sidebar() -> str | None:
    """Render sidebar and return the active OpenAI API key (or None if missing)."""
    with st.sidebar:
        st.title("⚙️ Configuration")

        # Env var takes priority (set before launching the app)
        env_key = os.getenv("OPENAI_API_KEY", "")

        # Text input — Streamlit manages its own widget state via key="api_key_input"
        typed_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            key="api_key_input",
            help="Your key is never stored — it lives only in this session.",
        )

        active_key = env_key or typed_key

        # If the typed key changed, force agent recreation
        if typed_key and typed_key != st.session_state.get("_last_api_key"):
            st.session_state.pop("agent", None)
            st.session_state["_last_api_key"] = typed_key

        if active_key:
            st.success("API key loaded ✓")
        else:
            st.warning("Entrez votre clé OpenAI pour utiliser l'agent.")

        st.divider()
        st.markdown("### About")
        st.markdown(
            "This agent analyses **Olist e-commerce data** (Brazil, 2016-2018, ~100k orders) "
            "using OpenAI function calling + scikit-learn."
        )

        if st.button("🗑️ Reset complet (session + cache)", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Clear @st.cache_data and @st.cache_resource
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

    return active_key or None
