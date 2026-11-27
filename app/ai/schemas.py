"""JSON schemas for the model's structured (JSON) outputs, derived from Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.models.api import PlanContent

_DROP_KEYS = frozenset({"title", "default", "description"})


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return a self-contained JSON schema suitable for structured outputs.

    ``$ref``s are inlined, titles and defaults removed, and every object is closed
    (``additionalProperties: false``) with all properties required.
    """
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(defs[node["$ref"].split("/")[-1]])
            out = {k: resolve(v) for k, v in node.items() if k not in _DROP_KEYS}
            if out.get("type") == "object" and "properties" in out:
                out["additionalProperties"] = False
                out["required"] = list(out["properties"])
            return out
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    schema: dict[str, Any] = resolve(raw)
    return schema


PLAN_SCHEMA: dict[str, Any] = strict_schema(PlanContent)

SIMULATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},
        "next_step": {"type": "string"},
    },
    "required": ["explanation", "next_step"],
    "additionalProperties": False,
}
