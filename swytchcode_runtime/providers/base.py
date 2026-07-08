"""Provider base for adapting neutral Swytchcode tools to each framework.

A single Provider base: `format_tool` wraps one neutral Tool into a framework's
native tool object, and `format_tools` maps over a list. Execution is carried on
the Tool itself via its `execute` closure (which runs the Swytchcode CLI): agentic
frameworks (OpenAI Agents, Vercel, LangGraph, CrewAI) invoke that closure directly
during their own loop, while non-agentic APIs (Anthropic) run it through
`Swytchcode.handle_tool_calls`. Note this is deliberately NOT Composio's two-class
agentic/non-agentic split — execution lives on the tool, not an injected function.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    canonical_id: str
    name: str
    description: str
    input_schema: dict
    execute: Callable[[dict], Any]


class Provider:
    def format_tool(self, tool: Tool) -> Any:
        raise NotImplementedError

    def format_tools(self, tools: list[Tool]) -> list[Any]:
        return [self.format_tool(t) for t in tools]
