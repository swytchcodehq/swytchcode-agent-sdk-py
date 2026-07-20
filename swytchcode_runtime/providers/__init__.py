"""Providers for integrating Swytchcode tools into various AI frameworks."""

__all__ = [
    "AnthropicProvider",
    "CrewAIProvider",
    "LangGraphProvider",
    "OpenAIAgentsProvider",
    "VercelProvider",
]


def __getattr__(name):
    """Lazy provider imports for backward compatibility."""
    _provider_map = {
        "AnthropicProvider": "anthropic",
        "OpenAIAgentsProvider": "openai_agents",
        "VercelProvider": "vercel",
        "LangGraphProvider": "langgraph",
        "CrewAIProvider": "crewai",
    }
    if name in _provider_map:
        module_name = _provider_map[name]
        import importlib

        mod = importlib.import_module(f".{module_name}", __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
