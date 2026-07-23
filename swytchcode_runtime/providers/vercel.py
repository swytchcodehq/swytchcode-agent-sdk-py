"""Vercel AI SDK provider (Python equivalent)."""

from __future__ import annotations
from .base import Provider, Tool


class VercelProvider(Provider):
    def format_tool(self, tool: Tool):
        try:
            from ai_sdk import tool as vercel_tool
        except ImportError:
            raise ImportError(
                "Please install the Vercel AI SDK (requires Python 3.12+): pip install ai-sdk-python"
            )

        # The handler MUST be synchronous. ai_sdk's sync generate_text() calls the
        # tool handler without awaiting it, so an async handler is silently never
        # awaited - the tool never runs and the model hallucinates success. A sync
        # handler returns a plain value that works in generate_text AND is fine for
        # the async Tool.run path (which only awaits awaitables). Called as
        # handler(**kwargs) - arguments by field name, never a positional dict.
        def _execute(**kwargs):
            return tool.execute(kwargs)

        return vercel_tool(
            name=tool.name,
            description=tool.description,
            parameters=tool.input_schema,
            execute=_execute,
        )
