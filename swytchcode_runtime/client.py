"""High-level agentic client on top of the existing exec()."""

from __future__ import annotations
from typing import Any, Optional

from . import discover as _discover, schema as _schema, manage as _manage
from .exec import exec_ as _exec
from .providers.base import Provider, Tool


def _strip_empty(obj: Any) -> Any:
    """Recursively drop keys whose value is None or an empty string ("").

    With 'expose all fields', agents often fill unused optional fields with "",
    which APIs like Stripe reject ("empty values are an attempt to unset").
    Only None and "" are dropped — 0, False, [], {} are preserved as meaningful.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if v is None or (isinstance(v, str) and v == ""):
                continue
            out[k] = _strip_empty(v)
        return out
    if isinstance(obj, list):
        return [_strip_empty(v) for v in obj]
    return obj


class _Tools:
    def __init__(self, client: "Swytchcode"):
        self._c = client
        # Maps a sanitized tool name (dots -> underscores) back to its canonical
        # ID, populated as tools are built. Used to reverse names in
        # handle_tool_calls without a lossy "_"->"." string replace.
        self._name_to_cid: dict[str, str] = {}

    def get(self, *, toolkits=None, tools=None, search=None):
        neutral = [self._tool(cid) for cid in self._ids(toolkits, tools, search)]
        p = self._c.provider
        return p.format_tools(neutral) if p else neutral

    def execute(self, canonical_id: str, args: dict, **options) -> Any:
        # If args are flat (no body/params top-level keys), wrap them in body
        # as expected by the Swytchcode CLI kernel (like in run-workflow.js)
        if "body" not in args and "params" not in args:
            args = {"body": args}
        # Drop empty optional fields (None/"") from body & params so values an
        # agent over-filled don't reach the API (e.g. Stripe rejects customer="").
        args = dict(args)
        if isinstance(args.get("body"), (dict, list)):
            args["body"] = _strip_empty(args["body"])
        if isinstance(args.get("params"), (dict, list)):
            args["params"] = _strip_empty(args["params"])
        # Forward exec options (dry_run, raw, allow_raw, cwd, env) to the CLI.
        return _exec(canonical_id, args, **options)

    def _tool(self, cid: str) -> Tool:
        m = _discover.info(cid)
        name = cid.replace(".", "_")
        self._name_to_cid[name] = cid
        return Tool(
            canonical_id=cid,
            name=name,
            description=m.get("summary") or m.get("description") or cid,
            input_schema=_schema.simplify(m.get("inputs")),
            execute=lambda args, _c=cid: self.execute(_c, args),
        )

    def _ids(self, toolkits, tools, search) -> list[str]:
        # Implementation for Phase 1: resolve against CLI local state
        if tools:
            return tools
        if search:
            # Mirror the TS runtime: resolve a natural-language search to
            # canonical IDs via the CLI's discover/search.
            return [
                t["canonical_id"]
                for t in _discover.search(search)
                if t.get("canonical_id")
            ]
        if toolkits:
            # Resolve toolkits against local tooling.json instead of global search
            res = _manage.list_tools("tooling")
            found = []
            for m in res.get("methods", []):
                integration = m.get("integration", "")
                for tk in toolkits:
                    if tk in integration:
                        found.append(m.get("canonical_id"))
            return found
        return []


class Swytchcode:
    def __init__(self, provider: Optional[Provider] = None):
        self.provider = provider
        self.tools = _Tools(self)

    def handle_tool_calls(self, response: Any) -> list[dict]:
        """Helper to execute tools for non-agentic APIs like Anthropic."""
        results = []
        for block in getattr(response, "content", []):
            if getattr(block, "type", "") == "tool_use":
                # Reverse the sanitized name via the map built in _tool(). A plain
                # "_"->"." replace would corrupt canonical IDs whose segments
                # contain underscores (e.g. stripe.create_payment).
                cid = self.tools._name_to_cid.get(block.name) or block.name.replace(
                    "_", "."
                )
                result = self.tools.execute(cid, getattr(block, "input", {}))
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    }
                )
        return results
