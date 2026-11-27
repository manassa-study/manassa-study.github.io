"""Record ten search queries and their result counts on the baseline pilot page,
into tests/fixtures/queries.json (spec section 9: ten saved search queries).

    MUDHAKARAH_CHROMIUM=/path/to/chrome python tests/browser/capture_queries.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pagekit import block_outside, launch, seed_script, serve  # noqa: E402

REPO = HERE.parents[1]
OUT = REPO / "tests" / "fixtures" / "queries.json"
QUERIES = ["المنع", "السند المساوي", "النقض الإجمالي", "المعارضة بالقلب", "الغصب", "المقاطع", "المكابرة",
           "التقريب", "المناظرة", "الدليل"]


def search_counts(page, url, queries):
    page.goto(url + "#home")
    out = {}
    for q in queries:
        page.click("#searchBtn")
        page.fill("#q", q)
        head = page.locator("#spRes .sr-g").first.inner_text()
        out[q] = {"header": head, "results": page.locator("#spRes .sr-i").count()}
        page.click("#spClose")
    return out


def main():
    from playwright.sync_api import sync_playwright
    html = (REPO / "tests" / "golden" / "MunazaraRashidiyaAQU.html").read_bytes()
    with tempfile.TemporaryDirectory() as tmp, serve(html, tmp) as url, sync_playwright() as p:
        browser = launch(p)
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        block_outside(ctx, [])
        ctx.add_init_script(seed_script())
        counts = search_counts(ctx.new_page(), url, QUERIES)
        browser.close()
    OUT.write_text(json.dumps({"source": "tests/golden/MunazaraRashidiyaAQU.html (baseline de019d2)",
                               "queries": counts}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
