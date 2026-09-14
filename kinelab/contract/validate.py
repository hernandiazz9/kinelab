"""Validador mínimo de `schema.json`, sin dependencias: type, enum, required,
properties, additionalProperties, items, y las tres referencias internas
(`$event`, `$metric`, `$subframe`) que apuntan a `$defs`. Suficiente para que un campo
renombrado o una unidad cambiada no pasen (CONTRATO.md §Versionado)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("schema.json")
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class ContractError(ValueError):
    """El `analysis.json` no cumple el contrato. `errors` tiene la lista."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("analysis.json no cumple el contrato:\n  " + "\n  ".join(errors))
        self.errors = errors


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _is_type(value: Any, t: str) -> bool:
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def _check(value: Any, schema: dict, path: str, errors: list[str], defs: dict) -> None:
    if schema.get("$event"):
        schema = defs["event"]
    elif schema.get("$metric"):
        schema = defs["metric"]
    elif schema.get("$subframe"):
        schema = defs["subframe"]
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_is_type(value, x) for x in types):
            errors.append(f"{path}: se esperaba {'/'.join(types)}, llegó {type(value).__name__}")
            return
    if value is None:
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} no está en {schema['enum']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: falta el campo obligatorio '{key}'")
        for key, v in value.items():
            if key in props:
                _check(v, props[key], f"{path}.{key}", errors, defs)
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{path}: campo desconocido '{key}' (¿renombrado? eso es cambio mayor)")
                elif isinstance(extra, dict):
                    _check(v, extra, f"{path}.{key}", errors, defs)
    elif isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            _check(v, schema["items"], f"{path}[{i}]", errors, defs)


def validate_analysis(obj: Any, schema: dict | None = None) -> list[str]:
    """Lista de errores; vacía si el objeto cumple el contrato."""
    schema = schema or load_schema()
    errors: list[str] = []
    _check(obj, schema, "$", errors, schema.get("$defs", {}))
    return errors
