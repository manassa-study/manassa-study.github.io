"""Browser tests of the built المدخل إلى الفقه الإسلامي page (Phase 3, book 1). Browser
tests block at each book's migration (master plan section I). The build equals the live
page byte for byte (tests/integration/test_fiqh.py); these check the built page in a
real browser. No network: everything but 127.0.0.1 is blocked, so Supabase is never
contacted (R5)."""
import json
import tempfile

import pytest

from helpers import EXTRACTS, REPO
from pagekit import block_outside, seed_script, serve

SLUG = "madkhal-fiqh"
BOOK = json.loads((REPO / "books" / SLUG / "book.json").read_text(encoding="utf-8"))
LIVE = json.loads(EXTRACTS["MadkhalFiqhAQU"].read_text(encoding="utf-8"))
TOPICS = [t["id"] for ch in LIVE["DEEP_STUDY_DATA"] for s in ch["sections"] for t in s["topics"]]
ROUTES = (["#home", "#about", "#quiz"] + [f"#study-{t}" for t in TOPICS]
          + [f"#review-{t}" for t in ("cards", "tables", "capsules", "ayat", "sheet")]
          + [f"#maps-{i}" for i in range(len(LIVE["MIND_MAPS"]) + 1)])


@pytest.fixture(scope="module")
def fiqh_url():
    from mudhakarah.pipeline import run_book
    html = run_book(REPO, SLUG).html
    with tempfile.TemporaryDirectory() as tmp, serve(html, tmp, BOOK["output"]) as url:
        yield url


@pytest.fixture
def open_fiqh(browser):
    contexts = []

    def _open(width=390, state=None, welcome_seen=True, color_scheme="light"):
        ctx = browser.new_context(viewport={"width": width, "height": 844}, color_scheme=color_scheme)
        contexts.append(ctx)
        blocked = []
        block_outside(ctx, blocked)
        ctx.add_init_script(seed_script(state, welcome_seen=welcome_seen, storage_key=BOOK["storage_key"],
                                        welcome_key=BOOK["welcome_session_key"]))
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        return page, errors, blocked

    yield _open
    for c in contexts:
        c.close()


def stored(page):
    return json.loads(page.evaluate(f"localStorage.getItem({json.dumps(BOOK['storage_key'])})"))


def test_every_route_opens(open_fiqh, fiqh_url):
    page, errors, _ = open_fiqh()
    for r in ROUTES:
        page.goto(fiqh_url + r)
        assert page.locator("#view").inner_text().strip(), r
    assert errors == []


def test_supabase_is_never_reached(open_fiqh, fiqh_url):
    page, _, _ = open_fiqh()
    page.goto(fiqh_url + "#home")
    page.wait_for_timeout(300)
    reached = page.evaluate("performance.getEntriesByType('resource').map(e=>e.name)")
    assert not any("supabase" in u for u in reached)


def test_welcome_shows_the_dedication_card(open_fiqh, fiqh_url):
    page, errors, _ = open_fiqh(welcome_seen=False)
    page.goto(fiqh_url + "#home")
    assert page.locator("#wel").is_visible()
    assert page.locator("#wel .wel-dr").inner_text() == BOOK["dedication"]["teacher"]
    assert errors == []


def test_quiz_chapters_are_the_four_chapters(open_fiqh, fiqh_url):
    page, errors, _ = open_fiqh()
    page.goto(fiqh_url + "#quiz")
    chapters = page.evaluate("[...new Set(D.QUIZ_BANK.map(q=>q.chapter))]")
    assert chapters == [c["quiz_name"] for c in BOOK["content"]["chapters"]]
    assert errors == []


def test_a_practice_quiz_saves_under_the_book_key(open_fiqh, fiqh_url):
    page, errors, _ = open_fiqh()
    page.goto(fiqh_url + "#quiz")
    page.click('.chip[data-cnt="10"]')
    page.click("#qStart")
    for i in range(10):
        page.click('.opt[data-oi="0"]')
        page.click("#qFinish" if i == 9 else "#qNext")
    s = stored(page)
    assert s["quizHist"][-1]["n"] == 10
    assert errors == []


def test_cards_and_examples_get_topics_from_their_pages(open_fiqh, fiqh_url):
    """The app's attach() gives each card and example the topic its page falls in."""
    page, errors, _ = open_fiqh()
    page.goto(fiqh_url + "#review-cards")
    assert page.evaluate("D.FLASHCARDS.filter(x=>!x.topic).length") == 0
    assert page.evaluate("D.QURANIC_EXAMPLES.filter(x=>!x.topic).length") == 0
    assert errors == []


@pytest.mark.parametrize("width", [360, 390])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_phone_widths_in_both_themes(open_fiqh, fiqh_url, width, theme):
    page, errors, _ = open_fiqh(width=width, state={"theme": theme})
    page.goto(fiqh_url + "#home")
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == theme
    for r in ("#home", "#study-" + TOPICS[0], "#review-cards", "#quiz"):
        page.goto(fiqh_url + r)
        assert page.evaluate("document.documentElement.scrollWidth") <= width, r
    assert errors == []
