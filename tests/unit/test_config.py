import copy
import json
from pathlib import Path

import pytest

from mudhakarah import config
from mudhakarah.errors import BLOCKING

REPO = Path(__file__).resolve().parents[2]
VALID = json.loads((REPO / "tests/fixtures/config/valid_book.json").read_text(encoding="utf-8"))


def codes(findings):
    return {f.code for f in findings}


def test_platform_site_json_is_valid():
    site, findings = config.load_site(REPO)
    assert findings == []
    assert site["platform_name"] == "منصة المذاكرة"


def test_site_rejects_secret_key_and_unknown_field():
    site, _ = config.load_site(REPO)
    bad = dict(site, supabase_publishable_key="service_role_xyz", extra=1)
    found = config.validate_site(bad)
    assert {"V1.value", "V1.unknown-field"} <= codes(found)
    assert all(f.severity == BLOCKING for f in found)


def test_valid_book_passes():
    assert config.validate_book(VALID, folder_name="fixture-book") == []


def test_tafseer_published_folder_is_approved():
    book = copy.deepcopy(VALID)
    book["output"] = "Tafseer/TareekhTafseerAQU.html"
    assert config.validate_book(book) == []


@pytest.mark.parametrize("mutate,code", [
    (lambda b: b.update(colour_typo="x"), "V1.unknown-field"),
    (lambda b: b["theme"]["light"].update(acent="#000000"), "V1.unknown-field"),
    (lambda b: b.pop("storage_key"), "V1.missing-field"),
    (lambda b: b["theme"]["dark"].pop("line"), "V1.missing-field"),
    (lambda b: b["theme"]["light"].update(accent="red"), "V1.value"),
    (lambda b: b.update(output="unknown/Other.html"), "V1.value"),
    (lambda b: b.update(output="mantiq/../index.html"), "V1.value"),
    (lambda b: b.update(slug="Fixture_Book"), "V1.value"),
    (lambda b: b.update(schema_version=2), "V1.value"),
    (lambda b: b["content"].update(loader="json"), "V1.value"),
    (lambda b: b["content"]["files"].append("../evil.py"), "V1.value"),
    (lambda b: b["quiz"].update(seed="1447"), "V1.type"),
    (lambda b: b.update(title=""), "V1.empty"),
    (lambda b: b["content"]["chapters"].append({"symbol": "CH2", "quiz_name": "الباب الأول"}),
     "V1.duplicate-chapter"),
    (lambda b: b["content"].update(anchor="page"), "V1.value"),
    (lambda b: b["content"]["chapters"][0].update(from_page=10), "V1.chapter-pages"),
    (lambda b: b.update(dedication={"teacher": "د. فلان"}), "V1.unknown-field"),
    (lambda b: b.setdefault("features", {}).update(dedication_card=True), "V1.missing-field"),
    (lambda b: b.setdefault("features", {}).update(step2=["S2-9"]), "V1.value"),
    (lambda b: b.setdefault("features", {}).update(step2="S2-1"), "V1.type"),
    (lambda b: b.setdefault("features", {}).update(step2=["S2-1", "S2-1"]), "V1.duplicate-switch"),
])
def test_book_errors_block(mutate, code):
    book = copy.deepcopy(VALID)
    mutate(book)
    found = config.validate_book(book, folder_name="fixture-book")
    assert code in codes(found), found
    assert all(f.severity == BLOCKING for f in found)


def test_slug_must_equal_folder():
    found = config.validate_book(VALID, folder_name="another-folder")
    assert "V1.slug-folder" in codes(found)


def test_read_json_reports_bad_files(tmp_path):
    (tmp_path / "a.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "b.json").write_bytes(b"\xff\xfe")
    assert codes(config.read_json(tmp_path / "a.json")[1]) == {"V1.json"}
    assert codes(config.read_json(tmp_path / "b.json")[1]) == {"V1.encoding"}
    assert codes(config.read_json(tmp_path / "missing.json")[1]) == {"V1.missing-file"}


def test_step2_switches_are_optional_and_listed_once():
    book = copy.deepcopy(VALID)
    assert config.step2_changes(book) == frozenset()
    book.setdefault("features", {})["step2"] = list(config.STEP2_CHANGES)
    assert config.validate_book(book, folder_name="fixture-book") == []
    assert config.step2_changes(book) == frozenset({"S2-1", "S2-2", "S2-3"})


def test_chapter_anchor_needs_increasing_from_pages():
    fiqh = json.loads((REPO / "books" / "madkhal-fiqh" / "book.json").read_text(encoding="utf-8"))
    assert config.validate_book(fiqh, folder_name="madkhal-fiqh") == []
    for bad in ([None, 51, 51, 143], [None, 105, 51, 143], [1, 51, 105, 143], [None, None, 105, 143]):
        b = copy.deepcopy(fiqh)
        for ch, p in zip(b["content"]["chapters"], bad):
            ch.pop("from_page", None)
            if p is not None:
                ch["from_page"] = p
        assert "V1.chapter-pages" in codes(config.validate_book(b, folder_name="madkhal-fiqh")), bad
