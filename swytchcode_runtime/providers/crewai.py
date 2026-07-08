"""CrewAI provider: neutral tools -> BaseTool subclasses."""

from __future__ import annotations
from .base import Provider, Tool


class CrewAIProvider(Provider):
    def format_tool(self, tool: Tool):
        from crewai.tools import BaseTool
        from ..schema import to_pydantic_model

        args_schema_cls = to_pydantic_model(tool.input_schema, tool.name + "Schema")

        class DynamicCrewTool(BaseTool):
            name: str = tool.name
            description: str = tool.description
            args_schema: type = args_schema_cls

            def _run(self, **kwargs):
                return tool.execute(kwargs)

        return DynamicCrewTool()
