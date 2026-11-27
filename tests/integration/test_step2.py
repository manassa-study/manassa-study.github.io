"""Step 2 of the pilot migration (docs/step-2-list.md, decision N3).

The published page may differ from the Phase 1 baseline only by the approved
step-2 changes the book has turned on. Each change is written here as the exact
text it replaces in the baseline page and the text that takes its place, so the
whole difference between the baseline and the published page is reviewed in
this file:

- with no switch on, the pilot still builds to the baseline byte for byte;
- with each switch on alone, the build is the baseline with only that change;
- with the book's own switches, the build is the step-2 golden page, which is
  the committed page.
"""
import hashlib
import json

import pytest

from helpers import GOLDEN, PILOT, PILOT_PAGE, PILOT_SHA256, REPO, STEP2_GOLDEN, make_repo
from mudhakarah import TOOL_VERSION
from mudhakarah.config import STEP2_CHANGES
from mudhakarah.pipeline import run_book

BASELINE = GOLDEN / "MunazaraRashidiyaAQU.html"

# change id -> [(text in the baseline page, its replacement, how many times)]
APPROVED = {
    "S2-1": [("<!doctype html><html><head>", '<!doctype html><html lang="ar" dir="rtl"><head>', 1)],
    "S2-2": [('<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
              '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
              f'<meta name="mudhakarah:template" content="{TOOL_VERSION}">', 1)],
    # S2-3 (O-5): one config object after "use strict", and each use reads from it.
    "S2-3": [
        ('"use strict";\n', '"use strict";\nconst BOOK={"storage_key":"munazara-rashidiya-v1",'
         '"welcome_session_key":"munazara-wel","labels":{"examples_title":"الأمثلة التطبيقية",'
         '"examples_short":"الأمثلة","examples_count_noun":"مثالاً","examples_in_lesson":"أمثلة هذا الدرس"},'
         '"search":{"suggestions":["المنع","السند المساوي","النقض الإجمالي","المعارضة بالقلب","الغصب",'
         '"المقاطع","المكابرة","التقريب"]}};\n', 1),
        ('const KEY="munazara-rashidiya-v1";', 'const KEY=BOOK.storage_key;', 1),
        ('["#review-ayat","ayah","الأمثلة التطبيقية",toAr(EX.length)+" مثالاً","t2"],',
         '["#review-ayat","ayah",BOOK.labels.examples_title,toAr(EX.length)+" "+BOOK.labels.examples_count_noun,"t2"],',
         1),
        ('<h2 class="h2">أمثلة هذا الدرس</h2>', '<h2 class="h2">${BOOK.labels.examples_in_lesson}</h2>', 1),
        ('["ayat","الأمثلة"]', '["ayat",BOOK.labels.examples_short]', 1),
        ('IDX.push({g:"الأمثلة التطبيقية",', 'IDX.push({g:BOOK.labels.examples_title,', 1),
        ('${["المنع","السند المساوي","النقض الإجمالي","المعارضة بالقلب","الغصب","المقاطع","المكابرة","التقريب"].map(',
         '${BOOK.search.suggestions.map(', 1),
        ('sessionStorage.getItem("munazara-wel")', 'sessionStorage.getItem(BOOK.welcome_session_key)', 1),
        ('sessionStorage.setItem("munazara-wel","1")', 'sessionStorage.setItem(BOOK.welcome_session_key,"1")', 1),
    ],
}


def book_switches():
    book = json.loads((REPO / "books" / PILOT / "book.json").read_text(encoding="utf-8"))
    return book.get("features", {}).get("step2", [])


def build(tmp_path, switches):
    root = make_repo(tmp_path, [(PILOT, REPO / "books" / PILOT)])
    path = root / "books" / PILOT / "book.json"
    book = json.loads(path.read_text(encoding="utf-8"))
    book.setdefault("features", {})["step2"] = list(switches)
    path.write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
    return run_book(root, PILOT).html


def apply(text, change):
    for old, new, count in APPROVED[change]:
        assert text.count(old) == count, (change, old)
        text = text.replace(old, new)
    return text


def test_every_approved_change_has_its_expected_diff():
    assert set(APPROVED) <= set(STEP2_CHANGES)
    assert set(book_switches()) <= set(APPROVED), "a switch is on without its expected diff in this file"


def test_with_no_switch_on_the_pilot_still_builds_to_the_baseline(tmp_path):
    html = build(tmp_path, [])
    assert html == BASELINE.read_bytes()
    assert hashlib.sha256(html).hexdigest() == PILOT_SHA256
    assert len(html) == 408_561


@pytest.mark.parametrize("change", sorted(APPROVED))
def test_each_change_alone_differs_from_the_baseline_only_by_its_diff(tmp_path, change):
    baseline = BASELINE.read_text(encoding="utf-8")
    assert build(tmp_path, [change]).decode("utf-8") == apply(baseline, change)


def test_the_books_switches_give_the_step2_golden_page(tmp_path):
    expected = BASELINE.read_text(encoding="utf-8")
    for change in STEP2_CHANGES:
        if change in book_switches():
            expected = apply(expected, change)
    assert STEP2_GOLDEN.read_text(encoding="utf-8") == expected
    assert build(tmp_path, book_switches()) == STEP2_GOLDEN.read_bytes()


def test_the_committed_page_is_the_step2_golden_page():
    assert (REPO / PILOT_PAGE).read_bytes() == STEP2_GOLDEN.read_bytes()
    assert run_book(REPO, PILOT).html == STEP2_GOLDEN.read_bytes()


def test_s2_3_moves_every_listed_word_out_of_the_app_script_body():
    """After S2-3 each listed book word appears in the app script once: in the config object
    (the storage key also stays in the head's theme script, which is not on the list)."""
    page = STEP2_GOLDEN.read_text(encoding="utf-8")
    app = page.split('"use strict";\n', 1)[1]
    book = json.loads((REPO / "books" / PILOT / "book.json").read_text(encoding="utf-8"))
    words = [book["storage_key"], book["welcome_session_key"]] + [
        book["labels"][k] for k in ("examples_title", "examples_short", "examples_count_noun", "examples_in_lesson")]
    config_line, body = app.split("\n", 1)
    assert config_line.startswith("const BOOK={") and config_line.endswith("};")
    for word in words:
        assert f'"{word}"' in config_line, word
        assert f'"{word}"' not in body, word
    assert json.dumps(book["search"]["suggestions"], ensure_ascii=False, separators=(",", ":")) not in body
