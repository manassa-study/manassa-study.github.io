"""Phase 3, book 1: المدخل إلى الفقه الإسلامي (master plan section I).

The book counts as migrated only when its new build matches its live file, or every
difference is on its approved list. Its expected difference is none, so the build must
equal the page published at the Phase 0 baseline byte for byte. The book has no topic on
its cards and questions, so they are anchored to their chapter (O-3), found from the
first «ص» page, as its legacy build named quiz chapters.
"""
import copy
import hashlib
import json

import pytest

from helpers import EXTRACTS, REPO
from mudhakarah.config import load_book
from mudhakarah.errors import BuildStopped
from mudhakarah.ids import bind, bootstrap, raw_items, read_lock
from mudhakarah.loaders import load_content
from mudhakarah.model import assemble, item_anchor, page_chapter
from mudhakarah.output import parse_data_line
from mudhakarah.pipeline import run_book

SLUG = "madkhal-fiqh"
PAGE = "fiqh/MadkhalFiqhAQU.html"
# The page at the Phase 0 baseline de019d2 (preservation package, 03-deployed-books-at-baseline)
BASELINE_SHA256 = "725d5d1f419527abdf8d006cf7e1b1c786020f6ac1076167b9993d2b7adca3ec"
# The content files, unchanged from the package's 05-recovered-sources/fiqh-canvas/source/
SOURCE_SHA256 = {
    "f1.py": "d4ec4235cfc930903026d332672a68ee5dd513aba9e091a03374e25af20c65bb",
    "f2.py": "6d9b24ee43fb486be7ebe21d25ea90aef7f8a27865fce4d573589ffb93ea6013",
    "f3.py": "51c81131bac5fccc8154d0d23c43c82ec201235a7673c7ad84de6fca94d9d7f0",
}
CHAPTERS = ["الفصل التمهيدي", "الفصل الأول", "الفصل الثاني", "الفصل الثالث"]
W = "test"


@pytest.fixture(scope="module")
def base():
    book, _ = load_book(REPO, SLUG)
    raw, hashes, _ = load_content(REPO, SLUG, book)
    lock = read_lock(REPO, SLUG)
    live = parse_data_line((REPO / PAGE).read_text(encoding="utf-8"))
    return book, raw, hashes, lock, live


def test_the_committed_page_is_still_the_baseline_page():
    assert hashlib.sha256((REPO / PAGE).read_bytes()).hexdigest() == BASELINE_SHA256


def test_build_equals_the_live_page_byte_for_byte():
    result = run_book(REPO, SLUG)
    assert result.output_path == PAGE
    assert result.html == (REPO / PAGE).read_bytes()
    assert hashlib.sha256(result.html).hexdigest() == BASELINE_SHA256


def test_data_equals_the_phase0_extract_exactly():
    result = run_book(REPO, SLUG)
    assert json.dumps(result.model, ensure_ascii=False) == EXTRACTS["MadkhalFiqhAQU"].read_text(encoding="utf-8")


def test_content_files_are_the_recovered_sources(base):
    _, _, hashes, _, _ = base
    assert sorted(hashes) == [f"f{i}.py" for i in range(1, 8)]
    for name, sha in SOURCE_SHA256.items():
        assert hashes[name] == sha


def test_lock_matches_the_live_page(base):
    book, raw, _, lock, live = base
    assert [c["id"] for c in lock["cards"]["items"]] == [c["id"] for c in live["FLASHCARDS"]] == list(range(1, 187))
    assert [q["id"] for q in lock["questions"]["items"]] == [q["id"] for q in live["QUIZ_BANK"]] == list(range(1, 182))
    assert len(lock["topics"]) == 31 and len(lock["maps"]) == 7
    assert lock["fingerprint"]["cards"] == ["chapter", "q"]
    assert lock["fingerprint"]["questions"][0] == "chapter"
    assert all("chapter" in it and "topic" not in it for c in ("cards", "questions") for it in lock[c]["items"])
    assert lock["bootstrap"]["sha256"] == BASELINE_SHA256
    assert lock["bootstrap"]["commit"] == "de019d25ba8ea2be7f3dbc56b98de2a63248ea31"


def test_bootstrap_regenerates_the_committed_lock(base):
    book, raw, _, lock, live = base
    change = lock["changes"][0]
    again = bootstrap(raw, book, live, lock["bootstrap"], change["approved_by"], change["pull_request"],
                      change["date"], W)
    assert again == lock


def test_every_item_has_a_chapter_anchor_equal_to_its_quiz_chapter(base):
    book, raw, _, _, live = base
    for q, lq in zip(raw["questions"], live["QUIZ_BANK"]):
        assert item_anchor(book, "questions", q) == lq["chapter"] in CHAPTERS
    assert {item_anchor(book, "cards", c) for c in raw["cards"]} == set(CHAPTERS)
    items = raw_items(raw, book)
    for collection in ("cards", "questions"):
        fps = [x["fp"] for x in items[collection]]
        assert len(set(fps)) == len(fps), f"{collection}: colliding fingerprints"


def test_page_thresholds_are_the_legacy_builds():
    book, _ = load_book(REPO, SLUG)
    for page, name in ((15, CHAPTERS[0]), (50, CHAPTERS[0]), (51, CHAPTERS[1]), (104, CHAPTERS[1]),
                       (105, CHAPTERS[2]), (142, CHAPTERS[2]), (143, CHAPTERS[3]), (169, CHAPTERS[3])):
        arabic = "".join("٠١٢٣٤٥٦٧٨٩"[int(d)] for d in str(page))
        assert page_chapter(book, f"(ص {arabic})") == name
        assert page_chapter(book, f"ص{page}") == name
    assert page_chapter(book, "بلا صفحة") is None


def test_exact_rebind_reproduces_today(base):
    book, raw, _, lock, live = base
    ids, findings, cases = bind(raw, book, lock, W)
    assert [f for f in findings if f.severity == "blocking"] == [] and cases == []
    m, _ = assemble(raw, book, ids)
    assert m["QUIZ_BANK"] == live["QUIZ_BANK"] and m["FLASHCARDS"] == live["FLASHCARDS"]


def test_moving_a_question_to_another_chapter_stops_for_review(base):
    """O-3 consequence: with the chapter as anchor, moving an item to another chapter stops the build."""
    book, raw, _, lock, _ = base
    raw = copy.deepcopy(raw)
    q = raw["questions"][0]
    assert item_anchor(book, "questions", q) == CHAPTERS[0]
    q["exp"] = "(ص ١٦٠) " + q["exp"]  # its first page is now in the last chapter
    assert item_anchor(book, "questions", q) == CHAPTERS[3]
    ids, findings, cases = bind(raw, book, lock, W)
    assert ids is None
    assert {"V3.unbound", "V3.missing"} <= {f.code for f in findings}


def test_a_question_without_a_page_stops_the_build(base):
    book, raw, _, _, _ = base
    raw = copy.deepcopy(raw)
    raw["questions"][3]["exp"] = "شرح بلا رقم صفحة"
    with pytest.raises(BuildStopped) as e:
        assemble(raw, book)
    assert "V5.anchor" in {f.code for f in e.value.findings}


def test_questions_have_no_topic_key_as_on_the_live_page():
    model = run_book(REPO, SLUG).model
    assert all("topic" not in q for q in model["QUIZ_BANK"])
    assert list(model["QUIZ_BANK"][0]) == ["id", "chapter", "type", "q", "options", "correct", "exp"]
