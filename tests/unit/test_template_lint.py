"""Template lint (spec section 4): no slug or title comparisons, no hard-coded
book words, no stray Jinja2 delimiters, LF only."""
import json
import re

from helpers import PILOT, REPO
from mudhakarah.config import STEP2_CHANGES
from mudhakarah.render import TEMPLATE_DIR, template_files

TEMPLATES = template_files(REPO)
# Shared literals that happen to equal a pilot value but belong to every page.
SHARED_LITERALS = {"#ffffff"}


def _leaves(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _leaves(v)
    elif isinstance(x, list):
        for v in x:
            yield from _leaves(v)
    elif isinstance(x, str):
        yield x


PARTIALS = ["app.js.j2", "auth.html.j2", "auth.js.j2", "head.html.j2", "report.html.j2", "styles.css.j2"]


def test_templates_exist():
    assert [p.relative_to(REPO / TEMPLATE_DIR).as_posix() for p in TEMPLATES] == \
        ["book.html.j2"] + ["partials/" + n for n in PARTIALS]


def test_no_slug_or_title_comparisons():
    pattern = re.compile(r"\{%-?\s*(if|elif)\b[^%]*\b(book\.slug|book\.title|slug|title)\b", re.S)
    for path in TEMPLATES:
        assert not pattern.search(path.read_text(encoding="utf-8")), path


def test_no_type_branches():
    for path in TEMPLATES:
        assert not re.search(r"\{%-?\s*(if|elif)\b[^%]*\btype\b", path.read_text(encoding="utf-8")), path


def test_no_hard_coded_pilot_values():
    book = json.loads((REPO / "books" / PILOT / "book.json").read_text(encoding="utf-8"))
    site = json.loads((REPO / "platform" / "site.json").read_text(encoding="utf-8"))
    identity = {k: v for k, v in book.items() if k not in ("content", "quiz", "features", "schema_version")}
    values = {v for v in _leaves(identity) if len(v) >= 2} - SHARED_LITERALS
    values |= {book["output"].split("/")[-1], book["og_image"].split("/")[-1], book["slug"]}
    values |= {site["supabase_url"], site["supabase_publishable_key"], site["platform_name"], site["fonts_url"]}
    for path in TEMPLATES:
        text = path.read_text(encoding="utf-8")
        leaked = sorted(v for v in values if v in text)
        assert leaked == [], f"{path.name} hard-codes: {leaked}"


def test_lf_only_and_no_unknown_tags():
    for path in TEMPLATES:
        raw = path.read_bytes()
        assert b"\r" not in raw
        text = raw.decode("utf-8")
        assert "{#" not in text
        # the only statements are includes of the partials (spec section 4, hierarchy) and
        # the approved step-2 switches (docs/step-2-list.md): if "S2-n" in step2 / else / endif
        for stmt in re.findall(r"\{%(.*?)%\}", text, re.S):
            m = re.fullmatch(r'\s*if "(S2-[0-9]+)" in step2\s*', stmt)
            if m:
                assert m.group(1) in STEP2_CHANGES, stmt
                continue
            assert re.fullmatch(r'\s*(include "partials/[a-z.]+\.j2"|else|endif)\s*', stmt), stmt


def test_every_expression_uses_known_roots():
    for path in TEMPLATES:
        for expr in re.findall(r"\{\{(.*?)\}\}", path.read_text(encoding="utf-8")):
            expr = expr.strip()
            assert re.match(r'^(\(?(book|site|model)\b|"\$\{"$)', expr), expr


def test_every_partial_is_included_once():
    text = "".join(p.read_text(encoding="utf-8") for p in TEMPLATES)
    for name in PARTIALS:
        assert text.count(f'{{% include "partials/{name}" %}}') == 1, name
