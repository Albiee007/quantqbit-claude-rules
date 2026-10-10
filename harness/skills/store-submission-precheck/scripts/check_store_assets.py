#!/usr/bin/env python3
"""Check store images against the Play and App Store specs (references/store-specs.md).

Two modes:
  inspect (default)  checks the images that exist; empty or missing slots are INFO.
  --release          a submission gate: every slot the declared stores require
                     must hold valid images. Stores come from --stores or the config.

Slots (a folder, its accepted sizes or size rule, a count and when it is required)
come from references/store-slots.json, the harness defaults:
  <root>/play/phone/  play/tablet7/  play/tablet10/  play/feature_graphic*.png|jpg
  <root>/ios/6.3/     ios/6.9/       ios/6.5/        ios/ipad13/
An image folder under play/ or ios/ that no slot reads is a warning (an error
with --release): declare it as a slot rather than leave it unchecked.
Optional config, <root>/store-assets.json (or --config); paths are relative to it:
  {"version": 1, "stores": ["play", "ios"],
   "ios":  {"supports_tablet": true, "icon": "../assets/icon.png", "app_json": "../app.json"},
   "play": {"icon": "../assets/play-icon-512.png", "tablet_slots": ["tablet7", "tablet10"]},
   "min_counts": {"play-phone": 4},
   "slots": {"ios-6.9": {"need": "always"},
             "ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1179x2556"], "need": "optional"}}}
"slots" adds a slot (store, folder, and sizes or {"rule": {"maxSide": N}}; optional
count [min, max] and need always|tablet|declared|optional) or changes a built-in
slot's need, count or sizes.
Needs Pillow (pip install pillow).

Usage:
  python check_store_assets.py <root> [--release] [--config FILE] [--stores play,ios]
      [--supports-tablet | --no-supports-tablet] [--ios-icon P] [--play-icon P] [--json]
      [--catalog FILE]
Exit: 0 no errors, 1 errors found, 2 bad arguments or config.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

MB = 1024 * 1024
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
ICON = {"ios": (1024, 1024), "play": (512, 512)}
CATALOG = Path(__file__).resolve().parent.parent / "references" / "store-slots.json"
STORES = ("play", "ios")
NEEDS = ("always", "tablet", "declared", "optional")
STORE_COUNTS = {"play": (1, 8), "ios": (1, 10)}  # default count for a project-added slot
SIDE = (320, 7680)  # smallest and largest side any slot or rule may name
SIZE_RE = re.compile(r"^([1-9][0-9]{1,4})x([1-9][0-9]{1,4})$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,39}$")
RENDER_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
FOLDER_RE = re.compile(r"^(play|ios)(/[A-Za-z0-9][A-Za-z0-9._-]*)+$")
SLOT_KEYS = {"store", "folder", "sizes", "rule", "count", "need"}
OVERRIDE_KEYS = {"sizes", "count", "need"}


def both(sizes: set) -> frozenset:
    return frozenset(sizes | {(h, w) for (w, h) in sizes})


@dataclass(frozen=True)
class Slot:
    name: str
    folder: str
    store: str
    sizes: frozenset | None  # exact sizes (both orientations), or None for the size rule
    max_side: int  # size rule: longest side allowed (Play phone 3840, large screens 7680); 0 with exact sizes
    lo: int
    hi: int
    need: str  # always | tablet (iOS app supports iPad) | declared (play.tablet_slots) | optional


@dataclass(frozen=True)
class Catalog:
    slots: dict  # name -> Slot, in check order
    render: dict  # store-mockups size key -> (width, height, store, folder)
    feature_graphic: tuple
    fg_file: str  # where store-mockups writes it, relative to the assets root
    fg_match: str  # glob the checker reads, relative to the assets root


CONFIG_KEYS = {"version", "stores", "ios", "play", "min_counts", "slots"}
IOS_KEYS = {"supports_tablet", "icon", "app_json"}
PLAY_KEYS = {"icon", "tablet_slots"}


class ConfigError(Exception):
    pass


# ------------------------------------------------------------------ slots

def is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def parse_size(value, where: str) -> tuple[int, int]:
    m = SIZE_RE.match(value) if isinstance(value, str) else None
    if not m:
        raise ConfigError(f"{where}: {value!r} is not a size like \"1206x2622\"")
    w, h = int(m[1]), int(m[2])
    if not (SIDE[0] <= w <= SIDE[1] and SIDE[0] <= h <= SIDE[1]):
        raise ConfigError(f"{where}: {value}: each side must be {SIDE[0]}-{SIDE[1]} px")
    return w, h


def parse_sizes(value, where: str) -> frozenset:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{where}: must be a non-empty list of sizes like [\"1206x2622\"]")
    return both({parse_size(v, where) for v in value})


def parse_count(value, where: str) -> tuple[int, int]:
    if not (isinstance(value, list) and len(value) == 2 and all(is_int(v) for v in value)
            and 0 <= value[0] <= value[1] and value[1] >= 1):
        raise ConfigError(f"{where}: must be [min, max], whole numbers with 0 <= min <= max and max >= 1")
    return value[0], value[1]


def parse_rule(value, where: str) -> int:
    if not isinstance(value, dict) or set(value) != {"maxSide"}:
        raise ConfigError(f"{where}: must be {{\"maxSide\": N}}")
    n = value["maxSide"]
    if not is_int(n) or not SIDE[0] <= n <= SIDE[1]:
        raise ConfigError(f"{where}.maxSide: must be a whole number from {SIDE[0]} to {SIDE[1]}")
    return n


def parse_need(value, where: str) -> str:
    if value not in NEEDS:
        raise ConfigError(f"{where}: must be one of {', '.join(NEEDS)}")
    return value


def check_folder(folder, store: str, where: str) -> str:
    """A slot folder is relative, inside the store's own tree, and has no '..'."""
    if not isinstance(folder, str) or not FOLDER_RE.match(folder) or ".." in folder.split("/"):
        raise ConfigError(f"{where}: {folder!r} must be a relative folder such as \"{store}/name\" "
                          "(letters, digits, '.', '_', '-'; no '..')")
    if folder.split("/", 1)[0] != store:
        raise ConfigError(f"{where}: a {store} slot's folder must start with \"{store}/\" (got {folder!r})")
    return folder


def new_slot(name: str, d, where: str, allowed: set, defaults: bool) -> Slot:
    if not NAME_RE.match(name):
        raise ConfigError(f"{where}: slot names are lowercase letters, digits, '.' and '-' (got {name!r})")
    if not isinstance(d, dict):
        raise ConfigError(f"{where}: must be an object")
    unknown = sorted(set(d) - allowed)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s): {', '.join(unknown)}")
    store = d.get("store")
    if store not in STORES:
        raise ConfigError(f"{where}.store: must be \"play\" or \"ios\"")
    folder = check_folder(d.get("folder"), store, f"{where}.folder")
    if ("sizes" in d) == ("rule" in d):
        raise ConfigError(f"{where}: give exactly one of \"sizes\" (exact sizes) or \"rule\" ({{\"maxSide\": N}})")
    sizes = parse_sizes(d["sizes"], f"{where}.sizes") if "sizes" in d else None
    max_side = parse_rule(d["rule"], f"{where}.rule") if "rule" in d else 0
    if not defaults and not ("count" in d and "need" in d):
        raise ConfigError(f"{where}: catalog slots set both count and need")
    lo, hi = parse_count(d["count"], f"{where}.count") if "count" in d else STORE_COUNTS[store]
    need = parse_need(d.get("need", "optional"), f"{where}.need")
    return Slot(name, folder, store, sizes, max_side, lo, hi, need)


def no_shared_folders(slots: dict, where: str) -> None:
    seen: dict[str, str] = {}
    for s in slots.values():
        if s.folder in seen:
            raise ConfigError(f"{where}: slots {seen[s.folder]!r} and {s.name!r} both use folder {s.folder!r}")
        seen[s.folder] = s.name


def fits(slot: Slot, w: int, h: int) -> bool:
    return (w, h) in slot.sizes if slot.sizes is not None else play_rule(w, h, slot.max_side) is None


def load_catalog(path: Path = CATALOG) -> Catalog:
    """The harness defaults (references/store-slots.json), fully validated."""
    where = path.name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"{path}: {exc} (re-run harness sync if the file is missing)") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ConfigError(f"{where}: must be an object with \"version\": 1")
    unknown = sorted(set(data) - {"version", "checked", "note", "slots", "featureGraphic"})
    if unknown:
        raise ConfigError(f"{where}: unknown key(s): {', '.join(unknown)}")
    if not isinstance(data.get("slots"), dict) or not data["slots"]:
        raise ConfigError(f"{where}: \"slots\" must be a non-empty object")
    slots: dict[str, Slot] = {}
    render: dict[str, tuple] = {}
    for name, d in data["slots"].items():
        sw = f"{where}: slots.{name}"
        slots[name] = slot = new_slot(name, d, sw, SLOT_KEYS | {"render"}, defaults=False)
        aliases = d.get("render", {})
        if not isinstance(aliases, dict):
            raise ConfigError(f"{sw}.render: must be an object of size key -> \"WxH\"")
        for key, size in aliases.items():
            if not RENDER_KEY_RE.match(key) or key == "fg" or key in render:
                raise ConfigError(f"{sw}.render: {key!r} is not a free size key (lowercase, digits, '-'; not 'fg')")
            w, h = parse_size(size, f"{sw}.render.{key}")
            if not fits(slot, w, h):
                raise ConfigError(f"{sw}.render.{key}: {size} is not accepted by the slot itself")
            render[key] = (w, h, slot.store, slot.folder)
    no_shared_folders(slots, where)
    fg = data.get("featureGraphic")
    if not isinstance(fg, dict) or set(fg) != {"size", "file", "match"}:
        raise ConfigError(f"{where}: featureGraphic must have size, file and match")
    fg_size = parse_size(fg["size"], f"{where}: featureGraphic.size")
    for k in ("file", "match"):
        if not isinstance(fg[k], str) or not fg[k].startswith("play/") or ".." in fg[k].split("/"):
            raise ConfigError(f"{where}: featureGraphic.{k} must be a path under play/")
    return Catalog(slots, render, fg_size, fg["file"], fg["match"])


def merge_slots(base: dict, decl, where: str) -> dict:
    """The catalog's slots with a project's "slots" applied: new slots added, built-in ones adjusted."""
    if not isinstance(decl, dict):
        raise ConfigError(f"{where}: slots must be an object of slot name -> slot")
    slots = dict(base)
    for name, d in decl.items():
        sw = f"{where}: slots.{name}"
        if name not in base:
            slots[name] = new_slot(name, d, sw, SLOT_KEYS, defaults=True)
            continue
        if not isinstance(d, dict):
            raise ConfigError(f"{sw}: must be an object")
        extra = sorted(set(d) - OVERRIDE_KEYS)
        if extra:
            raise ConfigError(f"{sw}: a built-in slot takes only need, count and sizes (not {', '.join(extra)}); "
                              "add a new slot for a different folder or store")
        changes: dict = {}
        if "sizes" in d:  # exact sizes replace whatever constraint the slot had, a size rule included
            changes.update(sizes=parse_sizes(d["sizes"], f"{sw}.sizes"), max_side=0)
        if "count" in d:
            changes["lo"], changes["hi"] = parse_count(d["count"], f"{sw}.count")
        if "need" in d:
            changes["need"] = parse_need(d["need"], f"{sw}.need")
        slots[name] = dataclasses.replace(base[name], **changes)
    no_shared_folders(slots, where)
    return slots


@dataclass
class Finding:
    level: str  # ERROR | WARN | INFO
    code: str
    slot: str
    path: str
    message: str


@dataclass
class Report:
    mode: str
    stores: list
    supports_tablet: bool | None
    findings: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    def add(self, level: str, code: str, slot: str, path: str, message: str) -> None:
        self.findings.append(Finding(level, code, slot, path, message))

    def total(self, level: str) -> int:
        return sum(1 for f in self.findings if f.level == level)

    def to_json(self) -> str:
        return json.dumps({
            "mode": self.mode, "stores": self.stores, "supports_tablet": self.supports_tablet,
            "errors": self.total("ERROR"), "warnings": self.total("WARN"),
            "counts": self.counts, "findings": [asdict(f) for f in self.findings],
        }, indent=2)

    def to_text(self) -> str:
        lines = [f"mode: {self.mode}; stores: {', '.join(self.stores) or 'all found'}"]
        for name, n in self.counts.items():
            lines.append(f"{name}: {n} image(s)")
        for f in self.findings:
            where = f" {f.path}:" if f.path else ""
            lines.append(f"  {f.level:<6} [{f.code}]{where} {f.message}")
        lines.append(f"\n{self.total('ERROR')} error(s), {self.total('WARN')} warning(s)")
        return "\n".join(lines)


def has_alpha(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)


def play_rule(w: int, h: int, max_side: int) -> str | None:
    short, long_ = min(w, h), max(w, h)
    if short < 320 or long_ > max_side:
        return f"{w}x{h}: each side must be 320-{max_side} px"
    if long_ > 2 * short:
        return f"{w}x{h}: long side is more than twice the short side"
    return None


def open_image(report: Report, path: Path, slot: str, rel: str) -> Image.Image | None:
    """Fully decode the file; a corrupt or non-PNG/JPEG file is a finding, never a traceback."""
    try:
        with Image.open(path) as im:
            im.verify()
        im = Image.open(path)
        im.load()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        report.add("ERROR", "corrupt", slot, rel, f"cannot be decoded ({exc.__class__.__name__}: {exc})")
        return None
    if im.format not in ("PNG", "JPEG"):
        report.add("ERROR", "format", slot, rel, f"is {im.format}; the stores take PNG or JPEG")
        return None
    expected = "PNG" if path.suffix.lower() == ".png" else "JPEG"
    if im.format != expected:
        report.add("WARN", "format", slot, rel, f"is a {im.format} file with a {path.suffix} name")
    return im


def png_bit_depth(path: Path) -> int:
    """Bits per channel from the PNG header (Pillow reads 16-bit RGB as 8-bit RGB)."""
    with path.open("rb") as fh:
        head = fh.read(25)
    return head[24] if len(head) == 25 and head[12:16] == b"IHDR" else 8


def check_pixels(report: Report, im: Image.Image, slot: str, rel: str, path: Path, alpha_ok: bool = False) -> None:
    if im.mode == "CMYK":
        report.add("ERROR", "mode", slot, rel, "is CMYK; convert to RGB")
    elif im.mode in ("I", "I;16", "I;16B", "I;16L", "F") or (im.format == "PNG" and png_bit_depth(path) > 8):
        report.add("ERROR", "mode", slot, rel, f"is {im.mode} (more than 8 bits per channel); save as 8-bit RGB")
    elif im.mode in ("P", "L", "1") and not has_alpha(im):
        level = "ERROR" if report.mode == "release" else "WARN"
        report.add(level, "mode", slot, rel, f"is {im.mode} (palette/greyscale); the stores ask for 24-bit RGB")
    if not alpha_ok and has_alpha(im):
        report.add("ERROR", "alpha", slot, rel, f"has an alpha channel ({im.mode}); flatten to RGB")


def slot_images(report: Report, root: Path, folder: Path, slot: str) -> list:
    """Images a store would take from a folder; anything else is reported and ignored."""
    images = []
    for p in sorted(folder.iterdir()) if folder.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            continue
        if p.name.startswith(".") or ".raw." in p.name:
            report.add("WARN", "leftover", slot, rel, "ignored (hidden or intermediate render file); remove it before uploading")
        elif p.suffix.lower() not in IMAGE_SUFFIXES:
            report.add("WARN", "leftover", slot, rel, "ignored: only .png, .jpg and .jpeg files are checked")
        else:
            images.append(p)
    return images


def slot_required(slot: Slot, stores: list, supports_tablet: bool | None, tablet_slots: list) -> bool:
    if slot.store not in stores:
        return False
    if slot.need == "always":
        return True
    if slot.need == "tablet":
        return bool(supports_tablet)
    if slot.need == "declared":
        return slot.name in tablet_slots
    return False


def accepted(slot: Slot) -> str:
    portrait = sorted({(min(s), max(s)) for s in slot.sizes or ()})
    return ", ".join(f"{a}x{b}" for a, b in portrait) + " (or landscape)"


def check_slot(report: Report, root: Path, slot: Slot, required: bool, min_count: int) -> None:
    files = slot_images(report, root, root / slot.folder, slot.name)
    report.counts[slot.name] = len(files)
    if not files:
        if required:
            report.add("ERROR", "missing-slot", slot.name, slot.folder, "no images, but this slot is required for the declared stores")
        else:
            report.add("INFO", "empty-slot", slot.name, slot.folder, "no images (skipped)")
        return
    lo = max(slot.lo, min_count)
    if not lo <= len(files) <= slot.hi:
        report.add("ERROR", "count", slot.name, slot.folder, f"{len(files)} images; allowed {lo}-{slot.hi}")
    big = 0
    for f in files:
        rel = f.relative_to(root).as_posix()
        im = open_image(report, f, slot.name, rel)
        if im is None:
            continue
        w, h = im.size
        problem = None
        if slot.sizes is not None:  # exact sizes; never the size rule as well
            if (w, h) not in slot.sizes:
                problem = f"{w}x{h} is not an accepted {slot.name} size: {accepted(slot)}"
        else:
            problem = play_rule(w, h, slot.max_side)
        if problem:
            report.add("ERROR", "bad-size", slot.name, rel, problem)
        elif slot.store == "play" and slot.name == "play-phone":
            big += min(w, h) >= 1080 and max(w, h) * 9 == min(w, h) * 16
        elif slot.store == "play" and min(w, h) < 1080:
            report.add("WARN", "large-screen", slot.name, rel, f"{w}x{h}: short side under 1080 px; not eligible for large-screen recommendations")
        check_pixels(report, im, slot.name, rel, f)
        if f.stat().st_size > 8 * MB:
            report.add("ERROR", "size-mb", slot.name, rel, f"{f.stat().st_size / MB:.1f} MB (max 8 MB)")
        im.close()
    if slot.name == "play-phone" and big < 4:
        report.add("WARN", "recommendation", slot.name, slot.folder,
                   f"only {big} screenshot(s) at 9:16 with a short side of 1080+ px; 4 are needed for recommendation eligibility")


def feature_graphic_files(root: Path, catalog: Catalog) -> list:
    return sorted(p for p in root.glob(catalog.fg_match) if p.is_file())


def check_feature_graphic(report: Report, root: Path, catalog: Catalog, required: bool) -> None:
    hits = []
    want = catalog.feature_graphic
    for p in feature_graphic_files(root, catalog):
        if ".raw." in p.name or p.suffix.lower() not in IMAGE_SUFFIXES:
            report.add("WARN", "leftover", "play-feature-graphic", p.relative_to(root).as_posix(), "ignored (not a .png/.jpg feature graphic)")
        else:
            hits.append(p)
    report.counts["play-feature-graphic"] = len(hits)
    if not hits:
        level, code = ("ERROR", "missing-slot") if required else ("INFO", "empty-slot")
        report.add(level, code, "play-feature-graphic", "play/", f"no {catalog.fg_match}.png|jpg (required for Play)")
        return
    if len(hits) > 1:
        report.add("ERROR", "duplicate-feature-graphic", "play-feature-graphic", "play/",
                   f"{len(hits)} candidates ({', '.join(p.name for p in hits)}); keep exactly one")
    for f in hits:
        rel = f.relative_to(root).as_posix()
        im = open_image(report, f, "play-feature-graphic", rel)
        if im is None:
            continue
        if im.size != want:
            report.add("ERROR", "bad-size", "play-feature-graphic", rel, f"{im.size[0]}x{im.size[1]}; must be {want[0]}x{want[1]}")
        check_pixels(report, im, "play-feature-graphic", rel, f)
        im.close()


def check_unknown_folders(report: Report, root: Path, slots: dict, catalog: Catalog, stores: list) -> None:
    """Images no store check would see: a folder under play/ or ios/ that no slot reads."""
    folders = {s.folder for s in slots.values()}
    fg = set(feature_graphic_files(root, catalog))
    level = "ERROR" if report.mode == "release" else "WARN"
    for store in stores:
        top = root / store
        if not top.is_dir():
            continue
        for d in [top, *sorted(p for p in top.rglob("*") if p.is_dir())]:
            rel = d.relative_to(root).as_posix()
            if rel in folders:
                continue
            images = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
                      and not p.name.startswith(".") and ".raw." not in p.name and p not in fg]
            if images:
                report.add(level, "unknown-folder", "", rel + "/",
                           f"{len(images)} image(s) not checked: no slot reads this folder. Declare it in "
                           "store-assets.json \"slots\" (store, folder, sizes) or move the files")


def check_icon(report: Report, path: Path | None, store: str, required: bool) -> None:
    slot = f"{store}-icon"
    if path is None:
        if required:
            report.add("ERROR", "missing-slot", slot, "",
                       f"no {store} icon given (set {store}.icon in store-assets.json or pass --{store}-icon)")
        return
    shown = str(path)
    if not path.is_file():
        report.add("ERROR", "missing-slot", slot, shown, "not found")
        return
    im = open_image(report, path, slot, shown)
    if im is None:
        return
    want = ICON[store]
    if im.size != want:
        report.add("ERROR", "bad-size", slot, shown, f"{im.size[0]}x{im.size[1]}; must be {want[0]}x{want[1]}")
    # Play takes a 32-bit PNG with alpha; the App Store icon must be opaque.
    check_pixels(report, im, slot, shown, path, alpha_ok=(store == "play"))
    if store == "play" and path.stat().st_size > 1024 * 1024:
        report.add("ERROR", "size-mb", slot, shown, "over 1024 KB")
    im.close()


def load_config(path: Path, catalog: Catalog) -> tuple[dict, dict]:
    """(config, resolved slots) from a project's store-assets.json."""
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    if not isinstance(cfg, dict):
        raise ConfigError(f"{path}: must be a JSON object")
    for section in ("ios", "play"):
        if not isinstance(cfg.get(section, {}), dict):
            raise ConfigError(f"{path}: {section} must be an object")
    unknown = set(cfg) - CONFIG_KEYS
    unknown |= {f"ios.{k}" for k in set(cfg.get("ios") or {}) - IOS_KEYS}
    unknown |= {f"play.{k}" for k in set(cfg.get("play") or {}) - PLAY_KEYS}
    if unknown:
        raise ConfigError(f"{path}: unknown key(s): {', '.join(sorted(unknown))}")
    if cfg.get("version", 1) != 1:
        raise ConfigError(f"{path}: unsupported version {cfg.get('version')!r}")
    stores = cfg.get("stores", [])
    if not isinstance(stores, list) or not set(stores) <= set(STORES):
        raise ConfigError(f"{path}: stores must be a list of \"play\" and/or \"ios\"")
    slots = merge_slots(catalog.slots, cfg.get("slots", {}), str(path))
    play_slots = [n for n, s in slots.items() if s.store == "play"]
    tablet_slots = (cfg.get("play") or {}).get("tablet_slots", [])
    if not isinstance(tablet_slots, list):
        raise ConfigError(f"{path}: play.tablet_slots must be a list of Play slot names")
    resolved = []
    for t in tablet_slots:  # "tablet7" stays a short name for "play-tablet7"
        name = t if t in play_slots else f"play-{t}" if isinstance(t, str) and f"play-{t}" in play_slots else None
        if name is None:
            raise ConfigError(f"{path}: play.tablet_slots: unknown Play slot {t!r} (one of {', '.join(play_slots)})")
        resolved.append(name)
    cfg.setdefault("play", {})["tablet_slots"] = resolved
    st = (cfg.get("ios") or {}).get("supports_tablet")
    if st is not None and not isinstance(st, bool):
        raise ConfigError(f"{path}: ios.supports_tablet must be true or false")
    mins = cfg.get("min_counts", {})
    if not isinstance(mins, dict):
        raise ConfigError(f"{path}: min_counts must be an object")
    for name, n in mins.items():
        if name not in slots:
            raise ConfigError(f"{path}: min_counts: unknown slot {name!r} (one of {', '.join(slots)})")
        if not is_int(n) or not slots[name].lo <= n <= slots[name].hi:
            raise ConfigError(f"{path}: min_counts.{name} must be a whole number from {slots[name].lo} to {slots[name].hi}")
    return cfg, slots


def app_json_supports_tablet(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    ios = (data.get("expo", data) if isinstance(data, dict) else {}).get("ios") or {}
    return bool(ios.get("supportsTablet", False))  # Expo's default is false


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path, help="assets root containing play/ and/or ios/")
    parser.add_argument("--release", action="store_true", help="submission gate: required slots must be present")
    parser.add_argument("--config", type=Path, help="config file (default: <root>/store-assets.json if present)")
    parser.add_argument("--stores", help="comma-separated stores to check: play, ios (overrides the config)")
    parser.add_argument("--supports-tablet", action=argparse.BooleanOptionalAction, default=None,
                        help="the iOS app supports iPad (iPad 13\" screenshots required); overrides the config")
    parser.add_argument("--ios-icon", type=Path, help="1024x1024 App Store icon to check")
    parser.add_argument("--play-icon", type=Path, help="512x512 Play icon to check")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument("--catalog", type=Path, default=CATALOG, help=argparse.SUPPRESS)  # fixtures only
    args = parser.parse_args()
    if not args.root.is_dir():
        print(f"not a folder: {args.root}", file=sys.stderr)
        return 2

    try:
        catalog = load_catalog(args.catalog)
        cfg, base, slots = {}, args.root, catalog.slots
        config = args.config or (args.root / "store-assets.json")
        if args.config or config.is_file():
            (cfg, slots), base = load_config(config, catalog), config.resolve().parent
        ios_cfg, play_cfg = cfg.get("ios") or {}, cfg.get("play") or {}

        if args.stores is not None:
            stores = [s.strip() for s in args.stores.split(",") if s.strip()]
            if not stores or not set(stores) <= {"play", "ios"}:
                raise ConfigError("--stores takes play and/or ios")
        else:
            stores = list(cfg.get("stores", []))
        if args.release and not stores:
            raise ConfigError("--release needs the target stores: pass --stores or set \"stores\" in store-assets.json")

        supports_tablet = args.supports_tablet
        report_findings = []
        if supports_tablet is None:
            supports_tablet = ios_cfg.get("supports_tablet")
        if ios_cfg.get("app_json"):
            from_app = app_json_supports_tablet(base / ios_cfg["app_json"])
            if supports_tablet is None:
                supports_tablet = from_app
            elif supports_tablet != from_app:
                report_findings.append(("ERROR", "config", "ios-ipad13", ios_cfg["app_json"],
                                        f"supportsTablet is {str(from_app).lower()} in app.json but "
                                        f"{str(supports_tablet).lower()} for this check"))
        if args.release and "ios" in stores and supports_tablet is None:
            raise ConfigError("--release for ios needs to know about iPad: pass --[no-]supports-tablet, "
                              "or set ios.supports_tablet or ios.app_json in store-assets.json")
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    report = Report("release" if args.release else "inspect", stores, supports_tablet)
    for finding in report_findings:
        report.add(*finding)
    checked = stores or ["play", "ios"]
    tablet_slots = play_cfg.get("tablet_slots", [])
    mins = cfg.get("min_counts", {})
    for slot in slots.values():
        if slot.store not in checked:
            if any((args.root / slot.folder).glob("*")):
                report.add("INFO", "undeclared-store", slot.name, slot.folder, f"not checked: {slot.store} is not a declared store")
            continue
        required = args.release and slot_required(slot, stores, supports_tablet, tablet_slots)
        check_slot(report, args.root, slot, required, mins.get(slot.name, 0))
    if "play" in checked:
        check_feature_graphic(report, args.root, catalog, args.release and "play" in stores)
    check_unknown_folders(report, args.root, slots, catalog, checked)

    icons = {"ios": args.ios_icon or (base / ios_cfg["icon"] if ios_cfg.get("icon") else None),
             "play": args.play_icon or (base / play_cfg["icon"] if play_cfg.get("icon") else None)}
    for store, path in icons.items():
        # App Store Connect takes the icon from the build, so only Play's is a release requirement.
        required = args.release and store == "play" and "play" in stores
        if store in checked:
            check_icon(report, path, store, required)

    print(report.to_json() if args.json else report.to_text())
    return 1 if report.total("ERROR") else 0


if __name__ == "__main__":
    raise SystemExit(main())
