"""High-level agentic client on top of the existing exec()."""

from __future__ import annotations
from typing import Any, Optional

import re
import hashlib

from . import discover as _discover, schema as _schema, manage as _manage
from .exec import exec_ as _exec
from .providers.base import Provider, Tool


MAX_TOOL_NAME_LEN = 64  # OpenAI and Anthropic strict limit


def _make_alias(cid: str, taken: dict[str, str]) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]", "_", cid)
    existing = taken.get(base)
    needs_hash = len(base) > MAX_TOOL_NAME_LEN or (existing and existing != cid)

    if not needs_hash:
        return base

    h = hashlib.sha1(cid.encode("utf-8")).hexdigest()[:6]
    keep = MAX_TOOL_NAME_LEN - 1 - len(h)
    return base[:keep] + "_" + h


def _toolkit_matches(toolkit: str, integration: str) -> bool:
    """Case-insensitive match of a toolkit name against an integration string.

    integration has the shape "ProjectDisplayName.library_slug@version"
    (e.g. "GitHub.github@1.1.4"). We compare against both the project name
    and the library slug so that ``toolkits=["github"]`` matches regardless
    of the capitalised display name.
    """
    tk = toolkit.lower()
    # Strip version: "GitHub.github@1.1.4" → "GitHub.github"
    at_idx = integration.find("@")
    prefix = integration[:at_idx] if at_idx != -1 else integration
    # Split project.library: "GitHub.github" → ("GitHub", "github")
    dot_idx = prefix.find(".")
    if dot_idx != -1:
        project = prefix[:dot_idx].lower()
        lib_slug = prefix[dot_idx + 1 :].lower()
    else:
        project = prefix.lower()
        lib_slug = ""
    return tk == project or tk == lib_slug or tk == prefix.lower()


def _strip_empty(obj: Any) -> Any:
    """Recursively drop keys whose value is None or an empty string ("").

    With 'expose all fields', agents often fill unused optional fields with "",
    which APIs like Stripe reject ("empty values are an attempt to unset").
    Only None and "" are dropped - 0, False, [], {} are preserved as meaningful.
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


def _split_by_location(inputs: Any, flat_args: dict) -> dict:
    """Route flat args into body/params based on LOCATION metadata from wrekenfile."""
    body = {}
    params = {}
    # inputs is the raw wrekenfile list-of-single-key-dicts with LOCATION, or a JSON schema dict
    locations = {}

    if isinstance(inputs, list):
        for item in inputs:
            if isinstance(item, dict):
                for name, spec in item.items():
                    if isinstance(spec, dict):
                        loc = str(
                            spec.get("LOCATION", spec.get("location", "body"))
                        ).lower()
                        locations[name] = loc
    elif isinstance(inputs, dict) and isinstance(inputs.get("properties"), dict):
        for name, spec in inputs["properties"].items():
            if isinstance(spec, dict):
                loc = str(spec.get("LOCATION", spec.get("location", "body"))).lower()
                locations[name] = loc

    for key, val in flat_args.items():
        loc = locations.get(key, "body")
        if loc in ("path", "query"):
            params[key] = val
        else:
            body[key] = val

    result = {}
    if body:
        result["body"] = body
    if params:
        result["params"] = params
    return result if result else {"body": flat_args}


class _Tools:
    def __init__(self, client: "Swytchcode"):
        self._c = client
        # Maps a sanitized tool name (dots -> underscores) back to its canonical
        # ID, populated as tools are built. Used to reverse names in
        # handle_tool_calls without a lossy "_"->"." string replace.
        self._name_to_cid: dict[str, str] = {}
        self._cid_to_inputs: dict[str, Any] = {}

    def get(self, *, toolkits=None, tools=None, search=None):
        # Sort canonical IDs lexicographically before alias assignment.
        # This ensures deterministic assignment order across runs, guaranteeing the
        # same canonical ID always receives the exact same alias (and same hash if colliding).
        ids = sorted(self._ids(toolkits, tools, search))
        neutral = [self._tool(cid) for cid in ids]
        p = self._c.provider
        return p.format_tools(neutral) if p else neutral

    def execute(self, canonical_id: str, args: dict, **options) -> Any:
        final_args = dict(args)

        # If args are flat (no body/params top-level keys), wrap them in body
        # as expected by the Swytchcode CLI kernel (like in run-workflow.js)
        if "body" not in final_args and "params" not in final_args:
            raw_inputs = options.pop("_raw_inputs", None)
            if raw_inputs is not None:
                final_args = _split_by_location(raw_inputs, final_args)
            else:
                final_args = {"body": final_args}
        else:
            options.pop("_raw_inputs", None)

        # Drop empty optional fields (None/"") from body & params so values an
        # agent over-filled don't reach the API (e.g. Stripe rejects customer="").
        if isinstance(final_args.get("body"), (dict, list)):
            final_args["body"] = _strip_empty(final_args["body"])
        if isinstance(final_args.get("params"), (dict, list)):
            final_args["params"] = _strip_empty(final_args["params"])
        # Forward exec options (dry_run, raw, allow_raw, cwd, env) to the CLI.
        return _exec(canonical_id, final_args, **options)

    def _tool(self, cid: str) -> Tool:
        m = _discover.info(cid)
        if not m or not m.get("inputs"):
            raise ValueError(
                f"Tool discovery failed for {cid}: Invalid or missing Wrekenfile schema"
            )

        name = _make_alias(cid, self._name_to_cid)

        self._name_to_cid[name] = cid
        raw_inputs = m.get("inputs")
        self._cid_to_inputs[cid] = raw_inputs
        return Tool(
            canonical_id=cid,
            name=name,
            description=m.get("summary") or m.get("description") or cid,
            input_schema=_schema.simplify(raw_inputs),
            execute=lambda args, _c=cid, _inputs=raw_inputs: self.execute(
                _c, args, _raw_inputs=_inputs
            ),
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
                cid = m.get("canonical_id")
                if not cid:
                    continue
                for tk in toolkits:
                    if _toolkit_matches(tk, integration):
                        found.append(cid)
                        break
            return found
        return []


class Swytchcode:
    def __init__(self, provider: Optional[Provider] = None):
        self.provider = provider
        self.tools = _Tools(self)

    def handle_tool_calls(
        self, response: Any, timeout: float | None = None
    ) -> list[dict]:
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
                raw_inputs = self.tools._cid_to_inputs.get(cid, {})
                # Isolate failures per block so one failing tool doesn't drop the
                # results for the other tool_use blocks in the same turn.
                try:
                    content = str(
                        self.tools.execute(
                            cid,
                            getattr(block, "input", {}),
                            _raw_inputs=raw_inputs,
                            timeout=timeout,
                        )
                    )
                    is_error = False
                except Exception as e:
                    content = f"Error executing {cid}: {e}"
                    is_error = True
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                        "is_error": is_error,
                    }
                )
        return results
