"""Agent CRM — boucle d'outils de style ReAct, via le function calling d'OpenAI."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.txt").read_text(encoding="utf-8")

# Messages rendus au visiteur. Ils disent quoi faire, pas ce qui a techniquement
# échoué : la trace réelle part dans les logs du serveur, pas à l'écran.
MSG_CLE_INVALIDE = (
    "La clé OpenAI fournie a été refusée. Vérifiez qu'elle est complète et toujours "
    "active sur votre compte, puis saisissez-la de nouveau dans la barre latérale."
)
MSG_QUOTA = (
    "Le quota de la clé OpenAI utilisée est épuisé, ou sa limite de débit est atteinte. "
    "Réessayez dans quelques instants, ou utilisez une clé disposant de crédits."
)
MSG_RESEAU = (
    "Le service OpenAI n'a pas répondu à temps. C'est en général passager : "
    "reposez votre question dans un instant."
)
MSG_INATTENDU = (
    "Une erreur inattendue est survenue pendant l'analyse. Elle a été journalisée. "
    "Vous pouvez reformuler votre question ou réinitialiser la conversation."
)
MSG_TROP_ETAPES = (
    "Je n'ai pas réussi à aboutir en {n} étapes d'analyse. Pouvez-vous reformuler votre "
    "question, ou la découper en deux ?"
)


class ErreurAgent(Exception):
    """Erreur destinée à être montrée telle quelle au visiteur."""


class CRMAgent:
    """Agent conversationnel qui route les questions vers les outils analytiques.

    Les figures sont rendues hors bande, jamais injectées dans les messages de la
    conversation : le contexte reste propre et ne se remplit pas de JSON Plotly.
    """

    def __init__(self, tools: list, api_key: str | None = None) -> None:
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.openai_model
        self.tools_by_name = {t.name: t for t in tools}
        self.tool_schemas = [t.schema for t in tools]
        self.conversation: list[dict] = []
        # Journal du dernier tour : alimente l'encart « Comment j'ai obtenu ce
        # résultat » de l'interface.
        self.dernieres_etapes: list[dict] = []

    def chat(
        self,
        user_message: str,
        on_progress: Callable[[str, dict], None] | None = None,
    ) -> tuple[str, list[Any]]:
        """Traite un tour de conversation.

        Args:
            user_message: la question du visiteur.
            on_progress: rappel optionnel, appelé avec (nom_du_tool, arguments)
                juste avant chaque exécution d'outil. Sert à afficher le
                raisonnement en direct.

        Returns:
            Le couple (texte de la réponse, figures Plotly).

        Raises:
            ErreurAgent: message déjà formulé pour le visiteur.
        """
        self.conversation.append({"role": "user", "content": user_message})
        self.dernieres_etapes = []
        figures: list[Any] = []

        for _ in range(settings.max_tool_iterations):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._context_window()
            msg = self._appeler_modele(messages)

            if not msg.tool_calls:
                self.conversation.append({"role": "assistant", "content": msg.content})
                return msg.content or "", figures

            self.conversation.append(msg.model_dump(exclude_none=True))

            error_occurred = False
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    # Le modèle a produit des arguments illisibles : on le lui dit
                    # plutôt que de lever, il sait se corriger au tour suivant.
                    logger.warning("Arguments illisibles pour '%s'", tool_name)
                    self.conversation.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": "Error: arguments JSON invalides",
                        }
                    )
                    error_occurred = True
                    continue

                if on_progress is not None:
                    on_progress(tool_name, args)

                debut = time.perf_counter()
                result, fig = self._execute_tool(tool_name, args)
                duree = time.perf_counter() - debut

                self.dernieres_etapes.append(
                    {
                        "tool": tool_name,
                        "args": args,
                        "resultat": result,
                        "duree_s": round(duree, 2),
                    }
                )

                if fig is not None:
                    figures.append(fig)

                self.conversation.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )

                if result.startswith("Error:") or result.startswith("Tool '"):
                    error_occurred = True

            if error_occurred:
                # Éviter la cascade : orienter le modèle vers une explication.
                self.conversation.append(
                    {
                        "role": "user",
                        "content": (
                            "[System] A tool returned an error. "
                            "Explain the limitation clearly to the user. Do not retry."
                        ),
                    }
                )

        logger.warning("Agent reached max iterations (%d)", settings.max_tool_iterations)
        fallback = MSG_TROP_ETAPES.format(n=settings.max_tool_iterations)
        self.conversation.append({"role": "assistant", "content": fallback})
        return fallback, figures

    def reset(self) -> None:
        self.conversation.clear()
        self.dernieres_etapes = []

    # ------------------------------------------------------------------
    # Interne
    # ------------------------------------------------------------------

    def _appeler_modele(self, messages: list[dict]):
        """Appelle le modèle en traduisant chaque panne en message lisible."""
        try:
            reponse = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_schemas,
                tool_choice="auto",
            )
            return reponse.choices[0].message
        except AuthenticationError as exc:
            logger.warning("Cle OpenAI refusee : %s", exc)
            raise ErreurAgent(MSG_CLE_INVALIDE) from exc
        except PermissionDeniedError as exc:
            logger.warning("Acces refuse au modele %s : %s", self.model, exc)
            raise ErreurAgent(
                f"La clé fournie n'a pas accès au modèle « {self.model} »."
            ) from exc
        except RateLimitError as exc:
            logger.warning("Quota ou debit depasse : %s", exc)
            raise ErreurAgent(MSG_QUOTA) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning("Probleme reseau vers OpenAI : %s", exc)
            raise ErreurAgent(MSG_RESEAU) from exc
        except Exception as exc:
            logger.exception("Erreur inattendue lors de l'appel au modele")
            raise ErreurAgent(MSG_INATTENDU) from exc

    def _execute_tool(self, name: str, args: dict) -> tuple[str, Any]:
        tool = self.tools_by_name.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'", None
        try:
            result, fig = tool.run(**args)
            if len(result) > 2000:
                result = result[:1900] + "\n[...tronqué]"
            return result, fig
        except Exception as exc:
            logger.exception("Tool '%s' raised an exception", name)
            return f"Tool '{name}' failed: {type(exc).__name__}: {exc}", None

    def _context_window(self) -> list[dict]:
        """Rend les messages récents tenant dans le budget de contexte (heuristique)."""
        budget = settings.max_conversation_tokens * 4  # ~4 caractères par token
        window: list[dict] = []
        for msg in reversed(self.conversation):
            content = msg.get("content") or ""
            if isinstance(content, list):
                content = str(content)
            budget -= len(content)
            if budget < 0:
                break
            window.append(msg)
        return list(reversed(window))
