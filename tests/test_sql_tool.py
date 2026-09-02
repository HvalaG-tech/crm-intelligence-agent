"""Tests de tools/sql_tool.py.

L'outil exécute du texte produit par un modèle de langage sur une application
publique : les cas dangereux comptent autant que les cas nominaux. Chacun des
refus ci-dessous correspond à un contournement qui passait dans la version
antérieure, où le garde-fou ne testait que le premier mot de la requête.
"""

import pytest

from tools.sql_tool import SQLTool, valider

# Huit contournements. Les cinq premiers réussissaient réellement avant le
# correctif — les tables « pirate » étaient créées et read_parquet lisait le
# disque du serveur.
REQUETES_DANGEREUSES = [
    ("instructions multiples", "SELECT 1; CREATE TABLE pirate AS SELECT 1"),
    ("commentaire en tete", "/* ruse */ CREATE TABLE pirate AS SELECT 1"),
    ("commentaire ligne", "-- ruse\nDROP TABLE orders_enriched"),
    ("lecture disque parquet", "SELECT * FROM read_parquet('/etc/passwd')"),
    ("lecture disque csv", "SELECT * FROM read_csv_auto('secrets.csv')"),
    ("ecriture disque", "COPY (SELECT 1) TO 'sortie.csv'"),
    ("chargement extension", "INSTALL httpfs"),
    ("introspection moteur", "PRAGMA database_list"),
    ("attachement base", "ATTACH 'autre.db' AS autre"),
    ("reouverture config", "SET enable_external_access=true"),
    ("ecriture apres CTE", "WITH x AS (SELECT 1) INSERT INTO orders_enriched SELECT * FROM x"),
]

REQUETES_LEGITIMES = [
    ("select simple", "SELECT COUNT(*) AS n FROM orders_enriched"),
    ("cte", "WITH t AS (SELECT customer_state, COUNT(*) c FROM orders_enriched GROUP BY 1) SELECT * FROM t"),
    ("select parenthese", "(SELECT 1 AS n)"),
    ("point virgule final tolere", "SELECT COUNT(*) AS n FROM orders_enriched;"),
]


@pytest.mark.parametrize("nom, requete", REQUETES_DANGEREUSES, ids=[n for n, _ in REQUETES_DANGEREUSES])
def test_requetes_dangereuses_refusees(sample_data, nom, requete):
    tool = SQLTool(sample_data)
    resultat, figure = tool.run(requete)
    assert resultat.startswith("Error:"), f"{nom} n'a pas ete bloque : {resultat[:120]}"
    assert figure is None


@pytest.mark.parametrize("nom, requete", REQUETES_LEGITIMES, ids=[n for n, _ in REQUETES_LEGITIMES])
def test_requetes_legitimes_acceptees(sample_data, nom, requete):
    assert valider(requete) is None, f"{nom} a ete refuse a tort"


def test_sql_select(sample_data):
    tool = SQLTool(sample_data)
    result, _ = tool.run("SELECT COUNT(*) AS n FROM orders_enriched")
    assert "100" in result


def test_sql_invalid_query(sample_data):
    tool = SQLTool(sample_data)
    result, _ = tool.run("SELECT nonexistent_column FROM orders_enriched")
    assert result.startswith("Error:")


def test_moteur_verrouille_meme_si_la_syntaxe_passait(sample_data):
    """Deuxième barrière : le moteur refuse le disque de lui-même.

    On contourne volontairement le validateur pour éprouver la connexion seule.
    Si cette assertion tombe, c'est que le verrouillage DuckDB a été perdu.
    """
    tool = SQLTool(sample_data)
    with pytest.raises(Exception):
        tool._conn.execute("SELECT * FROM read_parquet('data/samples/olist_orders_dataset.parquet')")


def test_limite_ajoutee_par_defaut(sample_data):
    """Une requête sans LIMIT ne doit pas pouvoir rendre toute la table."""
    tool = SQLTool(sample_data)
    result, _ = tool.run("SELECT order_id FROM orders_enriched")
    # 100 lignes en fixture, limite par defaut a 200 : tout passe, mais la
    # requete executee porte bien une limite.
    assert "Query returned" in result


def test_aucune_table_pirate_apres_les_essais(sample_data):
    """Non-régression : aucune des tentatives ne doit avoir écrit dans la base."""
    tool = SQLTool(sample_data)
    for _, requete in REQUETES_DANGEREUSES:
        tool.run(requete)
    tables, _ = tool.run("SELECT table_name FROM duckdb_tables()")
    assert "pirate" not in tables
