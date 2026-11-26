"""Configuration loading and validation (spec section 3; validator V1).

Plain Python, no schema library (spec section 7). Unknown fields are rejected so a
mistyped name fails instead of being ignored. The checks against the ID lock
(storage_key and output must equal the lock) are added by the ID system.
"""
import json
import re
from pathlib import Path

from .errors import BLOCKING, Finding

SCHEMA_VERSION = 1

# Folders a generated book page may be written to. A platform rule, kept in code
# so a book cannot widen it (spec section 5, stage 1).
PUBLISHED_BOOK_FOLDERS = ("fiqh/", "hadith/", "mantiq/")

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLOUR_RE = re.compile(r"^#[0-9a-f]{6}$")
THEME_TOKENS = ("accent", "accent_ink", "accent_soft", "hero_1", "hero_2",
                "paper", "surface", "surface_2", "line")
CONTENT_SYMBOL_FIELDS = ("meta", "cards", "questions", "examples", "tables", "maps", "capsules")


# --- small typed field description -------------------------------------------------

class F:
    """One field: its type, whether it is required, and an optional extra check."""

    def __init__(self, kind, required=True, check=None, fields=None, items=None):
        self.kind = kind          # "str", "int", "bool", "list", "dict"
        self.required = required
        self.check = check        # callable(value) -> error message or None
        self.fields = fields      # for dicts with fixed keys
        self.items = items        # for lists: F describing each item


_TYPES = {"str": str, "int": int, "bool": bool, "list": list, "dict": dict}


def _check(value, spec, path, where, out):
    expected = _TYPES[spec.kind]
    if spec.kind == "int" and isinstance(value, bool):
        ok = False
    else:
        ok = isinstance(value, expected)
    if not ok:
        out.append(Finding("V1.type", BLOCKING,
                           f"'{path}' must be {spec.kind}, found {type(value).__name__}", where))
        return
    if spec.kind == "str" and spec.check is None and value == "":
        out.append(Finding("V1.empty", BLOCKING, f"'{path}' must not be empty", where))
    if spec.check:
        msg = spec.check(value)
        if msg:
            out.append(Finding("V1.value", BLOCKING, f"'{path}': {msg}", where))
    if spec.kind == "dict" and spec.fields is not None:
        _check_fields(value, spec.fields, path + ".", where, out)
    if spec.kind == "list" and spec.items is not None:
        for i, item in enumerate(value):
            _check(item, spec.items, f"{path}[{i}]", where, out)


def _check_fields(obj, fields, prefix, where, out):
    for key in obj:
        if key not in fields:
            out.append(Finding("V1.unknown-field", BLOCKING,
                               f"unknown field '{prefix}{key}' (check the spelling; unknown fields are not allowed)",
                               where))
    for key, spec in fields.items():
        if key not in obj:
            if spec.required:
                out.append(Finding("V1.missing-field", BLOCKING, f"required field '{prefix}{key}' is missing", where))
            continue
        _check(obj[key], spec, prefix + key, where, out)


def _colour(v):
    return None if COLOUR_RE.match(v) else f"'{v}' is not a lowercase #rrggbb colour"


def _schema_version(v):
    return None if v == SCHEMA_VERSION else f"unsupported schema_version {v} (expected {SCHEMA_VERSION})"


def _https(v):
    return None if v.startswith("https://") else "must be an https:// address"


def _nonempty_list(v):
    return None if v else "must not be empty"


def _symbol(v):
    return None if re.match(r"^[A-Z][A-Z0-9_]*$", v) else f"'{v}' is not an upper-case content symbol"


def _theme_mode():
    return F("dict", fields={t: F("str", check=_colour) for t in THEME_TOKENS})


SITE_FIELDS = {
    "schema_version": F("int", check=_schema_version),
    "base_url": F("str", check=lambda v: None if v.startswith("https://") and v.endswith("/") else
                  "must be an https:// address ending in /"),
    "platform_name": F("str"),
    "report_script_url": F("str", check=_https),
    "fonts_url": F("str", check=_https),
    "supabase_url": F("str", check=_https),
    "supabase_publishable_key": F("str", check=lambda v: None if v.startswith("sb_publishable_") else
                                  "must be a publishable key (never a secret key)"),
}

BOOK_FIELDS = {
    "schema_version": F("int", check=_schema_version),
    "slug": F("str", check=lambda v: None if SLUG_RE.match(v) else
              "use lowercase letters, digits and hyphens"),
    "title": F("str"),
    "output": F("str", check=lambda v: None if (v.endswith(".html") and v.startswith(PUBLISHED_BOOK_FOLDERS)
                                                and ".." not in v and not v.startswith("/")) else
                f"must be an .html path under one of {', '.join(PUBLISHED_BOOK_FOLDERS)}"),
    "og_image": F("str", check=lambda v: None if not v.startswith(("/", "http")) and ".." not in v else
                  "must be a repository-relative path"),
    "description": F("str"),
    "storage_key": F("str"),
    "welcome_session_key": F("str"),
    "brand_mark": F("str"),
    "page_range": F("str"),
    "structure_summary": F("str"),
    "content": F("dict", fields={
        "loader": F("str", check=lambda v: None if v == "python" else "only the 'python' loader exists in Phase 1"),
        "files": F("list", check=_nonempty_list, items=F("str", check=lambda v: None if (
            v.endswith(".py") and "/" not in v and ".." not in v) else "must be a .py file name inside content/")),
        "symbols": F("dict", fields={k: F("str", check=_symbol) for k in CONTENT_SYMBOL_FIELDS}),
        "chapters": F("list", check=_nonempty_list, items=F("dict", fields={
            "symbol": F("str", check=_symbol), "quiz_name": F("str")})),
        "extras": F("list", required=False, items=F("str", check=_symbol)),
    }),
    "quiz": F("dict", fields={
        "shuffle": F("str", check=lambda v: None if v == "sequential" else
                     "only 'sequential' (today's order) is defined; option order comes from the ID lock"),
        "seed": F("int"),
    }),
    "labels": F("dict", fields={
        "examples_title": F("str"), "examples_short": F("str"), "examples_count_noun": F("str"),
        "examples_in_lesson": F("str"), "review_subtitle": F("str"),
    }),
    "welcome": F("dict", fields={"aim": F("str"), "study_line": F("str")}),
    "search": F("dict", fields={"placeholder": F("str"),
                                "suggestions": F("list", check=_nonempty_list, items=F("str"))}),
    "theme": F("dict", fields={"light": _theme_mode(), "dark": _theme_mode(),
                               "browser_theme_color": F("str", check=_colour)}),
    "features": F("dict", required=False, fields={"dedication_card": F("bool", required=False)}),
    "quran_check": F("dict", required=False, fields={
        "markers": F("bool", required=False),
        "fields": F("list", required=False, items=F("dict", fields={
            "collection": F("str"), "text": F("str"), "reference": F("str", required=False)})),
    }),
}


# --- public API -------------------------------------------------------------------

def read_json(path):
    """Read a JSON file; return (data, findings)."""
    path = Path(path)
    where = str(path)
    if not path.is_file():
        return None, [Finding("V1.missing-file", BLOCKING, "file not found", where)]
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, [Finding("V1.encoding", BLOCKING, "file is not UTF-8", where)]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, [Finding("V1.json", BLOCKING, f"invalid JSON: {e}", where)]
    if not isinstance(data, dict):
        return None, [Finding("V1.json", BLOCKING, "top level must be an object", where)]
    return data, []


def validate_site(site, where="platform/site.json"):
    out = []
    _check_fields(site, SITE_FIELDS, "", where, out)
    return out


def validate_book(book, folder_name=None, where="book.json"):
    out = []
    _check_fields(book, BOOK_FIELDS, "", where, out)
    if folder_name is not None and isinstance(book.get("slug"), str) and book["slug"] != folder_name:
        out.append(Finding("V1.slug-folder", BLOCKING,
                           f"slug '{book['slug']}' must equal its folder name '{folder_name}'", where))
    content = book.get("content")
    if isinstance(content, dict) and isinstance(content.get("chapters"), list):
        names = [c.get("quiz_name") for c in content["chapters"] if isinstance(c, dict)]
        syms = [c.get("symbol") for c in content["chapters"] if isinstance(c, dict)]
        if len(set(names)) != len(names):
            out.append(Finding("V1.duplicate-chapter", BLOCKING, "chapter quiz names must be unique", where))
        if len(set(syms)) != len(syms):
            out.append(Finding("V1.duplicate-chapter", BLOCKING, "chapter symbols must be unique", where))
    if isinstance(content, dict) and isinstance(content.get("files"), list):
        if len(set(content["files"])) != len(content["files"]):
            out.append(Finding("V1.duplicate-file", BLOCKING, "content files must be listed once", where))
    return out


def load_site(repo_root):
    path = Path(repo_root) / "platform" / "site.json"
    data, findings = read_json(path)
    if data is not None:
        findings += validate_site(data, where="platform/site.json")
    return data, findings


def load_book(repo_root, slug):
    folder = Path(repo_root) / "books" / slug
    where = f"books/{slug}/book.json"
    data, findings = read_json(folder / "book.json")
    if data is not None:
        findings += validate_book(data, folder_name=slug, where=where)
    return data, findings


def discover_books(repo_root):
    """Every folder under books/ that holds a book.json, in name order."""
    base = Path(repo_root) / "books"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if (p / "book.json").is_file())
