"""Book 4 preserves the published comparison-tafsir payload and IDs exactly."""
import copy
import json

import pytest

from helpers import EXTRACTS, REPO
from mudhakarah.config import load_book
from mudhakarah.errors import BLOCKING
from mudhakarah.ids import bind, read_lock, self_check
from mudhakarah.loaders import load_content
from mudhakarah.model import assemble

SLUG = "tafseer-maqaran"
PAGE = "Tafseer/TafseerMaqaranAQU.html"


@pytest.fixture(scope="module")
def base():
    book, _ = load_book(REPO, SLUG)
    raw, _, _ = load_content(REPO, SLUG, book)
    lock = read_lock(REPO, SLUG)
    baseline = json.loads(EXTRACTS["TafseerMaqaranAQU"].read_text(encoding="utf-8"))
    return book, raw, lock, baseline


def test_lock_and_assembled_questions_preserve_all_baseline_ids_and_order(base):
    book, raw, lock, baseline = base
    expected_ids = [q["id"] for q in baseline["QUIZ_BANK"]]
    assert [item["id"] for item in lock["questions"]["items"]] == expected_ids
    assert lock["bootstrap"]["option_order"] == "captured-from-baseline"

    ids, findings, cases = bind(raw, book, lock, f"books/{SLUG}/ids.lock.json")
    assert not [f for f in findings if f.severity == BLOCKING]
    assert cases == []
    model, _ = assemble(raw, book, ids=ids)
    assert model == baseline
    assert [q["id"] for q in model["QUIZ_BANK"]] == expected_ids
    assert [q["options"] for q in model["QUIZ_BANK"]] == [q["options"] for q in baseline["QUIZ_BANK"]]


def test_missing_baseline_question_fails_closed(base):
    book, raw, lock, _ = base
    broken = copy.deepcopy(raw)
    broken["questions"].pop(0)
    ids, findings, _ = bind(broken, book, lock, f"books/{SLUG}/ids.lock.json")
    assert ids is None
    assert "V3.missing" in {f.code for f in findings if f.severity == BLOCKING}


def test_duplicate_question_id_fails_closed(base):
    book, raw, lock, _ = base
    broken = copy.deepcopy(lock)
    broken["questions"]["items"][1]["id"] = broken["questions"]["items"][0]["id"]
    ids, findings, _ = bind(raw, book, broken, f"books/{SLUG}/ids.lock.json")
    assert ids is None
    assert any(f.severity == BLOCKING for f in findings)
    assert any(f.severity == BLOCKING for f in self_check(broken, f"books/{SLUG}/ids.lock.json"))


def test_fingerprint_mismatch_fails_closed_instead_of_reassigning_an_id(base):
    book, raw, lock, _ = base
    broken = copy.deepcopy(lock)
    broken["questions"]["items"][0]["fp"] = "0" * 40
    ids, findings, _ = bind(raw, book, broken, f"books/{SLUG}/ids.lock.json")
    assert ids is None
    assert {"V3.missing", "V3.unbound"} <= {f.code for f in findings if f.severity == BLOCKING}
