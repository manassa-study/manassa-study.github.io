"""Golden test (spec section 4, blocking): the pilot built from the template equals
the committed page, and its data equals the Phase 0 extract. That the build with
no step-2 switch on equals the baseline page byte for byte, and that the published
page differs from it only by the approved step-2 changes, is in test_step2.py."""
import hashlib
import json

from helpers import GOLDEN, PILOT, PILOT_PAGE, PILOT_SHA256, PUBLISHED_SHA256, REPO
from mudhakarah.output import parse_data_line
from mudhakarah.pipeline import run_book


def _build():
    return run_book(REPO, PILOT)


def test_golden_files_are_the_baseline():
    assert hashlib.sha256((GOLDEN / "MunazaraRashidiyaAQU.html").read_bytes()).hexdigest() == PILOT_SHA256


def test_pilot_build_equals_committed_page():
    result = _build()
    assert result.output_path == PILOT_PAGE
    assert result.html == (REPO / PILOT_PAGE).read_bytes()
    assert hashlib.sha256(result.html).hexdigest() == PUBLISHED_SHA256


def test_data_line_equals_phase0_extract_exactly():
    result = _build()
    extract = (GOLDEN / "MunazaraRashidiyaAQU.data.json").read_text(encoding="utf-8")
    assert json.dumps(result.model, ensure_ascii=False) == extract
    lines = result.html.decode("utf-8").split("\n")
    assert lines[716] == "const D = " + extract + ";"  # line 717 of the page


def test_data_parsed_back_equals_model():
    result = _build()
    assert parse_data_line(result.html.decode("utf-8")) == result.model


def test_build_is_repeatable_in_one_process():
    a, b = _build(), _build()
    assert a.html == b.html and a.manifest == b.manifest
