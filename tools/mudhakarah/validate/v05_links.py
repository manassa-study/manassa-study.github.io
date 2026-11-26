"""V5 Internal links (blocking): any in-text `#study-…` or `#maps-…` link points to
something that exists. (Every item's `topic` is checked by the assembler.)"""
import json
import re

from ..errors import BLOCKING, Finding

LINK = re.compile(r"#(study|maps)-([A-Za-z0-9_-]+)")


def check(model, where):
    out = []
    topics = {t["id"] for ch in model["DEEP_STUDY_DATA"] for s in ch["sections"] for t in s["topics"]}
    n_maps = len(model["MIND_MAPS"])
    text = json.dumps(model, ensure_ascii=False)
    for kind, target in LINK.findall(text):
        if kind == "study" and target not in topics:
            out.append(Finding("V5.link", BLOCKING, f"link #study-{target} points to no topic", where))
        if kind == "maps" and not (target.isdigit() and int(target) < n_maps):
            out.append(Finding("V5.link", BLOCKING, f"link #maps-{target} points to no map", where))
    return out
