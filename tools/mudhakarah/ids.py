"""The ID lock (spec section 6): bootstrap, binding, review, apply and invariants.

Principles: the lock, not position, decides every card and question ID; the build
reads the lock and never writes it; anything that can't be matched with certainty
stops the build; only a person, through `ids review` and `ids apply`, binds, adds,
retires or restores an ID; an ID is never reused.
"""
import difflib
import json
import random
from pathlib import Path

from .errors import BLOCKING, WARNING, BuildStopped, Finding
from .model import TRUE_FALSE_OPTIONS, TYPE_REGISTRY, sequential_orders, source_options, type_key
from .normalize import (ALGORITHM, CARD_FIELDS, NORMALIZATION, QUESTION_FIELDS, card_fingerprint,
                        content_hash, normalize, question_fingerprint, shown_hash)

LOCK_NAME = "ids.lock.json"
SCHEMA_VERSION = 1
CARD_NON_CONTENT = ("id",)  # a card's `id` in the source is positional; the lock replaces it
COLLECTIONS = ("cards", "questions")
DECISIONS = {
    "unbound": {"same", "new"},
    "missing": {"same", "retire"},
    "retired-match": {"restore", "new"},
    "duplicate": {"group"},
    "new-topic": {"new"},
    "reordered-options": {"keep-display"},
    "content-changed": {"accept"},
}


# ---------------------------------------------------------------- items

def has_options(q):
    return TYPE_REGISTRY[type_key(q)]["shape"] == "options"


def correct_text(q):
    if has_options(q):
        return q["correct"]
    return TRUE_FALSE_OPTIONS[0] if q["tf"] else TRUE_FALSE_OPTIONS[1]


def raw_items(raw):
    """The cards and questions of raw content with their fingerprints and content hashes."""
    cards = [{"pos": i, "topic": c.get("topic"), "fp": card_fingerprint(c.get("topic"), c.get("q")),
              "content": content_hash(c, CARD_NON_CONTENT), "raw": c} for i, c in enumerate(raw["cards"])]
    questions = []
    for i, q in enumerate(raw["questions"]):
        opts = source_options(q) if has_options(q) else None
        questions.append({"pos": i, "topic": q.get("topic"),
                          "fp": question_fingerprint(q.get("topic"), type_key(q), q.get("q"), opts, correct_text(q)),
                          "content": content_hash(q), "raw": q})
    return {"cards": cards, "questions": questions}


def content_topics(raw):
    return [t["id"] for ch in raw["chapters"] for s in ch["sections"] for t in s["topics"]]


def seeded_order(seed, qid, n):
    """A new question's option order: its own sequence, seeded with quiz.seed plus its ID."""
    order = list(range(n))
    random.Random(seed + qid).shuffle(order)
    return order


# ---------------------------------------------------------------- lock file

def lock_path(repo_root, slug):
    return Path(repo_root) / "books" / slug / LOCK_NAME


def dumps_lock(lock):
    """Stable, review-friendly JSON: one item per line inside the item lists."""
    def compact(x):
        return json.dumps(x, ensure_ascii=False, separators=(", ", ": "))

    out = ["{"]
    keys = list(lock)
    for n, key in enumerate(keys):
        value = lock[key]
        end = "," if n < len(keys) - 1 else ""
        if key in COLLECTIONS:
            out.append(f'  "{key}": {{')
            out.append(f'    "next_id": {value["next_id"]},')
            items = value["items"]
            if items:
                out.append('    "items": [')
                out += [f"      {compact(it)}{',' if i < len(items) - 1 else ''}" for i, it in enumerate(items)]
                out.append("    ]")
            else:
                out.append('    "items": []')
            out.append(f"  }}{end}")
        elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            out.append(f'  "{key}": [')
            out += [f"    {compact(v)}{',' if i < len(value) - 1 else ''}" for i, v in enumerate(value)]
            out.append(f"  ]{end}")
        else:
            out.append(f'  "{key}": {json.dumps(value, ensure_ascii=False)}{end}')
    out.append("}")
    return "\n".join(out) + "\n"


def read_lock(repo_root, slug):
    path = lock_path(repo_root, slug)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def empty_lock(book):
    return {
        "schema_version": SCHEMA_VERSION,
        "book": book["slug"],
        "storage_key": book["storage_key"],
        "output": book["output"],
        "fingerprint": {"algorithm": ALGORITHM, "normalization": NORMALIZATION,
                        "cards": list(CARD_FIELDS), "questions": list(QUESTION_FIELDS)},
        "bootstrap": None,
        "topics": [],
        "chapters": [],
        "maps": [],
        "cards": {"next_id": 1, "items": []},
        "questions": {"next_id": 1, "items": []},
        "duplicate_groups": [],
        "changes": [],
    }


def check_lock_identity(lock, book, where):
    """V1/V3: storage key and output path never change; the lock's settings are the tool's."""
    out = []
    if lock.get("schema_version") != SCHEMA_VERSION:
        out.append(Finding("V3.lock-schema", BLOCKING, f"unsupported lock schema_version {lock.get('schema_version')}",
                           where))
    if lock.get("storage_key") != book.get("storage_key"):
        out.append(Finding("V3.storage-key", BLOCKING,
                           f"storage_key '{book.get('storage_key')}' differs from the lock's "
                           f"'{lock.get('storage_key')}'; changing it would reset every student's progress", where))
    if lock.get("output") != book.get("output"):
        out.append(Finding("V3.output-path", BLOCKING,
                           f"output '{book.get('output')}' differs from the lock's '{lock.get('output')}'; "
                           "the published address must not change", where))
    fpcfg = lock.get("fingerprint", {})
    if (fpcfg.get("algorithm"), fpcfg.get("normalization"), fpcfg.get("cards"), fpcfg.get("questions")) != \
            (ALGORITHM, NORMALIZATION, CARD_FIELDS, QUESTION_FIELDS):
        out.append(Finding("V3.fingerprint-settings", BLOCKING,
                           "the lock's fingerprint settings differ from the tool's; a normalization change "
                           "needs a new version and a migration", where))
    return out


# ---------------------------------------------------------------- binding

def _suggest(missing_items, unbound_items, collection):
    """F3: pair missing and unbound items in the same topic, ranked by stem similarity and,
    for questions, option overlap. Never applied automatically."""
    out = {}
    for u in unbound_items:
        ranked = []
        for m in missing_items:
            if m["topic"] != u["topic"]:
                continue
            stem = difflib.SequenceMatcher(None, normalize(m["q"]), normalize(u["q"])).ratio()
            overlap = 0.0
            if collection == "questions":
                a = {normalize(o) for o in m.get("options") or []}
                b = {normalize(o) for o in u.get("options") or []}
                overlap = len(a & b) / len(a | b) if (a | b) else 1.0
            ranked.append((round(overlap + stem, 6), m["id"]))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        out[u["case"]] = [{"id": i, "score": s} for s, i in ranked[:3]]
    return out


def _view(collection, raw_item):
    """The item as a reviewer needs to see it."""
    if collection == "cards":
        return {"topic": raw_item.get("topic"), "q": raw_item.get("q"), "a": raw_item.get("a")}
    q = raw_item
    return {"topic": q.get("topic"), "type": q.get("type"), "q": q.get("q"),
            "options": source_options(q), "correct": correct_text(q)}


def previous_views(previous):
    """Old items by ID, from the data of the committed page (the lock holds no text)."""
    if not previous:
        return {"cards": {}, "questions": {}}
    cards = {c["id"]: {"topic": c.get("topic"), "q": c.get("q"), "a": c.get("a")}
             for c in previous.get("FLASHCARDS", [])}
    questions = {q["id"]: {"topic": q.get("topic"), "type": q.get("type"), "q": q.get("q"),
                           "options": q.get("options"), "correct": q["options"][q["correct"]]}
                 for q in previous.get("QUIZ_BANK", [])}
    return {"cards": cards, "questions": questions}


def bind(raw, book, lock, where, previous=None):
    """Bind content items to lock IDs. Returns (ids, findings, cases).
    `ids` is None when any blocking finding exists. `previous` is the data of the
    committed page, used only to show old items beside new ones in review cases."""
    old_views = previous_views(previous)
    findings, cases = [], []
    items = raw_items(raw)
    seq = [0]

    def case(kind, collection, **kw):
        seq[0] += 1
        c = {"case": seq[0], "kind": kind, "collection": collection, **kw,
             "decision": None, "reason": None}
        cases.append(c)
        return c

    # topics: one that disappears always stops; a new one needs a recorded decision
    topics_now = content_topics(raw)
    locked_topics = [t["id"] for t in lock["topics"]]
    for t in locked_topics:
        if t not in topics_now:
            findings.append(Finding("V3.topic-removed", BLOCKING,
                                    f"topic '{t}' is in the lock but not in the content; topic IDs can't be "
                                    "renamed or removed, because students' 'done' points at them", where))
    for t in topics_now:
        if t not in locked_topics:
            case("new-topic", "topics", topic=t)
            findings.append(Finding("V3.topic-new", BLOCKING, f"topic '{t}' is new; record it with ids review/apply",
                                    where))
    # chapters and maps: recorded so changes are visible (warnings)
    names_now = [c["quiz_name"] for c in book["content"]["chapters"]]
    if [c["quiz_name"] for c in lock["chapters"]] != names_now:
        findings.append(Finding("V3.chapters-changed", WARNING,
                                "chapter quiz names differ from the lock; old quiz history filters differently",
                                where))
    maps_now = [m.get("id") for m in raw["maps"]]
    if [m["id"] for m in lock["maps"]] != maps_now:
        findings.append(Finding("V3.maps-changed", WARNING,
                                "mind maps were added, removed or reordered; only the last map opened is affected",
                                where))

    result = {}
    for collection in COLLECTIONS:
        locked = lock[collection]["items"]
        active = {}
        retired = {}
        for it in locked:
            (active if it["status"] == "active" else retired).setdefault(it["fp"], []).append(it)
        groups = {g["fp"]: g for g in lock["duplicate_groups"] if g["collection"] == collection}
        by_fp = {}
        for it in items[collection]:
            by_fp.setdefault(it["fp"], []).append(it)

        bound = {}           # content position -> lock item
        used = set()
        unbound = []
        for fp, group in by_fp.items():
            if len(group) > 1 or fp in groups:
                g = groups.get(fp)
                if g is None or len(g["items"]) != len(group) or \
                        [x["content"] for x in g["items"]] != [x["content"] for x in group]:
                    positions = ", ".join(str(x["pos"] + 1) for x in group)
                    c = case("duplicate", collection, fp=fp, positions=[x["pos"] + 1 for x in group],
                             items=[_view(collection, x["raw"]) for x in group],
                             locked_ids=[it["id"] for it in active.get(fp, [])], ids=None)
                    findings.append(Finding("V4.duplicate", BLOCKING,
                                            f"{collection[:-1]}s at positions {positions} have the same fingerprint"
                                            + (" (an approved duplicate group no longer matches: reordered or "
                                               "edited)" if g is not None else "")
                                            + f"; see review case {c['case']}", where))
                    used.update(it["id"] for it in active.get(fp, []))  # covered by this case, not missing
                    continue
                lock_by_id = {it["id"]: it for it in locked}
                for x, gi in zip(group, g["items"]):
                    li = lock_by_id.get(gi["id"])
                    if li is None or li["status"] != "active":
                        findings.append(Finding("V3.group", BLOCKING,
                                                f"duplicate group names {collection[:-1]} {gi['id']}, which is not "
                                                "active in the lock", where))
                        continue
                    bound[x["pos"]] = li
                    used.add(li["id"])
                continue
            x = group[0]
            matches = [it for it in active.get(fp, []) if it["id"] not in used]
            if len(matches) == 1:
                bound[x["pos"]] = matches[0]
                used.add(matches[0]["id"])
            elif len(matches) > 1:
                findings.append(Finding("V3.ambiguous", BLOCKING,
                                        f"{collection[:-1]} at position {x['pos'] + 1} matches several active IDs "
                                        f"({', '.join(str(m['id']) for m in matches)})", where))
            elif fp in retired:
                c = case("retired-match", collection, position=x["pos"] + 1, item=_view(collection, x["raw"]),
                         retired_ids=[it["id"] for it in retired[fp]], id=None)
                findings.append(Finding("V3.retired-match", BLOCKING,
                                        f"{collection[:-1]} at position {x['pos'] + 1} matches retired ID "
                                        f"{retired[fp][0]['id']}; decide restore or new (review case "
                                        f"{c['case']})", where))
            else:
                unbound.append(x)

        missing = [it for it in locked if it["status"] == "active" and it["id"] not in used]
        # review cases for unbound and missing items, with suggested pairings
        miss_views, unb_views = [], []
        for it in missing:
            old = old_views[collection].get(it["id"], {})
            c = case("missing", collection, id=it["id"], topic=it["topic"], locked_fp=it["fp"], old_item=old or None)
            miss_views.append({"id": it["id"], "topic": it["topic"], "q": old.get("q", ""),
                               "options": old.get("options"), "case": c["case"]})
            findings.append(Finding("V3.missing", BLOCKING,
                                    f"{collection[:-1]} ID {it['id']} (topic {it['topic']}) is in the lock but no "
                                    f"content item matches it (review case {c['case']})", where))
        for x in unbound:
            view = _view(collection, x["raw"])
            c = case("unbound", collection, position=x["pos"] + 1, item=view, fp=x["fp"], same_as=None,
                     suggestions=[])
            unb_views.append({"case": c["case"], "topic": x["topic"], "q": view["q"],
                              "options": view.get("options")})
            findings.append(Finding("V3.unbound", BLOCKING,
                                    f"{collection[:-1]} at position {x['pos'] + 1} (topic {x['topic']}) matches "
                                    f"no lock ID (review case {c['case']})", where))
        if missing and unbound:
            sugg = _suggest(miss_views, unb_views, collection)
            for c in cases:
                if c["kind"] == "unbound" and c["case"] in sugg:
                    c["suggestions"] = sugg[c["case"]]

        # F1: identity kept, but something in the item changed
        for pos, li in sorted(bound.items()):
            x = items[collection][pos]
            if x["content"] != li["content"]:
                case("content-changed", collection, id=li["id"], position=pos + 1,
                     item=_view(collection, x["raw"]), old_item=old_views[collection].get(li["id"]))
                findings.append(Finding("V3.content-changed", WARNING,
                                        f"{collection[:-1]} {li['id']} kept its ID but its content changed "
                                        "(wording absorbed by normalization, a card's back or an explanation); "
                                        "a student's earlier answer may refer to the old text; accept it with "
                                        "ids review/apply", where))
        result[collection] = (bound, items[collection])

    if any(f.severity == BLOCKING for f in findings):
        return None, findings, cases

    # option order (design A) and F4
    card_bound, card_items = result["cards"]
    q_bound, q_items = result["questions"]
    card_ids = [card_bound[i]["id"] for i in range(len(card_items))]
    question_ids, orders = [], []
    for i, x in enumerate(q_items):
        li = q_bound[i]
        question_ids.append(li["id"])
        q = x["raw"]
        if not has_options(q):
            orders.append(None)
            continue
        order = li.get("order")
        opts = source_options(q)
        if order is None or sorted(order) != list(range(len(opts))):
            findings.append(Finding("V3.order-missing", BLOCKING,
                                    f"question {li['id']} has no valid option order in the lock", where))
            orders.append(None)
            continue
        if shown_hash([opts[s] for s in order]) != li["shown"]:
            c = case("reordered-options", "questions", id=li["id"], position=i + 1, item=_view("questions", q),
                     locked_order=order)
            findings.append(Finding("V3.options-reordered", BLOCKING,
                                    f"question {li['id']}: the source's wrong answers were reordered, so the "
                                    f"options would appear in a new order (F4, review case {c['case']})", where))
        orders.append(order)
    if any(f.severity == BLOCKING for f in findings):
        return None, findings, cases
    return {"cards": card_ids, "questions": question_ids, "orders": orders}, findings, cases


def check_output_ids(model, lock, where):
    """Every ID in the output is an active lock ID, and every active lock ID is in the output."""
    out = []
    for collection, key in (("cards", "FLASHCARDS"), ("questions", "QUIZ_BANK")):
        built = [x["id"] for x in model[key]]
        active = sorted(it["id"] for it in lock[collection]["items"] if it["status"] == "active")
        if sorted(built) != active or len(set(built)) != len(built):
            out.append(Finding("V3.output-ids", BLOCKING,
                               f"the {collection} IDs in the page are not exactly the lock's active IDs", where))
    return out


# ---------------------------------------------------------------- bootstrap

def bootstrap(raw, book, live, page_info, approved_by, pull_request, date, where, check_sequence=True):
    """Create the first lock from the deployed page's data (`live`, the parsed `const D`).
    Refuses unless every source item binds to exactly the ID it has in the live page.
    `check_sequence` also requires the live option order to equal the legacy shared
    seed sequence (always on for a real book; tests on other books' extracts, whose
    seeds aren't sources here, turn it off)."""
    findings = []
    lock = empty_lock(book)
    lock["bootstrap"] = page_info
    items = raw_items(raw)

    live_topics = [t["id"] for ch in live["DEEP_STUDY_DATA"] for s in ch["sections"] for t in s["topics"]]
    if live_topics != content_topics(raw):
        findings.append(Finding("V3.bootstrap-topics", BLOCKING, "topic IDs in the source differ from the live page",
                                where))
    lock["topics"] = [{"id": t} for t in live_topics]
    live_chapters = list(dict.fromkeys(q["chapter"] for q in live["QUIZ_BANK"]))
    names = [c["quiz_name"] for c in book["content"]["chapters"]]
    if any(c not in names for c in live_chapters):
        findings.append(Finding("V3.bootstrap-chapters", BLOCKING,
                                "a chapter name in the live quiz bank is not in book.json", where))
    lock["chapters"] = [{"quiz_name": n} for n in names]
    lock["maps"] = [{"id": m.get("id"), "index": i} for i, m in enumerate(live["MIND_MAPS"])]
    if [m.get("id") for m in raw["maps"]] != [m["id"] for m in lock["maps"]]:
        findings.append(Finding("V3.bootstrap-maps", BLOCKING, "mind maps in the source differ from the live page",
                                where))

    # cards: the live fingerprint of each card must match exactly one source card
    live_cards = {}
    for c in live["FLASHCARDS"]:
        live_cards.setdefault(card_fingerprint(c.get("topic"), c.get("q")), []).append(c)
    for x in items["cards"]:
        hits = live_cards.get(x["fp"], [])
        if len(hits) != 1:
            findings.append(Finding("V3.bootstrap-bind", BLOCKING,
                                    f"source card {x['pos'] + 1} matches {len(hits)} live cards", where))
            continue
        lc = hits[0]
        src_view = {k: v for k, v in x["raw"].items() if k != "id"}
        if {k: v for k, v in lc.items() if k != "id"} != src_view:
            findings.append(Finding("V3.bootstrap-bind", BLOCKING,
                                    f"source card {x['pos'] + 1} differs from live card {lc['id']}", where))
        lock["cards"]["items"].append({"id": lc["id"], "fp": x["fp"], "content": x["content"],
                                       "topic": x["topic"], "status": "active"})
    if len(live["FLASHCARDS"]) != len(items["cards"]):
        findings.append(Finding("V3.bootstrap-bind", BLOCKING, "card counts differ between source and live page",
                                where))

    # questions: also record today's option order by source slot (design A)
    live_q = {}
    for q in live["QUIZ_BANK"]:
        tf = q["options"] == list(TRUE_FALSE_OPTIONS)
        key = type_key(q)
        fp = question_fingerprint(q.get("topic"), key, q["q"], None if (key and not has_options(q)) else q["options"],
                                  q["options"][q["correct"]])
        live_q.setdefault(fp, []).append((q, tf))
    reference = sequential_orders(raw, book) if check_sequence else [None] * len(items["questions"])
    for x, ref in zip(items["questions"], reference):
        hits = live_q.get(x["fp"], [])
        if len(hits) != 1:
            findings.append(Finding("V3.bootstrap-bind", BLOCKING,
                                    f"source question {x['pos'] + 1} matches {len(hits)} live questions", where))
            continue
        lq, _ = hits[0]
        q = x["raw"]
        entry = {"id": lq["id"], "fp": x["fp"], "content": x["content"], "topic": x["topic"], "status": "active"}
        if has_options(q):
            opts = source_options(q)
            order = [opts.index(o) for o in lq["options"]]
            if check_sequence and order != ref:
                findings.append(Finding("V3.bootstrap-order", BLOCKING,
                                        f"live question {lq['id']}: option order differs from the seed sequence",
                                        where))
            entry["order"] = order
            entry["shown"] = shown_hash(lq["options"])
        if lq["options"][lq["correct"]] != correct_text(q):
            findings.append(Finding("V3.answer-invariant", BLOCKING,
                                    f"live question {lq['id']}: the correct option is not the source's answer", where))
        lock["questions"]["items"].append(entry)
    if len(live["QUIZ_BANK"]) != len(items["questions"]):
        findings.append(Finding("V3.bootstrap-bind", BLOCKING,
                                "question counts differ between source and live page", where))

    for collection in COLLECTIONS:
        its = lock[collection]["items"]
        ids = [it["id"] for it in its]
        if len(set(ids)) != len(ids):
            findings.append(Finding("V3.bootstrap-bind", BLOCKING, f"duplicate live {collection} IDs", where))
        lock[collection]["next_id"] = max(ids, default=0) + 1
    lock["changes"].append({"seq": 1, "date": date, "collection": "all", "action": "bootstrap",
                            "reason": f"First lock, generated from the deployed page {page_info['from']} "
                                      f"at {page_info['commit'][:7]}",
                            "approved_by": approved_by, "pull_request": pull_request})
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("ID bootstrap", findings)
    return lock


# ---------------------------------------------------------------- review and apply

def review(raw, book, lock, where, previous=None):
    """The proposal a person fills in: every case the build can't decide."""
    if lock is None:
        lock = empty_lock(book)
    findings = check_lock_identity(lock, book, where)
    _, bind_findings, cases = bind(raw, book, lock, where, previous)
    findings += bind_findings
    covered = ("V3.topic-new", "V3.missing", "V3.unbound", "V3.retired-match", "V4.duplicate",
               "V3.options-reordered")
    other = [f for f in findings if f.severity == BLOCKING and f.code not in covered]
    return {
        "book": book["slug"],
        "instructions": "For each case set 'decision' and 'reason'. Allowed decisions by kind: "
                        + "; ".join(f"{k}: {', '.join(sorted(v))}" for k, v in DECISIONS.items())
                        + ". For 'same' on an unbound case, set 'same_as' to the missing ID it keeps. "
                          "For 'group', set 'ids' to the ID of each item in order (null for a new one). "
                          "The test for 'same': would a student who mastered the old item have mastered the new "
                          "one? If the meaning changed, it is new and the old ID is retired.",
        "lock_changes_seq": len(lock["changes"]),
        "cases": cases,
        "other_findings": [str(f) for f in other],
    }


def apply(raw, book, lock, proposal, approved_by, pull_request, date, where, previous=None):
    """Check every case is decided, then return the updated lock. Append-only."""
    if not approved_by or not isinstance(pull_request, int) or pull_request < 0 or not date:
        raise BuildStopped("ID apply", [Finding("V3.apply", BLOCKING,
                                                "an approver, a pull request number and a date are required", where)])
    new_lock = json.loads(json.dumps(lock if lock is not None else empty_lock(book)))
    fresh = review(raw, book, new_lock, where, previous)
    errs = []
    if fresh["other_findings"]:
        errs += [Finding("V3.apply", BLOCKING, f"cannot apply while other problems exist: {m}", where)
                 for m in fresh["other_findings"]]
    if proposal.get("lock_changes_seq") != len(new_lock["changes"]):
        errs.append(Finding("V3.apply", BLOCKING, "the lock changed since this proposal was written; run ids review "
                                                  "again", where))
    decided = {c["case"]: c for c in proposal.get("cases", [])}
    current = fresh["cases"]
    if [(c["kind"], c["collection"], c.get("id"), c.get("position"), c.get("topic")) for c in current] != \
            [(c["kind"], c["collection"], c.get("id"), c.get("position"), c.get("topic"))
             for c in proposal.get("cases", [])]:
        errs.append(Finding("V3.apply", BLOCKING, "the proposal's cases no longer match the content; run ids review "
                                                  "again", where))
    for c in current:
        d = decided.get(c["case"], {})
        if d.get("decision") not in DECISIONS[c["kind"]]:
            errs.append(Finding("V3.apply", BLOCKING, f"case {c['case']} ({c['kind']}) has no valid decision", where))
        elif not (isinstance(d.get("reason"), str) and d["reason"].strip()):
            errs.append(Finding("V3.apply", BLOCKING, f"case {c['case']} needs a reason", where))
    # 'same' pairs must be consistent: each unbound 'same' names a missing case decided 'same'
    missing_same = {d["id"]: d for d in decided.values() if d.get("kind") == "missing" and d.get("decision") == "same"}
    paired = [d.get("same_as") for d in decided.values() if d.get("kind") == "unbound" and d.get("decision") == "same"]
    if sorted(x for x in paired if x is not None) != sorted(missing_same) or None in paired or \
            len(set(paired)) != len(paired):
        errs.append(Finding("V3.apply", BLOCKING, "every 'same' must pair one unbound item with one missing ID that "
                                                  "is also marked 'same'", where))
    if errs:
        raise BuildStopped("ID apply", errs)

    items = raw_items(raw)
    seq = len(new_lock["changes"])
    summary = {}

    def record(collection, action, reason, **kw):
        nonlocal seq
        seq += 1
        new_lock["changes"].append({"seq": seq, "date": date, "collection": collection, "action": action, **kw,
                                    "reason": reason, "approved_by": approved_by, "pull_request": pull_request})
        summary[action] = summary.get(action, 0) + 1

    def new_entry(collection, x, qid):
        entry = {"id": qid, "fp": x["fp"], "content": x["content"], "topic": x["topic"], "status": "active"}
        if collection == "questions" and has_options(x["raw"]):
            opts = source_options(x["raw"])
            entry["order"] = seeded_order(book["quiz"]["seed"], qid, len(opts))
            entry["shown"] = shown_hash([opts[s] for s in entry["order"]])
        return entry

    def by_id(collection, i):
        return next(it for it in new_lock[collection]["items"] if it["id"] == i)

    for c in current:
        d = decided[c["case"]]
        col, kind, decision, reason = c["collection"], c["kind"], d["decision"], d["reason"].strip()
        if kind == "new-topic":
            new_lock["topics"].append({"id": c["topic"]})
            record("topics", "new", reason, topic=c["topic"])
        elif kind == "missing" and decision == "retire":
            it = by_id(col, c["id"])
            it["status"] = "retired"
            record(col, "retire", reason, id=c["id"], old_fp=it["fp"])
        elif kind == "unbound":
            x = items[col][c["position"] - 1]
            if decision == "new":
                qid = new_lock[col]["next_id"]
                new_lock[col]["next_id"] += 1
                new_lock[col]["items"].append(new_entry(col, x, qid))
                record(col, "new", reason, id=qid, new_fp=x["fp"])
            else:
                it = by_id(col, d["same_as"])
                old_fp = it["fp"]
                it.update(fp=x["fp"], content=x["content"], topic=x["topic"])
                if col == "questions" and "order" in it:
                    # options are placed by the recorded slot order, so an edited option keeps its position
                    opts = source_options(x["raw"])
                    it["shown"] = shown_hash([opts[s] for s in it["order"]])
                record(col, "rebind", reason, id=it["id"], old_fp=old_fp, new_fp=x["fp"])
        elif kind == "retired-match":
            x = items[col][c["position"] - 1]
            if decision == "restore":
                it = by_id(col, c["retired_ids"][0])
                it.update(status="active", content=x["content"])
                record(col, "restore", reason, id=it["id"], new_fp=x["fp"])
            else:
                qid = new_lock[col]["next_id"]
                new_lock[col]["next_id"] += 1
                new_lock[col]["items"].append(new_entry(col, x, qid))
                record(col, "new", reason, id=qid, new_fp=x["fp"])
        elif kind == "duplicate":
            ids = d.get("ids")
            group = [x for x in items[col] if x["fp"] == c["fp"]]
            if not isinstance(ids, list) or len(ids) != len(group):
                raise BuildStopped("ID apply", [Finding("V3.apply", BLOCKING,
                                                        f"case {c['case']}: 'ids' must list one ID (or null) per "
                                                        "item", where)])
            entries = []
            for x, i in zip(group, ids):
                if i is None:
                    i = new_lock[col]["next_id"]
                    new_lock[col]["next_id"] += 1
                    new_lock[col]["items"].append(new_entry(col, x, i))
                    record(col, "new", reason, id=i, new_fp=x["fp"])
                else:
                    it = by_id(col, i)
                    it["content"] = x["content"]
                entries.append({"id": i, "content": x["content"]})
            new_lock["duplicate_groups"] = [g for g in new_lock["duplicate_groups"]
                                            if not (g["collection"] == col and g["fp"] == c["fp"])]
            new_lock["duplicate_groups"].append({"collection": col, "fp": c["fp"], "items": entries})
            record(col, "group", reason, ids=[e["id"] for e in entries])
        elif kind == "content-changed":
            it = by_id(col, c["id"])
            x = items[col][c["position"] - 1]
            old_content = it["content"]
            it["content"] = x["content"]
            record(col, "accept-content", reason, id=it["id"], old_content=old_content, new_content=x["content"])
        elif kind == "reordered-options":
            it = by_id("questions", c["id"])
            x = items["questions"][c["position"] - 1]
            opts = source_options(x["raw"])
            old = it["order"]
            shown_texts = None
            # keep what students see: find the slot order that reproduces the recorded display
            for perm in _permutations(len(opts)):
                if shown_hash([opts[s] for s in perm]) == it["shown"]:
                    shown_texts = perm
                    break
            if shown_texts is None:
                raise BuildStopped("ID apply", [Finding("V3.apply", BLOCKING,
                                                        f"case {c['case']}: the recorded display can't be rebuilt "
                                                        "from the new options", where)])
            it["order"] = list(shown_texts)
            it["content"] = x["content"]
            record("questions", "reorder-slots", reason, id=it["id"], old_order=old, new_order=it["order"])
    # chapter names and maps are recorded so their changes stay visible (warnings in the build)
    chapters_now = [{"quiz_name": c["quiz_name"]} for c in book["content"]["chapters"]]
    if new_lock["chapters"] != chapters_now:
        new_lock["chapters"] = chapters_now
        record("chapters", "update", "chapter quiz names recorded as they are now")
    maps_now = [{"id": m.get("id"), "index": i} for i, m in enumerate(raw["maps"])]
    if new_lock["maps"] != maps_now:
        new_lock["maps"] = maps_now
        record("maps", "update", "mind maps recorded as they are now")
    problems = invariants(lock, new_lock, where) if lock is not None else self_check(new_lock, where)
    if problems:
        raise BuildStopped("ID apply", problems)
    return new_lock, summary


def _permutations(n):
    from itertools import permutations
    return permutations(range(n))


# ---------------------------------------------------------------- invariants

def self_check(lock, where):
    out = []
    for collection in COLLECTIONS:
        ids = [it["id"] for it in lock[collection]["items"]]
        if len(set(ids)) != len(ids):
            out.append(Finding("V3.invariant", BLOCKING, f"an ID is used twice in {collection}", where))
        if ids and lock[collection]["next_id"] <= max(ids):
            out.append(Finding("V3.invariant", BLOCKING, f"{collection}.next_id is not above every issued ID", where))
        for it in lock[collection]["items"]:
            if it["status"] not in ("active", "retired"):
                out.append(Finding("V3.invariant", BLOCKING, f"{collection} {it['id']}: unknown status", where))
    seqs = [c["seq"] for c in lock["changes"]]
    if seqs != list(range(1, len(seqs) + 1)):
        out.append(Finding("V3.invariant", BLOCKING, "change record sequence numbers are not 1, 2, 3, …", where))
    for c in lock["changes"]:
        if not c.get("approved_by") or not isinstance(c.get("pull_request"), int) or not c.get("reason"):
            out.append(Finding("V3.invariant", BLOCKING, f"change {c.get('seq')} lacks an approver, pull request or "
                                                         "reason", where))
    return out


def invariants(old, new, where):
    """CI check of a lock against the previous one (main's)."""
    out = self_check(new, where)
    if old is None:
        return out
    for key in ("storage_key", "output", "book"):
        if old.get(key) != new.get(key):
            out.append(Finding("V3.invariant", BLOCKING, f"'{key}' changed in the lock", where))
    if old.get("bootstrap") != new.get("bootstrap"):
        out.append(Finding("V3.invariant", BLOCKING, "the bootstrap record changed", where))
    if [t["id"] for t in new["topics"]][:len(old["topics"])] != [t["id"] for t in old["topics"]]:
        out.append(Finding("V3.invariant", BLOCKING, "a topic was removed or reordered in the lock", where))
    if new["changes"][:len(old["changes"])] != old["changes"]:
        out.append(Finding("V3.invariant", BLOCKING, "earlier change records were edited or removed", where))
    added = new["changes"][len(old["changes"]):]
    for collection in COLLECTIONS:
        if new[collection]["next_id"] < old[collection]["next_id"]:
            out.append(Finding("V3.invariant", BLOCKING, f"{collection}.next_id decreased", where))
        new_by = {it["id"]: it for it in new[collection]["items"]}
        old_ids = {it["id"] for it in old[collection]["items"]}
        for it in old[collection]["items"]:
            n = new_by.get(it["id"])
            if n is None:
                out.append(Finding("V3.invariant", BLOCKING, f"{collection} {it['id']} was removed from the lock",
                                   where))
                continue
            if it["status"] == "retired" and n["status"] == "active" and not any(
                    c["action"] == "restore" and c.get("id") == it["id"] and c["collection"] == collection
                    for c in added):
                out.append(Finding("V3.invariant", BLOCKING,
                                   f"{collection} {it['id']} went from retired to active without a restore entry",
                                   where))
            if n != it:
                if not any(c.get("id") == it["id"] and c["collection"] == collection for c in added) and not any(
                        c["action"] == "group" and it["id"] in c.get("ids", []) for c in added):
                    out.append(Finding("V3.invariant", BLOCKING,
                                       f"{collection} {it['id']} changed without a change record", where))
        for i in new_by:
            if i not in old_ids and i < old[collection]["next_id"]:
                out.append(Finding("V3.invariant", BLOCKING, f"{collection} ID {i} reuses an issued number", where))
            if i not in old_ids and not any(c.get("id") == i and c["action"] == "new" and c["collection"] == collection
                                            for c in added):
                out.append(Finding("V3.invariant", BLOCKING, f"{collection} {i} was added without a 'new' record",
                                   where))
    return out
