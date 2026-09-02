"""Tool: list_capabilities — describes what the agent can and cannot do."""

from typing import Any

from tools.base import BaseTool

CAPABILITIES_TEXT = """
## Ce que l'agent CRM peut faire

**Analyses disponibles :**
- Segmentation RFM (meilleurs clients, clients dormants, clients à fort potentiel)
- Prédiction de churn (clients à risque de départ)
- Clustering comportemental KMeans (groupes de clients par profil d'achat)
- Valeur vie client (CLV / LTV)
- Requêtes SQL ad-hoc : revenus, volumes, répartitions géographiques, par catégorie produit

**Exemples de questions supportées :**
- "Qui sont mes 10 meilleurs clients ?"
- "Quels clients risquent de partir dans les 30 prochains jours ?"
- "Segmente mes clients par comportement d'achat."
- "Quel est le revenu total par état brésilien ?"
- "Montre-moi la valeur vie de mes clients."

**Hors périmètre (non supporté) :**
- Prédiction de revenus futurs
- Analyse de stocks ou gestion logistique
- Recommandation de produits
- Données temps réel (dataset figé 2016-2018)
"""


class CapabilitiesTool(BaseTool):
    name = "list_capabilities"
    description = (
        "List what the agent can and cannot do. Use when the user asks an out-of-scope question "
        "or wants to know what analyses are available."
    )

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }

    def run(self) -> tuple[str, Any]:
        return CAPABILITIES_TEXT.strip(), None
