"""Focused checks for the public About, Team and Privacy pages."""
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGES = ("about.html", "team.html", "privacy.html", "Tafseer/privacy.html")
READERS = (
    "Tafseer/TareekhTafseerAQU.html",
    "hadith/TakhreejAsaneedAQU.html",
    "fiqh/MadkhalFiqhAQU.html",
    "mantiq/MunazaraRashidiyaAQU.html",
)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = set()
        self.ids = set()
        self.h1_count = 0
        self.nav_labels = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("href"):
            self.hrefs.add(attrs["href"])
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "nav" and attrs.get("aria-label"):
            self.nav_labels.add(attrs["aria-label"])


def test_public_pages_are_arabic_rtl_and_use_shared_accessible_shell():
    for name in PAGES:
        text = (REPO / name).read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        assert '<html lang="ar" dir="rtl">' in text
        assert 'href="/public-nav.css"' in text
        assert 'href="/public-pages.css"' in text
        assert 'src="/public-nav.js"' in text
        assert 'aria-controls="site-nav"' in text
        assert "انتقل إلى المحتوى الرئيسي" in text
        assert parser.h1_count == 1
        assert "التنقل الرئيسي" in parser.nav_labels
        for href in parser.hrefs:
            if href.startswith("/") and not href.startswith("/#"):
                target = href.split("#", 1)[0].lstrip("/") or "index.html"
                assert (REPO / target).is_file(), f"{name}: {href} does not resolve"


def test_homepage_keeps_anchors_and_links_to_about_team_and_privacy():
    text = (REPO / "index.html").read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(text)
    assert {"home", "about", "books", "team", "join", "portal"} <= parser.ids
    assert {"/about.html", "/team.html", "/privacy.html"} <= parser.hrefs


def test_team_page_uses_only_the_verified_publicly_named_contributor():
    text = (REPO / "team.html").read_text(encoding="utf-8")
    assert "محمد بلال البلوشي" in text
    assert "إعداد وتصميم المنصة" in text
    assert "لا نضيف أسماء أو أدواراً أو مؤهلات" in text


def test_privacy_copy_matches_reader_and_feedback_implementation():
    text = (REPO / "privacy.html").read_text(encoding="utf-8")
    readers = "\n".join((REPO / name).read_text(encoding="utf-8") for name in READERS)
    feedback = (REPO / "report.js").read_text(encoding="utf-8")
    assert "localStorage.getItem(KEY)" in readers
    assert "localStorage.setItem(KEY" in readers
    assert 'storageKey:"study-auth"' in readers
    assert 'from("progress").upsert' in readers
    assert 'from("progress").select' in readers
    assert "signInWithOAuth" in readers and "signInWithOtp" in readers
    assert "fonts.googleapis.com" in text
    assert "Supabase" in text and "التخزين المحلي للمتصفح" in text
    assert "Google Forms" in text
    assert "location.href" in feedback and 'fetch("https://docs.google.com/forms' in feedback
    assert "حقل التواصل اختياري" in text
    assert "لم أتحقق من مدد الاحتفاظ" in text
    assert "مسح تقدّمي في هذا المقرر" in text
    assert "البريد الإلكتروني إن توفر" in text and "الاسم إن توفر" in text
    assert "last_seen" in text
    assert "لا يحذف حساب الطالب" in text
    auth = (REPO / "platform/templates/partials/auth.js.j2").read_text(encoding="utf-8")
    assert 'g("accReset").onclick' in auth
    assert 'from("progress").upsert' in auth
    assert 'from("profiles").upsert' in auth
    assert "last_seen:new Date().toISOString()" in auth
    assert "document.cookie" not in readers
    assert "لم يظهر في الشيفرة المباشرة استدعاء لكتابة ملفات تعريف ارتباط" in text


def test_existing_reader_privacy_url_is_available_without_redirect():
    root = (REPO / "privacy.html").read_text(encoding="utf-8")
    reader_path = REPO / "Tafseer/privacy.html"
    assert reader_path.is_file()
    assert reader_path.read_text(encoding="utf-8") == root
    for name in READERS:
        assert "Tafseer/privacy.html" in (REPO / name).read_text(encoding="utf-8")


def test_public_page_styles_handle_mobile_focus_and_reduced_motion():
    css = (REPO / "public-pages.css").read_text(encoding="utf-8")
    assert "@media(max-width:680px)" in css
    assert "@media(prefers-reduced-motion:reduce)" in css
    assert ":focus-visible" in css
    assert "@media(prefers-color-scheme:dark)" in css
