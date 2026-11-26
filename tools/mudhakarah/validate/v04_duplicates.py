"""V4 Duplicates. Blocking: duplicate topic, section, chapter or map IDs (exact
duplicate fingerprints are found during ID binding, mudhakarah.ids). Warning: the
same normalized card front or question stem under different topics."""
from collections import defaultdict

from ..errors import BLOCKING, WARNING, Finding
from ..normalize import normalize


def check(raw, where):
    out = []
    kinds = {"chapter": [], "section": [], "topic": []}
    for ch in raw["chapters"]:
        kinds["chapter"].append(ch.get("id"))
        for s in ch.get("sections", []):
            kinds["section"].append(s.get("id"))
            for t in s.get("topics", []):
                kinds["topic"].append(t.get("id"))
    kinds["map"] = [m.get("id") for m in raw.get("maps", [])]
    for kind, ids in kinds.items():
        seen = set()
        for i in ids:
            if i in seen:
                out.append(Finding("V4.duplicate-id", BLOCKING, f"{kind} ID '{i}' is used more than once", where))
            seen.add(i)
    for kind, items in (("card front", raw.get("cards", [])), ("question stem", raw.get("questions", []))):
        topics = defaultdict(set)
        for x in items:
            topics[normalize(x.get("q"))].add(x.get("topic"))
        for text, ts in topics.items():
            if len(ts) > 1:
                out.append(Finding("V4.near-duplicate", WARNING,
                                   f"the same {kind} appears under topics {', '.join(sorted(map(str, ts)))}: "
                                   f"«{text[:60]}»", where))
    return out
