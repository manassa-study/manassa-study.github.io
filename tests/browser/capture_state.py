"""Capture a saved progress state from the baseline pilot page (spec section 9, R4).

    MUDHAKARAH_CHROMIUM=/path/to/chrome python tests/browser/capture_state.py

Drives the Phase 0 baseline page (tests/golden) as a student would: marks three
topics studied, masters three cards and marks two for review, opens a map, and
takes a ten-question practice quiz answering the first option each time. The
localStorage it leaves is written to tests/fixtures/munazara-state.json. The
network is blocked throughout; nothing reaches Supabase."""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pagekit import STORAGE_KEY, block_outside, launch, seed_script, serve  # noqa: E402

REPO = HERE.parents[1]
OUT = REPO / "tests" / "fixtures" / "munazara-state.json"


def drive(page, url):
    for t in ("t1", "t2", "t5"):
        page.goto(url + "#study-" + t)
        page.click("#doneBtn")
    page.goto(url + "#review-cards")
    for _ in range(3):
        page.click("#fcBox")
        page.click("#fcKnow")
        page.click("#fcNext") if page.locator("#fcNext").count() else None
    for _ in range(2):
        page.click("#fcAgain")
        page.click("#fcNext") if page.locator("#fcNext").count() else None
    page.goto(url + "#maps-3")
    page.goto(url + "#quiz")
    page.click('.mode[data-m="practice"]')
    page.click('.chip[data-cnt="10"]')
    page.click("#qStart")
    for i in range(10):
        page.click('.opt[data-oi="0"]')
        page.click("#qFinish" if i == 9 else "#qNext")
    return json.loads(page.evaluate(f"localStorage.getItem({json.dumps(STORAGE_KEY)})"))


def main():
    from playwright.sync_api import sync_playwright
    html = (REPO / "tests" / "golden" / "MunazaraRashidiyaAQU.html").read_bytes()
    with tempfile.TemporaryDirectory() as tmp, serve(html, tmp) as url, sync_playwright() as p:
        browser = launch(p)
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        blocked = []
        block_outside(ctx, blocked)
        ctx.add_init_script(seed_script())
        state = drive(ctx.new_page(), url)
        browser.close()
    assert not any("supabase" in u for u in blocked if "supabase.co" in u.split("/")[2])
    fixture = {"source": "tests/golden/MunazaraRashidiyaAQU.html (baseline de019d2, sha256 a91018ea…)",
               "storage_key": STORAGE_KEY, "state": state}
    OUT.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False))


if __name__ == "__main__":
    main()
