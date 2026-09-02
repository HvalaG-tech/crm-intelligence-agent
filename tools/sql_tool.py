"""Tool: sql_query — SQL en lecture seule sur les données CRM, via DuckDB.

Cet outil est le seul à exécuter du texte produit par un modèle de langage, sur
une application publique. Il est donc traité comme une surface d'attaque, pas
comme une commodité.

La version précédente refusait une liste de mots-clés **en début de requête**.
Cinq contournements passaient : les instructions multiples (``SELECT 1; CREATE …``),
un commentaire en tête (``/*x*/ CREATE …``), les requêtes commençant par ``WITH``,
``PRAGMA``, et surtout ``read_parquet()`` / ``read_csv()``, qui donnent un accès
de lecture arbitraire au disque du serveur.

Deux barrières indépendantes le remplacent :

1. **Le moteur.** Les DataFrames sont matérialisés en tables DuckDB, la source
   pandas est désenregistrée, puis ``enable_external_access`` passe à faux et la
   configuration est verrouillée. À partir de là, DuckDB refuse lui-même l'accès
   au disque, au réseau et au chargement d'extensions — y compris si le garde-fou
   syntaxique laissait passer quelque chose.
2. **La syntaxe.** Une liste blanche : une seule instruction, commençant par
   ``SELECT`` ou ``WITH``, sans jeton interdit. C'est la barrière qui produit un
   message d'erreur exploitable par l'agent, là où le moteur ne rendrait qu'une
   exception de permission.

La première barrière est celle qui protège ; la seconde est celle qui explique.
"""

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from analytics.plots import auto_bar_chart
from tools.base import BaseTool

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path("data/processed/schema.json")

# Seuls verbes autorisés en tête d'instruction.
DEBUTS_AUTORISES = ("SELECT", "WITH")

# Jetons interdits où qu'ils se trouvent. La barrière moteur les bloque déjà :
# cette liste sert à rendre un refus explicite plutôt qu'une PermissionException.
JETONS_INTERDITS = (
    "ATTACH", "DETACH", "COPY", "INSTALL", "LOAD", "PRAGMA", "EXPORT", "IMPORT",
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "REPLACE",
    "CALL", "SET", "RESET", "GRANT", "REVOKE", "CHECKPOINT", "VACUUM", "ANALYZE",
    "READ_CSV", "READ_CSV_AUTO", "READ_PARQUET", "READ_JSON", "READ_JSON_AUTO",
    "READ_TEXT", "READ_BLOB", "GLOB", "SNIFF_CSV",
)

LIMITE_PAR_DEFAUT = 200
TIMEOUT_SECONDES = 15


def _sans_commentaires_ni_chaines(sql: str) -> str:
    """Neutralise commentaires et littéraux avant analyse.

    Sans cette étape, ``/*x*/ DROP …`` échappe au contrôle du verbe initial, et
    ``SELECT 'drop'`` déclencherait un faux positif.
    """
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    sql = re.sub(r'"(?:[^"]|"")*"', '""', sql)
    return sql


def valider(query: str) -> str | None:
    """Rend un message d'erreur si la requête est refusée, sinon ``None``."""
    nu = _sans_commentaires_ni_chaines(query).strip()

    if not nu:
        return "Error: empty query."

    # Une seule instruction. Le point-virgule final est toléré.
    if ";" in nu.rstrip().rstrip(";"):
        return "Error: only one statement is allowed. Remove the ';'."

    majuscules = nu.upper()

    if not majuscules.lstrip("( ").startswith(DEBUTS_AUTORISES):
        return "Error: only SELECT and WITH queries are allowed."

    for jeton in JETONS_INTERDITS:
        if re.search(rf"\b{jeton}\b", majuscules):
            return f"Error: '{jeton}' is not allowed in a read-only query."

    return None


def _avec_limite(query: str) -> str:
    """Ajoute une limite si la requête n'en porte pas.

    Une agrégation oubliée peut rendre des centaines de milliers de lignes : ni
    l'affichage ni le contexte du modèle ne les absorberaient.
    """
    nu = _sans_commentaires_ni_chaines(query).upper()
    if re.search(r"\bLIMIT\b", nu):
        return query
    return f"{query.rstrip().rstrip(';')} LIMIT {LIMITE_PAR_DEFAUT}"


class SQLTool(BaseTool):
    name = "sql_query"
    description = (
        "Run a read-only SQL SELECT query on the CRM dataset (DuckDB dialect). "
        "Use for ad-hoc counts, sums, aggregations, and breakdowns not covered by other tools. "
        "Tables available: orders_enriched, customers_enriched. "
        "Only a single SELECT or WITH statement is accepted; no DDL, no file access."
    )

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._conn = duckdb.connect()

        # Matérialiser puis désenregistrer : une fois l'accès externe coupé, les
        # scans de remplacement pandas ne fonctionneraient plus. Les tables, si.
        for table_name, df in data.items():
            if isinstance(df, pd.DataFrame):
                self._conn.register(f"_src_{table_name}", df)
                self._conn.execute(
                    f'CREATE TABLE "{table_name}" AS SELECT * FROM "_src_{table_name}"'
                )
                self._conn.unregister(f"_src_{table_name}")

        # Verrouillage du moteur. Après ces deux lignes, DuckDB refuse de lui-même
        # le disque, le réseau et les extensions, et la configuration ne peut plus
        # être rouverte depuis une requête.
        self._conn.execute("SET enable_external_access=false")
        self._conn.execute("SET lock_configuration=true")

        schema_text = ""
        if SCHEMA_PATH.exists():
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            lines = ["Available tables and columns:"]
            for tbl, cols in schema.items():
                lines.append(f"\n{tbl}:")
                for col, dtype in cols.items():
                    lines.append(f"  - {col} ({dtype})")
            schema_text = "\n".join(lines)
        self._schema_text = schema_text

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description
                + (f"\n\nSchema reference:\n{self._schema_text}" if self._schema_text else ""),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A single DuckDB SELECT or WITH statement.",
                        }
                    },
                    "required": ["query"],
                },
            },
        }

    def run(self, query: str) -> tuple[str, Any]:
        refus = valider(query)
        if refus is not None:
            return refus, None

        # DuckDB n'expose pas de délai maximum : on l'interrompt depuis un timer.
        # Sans cela, une jointure croisée mal formée bloquerait le serveur.
        chien_de_garde = threading.Timer(TIMEOUT_SECONDES, self._conn.interrupt)
        chien_de_garde.start()
        try:
            result = self._conn.execute(_avec_limite(query)).df()
        except Exception as exc:
            # Message court et exploitable par l'agent, sans trace interne.
            logger.info("Requete SQL refusee ou en echec : %s", exc)
            premiere_ligne = str(exc).strip().splitlines()[0][:200]
            return f"Error: SQL execution failed — {premiere_ligne}", None
        finally:
            chien_de_garde.cancel()

        if result.empty:
            return "The query returned no results.", None

        row_count = len(result)
        display = result.head(50)
        summary = f"Query returned {row_count} rows.\n\n{display.to_string(index=False)}"

        fig = None
        if 2 <= len(result.columns) <= 3 and row_count <= 30:
            fig = auto_bar_chart(result)

        return summary, fig
