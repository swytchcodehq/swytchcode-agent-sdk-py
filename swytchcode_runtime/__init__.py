"""Thin runtime wrapper around the Swytchcode CLI."""

from .errors import SwytchcodeError, is_swytchcode_error
from .exec import exec_ as exec
from .client import Swytchcode
from .providers import (
    AnthropicProvider,
    OpenAIAgentsProvider,
    VercelProvider,
    LangGraphProvider,
    CrewAIProvider,
)

__all__ = [
    "exec",
    "Swytchcode",
    "SwytchcodeError",
    "is_swytchcode_error",
    "AnthropicProvider",
    "OpenAIAgentsProvider",
    "VercelProvider",
    "LangGraphProvider",
    "CrewAIProvider",
]
