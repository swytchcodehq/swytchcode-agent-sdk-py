"""Thin runtime wrapper around the Swytchcode CLI."""

from .errors import SwytchcodeError, is_swytchcode_error
from .exec import exec_ as exec
from .client import Swytchcode

__all__ = [
    "exec",
    "Swytchcode",
    "SwytchcodeError",
    "is_swytchcode_error",
]


def __getattr__(name):
    """Lazy provider imports for backward compatibility."""
    _provider_map = {
        "AnthropicProvider": ("providers.anthropic", "AnthropicProvider"),
        "OpenAIAgentsProvider": ("providers.openai_agents", "OpenAIAgentsProvider"),
        "VercelProvider": ("providers.vercel", "VercelProvider"),
        "LangGraphProvider": ("providers.langgraph", "LangGraphProvider"),
        "CrewAIProvider": ("providers.crewai", "CrewAIProvider"),
    }
    if name in _provider_map:
        module_path, attr = _provider_map[name]
        import importlib

        mod = importlib.import_module(f".{module_path}", __package__)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
