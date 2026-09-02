"""CRM Intelligence Agent — Streamlit entry point."""

import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from app.components.sidebar import render_sidebar
from app.components.metrics import render_kpi_cards
from core.loader import OlistLoader
from core.agent import CRMAgent
from tools import get_all_tools

st.set_page_config(
    page_title="CRM Intelligence Agent",
    page_icon="🧠",
    layout="wide",
)

# ------------------------------------------------------------------
# Sidebar (API key, settings, clear button)
# ------------------------------------------------------------------
api_key = render_sidebar()

# ------------------------------------------------------------------
# Data loading (cached — survives Streamlit reruns)
# ------------------------------------------------------------------
@st.cache_data(show_spinner="Loading Olist dataset…")
def load_data() -> dict:
    return OlistLoader().load_all()

# ------------------------------------------------------------------
# Page header
# ------------------------------------------------------------------
st.title("🧠 CRM Intelligence Agent")
st.caption("Ask questions about your customers in natural language — powered by OpenAI function calling.")

# ------------------------------------------------------------------
# KPI cards
# ------------------------------------------------------------------
try:
    data = load_data()
    render_kpi_cards(data)
except Exception as exc:
    st.warning(f"Could not load dataset: {exc}. Make sure `data/raw/` contains the Olist CSV files.")
    data = None

st.divider()

# ------------------------------------------------------------------
# Example questions (quick-start buttons)
# ------------------------------------------------------------------
EXAMPLE_QUESTIONS = [
    "Qui sont mes meilleurs clients ?",
    "Quels clients risquent de partir ?",
    "Montre le revenu total par état brésilien.",
    "Segmente mes clients par comportement.",
]

st.markdown("**Questions d'exemple :**")
cols = st.columns(len(EXAMPLE_QUESTIONS))
for col, question in zip(cols, EXAMPLE_QUESTIONS):
    if col.button(question, use_container_width=True):
        st.session_state["prefill"] = question

# ------------------------------------------------------------------
# Agent initialisation (persisted in session state)
# ------------------------------------------------------------------
if data and api_key:
    if "agent" not in st.session_state:
        st.session_state.agent = CRMAgent(tools=get_all_tools(data), api_key=api_key)
else:
    st.session_state.pop("agent", None)

if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------------------------------------------------------
# Chat history
# ------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for fig in msg.get("figures", []):
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# Chat input
# ------------------------------------------------------------------
prefill = st.session_state.pop("prefill", None)
prompt = st.chat_input("Posez votre question sur vos clients…") or prefill

if prompt:
    if "agent" not in st.session_state:
        st.error("Veuillez fournir une clé API OpenAI dans la barre latérale.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt, "figures": []})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyse en cours…"):
                response, figures = st.session_state.agent.chat(prompt)
            st.markdown(response)
            for fig in figures:
                st.plotly_chart(fig, use_container_width=True)

        st.session_state.messages.append(
            {"role": "assistant", "content": response, "figures": figures}
        )
