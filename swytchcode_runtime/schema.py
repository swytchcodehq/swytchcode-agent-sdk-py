"""Simplify a tool's input schema for the LLM: expose all fields, mark required ones."""

from __future__ import annotations
from typing import Any, Optional


def simplify(inputs: Any) -> dict:
    # Handle Wrekenfile shape: a list of single-key dicts (e.g. [{"amount": {"TYPE": "INT"...}}])
    if isinstance(inputs, list):
        props = {}
        required = []
        for item in inputs:
            if not isinstance(item, dict):
                continue
            for name, spec in item.items():
                if not isinstance(spec, dict):
                    continue

                # Default to string if TYPE is missing
                t = spec.get("TYPE", "STRING").lower()
                if t == "int":
                    t = "integer"
                elif t in ("float", "number", "double"):
                    t = "number"
                elif t == "bool":
                    t = "boolean"
                elif t == "object":
                    t = "object"
                elif t == "any":
                    t = "object"
                elif t.startswith("[]"):
                    t = "array"
                else:
                    t = "string"

                props[name] = {"type": t, "description": spec.get("DESC", "")}

                req = spec.get("REQUIRED", False)
                loc = str(spec.get("LOCATION", spec.get("location", ""))).lower()
                is_required = (
                    loc == "path"
                    or req is True
                    or (isinstance(req, str) and req.strip().lower() == "true")
                )
                if is_required:
                    required.append(name)

        # Composio-style rule: expose ALL fields to the model and list only the
        # truly-required ones in `required`. A required-only approach hid optional
        # fields - which left all-optional tools (e.g. Stripe) with an empty schema
        # so the model called them with no arguments, and blinded the model to
        # optional fields on tools that do have some required ones.
        return {"type": "object", "properties": props, "required": required}

    # Fallback to standard JSON Schema handling
    if not isinstance(inputs, dict):
        return {"type": "object", "properties": {}, "required": []}

    props = inputs.get("properties") or {}
    required = inputs.get("required") or []
    keep = {}

    # Expose all fields (same rule as the wrekenfile branch above); use the
    # original required list only for the `required` key so optional/nested
    # fields stay optional instead of being dropped or forced required.
    for name, spec in props.items():
        if isinstance(spec, dict):
            loc = str(spec.get("LOCATION", spec.get("location", ""))).lower()
            if loc == "path" and name not in required:
                required.append(name)

            if spec.get("type") == "object" and "properties" in spec:
                spec = simplify(spec)  # recurse into nested objects
        keep[name] = spec

    return {
        "type": "object",
        "properties": keep,
        "required": [r for r in required if r in keep],
    }


def to_pydantic_model(schema: dict, name: str = "ArgsSchema") -> Any:
    """Dynamically build a Pydantic model from a JSON schema for LangGraph args_schema."""
    from pydantic import create_model

    if not schema or "properties" not in schema:
        return create_model(name)

    fields = {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for field_name, field_info in properties.items():
        field_type = str
        t = field_info.get("type")
        if t == "integer":
            field_type = int
        elif t == "number":
            field_type = float
        elif t == "boolean":
            field_type = bool
        elif t == "array":
            field_type = list
        elif t == "object":
            field_type = to_pydantic_model(field_info, f"{name}_{field_name}")

        if field_name in required:
            fields[field_name] = (field_type, ...)
        else:
            # Optional[...] so an explicit null is accepted (pydantic v2 rejects
            # None for a bare non-optional annotation).
            fields[field_name] = (Optional[field_type], None)

    return create_model(name, **fields)
