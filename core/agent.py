"""CRM Agent — ReAct-style tool loop using OpenAI function calling."""

import json
import logging
from pathlib import Path
from typing import Any

from openai import OpenAI

from core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.txt").read_text(encoding="utf-8")


class CRMAgent:
    """Conversational agent that routes user questions to analytical tools.

    Figures are returned out-of-band (not injected into conversation messages)
    to keep the context window clean.
    """

    def __init__(self, tools: list, api_key: str | None = None) -> None:
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.openai_model
        self.tools_by_name = {t.name: t for t in tools}
        self.tool_schemas = [t.schema for t in tools]
        self.conversation: list[dict] = []

    def chat(self, user_message: str) -> tuple[str, list[Any]]:
        """Process one user turn. Returns (text_response, list_of_plotly_figures)."""
        self.conversation.append({"role": "user", "content": user_message})
        figures: list[Any] = []

        for iteration in range(settings.max_tool_iterations):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._context_window()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_schemas,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                self.conversation.append({"role": "assistant", "content": msg.content})
                return msg.content or "", figures

            # Append assistant message with tool_calls
            self.conversation.append(msg.model_dump(exclude_none=True))

            error_occurred = False
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                args = json.loads(tc.function.arguments)
                result, fig = self._execute_tool(tool_name, args)

                if fig is not None:
                    figures.append(fig)

                self.conversation.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )

                if result.startswith("Error:") or result.startswith("Tool '"):
                    error_occurred = True

            if error_occurred:
                # Prevent cascade: steer the model toward an explanatory response
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
        fallback = "J'ai atteint le nombre maximum d'étapes de raisonnement. Pouvez-vous reformuler votre question ?"
        self.conversation.append({"role": "assistant", "content": fallback})
        return fallback, figures

    def reset(self) -> None:
        self.conversation.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
        """Return recent messages that fit within the token budget (heuristic)."""
        budget = settings.max_conversation_tokens * 4  # ~4 chars per token
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
