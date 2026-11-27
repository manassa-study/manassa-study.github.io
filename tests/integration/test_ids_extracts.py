"""ID tools on all five books' Phase 0 extracts, read-only (spec section 9):
real variety such as التفسير المقارن's explicit IDs with gaps and تاريخ التفسير's
look-alike chronology questions."""
import collections
import copy
import hashlib

import pytest

from helpers import EXTRACTS, extract_lock, register_extract_types
from mudhakarah.ids import bind, raw_items
from mudhakarah.model import assemble
from mudhakarah.normalize import normalize

import json

SHA = {
    "MadkhalFiqhAQU": "1cb977828e29bffb459891c43bfcd688ecc598cfa35365dcc83c61caf35d89b2",
    "MunazaraRashidiyaAQU": "98798740d47f3dce30f72431a8b9b0a2a9bf7b22b3ef59b1f5866a299d2eeca2",
    "TafseerMaqaranAQU": "412786e767e5ca520af023965f9cd368aad7d320461cd0a5bc0310a284986b81",
    "TakhreejAsaneedAQU": "3e4f61186fa0df8dbc3c91951f997afb397efb174636c78e678f3e8090ba1f96",
    "TareekhTafseerAQU": "3127b115fc8b5b852ee29bdbab23698ba0141c78c3802eed8cee22b5e7708e93",
}
BOOKS = sorted(EXTRACTS)


@pytest.fixture(params=BOOKS)
def book_data(request, monkeypatch):
    data = json.loads(EXTRACTS[request.param].read_text(encoding="utf-8"))
    register_extract_types(monkeypatch, data)
    return request.param, data


def codes(findings):
    return sorted({f.code for f in findings if f.severity == "blocking"})


@pytest.mark.parametrize("name", BOOKS)
def test_extracts_are_the_phase0_files(name):
    assert hashlib.sha256(EXTRACTS[name].read_bytes()).hexdigest() == SHA[name]


def test_no_fingerprint_collisions(book_data):
    name, data = book_data
    raw, book, _ = extract_lock(data, name)
    items = raw_items(raw, book)
    for collection in ("cards", "questions"):
        dup = [fp for fp, n in collections.Counter(x["fp"] for x in items[collection]).items() if n > 1]
        assert dup == [], f"{name} {collection}: {len(dup)} colliding fingerprints"


def test_stem_only_would_collide_in_tareekh():
    """Why options are in the fingerprint (O-2): topic plus stem alone leaves 24 collisions."""
    data = json.loads(EXTRACTS["TareekhTafseerAQU"].read_text(encoding="utf-8"))
    stems = collections.Counter(normalize(q["q"]) for q in data["QUIZ_BANK"])
    assert sum(n for n in stems.values() if n > 1) == 24


def test_bootstrap_and_exact_rebind_reproduce_the_page_data(book_data):
    name, data = book_data
    raw, book, lock = extract_lock(data, name)
    ids, findings, cases = bind(raw, book, lock, name)
    assert codes(findings) == [] and cases == []
    m, _ = assemble_like(raw, book, ids, data)
    assert m == data["QUIZ_BANK"]
    assert [c["id"] for c in data["FLASHCARDS"]] == ids["cards"]


def assemble_like(raw, book, ids, data):
    """The assembler needs a topic for each item's chapter name; the other books have
    none, so this rebuilds QUIZ_BANK from the extract's own chapter names."""
    from mudhakarah.model import source_options
    bank = []
    for q, built, qid, order in zip(raw["questions"], data["QUIZ_BANK"], ids["questions"], ids["orders"]):
        opts = source_options(q)
        if order is None:
            options, correct = opts, (0 if q["tf"] else 1)
        else:
            options, correct = [opts[s] for s in order], order.index(0)
        item = {k: built[k] for k in built}
        item.update(id=qid, options=options, correct=correct)
        bank.append(item)
    return bank, []


def test_explicit_ids_with_gaps_are_kept(monkeypatch):
    data = json.loads(EXTRACTS["TafseerMaqaranAQU"].read_text(encoding="utf-8"))
    register_extract_types(monkeypatch, data)
    raw, book, lock = extract_lock(data, "tafseer")
    live_ids = [q["id"] for q in data["QUIZ_BANK"]]
    assert live_ids != list(range(1, len(live_ids) + 1))  # gaps exist
    assert [q["id"] for q in lock["questions"]["items"]] == live_ids
    assert lock["questions"]["next_id"] == max(live_ids) + 1


@pytest.mark.parametrize("edit", ["insert-card", "delete-card", "reword-question", "change-option",
                                  "change-correct", "reorder-source-options"])
def test_scenarios_on_every_book(book_data, edit):
    name, data = book_data
    raw, book, lock = extract_lock(data, name)
    raw = copy.deepcopy(raw)
    mc = next(i for i, q in enumerate(raw["questions"]) if "correct" in q)
    if edit == "insert-card":
        raw["cards"].insert(len(raw["cards"]) // 2, {"id": 0, "cat": "x", "q": "بطاقة جديدة تماماً؟", "a": "y"})
        expected = ["V3.unbound"]
    elif edit == "delete-card":
        raw["cards"].pop(len(raw["cards"]) // 2)
        expected = ["V3.missing"]
    elif edit == "reword-question":
        raw["questions"][mc]["q"] = "صياغة مختلفة " + raw["questions"][mc]["q"]
        expected = ["V3.missing", "V3.unbound"]
    elif edit == "change-option":
        raw["questions"][mc]["wrong"][0] = "خيار بديل لم يكن"
        expected = ["V3.missing", "V3.unbound"]
    elif edit == "change-correct":
        raw["questions"][mc]["correct"] = raw["questions"][mc]["wrong"][0]
        raw["questions"][mc]["wrong"][0] = data["QUIZ_BANK"][mc]["options"][data["QUIZ_BANK"][mc]["correct"]]
        expected = ["V3.missing", "V3.unbound"]
    else:
        raw["questions"][mc]["wrong"] = raw["questions"][mc]["wrong"][::-1]
        expected = ["V3.options-reordered"]
    ids, findings, cases = bind(raw, book, lock, name, previous=data)
    assert ids is None and codes(findings) == expected, (name, edit)
    if edit in ("reword-question", "change-option", "change-correct"):
        unbound = next(c for c in cases if c["kind"] == "unbound")
        assert unbound["suggestions"] and unbound["suggestions"][0]["id"] == data["QUIZ_BANK"][mc]["id"]


def test_f3_lookalike_chronology_question_top_suggestion(monkeypatch):
    """One option replaced in one of تاريخ التفسير's look-alike chronology questions:
    the right ID is the top suggestion, ranked by option overlap."""
    data = json.loads(EXTRACTS["TareekhTafseerAQU"].read_text(encoding="utf-8"))
    register_extract_types(monkeypatch, data)
    raw, book, lock = extract_lock(data, "tareekh")
    stems = collections.Counter(normalize(q["q"]) for q in data["QUIZ_BANK"])
    group = [i for i, q in enumerate(data["QUIZ_BANK"]) if stems[normalize(q["q"])] >= 12]
    assert len(group) >= 12
    target = group[5]
    raw["questions"][target]["wrong"][1] = "كتاب لم يُذكر في المقرر"
    # also make another look-alike in the same topic missing, so there is real competition
    other = next(i for i in group if i != target and raw["questions"][i].get("topic") ==
                 raw["questions"][target].get("topic"))
    raw["questions"][other]["wrong"][0] = "كتاب آخر لم يُذكر"
    _, _, cases = bind(raw, book, lock, "tareekh", previous=data)
    u = {c["position"]: c for c in cases if c["kind"] == "unbound"}
    assert u[target + 1]["suggestions"][0]["id"] == data["QUIZ_BANK"][target]["id"]
    assert u[other + 1]["suggestions"][0]["id"] == data["QUIZ_BANK"][other]["id"]
