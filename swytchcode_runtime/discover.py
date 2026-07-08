"""Find tools by intent and read their schemas."""

from __future__ import annotations
from .cli import run_cli


def search(intent: str, *, top: int = 5) -> list[dict]:
    res = run_cli(["discover", intent, "--top", str(top)]) or {}
    return res.get("capabilities", [])


def info(canonical_id: str) -> dict:
    try:
        result = run_cli(["info", canonical_id]) or {}
        # CLI returns a JSON array of ToolInfo objects; unwrap the first one
        if isinstance(result, list):
            return result[0] if result else {}
        return result
    except Exception as e:
        print(
            f"Warning: Failed to fetch info for {canonical_id} ({e}). Using empty schema."
        )
        return {"canonical_id": canonical_id, "inputs": {}}
