"""V2 Content structure (blocking): chapters contain sections contain topics; each
block has a label and text, a list or a table; cards have a front, back and
category; tables' rows match their headers; maps have a known type; no empty text.
Question types and options are checked by the assembler's type registry (model.py)."""
from ..errors import BLOCKING, Finding

MAP_TYPES = ("tree", "timeline", "chains")  # the map renderers in the app script


def _text(v):
    return isinstance(v, str) and v.strip() != ""


def check(raw, where):
    out = []

    def bad(msg):
        out.append(Finding("V2.structure", BLOCKING, msg, where))

    if not isinstance(raw.get("chapters"), list) or not raw["chapters"]:
        bad("the book has no chapters")
        return out
    for ci, ch in enumerate(raw["chapters"], 1):
        if not isinstance(ch, dict) or not _text(ch.get("id")) or not _text(ch.get("title")):
            bad(f"chapter {ci} needs an id and a title")
            continue
        sections = ch.get("sections")
        if not isinstance(sections, list) or not sections:
            bad(f"chapter {ch['id']} has no sections")
            continue
        for s in sections:
            if not isinstance(s, dict) or not _text(s.get("id")) or not _text(s.get("title")):
                bad(f"chapter {ch['id']}: a section needs an id and a title")
                continue
            topics = s.get("topics")
            if not isinstance(topics, list) or not topics:
                bad(f"section {s['id']} has no topics")
                continue
            for t in topics:
                if not isinstance(t, dict) or not _text(t.get("id")) or not _text(t.get("title")):
                    bad(f"section {s['id']}: a topic needs an id and a title")
                    continue
                for bi, b in enumerate(t.get("blocks") or [], 1):
                    loc = f"topic {t['id']}, block {bi}"
                    if not isinstance(b, dict) or not _text(b.get("label")):
                        bad(f"{loc} needs a label")
                        continue
                    has = [k for k in ("text", "list", "table", "ayah") if k in b]
                    if not has:
                        bad(f"{loc} needs text, a list, an ayah or a table")
                    if "text" in b and not _text(b["text"]):
                        bad(f"{loc} has empty text")
                    if "ayah" in b and not _text(b["ayah"]):
                        bad(f"{loc} has an empty ayah")
                    if "list" in b and (not isinstance(b["list"], list) or not b["list"]
                                        or not all(_text(x) for x in b["list"])):
                        bad(f"{loc} has an empty list or an empty list item")
    for i, c in enumerate(raw.get("cards", []), 1):
        if not all(_text(c.get(k)) for k in ("q", "a", "cat")):
            bad(f"card {i} needs a front (q), a back (a) and a category (cat)")
    for i, q in enumerate(raw.get("questions", []), 1):
        if not _text(q.get("q")):
            bad(f"question {i} has an empty stem")
    for i, e in enumerate(raw.get("examples", []), 1):
        if not _text(e.get("ayah")) or not _text(e.get("detail")):
            bad(f"example {i} needs its text (ayah) and detail")
    for i, tb in enumerate(raw.get("tables", []), 1):
        headers = tb.get("headers")
        if not _text(tb.get("title")) or not isinstance(headers, list) or not headers:
            bad(f"table {i} needs a title and headers")
            continue
        for ri, row in enumerate(tb.get("rows") or [], 1):
            if not isinstance(row, list) or len(row) != len(headers):
                bad(f"table {i}, row {ri} has {len(row) if isinstance(row, list) else 0} cells for "
                    f"{len(headers)} headers")
    for i, m in enumerate(raw.get("maps", []), 1):
        book4_map = (_text(m.get("centerTitle")) and _text(m.get("centerSub"))
                     and isinstance(m.get("branches"), list) and m["branches"]
                     and all(_text(b.get("title")) and _text(b.get("badge")) and _text(b.get("summary"))
                             and isinstance(b.get("items"), list) and b["items"]
                             and all(_text(item) for item in b["items"]) and _text(b.get("modalDetails"))
                             for b in m["branches"]))
        if m.get("type") not in MAP_TYPES and not book4_map:
            bad(f"map {i} has unknown type '{m.get('type')}' and does not match the preserved Book 4 map shape")
        if not _text(m.get("title")):
            bad(f"map {i} needs a title")
    for i, cap in enumerate(raw.get("capsules", []), 1):
        if not _text(cap.get("title")) or not isinstance(cap.get("items"), list) or not cap["items"]:
            bad(f"capsule {i} needs a title and items")
    return out
