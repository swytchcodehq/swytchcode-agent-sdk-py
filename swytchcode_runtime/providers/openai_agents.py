"""OpenAI Agents SDK provider."""

from __future__ import annotations
import asyncio
import json
from .base import Provider, Tool


class OpenAIAgentsProvider(Provider):
    def format_tool(self, tool: Tool):
        try:
            from agents import FunctionTool
        except ImportError:
            raise ImportError(
                "Please install the OpenAI Agents SDK: pip install openai-agents"
            )

        async def _on_invoke(ctx, args: str):
            kwargs = json.loads(args) if args else {}
            # tool.execute drives the CLI through a blocking subprocess; offload
            # it to a worker thread so we never stall the agent's event loop.
            return await asyncio.to_thread(tool.execute, kwargs)

        return FunctionTool(
            name=str(tool.name).replace(".", "_"),
            description=str(tool.description),
            params_json_schema=tool.input_schema,
            on_invoke_tool=_on_invoke,
            strict_json_schema=False,
        )
