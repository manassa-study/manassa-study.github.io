"""Loader and assembler on the real pilot content (spec section 9)."""
import random

import pytest

from helpers import PILOT, REPO
from mudhakarah.config import load_book
from mudhakarah.errors import BuildStopped
from mudhakarah.loaders import load_content
from mudhakarah.model import MODEL_KEYS, assemble, sequential_orders, source_options


@pytest.fixture(scope="module")
def pilot():
    book, findings = load_book(REPO, PILOT)
    assert findings == []
    raw, hashes, findings = load_content(REPO, PILOT, book)
    assert findings == []
    return book, raw, hashes


def test_counts_and_key_order(pilot):
    book, raw, _ = pilot
    model, findings = assemble(raw, book)
    assert findings == []
    assert tuple(model) == MODEL_KEYS
    assert len(model["FLASHCARDS"]) == 169
    assert len(model["QUIZ_BANK"]) == 177
    assert [c["id"] for c in model["FLASHCARDS"]] == list(range(1, 170))
    assert [q["id"] for q in model["QUIZ_BANK"]] == list(range(1, 178))
    assert all(list(q) == ["id", "chapter", "type", "q", "options", "correct", "exp", "topic"]
               for q in model["QUIZ_BANK"])
    assert all(list(c) == ["id", "cat", "q", "a", "topic"] for c in model["FLASHCARDS"])


def test_content_hashes_match_phase0_package(pilot):
    _, _, hashes = pilot
    assert {k: v[:8] for k, v in hashes.items()} == {
        "m1.py": "8bb58ff4", "m2.py": "224bbbfa", "m3.py": "a69774d8", "m4.py": "895f66d9", "m5.py": "e81fb5e0"}


def test_shuffle_reproduces_the_legacy_seed_1447_order(pilot):
    """The legacy build: one Random(1447) shared by every multiple-choice question, in order."""
    book, raw, _ = pilot
    rng = random.Random(1447)
    model, _ = assemble(raw, book)
    for q, built in zip(raw["questions"], model["QUIZ_BANK"]):
        if q["type"] == "صح أو خطأ":
            assert built["options"] == ["صح", "خطأ"] and built["correct"] == (0 if q["tf"] else 1)
        else:
            opts = [q["correct"]] + list(q["wrong"])
            rng.shuffle(opts)
            assert built["options"] == opts and built["correct"] == opts.index(q["correct"])


def test_answer_invariant_holds(pilot):
    book, raw, _ = pilot
    model, _ = assemble(raw, book)
    for q, built in zip(raw["questions"], model["QUIZ_BANK"]):
        expected = q["correct"] if "correct" in q else ("صح" if q["tf"] else "خطأ")
        assert built["options"][built["correct"]] == expected


def test_orders_are_slot_permutations(pilot):
    book, raw, _ = pilot
    for q, order in zip(raw["questions"], sequential_orders(raw, book)):
        if order is not None:
            assert sorted(order) == list(range(len(source_options(q))))


def _tiny(**q):
    raw = {"meta": {}, "chapters": [{"sections": [{"topics": [{"id": "t1"}]}]}], "cards": [], "examples": [],
           "tables": [], "maps": [], "capsules": [], "extras": {},
           "questions": [dict({"type": "اختيار من متعدد", "q": "س", "correct": "أ", "wrong": ["ب", "ج", "د"],
                               "exp": "", "topic": "t1"}, **q)]}
    book = {"content": {"chapters": [{"symbol": "CH1", "quiz_name": "ف"}]}, "quiz": {"seed": 1}}
    return raw, book


@pytest.mark.parametrize("change, code", [
    ({"type": "نوع جديد"}, "V2.unknown-type"),
    ({"wrong": ["ب", "ب", "د"]}, "V2.question"),
    ({"wrong": ["ب", "ج"]}, "V2.question"),
    ({"topic": "t9"}, "V5.topic"),
])
def test_assembler_stops_on_bad_questions(change, code):
    raw, book = _tiny(**change)
    with pytest.raises(BuildStopped) as e:
        assemble(raw, book)
    assert code in [f.code for f in e.value.findings]
