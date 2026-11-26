"""Warnings and reports of the section 7 validators, and their data."""
import copy
import json
import subprocess

import pytest

from helpers import GOLDEN, PILOT, REPO
from mudhakarah.validate import v04_duplicates, v06_references, v07_assets, v08_html, v11_integrity, v13_paths
from mudhakarah.validate.v06_references import page_reference_problems, quran_reference_problems

SITE = json.loads((REPO / "platform" / "site.json").read_text(encoding="utf-8"))
LIVE = json.loads((GOLDEN / "MunazaraRashidiyaAQU.data.json").read_text(encoding="utf-8"))


def test_surah_table_is_complete():
    assert len(v06_references.SURAHS) == 114
    assert sum(n for _, n in v06_references.SURAHS) == 6236


@pytest.mark.parametrize("text, problems", [
    ("انظر ص ٢٢", 0), ("ص ٢٢ - ٩٣", 0), ("ص 5-7", 0), ("(ص ٣١).", 0), ("وصف حسن", 0),
    ("ص٢٢", 1), ("ص ٣٠ - ٢٥", 1), ("ص ٠", 1), ("ص ٥ - ", 1),
])
def test_page_reference_format(text, problems):
    assert len(page_reference_problems(text)) == problems


@pytest.mark.parametrize("text, problems", [
    ("«البقرة: ١٨٥»", 0), ("«سورة البقرة: ١٢٣»", 0), ("«آل عمران: ١٩٠ - ١٩١»", 0), ("«المقاصد الحسنة: ١٣٥٦»", 0),
    ("«الإسراء: ١»", 0), ("«الاسراء: ١١١»", 0), ("«ص: ٥»", 0),
    ("«البقرة: ٢٨٧»", 1), ("«سورة الفلاحة: ٣»", 1), ("«سورة ص: ٩٠»", 1), ("«آل عمران: ١٩١ - ١٩٠»", 1),
    ("«الناس: ٠»", 1),
])
def test_quran_references(text, problems):
    assert len(quran_reference_problems(text)) == problems


def test_v6_warns_only_and_is_quiet_on_the_pilot():
    assert v06_references.check(LIVE, "x") == []
    bad = copy.deepcopy(LIVE)
    bad["FLASHCARDS"][0]["a"] += " (البقرة: ٣٠٠)"
    found = v06_references.check(bad, "x")
    assert [f.severity for f in found] == ["warning"]


def test_near_duplicate_is_a_warning():
    raw = {"chapters": [], "maps": [], "cards": [{"q": "ما المنع؟", "topic": "t1"}, {"q": "ما المنع", "topic": "t2"}],
           "questions": []}
    found = v04_duplicates.check(raw, "x")
    assert [(f.code, f.severity) for f in found] == [("V4.near-duplicate", "warning")]


def test_new_external_host_is_a_warning(tmp_path):
    found = v07_assets.check('<script src="https://example.org/x.js">', tmp_path, SITE, "x")
    assert [(f.code, f.severity) for f in found] == [("V7.new-host", "warning")]


def test_baseline_hosts_and_the_tafseer_site_are_not_flagged():
    page = (REPO / "mantiq" / "MunazaraRashidiyaAQU.html").read_text(encoding="utf-8")
    assert v07_assets.check(page, REPO, SITE, "x", "mantiq/MunazaraRashidiyaAQU.html") == []


def test_page_size_warnings():
    text = v08_html.STEP1_OPENING + "x" * 10
    assert v08_html.check(text, {"storage_key": "k"}, "x", previous_size=10)[0].code == "V8.size"
    big = v08_html.STEP1_OPENING + "x" * 800_001
    assert [f.severity for f in v08_html.check(big, {"storage_key": "k"}, "x")] == ["warning"]


@pytest.mark.parametrize("key, page", [("madkhal-fiqh-v1", "fiqh/MadkhalFiqhAQU.html"),
                                       ("munazara-rashidiya-v1", "mantiq/MunazaraRashidiyaAQU.html"),
                                       ("takhreej-asaneed-v1", "hadith/TakhreejAsaneedAQU.html")])
def test_book_markers_belong_to_their_own_page_only(key, page):
    pages = {"madkhal-fiqh-v1": "fiqh/MadkhalFiqhAQU.html", "munazara-rashidiya-v1": "mantiq/MunazaraRashidiyaAQU.html",
             "takhreej-asaneed-v1": "hadith/TakhreejAsaneedAQU.html"}
    own = v08_html.chrome((REPO / page).read_text(encoding="utf-8"))
    for marker in v08_html.BOOK_MARKERS[key]:
        assert marker in own, marker
        for other_key, other in pages.items():
            if other_key != key:
                assert marker not in v08_html.chrome((REPO / other).read_text(encoding="utf-8")), (marker, other)
    # and each of these pages passes V8 as its own book
    assert [f for f in v08_html.check((REPO / page).read_text(encoding="utf-8"), {"storage_key": key}, "x")
            if f.severity == "blocking"] == []


def test_published_paths_are_the_baseline_tree():
    data = json.loads((REPO / "platform" / "published-paths.json").read_text(encoding="utf-8"))
    tree = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", data["baseline_commit"]],
                          capture_output=True, text=True)
    if tree.returncode == 0:
        assert sorted(tree.stdout.split()) == data["paths"]
    assert len(data["paths"]) == 18 and data["redirects"] == []
    assert v13_paths.check(REPO) == []


def test_approved_redirect_covers_a_moved_path(tmp_path):
    from helpers import make_repo
    root = make_repo(tmp_path)
    (root / "fiqh.html").unlink()
    path = root / "platform" / "published-paths.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["redirects"].append({"from": "fiqh.html", "to": "fiqh/", "approved_by": "Bilal", "pull_request": 1})
    path.write_text(json.dumps(data), encoding="utf-8")
    assert v13_paths.check(root) == []


def test_content_change_report():
    new = copy.deepcopy(LIVE)
    new["FLASHCARDS"][0]["a"] = "جواب جديد"
    new["QUIZ_BANK"].pop()
    new["QURANIC_EXAMPLES"][0]["ayah"] = "نص آخر"
    topic = new["DEEP_STUDY_DATA"][0]["sections"][0]["topics"][0]
    matn = next(i for i, b in enumerate(topic["blocks"]) if "المتن" in b["label"])
    topic["blocks"][matn]["text"] = "متن معدّل"
    report = v11_integrity.content_change_report(LIVE, new, "page")
    changes, special = report.split("## Matn quotations and Qur'an fields")
    assert "Card 1: changed" in changes and "`a`" in changes
    assert "Question 177: removed" in changes
    assert "Example 0: changed" in changes
    assert "Matn, topic t1" in special and "Example 0, `ayah`" in special
    assert "No content changes." in v11_integrity.content_change_report(LIVE, LIVE, "page")
