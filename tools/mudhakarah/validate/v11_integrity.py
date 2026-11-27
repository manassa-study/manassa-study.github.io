"""V11 Content integrity.

Blocking: the build never modifies a content file (hashes before and after), and in
step 1 the data line equals the baseline page's data line byte for byte.
Report (never blocks): after step 1, a content-change report lists every added,
removed or changed lesson block, card, question, map, table, example and capsule,
with matn quotations and Qur'an fields in their own section."""
import json

from ..errors import BLOCKING, Finding
from ..output import DATA_PREFIX, data_lines


def files_unchanged(before, after, where):
    out = []
    for name, digest in before.items():
        if after.get(name) != digest:
            out.append(Finding("V11.content-modified", BLOCKING,
                               f"content file '{name}' changed while the book was being built", where))
    return out


def data_line(text):
    idx, lines = data_lines(text)
    return lines[idx[0]] if len(idx) == 1 else None


def step1_data_identity(built_text, baseline_text, where):
    if data_line(built_text) != data_line(baseline_text):
        return [Finding("V11.data-changed", BLOCKING,
                        "step 1: the data line differs from the baseline page's data line", where)]
    return []


# ---------------------------------------------------------------- content-change report

def _short(x, n=160):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def _keyed(items, key):
    return {x.get(key): x for x in items}


def _blocks(model):
    out = {}
    for ch in model["DEEP_STUDY_DATA"]:
        for s in ch["sections"]:
            for t in s["topics"]:
                for i, b in enumerate(t.get("blocks") or []):
                    out[(t["id"], i)] = b
                out[(t["id"], "sum")] = t.get("sum")
    return out


def _compare(name, old, new, lines, sensitive):
    for k in new:
        if k not in old:
            lines.append(f"- {name} {k}: added: {_short(new[k])}")
    for k in old:
        if k not in new:
            lines.append(f"- {name} {k}: removed: {_short(old[k])}")
    for k in new:
        if k in old and old[k] != new[k]:
            lines.append(f"- {name} {k}: changed")
            for field in sorted(set(old[k]) | set(new[k])) if isinstance(new[k], dict) and isinstance(
                    old[k], dict) else [None]:
                a = old[k].get(field) if field else old[k]
                b = new[k].get(field) if field else new[k]
                if a != b:
                    label = f"`{field}`" if field else "value"
                    lines.append(f"  - {label}: {_short(a)} → {_short(b)}")
                    if sensitive(k, field, new[k]):
                        lines.append("    (matn or Qur'an field: listed again below)")


def content_change_report(old, new, label):
    """Markdown. `old` and `new` are book models (the committed page's data and a fresh build)."""
    lines = [f"# Content changes: {label}", ""]
    if old is None:
        return "\n".join(lines + ["No previous page to compare with."]) + "\n"
    body = []
    special = []

    def matn(k, field, item):
        return isinstance(item, dict) and "المتن" in str(item.get("label", ""))

    def quran(k, field, item):
        return field in ("ayah", "surah")

    _compare("Lesson block", _blocks(old), _blocks(new), body, matn)
    _compare("Card", _keyed(old["FLASHCARDS"], "id"), _keyed(new["FLASHCARDS"], "id"), body, lambda *a: False)
    _compare("Question", _keyed(old["QUIZ_BANK"], "id"), _keyed(new["QUIZ_BANK"], "id"), body, lambda *a: False)
    _compare("Map", dict(enumerate(old["MIND_MAPS"])), dict(enumerate(new["MIND_MAPS"])), body, lambda *a: False)
    _compare("Table", dict(enumerate(old["COMPARISON_TABLES"])), dict(enumerate(new["COMPARISON_TABLES"])), body,
             lambda *a: False)
    _compare("Example", dict(enumerate(old["QURANIC_EXAMPLES"])), dict(enumerate(new["QURANIC_EXAMPLES"])), body,
             quran)
    _compare("Capsule", dict(enumerate(old["CAPSULES"])), dict(enumerate(new["CAPSULES"])), body, lambda *a: False)
    ob, nb = _blocks(old), _blocks(new)
    for k in nb:
        if matn(k, None, nb[k]) and ob.get(k) != nb[k]:
            special.append(f"- Matn, topic {k[0]} block {k[1] + 1 if isinstance(k[1], int) else k[1]}: "
                           f"{_short(ob.get(k, {}).get('text') if isinstance(ob.get(k), dict) else None, 400)} → "
                           f"{_short(nb[k].get('text'), 400)}")
    oe, ne = dict(enumerate(old["QURANIC_EXAMPLES"])), dict(enumerate(new["QURANIC_EXAMPLES"]))
    for k in ne:
        o = oe.get(k, {})
        for f in ("ayah", "surah"):
            if o.get(f) != ne[k].get(f):
                special.append(f"- Example {k}, `{f}`: {_short(o.get(f), 400)} → {_short(ne[k].get(f), 400)}")
    lines += ["## Changes", ""] + (body or ["No content changes."])
    lines += ["", "## Matn quotations and Qur'an fields", ""] + (special or ["None changed."])
    return "\n".join(lines) + "\n"
