"""LangGraph provider: neutral tools -> LangChain StructuredTool objects."""

from __future__ import annotations
from .base import Provider, Tool


class LangGraphProvider(Provider):
    def format_tool(self, tool: Tool):
        from langchain_core.tools import StructuredTool
        from ..schema import to_pydantic_model

        return StructuredTool.from_function(
            name=tool.name,
            description=tool.description,
            func=lambda **kwargs: tool.execute(kwargs),
            args_schema=to_pydantic_model(tool.input_schema, tool.name + "Schema"),
        )
