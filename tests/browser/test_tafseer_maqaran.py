"""Browser coverage for Book 4's preserved payload and interactive renderer."""
import json
import tempfile

import pytest

from helpers import EXTRACTS, REPO
from pagekit import block_outside, seed_script, serve

SLUG = "tafseer-maqaran"
BOOK = json.loads((REPO / "books" / SLUG / "book.json").read_text(encoding="utf-8"))
LIVE = json.loads(EXTRACTS["TafseerMaqaranAQU"].read_text(encoding="utf-8"))
TOPICS = [t["id"] for ch in LIVE["DEEP_STUDY_DATA"] for s in ch["sections"] for t in s["topics"]]
ROUTES = (["#home", "#about", "#quiz"] + [f"#study-{t}" for t in TOPICS]
          + [f"#review-{t}" for t in ("cards", "tables", "capsules", "ayat", "sheet", "drill")]
          + [f"#maps-{i}" for i in range(len(LIVE["MIND_MAPS"]) + 1)])


@pytest.fixture(scope="module")
def tafseer_url():
    from mudhakarah.pipeline import run_book
    html = run_book(REPO, SLUG).html
    with tempfile.TemporaryDirectory() as tmp, serve(html, tmp, BOOK["output"]) as url:
        yield url


@pytest.fixture
def open_tafseer(browser):
    contexts = []

    def _open(width=390, state=None):
        ctx = browser.new_context(viewport={"width": width, "height": 844})
        contexts.append(ctx)
        blocked = []
        block_outside(ctx, blocked)
        ctx.add_init_script(seed_script(state, storage_key=BOOK["storage_key"],
                                        welcome_key=BOOK.get("welcome_session_key", "tafseer-wel")))
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        return page, errors, blocked

    yield _open
    for context in contexts:
        context.close()


def _visible_html(page, value):
    return page.evaluate("value => { const node=document.createElement('div'); node.innerHTML=value; return node.innerText; }", value)


def test_every_book4_route_opens(open_tafseer, tafseer_url):
    page, errors, _ = open_tafseer()
    for route in ROUTES:
        page.goto(tafseer_url + route)
        assert page.locator("#view").inner_text().strip(), route
    assert errors == []


def test_quiz_preserves_baseline_order_and_handles_answers(open_tafseer, tafseer_url):
    page, errors, _ = open_tafseer()
    page.goto(tafseer_url + "#quiz")
    expected = LIVE["QUIZ_BANK"]
    actual = page.evaluate("D.QUIZ_BANK.map(q => ({id:q.id, q:q.q, options:q.options}))")
    assert actual == [{"id": q["id"], "q": q["q"], "options": q["options"]} for q in expected]

    page.click('.chip[data-cnt="0"]')
    page.click("#qMore summary")
    if page.get_attribute("#qShuf", "aria-pressed") == "true":
        page.click("#qShuf")
    page.click("#qStart")
    first = expected[0]
    assert page.locator(".qrun .qtext").inner_text() == _visible_html(page, first["q"])
    assert page.locator(".qrun .opt > span:not(.l)").all_inner_texts() == [
        _visible_html(page, option) for option in first["options"]]

    page.click(f'.qrun .opt[data-oi="{first["correct"]}"]')
    assert page.locator(".exp.ok").count() == 1
    assert page.locator(".qrun .opt.right").count() == 1
    page.click("#qNext")
    assert page.locator(".qrun .qtext").inner_text() == _visible_html(page, expected[1]["q"])
    page.click("#qPrev")
    assert page.locator(".qrun .opt.right").count() == 1
    assert errors == []


def test_ayah_only_key_and_comparison_table_blocks_render(open_tafseer, tafseer_url):
    page, errors, _ = open_tafseer()
    page.goto(tafseer_url + "#home")
    targets = page.evaluate("""() => {
      const topics = D.DEEP_STUDY_DATA.flatMap(ch => ch.sections.flatMap(s => s.topics));
      return {
        ayah: topics.find(t => t.blocks.some(b => b.ayah && !b.text && !b.list && !b.table))?.id,
        key: topics.find(t => t.blocks.some(b => b.key))?.id,
        table: topics.find(t => t.blocks.some(b => b.table))?.id
      };
    }""")
    assert all(targets.values())

    page.goto(tafseer_url + f"#study-{targets['ayah']}")
    assert page.locator("details.blk .ayah-box").count() > 0
    page.goto(tafseer_url + f"#study-{targets['key']}")
    assert page.locator("details.blk.key[open]").count() > 0
    page.goto(tafseer_url + f"#study-{targets['table']}")
    assert page.locator(".reading .cmp table").count() > 0
    assert errors == []


def test_comparison_maps_support_recall_and_navigation(open_tafseer, tafseer_url):
    page, errors, _ = open_tafseer()
    page.goto(tafseer_url + "#maps-1")
    assert page.locator(".book4-map .mt-card").count() > 0
    page.click("#mmRecall")
    assert "recall" in page.locator("#mm2").get_attribute("class")
    first_card = page.locator(".book4-map .mt-card").first
    assert first_card.locator(":scope > .mt").is_hidden()
    first_card.locator(".mt-t").click()
    assert first_card.locator(":scope > .mt").is_visible()
    assert page.locator('.mm2-pick button[aria-pressed="true"]').count() == 1
    assert errors == []


def test_drill_accepts_the_source_classification_and_finishes(open_tafseer, tafseer_url):
    page, errors, _ = open_tafseer()
    page.goto(tafseer_url + "#review-drill")
    assert len(LIVE["DRILL"]) == 12
    for index in range(len(LIVE["DRILL"])):
        wording = page.locator("#rv h3").inner_text()
        item = page.evaluate("""wording => D.DRILL.find(item => {
          const node=document.createElement('div'); node.innerHTML=item.w; return node.innerText===wording;
        })""", wording)
        assert item is not None, wording
        page.click(f'[data-drill="{item["k"]}"]')
        assert page.locator("#rv .exp.ok").count() == 1
        assert page.locator("#rv .pg").inner_text() == item["p"]
        page.click("#drNext")
    result = page.locator("#rv h2").inner_text().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    assert "12 من 12" in result
    assert errors == []
