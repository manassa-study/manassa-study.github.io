"""Public RTL navigation, catalogue anchors, and student entry points."""
from html.parser import HTMLParser
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]
PUBLIC_PAGES = ("index.html", "fiqh.html", "hadith.html", "mantiq.html")
NAV_LINKS = {
    "/#home", "/#about", "/#books", "/#team", "/#join", "/portal.html",
}
READERS = (
    "Tafseer/TareekhTafseerAQU.html",
    "hadith/TakhreejAsaneedAQU.html",
    "fiqh/MadkhalFiqhAQU.html",
    "mantiq/MunazaraRashidiyaAQU.html",
    "Tafseer/TafseerMaqaranAQU.html",
)


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])


def test_public_pages_share_rtl_navigation_and_styles():
    for name in PUBLIC_PAGES:
        text = (REPO / name).read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in text
        assert 'aria-label="التنقل الرئيسي"' in text
        assert 'aria-controls="site-nav"' in text
        assert 'href="/public-nav.css"' in text
        assert 'src="/public-nav.js"' in text
        assert NAV_LINKS <= set(re.findall(r'href="([^"]+)"', text))


def test_home_links_resolve_to_catalogue_about_team_join_and_portal():
    text = (REPO / "index.html").read_text(encoding="utf-8")
    parser = IdParser()
    parser.feed(text)
    assert {"home", "about", "books", "team", "join", "portal"} <= parser.ids
    for href in (
        "https://manassa-study.github.io/mantiq.html",
        "https://manassa-study.github.io/Tafseer/",
        "https://manassa-study.github.io/hadith.html",
        "https://manassa-study.github.io/fiqh.html",
    ):
        assert href in text


def test_student_portal_targets_published_readers_and_login_entry():
    page = (REPO / "portal.html").read_text(encoding="utf-8")
    script = (REPO / "portal.js").read_text(encoding="utf-8")
    for path in READERS:
        assert f'href:"/{path}"' in script
        assert (REPO / path).is_file()
    assert 'id="google-login"' in page
    assert 'id="email-form"' in page


def test_mobile_navigation_toggle_supports_keyboard_and_breakpoint():
    js = (REPO / "public-nav.js").read_text(encoding="utf-8")
    css = (REPO / "public-nav.css").read_text(encoding="utf-8")
    assert 'classList.add("site-nav-js")' in js
    assert 'setAttribute("aria-expanded", String(open))' in js
    assert 'event.key === "Escape"' in js
    assert "(min-width: 901px)" in js
    assert "@media(max-width:900px)" in css
    assert "@media(max-width:520px)" in css
    assert ".site-nav-js .site-nav.is-open" in css
