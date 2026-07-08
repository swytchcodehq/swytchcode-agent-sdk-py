"""Management commands wrapper for the SDK."""

from __future__ import annotations
from .cli import run_cli


def add(library_or_url: str) -> dict:
    return run_cli(["add", library_or_url]) or {}


def list_tools(filter_arg: str = "") -> dict:
    args = ["list", "--json"]
    if filter_arg:
        args.insert(1, filter_arg)
    return run_cli(args) or {}


def keys() -> list[dict]:
    return run_cli(["key", "list"]) or []


def policies() -> list[dict]:
    return run_cli(["policy", "list"]) or []


def search(keyword: str = "") -> dict:
    args = ["search", "--json"]
    if keyword:
        args.insert(1, keyword)
    return run_cli(args) or {}
