# CRM Intelligence Agent

> A conversational AI agent that analyses 100k+ e-commerce orders and answers business questions in natural language — powered by OpenAI function calling and scikit-learn.

---

## Demo

*[Add demo GIF here — record 4 exchanges: RFM, churn, SQL, multi-turn]*

---

## What it does

- **Ask in natural language** — "Who are my best customers?" or "Which clients are at risk of churning?"
- **Agent picks the right analysis** — RFM segmentation, churn prediction, KMeans clustering, CLV estimation, or ad-hoc SQL
- **Automatic visualisations** — Plotly charts generated and displayed alongside each response
- **Multi-turn memory** — follow-up questions build on previous analyses

---

## Architecture

```
User (browser)
    ↓
Streamlit UI
    ↓
CRMAgent (OpenAI function calling — GPT-4o)
    ├── compute_rfm      → RFM segmentation (pandas)
    ├── predict_churn    → Churn scoring (RandomForest)
    ├── run_kmeans       → Behavioral clustering (KMeans)
    ├── compute_clv      → Customer Lifetime Value
    ├── sql_query        → Ad-hoc SQL (DuckDB)
    └── get_data_summary → Dataset overview
    ↓
Plotly charts + text response → Streamlit UI
```

---

## Available tools

| Tool | What it does | Example question |
|---|---|---|
| `compute_rfm` | RFM segmentation (Champions, Loyal, At Risk, Lost) | "Segment my customers by value" |
| `predict_churn` | Rank customers by churn probability | "Which customers might leave?" |
| `run_kmeans` | Behavioral clustering | "Group customers by purchase behavior" |
| `compute_clv` | 12-month CLV estimation | "Who are my highest-value customers?" |
| `sql_query` | DuckDB SELECT queries | "Total revenue by Brazilian state" |
| `get_data_summary` | Dataset overview | "Describe the data" |
| `list_capabilities` | What the agent can/cannot do | "What can you analyse?" |

---

## Quick Start

### 1. Installation

```bash
git clone <repo-url>
cd 02_CRM_Agent
pip install -r requirements.txt
```

### 2. Données Olist (première fois uniquement)

```bash
# Option A — téléchargement automatique via Kaggle API
KAGGLE_API_TOKEN=<votre_token>  python scripts/download_data.py
python scripts/preprocess.py

# Option B — téléchargement manuel
# 1. Télécharger le ZIP sur https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
# 2. Extraire les 8 CSV dans data/raw/
# 3. Lancer : python scripts/preprocess.py
```

> Le preprocessing génère les fichiers `data/processed/` (parquet). À ne faire qu'une seule fois.

### 3. Lancer le dashboard

**Windows (PowerShell) :**
```powershell
$env:PYTHONPATH = "."
$env:OPENAI_API_KEY = "sk-..."   # ou saisir la clé directement dans la sidebar
streamlit run app/main.py
```

**macOS / Linux :**
```bash
PYTHONPATH=. OPENAI_API_KEY=sk-... streamlit run app/main.py
```

**Ou via fichier `.env` :**
```bash
cp .env.example .env      # éditer le fichier et renseigner OPENAI_API_KEY
PYTHONPATH=. streamlit run app/main.py
```

L'app est accessible sur **http://localhost:8501**

> La clé OpenAI peut aussi être saisie directement dans la barre latérale de l'interface,  
> sans configurer de variable d'environnement.

---

## Dataset

**Olist Brazilian E-Commerce** — [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)  
~100k orders | 96k customers | 8 tables | Brazil, 2016-2018 | Public domain

---

## Technical highlights

- **OpenAI function calling** with multi-step reasoning (max 5 tool iterations per turn)
- **Stateless tool design** — each tool is a typed Python class implementing `BaseTool`
- **DuckDB** for in-process SQL on pandas DataFrames (no server required)
- **scikit-learn** RandomForest churn model trained at runtime on engineered features
- **Streamlit session state** pattern for persistent agent memory across UI reruns
- **Output size control** — all tool results hard-truncated at 2000 chars before injection into context

---

## Project structure

```
02_CRM_Agent/
├── app/          # Streamlit UI
├── core/         # Agent loop, data loader, config
├── tools/        # 7 OpenAI function-calling tools
├── analytics/    # Pure pandas/sklearn logic (testable without LLM)
├── docs/         # Data dictionary, tool schemas, demo script
├── tests/        # pytest suite (no OpenAI calls needed)
└── scripts/      # Data download and preprocessing
```

---

## Skills demonstrated

- LLM orchestration with function calling (OpenAI SDK)
- CRM analytics: RFM, churn modelling, segmentation, CLV (Dior & Galeries Lafayette experience)
- Machine learning pipeline with scikit-learn
- Interactive data application with Streamlit
- DuckDB for lightweight SQL analytics
- Clean Python architecture (typed interfaces, separation of concerns)
