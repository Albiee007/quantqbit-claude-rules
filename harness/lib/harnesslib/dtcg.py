"""Design Tokens (DTCG Format Module 2025.10), the subset the harness reads and writes.

Supported
- Groups and tokens, `$type` inherited from the nearest group, `$description`, `$deprecated`,
  `$extensions` (kept verbatim, never interpreted unless documented), the `$root` token name.
- Curly-brace aliases "{group.token}" as a whole `$value`, and inside typography composites.
- Types: color, dimension, fontFamily, fontWeight, number, duration, typography.
- color values as 2025.10 objects {colorSpace, components, alpha?, hex?} with colorSpace srgb,
  srgb-linear, oklab or oklch; a plain CSS colour string is read as a legacy form (warning).
- dimension values {value, unit: px|rem}; "16px" / "1rem" strings are read as a legacy form.

Rejected explicitly (TokenError): `$ref` JSON-pointer references, group `$extends`, other `$type`s
when a reference needs them, alias cycles, chains deeper than MAX_DEPTH, missing targets, and an
alias whose target type differs from the expected type. Other constructs are kept when merging.

Platform output (CSS clamp(), Android sp, Apple pt, React Native numbers) is not DTCG: the type
tools write it under $extensions["org.quantqbit.platform"] (see harnesslib.typescale).
"""

from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import color as col
from .fsutil import InputError, dumps_pretty, load_json, write_atomic

MAX_DEPTH = 32
SUPPORTED = {"color", "dimension", "fontFamily", "fontWeight", "number", "duration", "typography"}
COLOR_SPACES = {"srgb", "srgb-linear", "oklab", "oklch"}
FONT_WEIGHTS = {"thin": 100, "hairline": 100, "extra-light": 200, "ultra-light": 200, "light": 300,
                "normal": 400, "regular": 400, "book": 400, "medium": 500, "semi-bold": 600,
                "demi-bold": 600, "bold": 700, "extra-bold": 800, "ultra-bold": 800, "black": 900,
                "heavy": 900, "extra-black": 950, "ultra-black": 950}
TYPOGRAPHY_FIELDS = {"fontFamily": "fontFamily", "fontSize": "dimension", "fontWeight": "fontWeight",
                     "letterSpacing": "dimension", "lineHeight": "number"}
ALIAS = re.compile(r"^\{([^{}]+)\}$")
FONT_EXT = "org.quantqbit.font"
PLATFORM_EXT = "org.quantqbit.platform"


class TokenError(InputError):
    pass


@dataclass
class Resolved:
    path: str
    type: str
    value: Any                       # resolved value (aliases replaced)
    token: dict                      # the token object itself
    chain: list[str] = field(default_factory=list)  # alias chain followed
    warnings: list[str] = field(default_factory=list)


def is_alias(v: Any) -> bool:
    return isinstance(v, str) and bool(ALIAS.match(v))


def alias_target(v: str) -> str:
    return ALIAS.match(v).group(1)  # type: ignore[union-attr]


class Tokens:
    def __init__(self, doc: dict, source: str = "tokens") -> None:
        if not isinstance(doc, dict):
            raise TokenError(f"{source}: the token file must be a JSON object")
        self.doc = doc
        self.source = source
        self.index: dict[str, tuple[dict, str | None]] = {}
        self._walk(doc, [], None)

    # -------------------------------------------------------------- structure
    def _walk(self, node: dict, path: list[str], inherited: str | None) -> None:
        if "$ref" in node:
            raise TokenError(f"{self.source}: '$ref' at {'.'.join(path) or '(root)'} is not supported; use a "
                             "curly-brace alias")
        if "$extends" in node:
            raise TokenError(f"{self.source}: group '$extends' at {'.'.join(path) or '(root)'} is not supported")
        gtype = node.get("$type", inherited)
        for key, child in node.items():
            if key.startswith("$") and key != "$root":
                continue
            if not isinstance(child, dict):
                raise TokenError(f"{self.source}: {'.'.join(path + [key])} must be a group or token object")
            if "." in key or "{" in key or "}" in key:
                raise TokenError(f"{self.source}: name {key!r} may not contain '.', '{{' or '}}'")
            if "$value" in child:
                if "$ref" in child:
                    raise TokenError(f"{self.source}: '$ref' in {'.'.join(path + [key])} is not supported")
                self.index[".".join(path + [key])] = (child, child.get("$type", gtype))
            else:
                self._walk(child, path + [key], gtype)

    @classmethod
    def load(cls, path: Path) -> "Tokens":
        return cls(load_json(path), str(path))

    def paths(self) -> list[str]:
        return sorted(self.index)

    # -------------------------------------------------------------- resolution
    def resolve(self, ref: str, expected: str | None = None) -> Resolved:
        """Resolve a token path ("color.brand.500") or alias ("{color.brand.500}")."""
        path = alias_target(ref) if is_alias(ref) else ref
        return self._resolve(path, expected, [])

    def _resolve(self, path: str, expected: str | None, chain: list[str]) -> Resolved:
        if path in chain:
            raise TokenError(f"{self.source}: alias cycle {' -> '.join(chain + [path])}")
        if len(chain) >= MAX_DEPTH:
            raise TokenError(f"{self.source}: alias chain deeper than {MAX_DEPTH} at {path}")
        if path not in self.index:
            where = f" (via {' -> '.join(chain)})" if chain else ""
            raise TokenError(f"{self.source}: no token {path!r}{where}")
        token, ttype = self.index[path]
        raw = token["$value"]
        if is_alias(raw):
            inner = self._resolve(alias_target(raw), expected or ttype, chain + [path])
            if ttype and inner.type != ttype:
                raise TokenError(f"{self.source}: {path} is {ttype} but aliases {inner.path} ({inner.type})")
            return Resolved(path, inner.type, inner.value, token, chain + [path] + inner.chain, inner.warnings)
        if ttype is None:
            raise TokenError(f"{self.source}: {path} has no $type (set it on the token or a parent group)")
        if expected and ttype != expected:
            raise TokenError(f"{self.source}: {path} is {ttype}, expected {expected}")
        if ttype not in SUPPORTED:
            raise TokenError(f"{self.source}: {path} has $type {ttype!r}, which these tools do not support "
                             f"(supported: {', '.join(sorted(SUPPORTED))})")
        warnings: list[str] = []
        value = self._value(path, ttype, raw, chain + [path], warnings)
        return Resolved(path, ttype, value, token, chain + [path], warnings)

    def _value(self, path: str, ttype: str, raw: Any, chain: list[str], warnings: list[str]) -> Any:
        if ttype == "color":
            return check_color(path, raw, warnings)
        if ttype == "dimension":
            return check_dimension(path, raw, warnings)
        if ttype == "fontFamily":
            if isinstance(raw, str) and raw.strip():
                return [raw]
            if isinstance(raw, list) and raw and all(isinstance(x, str) and x.strip() for x in raw):
                return list(raw)
            raise TokenError(f"{path}: fontFamily must be a name or a non-empty list of names")
        if ttype == "fontWeight":
            if isinstance(raw, str) and raw in FONT_WEIGHTS:
                return FONT_WEIGHTS[raw]
            if isinstance(raw, (int, float)) and not isinstance(raw, bool) and 1 <= raw <= 1000:
                return raw
            raise TokenError(f"{path}: fontWeight must be 1-1000 or a keyword")
        if ttype == "number":
            if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw):
                return raw
            raise TokenError(f"{path}: number must be a finite number")
        if ttype == "duration":
            if isinstance(raw, dict) and raw.get("unit") in ("ms", "s") and _finite(raw.get("value")):
                return raw
            raise TokenError(f"{path}: duration must be {{value, unit: ms|s}}")
        if ttype == "typography":
            if not isinstance(raw, dict):
                raise TokenError(f"{path}: typography must be an object")
            out = {}
            for k, sub in raw.items():
                want = TYPOGRAPHY_FIELDS.get(k)
                if want is None:
                    raise TokenError(f"{path}: unknown typography field {k!r}")
                if is_alias(sub):
                    out[k] = self._resolve(alias_target(sub), want, chain).value
                else:
                    out[k] = self._value(f"{path}.{k}", want, sub, chain, warnings)
            missing = {"fontFamily", "fontSize", "fontWeight"} - set(out)
            if missing:
                raise TokenError(f"{path}: typography needs {', '.join(sorted(missing))}")
            return out
        raise TokenError(f"{path}: unsupported $type {ttype!r}")  # pragma: no cover

    def check_all(self) -> list[str]:
        """Resolve every token of a supported type; returns errors (never raises)."""
        errors = []
        for p in self.paths():
            ttype = self.index[p][1]
            if ttype is not None and ttype not in SUPPORTED and not is_alias(self.index[p][0]["$value"]):
                continue  # foreign type: kept, not interpreted
            try:
                self._resolve(p, None, [])
            except TokenError as e:
                errors.append(str(e))
        return errors


def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_color(path: str, raw: Any, warnings: list[str]) -> dict:
    """Normalise a colour value to {colorSpace, components, alpha, hex, srgb}."""
    if isinstance(raw, str):
        try:
            rgba = col.parse(raw)
        except col.ColorError as e:
            raise TokenError(f"{path}: {e}") from None
        warnings.append(f"{path}: legacy string colour {raw!r}; 2025.10 uses {{colorSpace, components}}")
        return {"colorSpace": "srgb", "components": list(rgba[:3]), "alpha": rgba[3], "hex": col.to_hex(rgba),
                "srgb": rgba}
    if not isinstance(raw, dict):
        raise TokenError(f"{path}: colour must be an object {{colorSpace, components}}")
    space, comps = raw.get("colorSpace"), raw.get("components")
    if space not in COLOR_SPACES:
        raise TokenError(f"{path}: colorSpace {space!r} is not supported here ({', '.join(sorted(COLOR_SPACES))})")
    if not (isinstance(comps, list) and len(comps) == 3 and all(_finite(c) or c == "none" for c in comps)):
        raise TokenError(f"{path}: components must be 3 finite numbers (or 'none')")
    alpha = raw.get("alpha", 1)
    if not _finite(alpha) or not 0 <= alpha <= 1:
        raise TokenError(f"{path}: alpha must be 0..1")
    c = [0.0 if v == "none" else float(v) for v in comps]
    if space == "srgb":
        rgb = tuple(c)
    elif space == "srgb-linear":
        rgb = tuple(col.linear_to_srgb(v) for v in c)
    elif space == "oklab":
        rgb = col.oklab_to_srgb((c[0], c[1], c[2]))
    else:
        hue = None if comps[2] == "none" else c[2]
        rgb = col.oklab_to_srgb(col.oklch_to_oklab((c[0], c[1], hue)))
    if not col.in_gamut(rgb):
        hexv = raw.get("hex")
        if isinstance(hexv, str):
            warnings.append(f"{path}: outside sRGB; the 'hex' fallback {hexv} is used for sRGB output")
            rgb = col.parse(hexv)[:3]
        else:
            raise TokenError(f"{path}: outside the sRGB gamut and no 'hex' fallback; map it (palette.py ramp does)")
    rgba = (*col.clip(rgb), float(alpha))
    hexv = raw.get("hex")
    if isinstance(hexv, str) and not re.fullmatch(r"#[0-9a-fA-F]{6}", hexv):
        raise TokenError(f"{path}: hex must be #rrggbb")
    return {"colorSpace": space, "components": comps, "alpha": alpha, "hex": hexv or col.to_hex(rgba), "srgb": rgba}


def check_dimension(path: str, raw: Any, warnings: list[str]) -> dict:
    if isinstance(raw, str):
        m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)(px|rem)\s*", raw)
        if not m:
            raise TokenError(f"{path}: dimension must be {{value, unit: px|rem}}")
        warnings.append(f"{path}: legacy string dimension {raw!r}; 2025.10 uses {{value, unit}}")
        return {"value": float(m.group(1)), "unit": m.group(2)}
    if isinstance(raw, dict) and raw.get("unit") in ("px", "rem") and _finite(raw.get("value")):
        return {"value": raw["value"], "unit": raw["unit"]}
    raise TokenError(f"{path}: dimension must be {{value, unit: px|rem}}")


def color_token(rgba: tuple[float, ...], description: str | None = None, extensions: dict | None = None,
                oklch: tuple[float, float, float | None] | None = None) -> dict:
    """A 2025.10 sRGB colour token (components rounded to 6 places, hex fallback)."""
    tok: dict = {"$type": "color", "$value": {"colorSpace": "srgb",
                                              "components": [round(c, 6) for c in col.clip(rgba)],
                                              "alpha": round(rgba[3], 4) if len(rgba) > 3 else 1,
                                              "hex": col.to_hex(rgba)}}
    if description:
        tok["$description"] = description
    ext = dict(extensions or {})
    if oklch is not None:
        L, C, H = oklch
        ext["org.quantqbit.oklch"] = {"l": round(L, 4), "c": round(C, 4), "h": None if H is None else round(H, 2)}
    if ext:
        tok["$extensions"] = ext
    return tok


# ------------------------------------------------------------------ merging

@dataclass
class Change:
    path: str
    kind: str          # add | replace | same | conflict
    old: Any = None
    new: Any = None


def _set(doc: dict, path: str, token: dict) -> None:
    node = doc
    parts = path.split(".")
    for p in parts[:-1]:
        node = node.setdefault(p, {})
        if not isinstance(node, dict) or "$value" in node:
            raise TokenError(f"cannot add {path}: {p} is a token, not a group")
    node[parts[-1]] = token


def merge(base: dict, additions: dict, replace: set[str] | frozenset[str] = frozenset()) -> tuple[dict, list[Change]]:
    """Merge additions into a copy of base. New tokens are added; a token whose value differs is a
    conflict and is left alone unless its path is named in `replace`. Group-level keys and foreign
    `$extensions` in base are preserved. The result is fully re-validated by the caller."""
    out = copy.deepcopy(base)
    old = Tokens(base, "existing tokens")
    new = Tokens(additions, "new tokens")
    changes: list[Change] = []
    for path in new.paths():
        tok = new.index[path][0]
        if path in old.index:
            cur = old.index[path][0]
            if cur.get("$value") == tok.get("$value") and cur.get("$type") == tok.get("$type"):
                changes.append(Change(path, "same"))
                continue
            if path not in replace:
                changes.append(Change(path, "conflict", cur.get("$value"), tok.get("$value")))
                continue
            merged = copy.deepcopy(cur)
            merged.update({k: v for k, v in tok.items()})
            if "$extensions" in cur and "$extensions" in tok:
                merged["$extensions"] = {**cur["$extensions"], **tok["$extensions"]}
            _set(out, path, merged)
            changes.append(Change(path, "replace", cur.get("$value"), tok.get("$value")))
        else:
            _set(out, path, copy.deepcopy(tok))
            changes.append(Change(path, "add", None, tok.get("$value")))
    unknown = set(replace) - {c.path for c in changes}
    if unknown:
        raise TokenError(f"--replace names tokens this run does not write: {', '.join(sorted(unknown))}")
    return out, changes


def write_tokens(path: Path, doc: dict, backup: bool = True) -> Path | None:
    """Validate the complete document, then replace the file atomically (keeping <name>.bak)."""
    errors = Tokens(doc, str(path)).check_all()
    if errors:
        raise TokenError("refusing to write invalid tokens:\n  " + "\n  ".join(errors))
    return write_atomic(Path(path), dumps_pretty(doc), backup=backup)


def merge_file(path: Path, additions: dict, replace: set[str], log=print) -> bool:
    """Merge additions into the token file at path (created if missing). Prints every change with
    its old and new value; on any conflict nothing is written. Returns True when written."""
    path = Path(path)
    base = load_json(path) if path.is_file() else {}
    merged, changes = merge(base, additions, replace)
    conflicts = [c for c in changes if c.kind == "conflict"]
    for c in changes:
        if c.kind == "add":
            log(f"  add      {c.path}")
        elif c.kind == "replace":
            log(f"  replace  {c.path}: {c.old!r} -> {c.new!r}")
        elif c.kind == "conflict":
            log(f"  conflict {c.path}: has {c.old!r}, this run wants {c.new!r} (pass --replace {c.path} to change it)")
    if conflicts:
        log(f"{len(conflicts)} conflict(s): nothing written to {path}")
        return False
    if not any(c.kind in ("add", "replace") for c in changes):
        log(f"{path}: already up to date")
        return True
    saved = write_tokens(path, merged)
    log(f"wrote {path}" + (f" (previous version kept as {saved.name})" if saved else ""))
    return True
