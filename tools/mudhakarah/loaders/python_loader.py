"""The Python content loader (spec section 2).

It executes the files listed in book.json, in the listed order, in one fresh
namespace, exactly as the legacy build.py did, and returns raw content: the named
structures the files define. The files are never edited. exec() is not a sandbox;
content files are written by the team and reviewed in pull requests, and the
loader runs before anything is written.
"""
import hashlib
from pathlib import Path

from ..errors import BLOCKING, WARNING, BuildStopped, Finding


def _looks_like_content(value):
    """An unmapped upper-case symbol is reported only if it looks like content:
    a non-empty list or dict holding dictionaries (helpers such as EXAM or CUR are not)."""
    if isinstance(value, dict):
        return bool(value) and any(isinstance(v, (dict, list)) for v in value.values())
    if isinstance(value, list):
        return any(isinstance(v, dict) for v in value)
    return False


def load_python_content(repo_root, slug, book):
    content = book["content"]
    folder = Path(repo_root) / "books" / slug / "content"
    where = f"books/{slug}/content"
    findings = []
    hashes = {}
    ns = {}
    for name in content["files"]:
        path = folder / name
        if not path.is_file():
            findings.append(Finding("V2.missing-file", BLOCKING, f"content file '{name}' not found", where))
            continue
        raw = path.read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        try:
            code = compile(raw.decode("utf-8"), str(path), "exec")
            exec(code, ns)  # noqa: S102 - reviewed content files, see module docstring
        except Exception as e:  # any error in a content file stops the build
            findings.append(Finding("V2.content-error", BLOCKING,
                                    f"{type(e).__name__} while running '{name}': {e}", where))
            raise BuildStopped("content loading", findings)
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("content loading", findings)

    raw_content = {}
    mapped = set()
    for field, symbol in content["symbols"].items():
        mapped.add(symbol)
        if symbol not in ns:
            findings.append(Finding("V2.missing-symbol", BLOCKING,
                                    f"symbol '{symbol}' (for '{field}') is not defined by the content files", where))
        else:
            raw_content[field] = ns[symbol]
    chapters = []
    for ch in content["chapters"]:
        mapped.add(ch["symbol"])
        if ch["symbol"] not in ns:
            findings.append(Finding("V2.missing-symbol", BLOCKING,
                                    f"chapter symbol '{ch['symbol']}' is not defined", where))
        else:
            chapters.append(ns[ch["symbol"]])
    raw_content["chapters"] = chapters
    extras = {}
    for symbol in content.get("extras", []):
        mapped.add(symbol)
        if symbol not in ns:
            findings.append(Finding("V2.missing-symbol", BLOCKING, f"extra symbol '{symbol}' is not defined", where))
        else:
            extras[symbol] = ns[symbol]
    raw_content["extras"] = extras

    # a symbol whose object is already part of a mapped structure (a section that a chapter
    # lists, for example) is in the page, so it is not reported
    reachable = set()
    stack = [ns[s] for s in mapped if s in ns]
    while stack:
        x = stack.pop()
        if id(x) in reachable or not isinstance(x, (dict, list)):
            continue
        reachable.add(id(x))
        stack.extend(x.values() if isinstance(x, dict) else x)
    for symbol, value in ns.items():
        if symbol.isupper() and not symbol.startswith("_") and symbol not in mapped and _looks_like_content(value) \
                and id(value) not in reachable:
            findings.append(Finding("V2.unmapped-symbol", WARNING,
                                    f"content symbol '{symbol}' is defined but not mapped in book.json, "
                                    "so it is not in the page", where))
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("content loading", findings)
    return raw_content, hashes, findings
