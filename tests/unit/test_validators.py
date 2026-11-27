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


PAGE_EXCEPTIONS = json.loads((REPO / "books" / "munazara-rashidiya" / "page-references.json").read_text(encoding="utf-8"))


UNREVIEWED = ("V6.unreviewed-exceptions", "warning")


def codes(found):
    return [(f.code, f.severity) for f in found]


def test_v6_on_the_pilot_only_warns_that_its_exceptions_are_unreviewed():
    found = v06_references.check(LIVE, "x", PAGE_EXCEPTIONS)
    assert codes(found) == [UNREVIEWED]
    assert "43 page-reference exception(s)" in found[0].message and "not verified" in found[0].message
    assert v06_references.check_exceptions_file(PAGE_EXCEPTIONS, "x") == []


def test_v6_seeded_exceptions_are_all_marked_unreviewed_and_carry_no_approver():
    assert "approved_by" not in PAGE_EXCEPTIONS and PAGE_EXCEPTIONS["rule_decided_by"] == "Bilal"
    assert all(e["review"] == "unreviewed" for e in PAGE_EXCEPTIONS["exceptions"])
    assert not any("reviewed_by" in e or "approved_by" in e for e in PAGE_EXCEPTIONS["exceptions"])


def test_v6_warning_counts_only_unreviewed_exceptions():
    data = copy.deepcopy(PAGE_EXCEPTIONS)
    for e in data["exceptions"][:40]:
        e.update(review="reviewed", reviewed_by="Reviewer", reviewed_on="2027-01-01")
    assert v06_references.check_exceptions_file(data, "x") == []
    found = v06_references.check(LIVE, "x", data)
    assert codes(found) == [UNREVIEWED] and found[0].message.startswith("3 page-reference")
    for e in data["exceptions"]:
        e.update(review="reviewed", reviewed_by="Reviewer", reviewed_on="2027-01-01")
    assert v06_references.check(LIVE, "x", data) == []


def test_v6_exceptions_seeded_exactly_from_the_live_page():
    # 37 lesson blocks and 6 explanations of the live page have no «ص»; nothing else is excepted
    kinds = [e["kind"] for e in PAGE_EXCEPTIONS["exceptions"]]
    assert kinds.count("block") == 37 and kinds.count("explanation") == 6
    without = v06_references.check(LIVE, "x")
    assert len(without) == 43 and {f.code for f in without} == {"V6.page-reference-missing"}
    assert all(f.severity == "blocking" for f in without)


def test_v6_reference_format_and_quran_stay_warnings():
    bad = copy.deepcopy(LIVE)
    bad["FLASHCARDS"][0]["a"] += " (البقرة: ٣٠٠)"
    bad["QUIZ_BANK"][0]["exp"] += " ص٢٢"
    found = v06_references.check(bad, "x", PAGE_EXCEPTIONS)
    assert sorted(f.code for f in found) == ["V6.page-reference", "V6.quran-reference", "V6.unreviewed-exceptions"]
    assert {f.severity for f in found} == {"warning"}


def test_v6_editing_an_excepted_item_blocks_again():
    bad = copy.deepcopy(LIVE)
    q = next(q for q in bad["QUIZ_BANK"] if q["id"] == 2)
    q["exp"] += " زيادة"
    found = v06_references.check(bad, "x", PAGE_EXCEPTIONS)
    assert [f.code for f in found if f.severity == "blocking"] == ["V6.page-reference-missing"]
    assert sorted(f.code for f in found if f.severity == "warning") == ["V6.stale-exception",
                                                                         "V6.unreviewed-exceptions"]


def test_v6_adding_a_reference_leaves_a_stale_exception_warning():
    fixed = copy.deepcopy(LIVE)
    q = next(q for q in fixed["QUIZ_BANK"] if q["id"] == 2)
    q["exp"] += " (ص ٢٢)"
    found = v06_references.check(fixed, "x", PAGE_EXCEPTIONS)
    assert sorted(codes(found)) == [("V6.stale-exception", "warning"), UNREVIEWED]


def test_v6_new_block_without_reference_blocks():
    bad = copy.deepcopy(LIVE)
    bad["DEEP_STUDY_DATA"][0]["sections"][0]["topics"][0]["blocks"].append({"label": "جديد", "text": "شرح جديد"})
    found = v06_references.check(bad, "x", PAGE_EXCEPTIONS)
    assert codes(found) == [("V6.page-reference-missing", "blocking"), UNREVIEWED]


def test_v6_reordering_blocks_keeps_exceptions():
    moved = copy.deepcopy(LIVE)
    blocks = moved["DEEP_STUDY_DATA"][0]["sections"][0]["topics"][0]["blocks"]
    blocks.reverse()
    assert codes(v06_references.check(moved, "x", PAGE_EXCEPTIONS)) == [UNREVIEWED]


@pytest.mark.parametrize("change", [
    lambda e: e.pop("exceptions"),
    lambda e: e["exceptions"][0].update(kind="table"),
    lambda e: e["exceptions"][0].pop("topic"),
    lambda e: e["exceptions"][-1].update(question="2"),
    lambda e: e["exceptions"][0].update(sha1="abc"),
    lambda e: e["exceptions"][0].update(reason=" "),
    lambda e: e["exceptions"].append(dict(e["exceptions"][0])),
    lambda e: e["exceptions"][0].pop("review"),
    lambda e: e["exceptions"][0].update(review="verified"),
    lambda e: e["exceptions"][0].update(review="reviewed"),
    lambda e: e["exceptions"][0].update(review="reviewed", reviewed_by="X"),
    lambda e: e["exceptions"][0].update(approved_by="X"),
    lambda e: e.update(approved_by="Bilal"),
])
def test_v6_exceptions_file_shape(change):
    data = copy.deepcopy(PAGE_EXCEPTIONS)
    change(data)
    assert [f.code for f in v06_references.check_exceptions_file(data, "x")] == ["V6.exceptions-invalid"]


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


def test_opening_follows_the_s2_1_switch():
    step1 = {"storage_key": "k"}
    s21 = {"storage_key": "k", "features": {"step2": ["S2-1"]}}
    assert v08_html.check(v08_html.STEP1_OPENING, step1, "x") == []
    assert v08_html.check(v08_html.STEP2_OPENING, s21, "x") == []
    assert [f.code for f in v08_html.check(v08_html.STEP2_OPENING, step1, "x")] == ["V8.opening"]
    assert [f.code for f in v08_html.check(v08_html.STEP1_OPENING, s21, "x")] == ["V8.opening"]
    assert [f.code for f in v08_html.check('<!doctype html><html lang="ar"><head>', s21, "x")] == ["V8.opening"]


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
    book = {"storage_key": key}
    if key == "munazara-rashidiya-v1":  # migrated: its step-2 switches decide the opening
        book = json.loads((REPO / "books" / "munazara-rashidiya" / "book.json").read_text(encoding="utf-8"))
    assert [f for f in v08_html.check((REPO / page).read_text(encoding="utf-8"), book, "x")
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
