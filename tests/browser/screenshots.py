"""Screenshots of the baseline pilot page at 360, 390 and 1280 px, light and dark
(spec section 9, R4). Evidence only; not a test.

    MUDHAKARAH_CHROMIUM=/path/to/chrome python tests/browser/screenshots.py OUT_DIR

Every request is blocked except the local server and Google Fonts (so the page
shows its real typefaces). Supabase and report.js are never reached."""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pagekit import launch, seed_script, serve  # noqa: E402

REPO = HERE.parents[1]
FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
SHOTS = [(w, h, theme) for w, h in ((360, 780), (390, 844), (1280, 800)) for theme in ("light", "dark")]
ROUTES = [("home", "#home"), ("lesson", "#study-t3")]


def main(out):
    from playwright.sync_api import sync_playwright
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    html = (REPO / "tests" / "golden" / "MunazaraRashidiyaAQU.html").read_bytes()
    log = {"page": "tests/golden/MunazaraRashidiyaAQU.html (baseline de019d2, sha256 a91018ea…)", "allowed": [],
           "blocked": [], "shots": []}
    with tempfile.TemporaryDirectory() as tmp, serve(html, tmp) as url, sync_playwright() as p:
        browser = launch(p)
        for w, h, theme in SHOTS:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, color_scheme=theme)

            def handler(route):
                u = route.request.url
                host = u.split("/")[2]
                if u.startswith("http://127.0.0.1:") or host in FONT_HOSTS:
                    if host in FONT_HOSTS:
                        log["allowed"].append(host)
                    return route.continue_()
                log["blocked"].append(host)
                return route.abort()
            ctx.route("**/*", handler)
            ctx.add_init_script(seed_script({"theme": theme}))
            page = ctx.new_page()
            for name, route in ROUTES:
                page.goto(url + route, wait_until="networkidle")
                page.wait_for_timeout(400)
                f = out / f"munazara-{name}-{w}-{theme}.png"
                page.screenshot(path=str(f))
                log["shots"].append(f.name)
            ctx.close()
        browser.close()
    log["allowed"], log["blocked"] = sorted(set(log["allowed"])), sorted(set(log["blocked"]))
    (out / "screenshots.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log))


if __name__ == "__main__":
    main(sys.argv[1])
