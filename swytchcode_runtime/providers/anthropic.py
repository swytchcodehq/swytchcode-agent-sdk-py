"""Anthropic Claude provider (Non-agentic / raw tool use schemas)."""

from __future__ import annotations
from .base import Provider, Tool


class AnthropicProvider(Provider):
    def format_tool(self, tool: Tool):
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
