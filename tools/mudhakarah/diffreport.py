"""The readable diff report (spec section 4): the page chrome and the data line
are compared separately, so app-code changes are not buried in 260 KB of data."""
import difflib
import json

from .output import DATA_PREFIX, data_lines

PLACEHOLDER = DATA_PREFIX + "…;  (data line, compared separately below)"


def _split(text):
    idx, lines = data_lines(text)
    data = None
    if len(idx) == 1:
        raw = lines[idx[0]]
        try:
            data = json.loads(raw[len(DATA_PREFIX):-1])
        except ValueError:
            data = None
        lines = list(lines)
        lines[idx[0]] = PLACEHOLDER
    return lines, data


def _data_changes(old, new, path="D", out=None, limit=200):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(old, dict) and isinstance(new, dict):
        if list(old) != list(new):
            out.append(f"{path}: keys {list(old)} -> {list(new)}")
        for k in new:
            if k in old:
                _data_changes(old[k], new[k], f"{path}.{k}", out, limit)
    elif isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            out.append(f"{path}: {len(old)} items -> {len(new)} items")
        for i, (a, b) in enumerate(zip(old, new)):
            _data_changes(a, b, f"{path}[{i}]", out, limit)
    elif type(old) is not type(new) or old != new:
        out.append(f"{path}: {json.dumps(old, ensure_ascii=False)[:120]} -> {json.dumps(new, ensure_ascii=False)[:120]}")
    return out


def diff_report(old_text, new_text, label):
    old_lines, old_data = _split(old_text)
    new_lines, new_data = _split(new_text)
    parts = [f"# Build diff: {label}", ""]
    chrome = list(difflib.unified_diff(old_lines, new_lines, "committed", "built", lineterm="", n=2))
    parts += ["## Page outside the data line", ""]
    parts += chrome if chrome else ["No differences."]
    parts += ["", "## Data line", ""]
    if old_data is None or new_data is None:
        parts.append("One side has no readable data line.")
    else:
        changes = _data_changes(old_data, new_data)
        parts += changes if changes else ["No differences."]
    return "\n".join(parts) + "\n"
