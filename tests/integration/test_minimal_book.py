"""Minimal-book test (spec section 4): a tiny fixture book builds and verifies,
and nothing of the pilot's leaks into it."""
import json

import pytest

from helpers import PILOT, REPO, make_repo
from mudhakarah.output import parse_data_line
from mudhakarah.pipeline import run_book, write_result

FIXTURE = REPO / "tests" / "fixtures" / "minimal-book"


@pytest.fixture
def built(tmp_path):
    root = make_repo(tmp_path, [("minimal", FIXTURE)])
    return root, run_book(root, "minimal")


def test_minimal_book_builds_and_round_trips(built):
    _, result = built
    text = result.html.decode("utf-8")
    assert parse_data_line(text) == result.model
    assert len(result.model["FLASHCARDS"]) == 3 and len(result.model["QUIZ_BANK"]) == 3
    assert {q["type"] for q in result.model["QUIZ_BANK"]} == {"اختيار من متعدد", "صح أو خطأ", "ما اسم هذا؟"}
    for q in result.model["QUIZ_BANK"]:
        assert 0 <= q["correct"] < len(q["options"])
    book = json.loads((FIXTURE / "book.json").read_text(encoding="utf-8"))
    for v in [book["title"], book["storage_key"], book["welcome_session_key"], book["theme"]["light"]["accent"],
              book["labels"]["examples_title"], "%23654321", book["search"]["placeholder"]]:
        assert v in text, v


def test_nothing_of_the_pilot_leaks(built):
    _, result = built
    text = result.html.decode("utf-8")
    pilot = json.loads((REPO / "books" / PILOT / "book.json").read_text(encoding="utf-8"))
    for v in [pilot["title"], pilot["storage_key"], pilot["welcome_session_key"], pilot["description"],
              pilot["theme"]["light"]["accent"], pilot["theme"]["dark"]["accent"], pilot["labels"]["examples_title"],
              pilot["page_range"], pilot["search"]["placeholder"], "MunazaraRashidiya", "og-munazara",
              "8a4b14", "efb57c"]:
        assert v not in text, v


def test_build_mode_writes_page_and_manifest_atomically(built):
    root, result = built
    write_result(root, result)
    assert (root / result.output_path).read_bytes() == result.html
    manifest = json.loads((root / "reports" / "build" / "minimal.manifest.json").read_text(encoding="utf-8"))
    assert manifest["output"]["sha256"] == result.manifest["output"]["sha256"]
    leftovers = [p.name for p in (root / result.output_path).parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_manifest_has_no_machine_details(built):
    root, result = built
    text = json.dumps(result.manifest, ensure_ascii=False)
    assert str(root) not in text and str(REPO) not in text
    assert list(result.manifest["inputs"])[:2] == ["platform/site.json", "books/minimal/book.json"]
