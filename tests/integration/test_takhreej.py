"""Phase 3, book 2: reconstruct the published التخريج payload without changing it."""
import hashlib
import json
import re

import pytest

from helpers import EXTRACTS, REPO
from mudhakarah.config import load_book
from mudhakarah.ids import bootstrap, read_lock
from mudhakarah.loaders import load_content
from mudhakarah.output import parse_data_line
from mudhakarah.pipeline import run_book

SLUG = "takhreej-asaneed"
PAGE = "hadith/TakhreejAsaneedAQU.html"
BASELINE_SHA256 = "3d96dae58c31fd3ad7b41e2375c4df5a979dae4176f098367858f35a1e34ab80"
BASELINE_COMMIT = "32aef51b48e2a2ddd058e99006951b9c7d4881c2"
EXTRACT_SHA256 = "3e4f61186fa0df8dbc3c91951f997afb397efb174636c78e678f3e8090ba1f96"


@pytest.fixture(scope="module")
def base():
    book, _ = load_book(REPO, SLUG)
    raw, _, _ = load_content(REPO, SLUG, book)
    lock = read_lock(REPO, SLUG)
    live = parse_data_line((REPO / PAGE).read_text(encoding="utf-8"))
    extract = json.loads(EXTRACTS["TakhreejAsaneedAQU"].read_text(encoding="utf-8"))
    return book, raw, lock, live, extract


def test_phase0_extract_is_the_recorded_file():
    assert hashlib.sha256(EXTRACTS["TakhreejAsaneedAQU"].read_bytes()).hexdigest() == EXTRACT_SHA256


def test_build_is_byte_identical_to_the_published_baseline():
    result = run_book(REPO, SLUG)
    assert result.output_path == PAGE
    assert hashlib.sha256(result.html).hexdigest() == BASELINE_SHA256
    assert result.html == (REPO / PAGE).read_bytes()


def test_reconstructed_sources_round_trip_to_the_verified_extract(base):
    _, _, _, _, extract = base
    result = run_book(REPO, SLUG)
    assert result.model == extract
    assert json.dumps(result.model, ensure_ascii=False) == EXTRACTS["TakhreejAsaneedAQU"].read_text(encoding="utf-8")


def test_live_ids_option_order_and_quiz_chapters_are_locked(base):
    book, raw, lock, live, extract = base
    assert lock["storage_key"] == "takhreej-asaneed-v1"
    assert lock["output"] == PAGE
    assert [c["id"] for c in lock["cards"]["items"]] == [c["id"] for c in live["FLASHCARDS"]]
    assert [q["id"] for q in lock["questions"]["items"]] == [q["id"] for q in live["QUIZ_BANK"]]
    result = run_book(REPO, SLUG)
    assert result.model["FLASHCARDS"] == extract["FLASHCARDS"]
    assert result.model["QUIZ_BANK"] == extract["QUIZ_BANK"]
    assert [c["quiz_name"] for c in book["content"]["chapters"]] == ["المقدمة والباب الأول", "الباب الثاني"]
    assert len(lock["topics"]) == 29 and len(lock["maps"]) == 7


def test_bootstrap_rebuilds_the_committed_lock_from_the_baseline(base):
    book, raw, lock, live, _ = base
    change = lock["changes"][0]
    assert lock["bootstrap"]["commit"] == BASELINE_COMMIT
    assert lock["bootstrap"]["option_order"] == "captured-from-baseline"
    regenerated = bootstrap(raw, book, live, lock["bootstrap"], change["approved_by"], change["pull_request"],
                            change["date"], SLUG, check_sequence=False)
    assert regenerated == lock


def test_deferred_report_script_follows_the_expand_collapse_css_block():
    html = (REPO / PAGE).read_text(encoding="utf-8")
    report = '<script src="https://manassa-study.github.io/report.js" defer></script>'
    css = "/* ===== clear expand / collapse controls ===== */"
    assert html.index(css) < html.index(report)
    assert re.search(r"</style>\s*" + re.escape(report), html)
