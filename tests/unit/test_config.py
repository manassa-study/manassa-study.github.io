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


@pytest.mark.parametrize("mutate,code", [
    (lambda b: b.update(colour_typo="x"), "V1.unknown-field"),
    (lambda b: b["theme"]["light"].update(acent="#000000"), "V1.unknown-field"),
    (lambda b: b.pop("storage_key"), "V1.missing-field"),
    (lambda b: b["theme"]["dark"].pop("line"), "V1.missing-field"),
    (lambda b: b["theme"]["light"].update(accent="red"), "V1.value"),
    (lambda b: b.update(output="Tafseer/Other.html"), "V1.value"),
    (lambda b: b.update(output="mantiq/../index.html"), "V1.value"),
    (lambda b: b.update(slug="Fixture_Book"), "V1.value"),
    (lambda b: b.update(schema_version=2), "V1.value"),
    (lambda b: b["content"].update(loader="json"), "V1.value"),
    (lambda b: b["content"]["files"].append("../evil.py"), "V1.value"),
    (lambda b: b["quiz"].update(seed="1447"), "V1.type"),
    (lambda b: b.update(title=""), "V1.empty"),
    (lambda b: b["content"]["chapters"].append({"symbol": "CH2", "quiz_name": "الباب الأول"}),
     "V1.duplicate-chapter"),
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
