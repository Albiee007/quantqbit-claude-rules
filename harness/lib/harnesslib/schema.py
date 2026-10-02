"""A small JSON Schema (2020-12 keyword subset) validator for the harness's own schemas.

Supported keywords: type, properties, required, additionalProperties, propertyNames, enum, const,
pattern, minLength, maxLength, minimum, maximum, exclusiveMinimum, exclusiveMaximum, items,
minItems, maxItems, uniqueItems, $ref (local "#/$defs/..."), anyOf, oneOf, allOf, format.
Extensions: format "relpath" (a project-relative path, see fsutil.safe_rel) and "x-uniqueKey"
(array items must not repeat that property). Any other keyword in a schema is an error, so a
constraint can never be silently ignored. Numbers must be finite (fsutil.load_json enforces it).
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .fsutil import InputError, load_json, safe_rel

HERE = Path(__file__).resolve().parent / "schemas"
ANNOTATIONS = {"$schema", "$id", "title", "description", "$defs", "$comment", "examples", "default"}
KEYWORDS = {"type", "properties", "required", "additionalProperties", "propertyNames", "enum", "const",
            "pattern", "minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum",
            "exclusiveMaximum", "items", "minItems", "maxItems", "uniqueItems", "$ref", "anyOf", "oneOf",
            "allOf", "format", "x-uniqueKey"}
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class SchemaError(InputError):
    pass


def _check_schema(s: Any, where: str) -> None:
    if isinstance(s, bool):
        return
    if not isinstance(s, dict):
        raise SchemaError(f"schema {where}: not an object")
    for k, v in s.items():
        if k in ANNOTATIONS:
            if k == "$defs":
                for name, sub in v.items():
                    _check_schema(sub, f"{where}/$defs/{name}")
            continue
        if k not in KEYWORDS:
            raise SchemaError(f"schema {where}: unsupported keyword {k!r}")
        if k in ("properties",):
            for name, sub in v.items():
                _check_schema(sub, f"{where}/properties/{name}")
        elif k in ("items", "additionalProperties", "propertyNames"):
            _check_schema(v, f"{where}/{k}")
        elif k in ("anyOf", "oneOf", "allOf"):
            for i, sub in enumerate(v):
                _check_schema(sub, f"{where}/{k}/{i}")


_cache: dict[str, dict] = {}


def load(name: str) -> dict:
    """A bundled schema by name (e.g. 'direction' -> schemas/direction.schema.json)."""
    if name not in _cache:
        schema = load_json(HERE / f"{name}.schema.json")
        _check_schema(schema, name)
        _cache[name] = schema
    return _cache[name]


def _type_ok(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    return isinstance(v, TYPES[t])


def _resolve_ref(root: dict, ref: str) -> dict:
    if not ref.startswith("#/$defs/"):
        raise SchemaError(f"only local '#/$defs/...' references are supported, got {ref!r}")
    return root["$defs"][ref[len("#/$defs/"):]]


def validate(data: Any, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    """All violations as 'path: message' strings (empty when valid)."""
    root = root or schema
    if schema is True:
        return []
    if schema is False:
        return [f"{path}: not allowed"]
    errs: list[str] = []
    if "$ref" in schema:
        errs += validate(data, _resolve_ref(root, schema["$ref"]), root, path)
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(data, x) for x in types):
            return errs + [f"{path}: expected {' or '.join(types)}"]
    if "const" in schema and data != schema["const"]:
        errs.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errs.append(f"{path}: {data!r} does not match {schema['pattern']}")
        if schema.get("format") == "relpath":
            try:
                safe_rel(data, path)
            except InputError as e:
                errs.append(str(e))
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if not math.isfinite(data):
            errs.append(f"{path}: must be finite")
        if "minimum" in schema and data < schema["minimum"]:
            errs.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errs.append(f"{path}: above {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            errs.append(f"{path}: must be above {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
            errs.append(f"{path}: must be below {schema['exclusiveMaximum']}")
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errs.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errs.append(f"{path}: at most {schema['maxItems']} item(s)")
        if schema.get("uniqueItems"):
            seen = []
            for x in data:
                if x in seen:
                    errs.append(f"{path}: duplicate item {x!r}")
                    break
                seen.append(x)
        key = schema.get("x-uniqueKey")
        if key:
            ids = [x.get(key) for x in data if isinstance(x, dict) and key in x]
            for dup in sorted({i for i in ids if ids.count(i) > 1}, key=str):
                errs.append(f"{path}: {key} {dup!r} is used more than once")
        if "items" in schema:
            for i, x in enumerate(data):
                errs += validate(x, schema["items"], root, f"{path}[{i}]")
    if isinstance(data, dict):
        props = schema.get("properties", {})
        for r in schema.get("required", []):
            if r not in data:
                errs.append(f"{path}: missing {r!r}")
        for k, v in data.items():
            if "propertyNames" in schema:
                errs += [e.replace(f"{path}.{{name}}", f"{path} key {k!r}")
                         for e in validate(k, schema["propertyNames"], root, f"{path}.{{name}}")]
            if k in props:
                errs += validate(v, props[k], root, f"{path}.{k}")
            elif "additionalProperties" in schema:
                ap = schema["additionalProperties"]
                if ap is False:
                    errs.append(f"{path}: unknown key {k!r}")
                elif isinstance(ap, dict):
                    errs += validate(v, ap, root, f"{path}.{k}")
    for sub in schema.get("allOf", []):
        errs += validate(data, sub, root, path)
    if "anyOf" in schema:
        results = [validate(data, s, root, path) for s in schema["anyOf"]]
        if all(results):
            errs.append(f"{path}: matches none of the allowed forms ({'; '.join(r[0] for r in results)})")
    if "oneOf" in schema:
        results = [validate(data, s, root, path) for s in schema["oneOf"]]
        ok = sum(1 for r in results if not r)
        if ok != 1:
            errs.append(f"{path}: must match exactly one allowed form (matched {ok})")
    return errs


def check(data: Any, name: str, where: str) -> None:
    """Raise SchemaError listing every violation of the named bundled schema."""
    errs = validate(data, load(name))
    if errs:
        raise SchemaError(f"{where} does not match the {name} schema:\n  " + "\n  ".join(errs[:40]))
