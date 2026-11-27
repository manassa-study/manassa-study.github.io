"""Browser tests of the built pilot page (spec section 9). Advisory in Phase 1,
blocking from the pilot migration (Phase 2). No network: everything but 127.0.0.1 is
blocked, so Supabase is never contacted (R5)."""
import json

import pytest

from helpers import GOLDEN, REPO
from pagekit import STORAGE_KEY, block_outside

LIVE = json.loads((GOLDEN / "MunazaraRashidiyaAQU.data.json").read_text(encoding="utf-8"))
TOPICS = [t["id"] for ch in LIVE["DEEP_STUDY_DATA"] for s in ch["sections"] for t in s["topics"]]
ROUTES = (["#home", "#about", "#quiz"] + [f"#study-{t}" for t in TOPICS]
          + [f"#review-{t}" for t in ("cards", "tables", "capsules", "ayat", "sheet")]
          + [f"#maps-{i}" for i in range(len(LIVE["MIND_MAPS"]) + 1)])
FIXTURE = json.loads((REPO / "tests" / "fixtures" / "munazara-state.json").read_text(encoding="utf-8"))
QUERIES = json.loads((REPO / "tests" / "fixtures" / "queries.json").read_text(encoding="utf-8"))["queries"]


def stored(page):
    return json.loads(page.evaluate(f"localStorage.getItem({json.dumps(STORAGE_KEY)})"))


def no_overflow(page, width):
    return page.evaluate("document.documentElement.scrollWidth") <= width


def test_every_route_opens(open_page, page_url):
    page, errors, blocked = open_page()
    for r in ROUTES:
        page.goto(page_url + r)
        assert page.locator("#view").inner_text().strip(), r
    assert errors == []


def test_language_and_direction_are_set_before_any_script_runs(browser, page_url):
    """S2-1: with JavaScript off, the page is still Arabic and right-to-left."""
    ctx = browser.new_context(java_script_enabled=False)
    try:
        blocked = []
        block_outside(ctx, blocked)
        page = ctx.new_page()
        page.goto(page_url + "#home")
        html = page.locator("html")
        assert html.get_attribute("lang") == "ar"
        assert html.get_attribute("dir") == "rtl"
        assert page.evaluate("getComputedStyle(document.body).direction") == "rtl"
    finally:
        ctx.close()


def test_supabase_is_never_reached(open_page, page_url):
    page, errors, blocked = open_page()
    page.goto(page_url + "#home")
    page.wait_for_timeout(300)
    reached = page.evaluate("performance.getEntriesByType('resource').map(e=>e.name)")
    assert not any("supabase" in u for u in reached)


def test_card_flip_and_mastery(open_page, page_url):
    page, errors, _ = open_page()
    page.goto(page_url + "#review-cards")
    first = page.locator(".fc-q").inner_text()
    page.click("#fcBox")
    assert "back" in page.locator("#fcBox").get_attribute("class")
    assert page.locator(".fc-a").inner_text()
    page.click("#fcKnow")
    s = stored(page)
    assert s["mastered"].get("1") is True and first
    assert errors == []


@pytest.mark.parametrize("width", [360, 390])
def test_maps_open_on_phones(open_page, page_url, width):
    page, errors, _ = open_page(width=width)
    for i in range(len(LIVE["MIND_MAPS"]) + 1):
        page.goto(page_url + f"#maps-{i}")
        assert page.locator("#mm2").count() == 1, i
        assert no_overflow(page, width), i
    assert errors == []


def test_full_practice_quiz(open_page, page_url):
    page, errors, _ = open_page()
    page.goto(page_url + "#quiz")
    page.click('.mode[data-m="practice"]')
    page.click('.chip[data-cnt="0"]')
    page.click("#qStart")
    n = len(LIVE["QUIZ_BANK"])
    for i in range(n):
        page.click('.opt[data-oi="0"]')
        assert page.locator(".opt.right").count() == 1
        page.click("#qFinish" if i == n - 1 else "#qNext")
    s = stored(page)
    assert s["quizHist"][-1]["n"] == n and s["quizHist"][-1]["mode"] == "practice"
    assert errors == []


def test_mock_exam(open_page, page_url):
    page, errors, _ = open_page()
    page.goto(page_url + "#quiz")
    page.click('.mode[data-m="exam"]')
    page.click('.chip[data-cnt="10"]')
    page.click("#qStart")
    assert page.locator("#tmr").count() == 1
    for i in range(10):
        page.click('.opt[data-oi="1"]')
        page.click("#qFinish" if i == 9 else "#qNext")
    s = stored(page)
    assert s["quizHist"][-1]["mode"] == "exam" and s["quizHist"][-1]["n"] == 10
    assert errors == []


def test_ten_saved_search_queries(open_page, page_url):
    page, errors, _ = open_page()
    page.goto(page_url + "#home")
    assert len(QUERIES) == 10
    for q, expected in QUERIES.items():
        page.click("#searchBtn")
        page.fill("#q", q)
        assert page.locator("#spRes .sr-g").first.inner_text() == expected["header"], q
        assert page.locator("#spRes .sr-i").count() == expected["results"], q
        page.click("#spClose")
    assert errors == []


@pytest.mark.parametrize("width", [360, 390])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_phone_widths_in_both_themes(open_page, page_url, width, theme):
    page, errors, _ = open_page(width=width, state={"theme": theme})
    page.goto(page_url + "#home")
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == theme
    for r in ("#home", "#study-t1", "#review-cards", "#quiz"):
        page.goto(page_url + r)
        assert no_overflow(page, width), r
    assert errors == []


def test_saved_progress_from_the_live_page_loads_unchanged(open_page, page_url):
    state = FIXTURE["state"]
    page, errors, _ = open_page(state=state)
    page.goto(page_url + "#home")
    s = stored(page)
    for key in ("done", "mastered", "again", "quizHist", "lastWrong", "wrongBank", "mapIdx", "last"):
        assert s[key] == state[key], key
    page.goto(page_url + "#review-cards")
    mastered = sum(1 for v in state["mastered"].values() if v)
    assert f"أتقنت {mastered}".translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")) in page.inner_text("#rv")
    page.goto(page_url + "#quiz")
    assert f"({str(len(state['wrongBank'])).translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))})" in \
        page.locator("#qMore").text_content()
    page.goto(page_url + "#study-t1")
    assert page.locator("#doneBtn").inner_text() == "إلغاء العلامة"  # t1 is still marked studied
    assert errors == []
