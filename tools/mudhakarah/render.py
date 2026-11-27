"""The renderer (spec section 2, layer 4, and section 4).

Jinja2 renders platform/templates/book.html.j2 with five values: `book`
(book.json), `site` (platform/site.json), `model` (the book model), `step2`
(the approved step-2 changes the book has turned on, from features.step2) and
`build` (the template version written by S2-2: the tool version). The
environment is fixed so that output bytes depend only on the inputs:
StrictUndefined, HTML autoescaping, keep_trailing_newline, no block trimming,
LF line endings.
"""
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, UndefinedError
from markupsafe import Markup

from . import TOOL_VERSION
from .config import step2_changes
from .errors import BLOCKING, BuildStopped, Finding

TEMPLATE_DIR = Path("platform") / "templates"
TEMPLATE_NAME = "book.html.j2"

# Content that could end the data script early or open an HTML comment (spec section 4).
SCRIPT_BREAKERS = ("</script", "<!--")
_COLOUR_RE = re.compile(r"^#[0-9a-f]{6}$")
_URL_RE = re.compile(r"^https://[^\s\"'<>\\`]+$")


class RenderRefused(ValueError):
    """Raised by a filter when a value must not be written into the page."""


def data_json(model):
    """The data line: exactly json.dumps(..., ensure_ascii=False), refusing script breakers."""
    text = json.dumps(model, ensure_ascii=False)
    lowered = text.lower()
    for bad in SCRIPT_BREAKERS:
        if bad in lowered:
            raise RenderRefused(f"the book data contains '{bad}', which would break the page's script tag")
    return Markup(text)


def js_array(values):
    """A compact JavaScript array of strings, as the pages write them: ["a","b"]."""
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise RenderRefused("js_array expects a list of strings")
    text = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    lowered = text.lower()
    for bad in SCRIPT_BREAKERS:
        if bad in lowered:
            raise RenderRefused(f"a search suggestion contains '{bad}'")
    return Markup(text)


# S2-3 (O-5): the book-specific words the app script uses, gathered into one object at the
# top of the script. Paths are into book.json; the object keeps the same shape.
APP_CONFIG_FIELDS = (
    ("storage_key",),
    ("welcome_session_key",),
    ("labels", "examples_title"),
    ("labels", "examples_short"),
    ("labels", "examples_count_noun"),
    ("labels", "examples_in_lesson"),
    ("search", "suggestions"),
)


def app_config(book):
    """The app script's config object (S2-3) as compact JSON, refusing script breakers."""
    config = {}
    for path in APP_CONFIG_FIELDS:
        value = book
        for key in path:
            if not isinstance(value, dict) or key not in value:
                raise RenderRefused(f"app_config needs book.{'.'.join(path)}")
            value = value[key]
        ok = isinstance(value, str) or (isinstance(value, list) and all(isinstance(v, str) for v in value))
        if not ok:
            raise RenderRefused(f"book.{'.'.join(path)} must be a string or a list of strings")
        target = config
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value
    text = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    lowered = text.lower()
    for bad in SCRIPT_BREAKERS:
        if bad in lowered:
            raise RenderRefused(f"a value in the app config contains '{bad}'")
    return Markup(text)


def url(value):
    """An https address written as is (no escaping, so '&' in the fonts address stays raw).
    Refused if it could leave an HTML attribute or a JavaScript string."""
    if not isinstance(value, str) or not _URL_RE.match(value):
        raise RenderRefused(f"'{value}' is not a plain https address")
    return Markup(value)


def pct_hex(value):
    """A colour for an SVG data URL: '#8a4b14' becomes '%238a4b14'."""
    if not isinstance(value, str) or not _COLOUR_RE.match(value):
        raise RenderRefused(f"'{value}' is not a lowercase #rrggbb colour")
    return Markup("%23" + value[1:])


def make_environment(repo_root):
    env = Environment(
        loader=FileSystemLoader(str(Path(repo_root) / TEMPLATE_DIR)),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        newline_sequence="\n",
        auto_reload=False,
        cache_size=0,
    )
    env.filters.update(data_json=data_json, js_array=js_array, app_config=app_config, url=url, pct_hex=pct_hex)
    return env


def template_files(repo_root):
    """Every template file, for the build manifest."""
    base = Path(repo_root) / TEMPLATE_DIR
    return sorted(p for p in base.rglob("*.j2"))


def render(repo_root, book, site, model, where="renderer"):
    if book.get("features", {}).get("dedication_card"):
        # Only the Fiqh page has this card. Its block joins the template when that book migrates.
        raise BuildStopped("rendering", [Finding(
            "V1.feature-unavailable", BLOCKING,
            "features.dedication_card is true, but the template has no dedication card block yet "
            "(it is added when the Fiqh book migrates)", where)])
    env = make_environment(repo_root)
    try:
        text = env.get_template(TEMPLATE_NAME).render(book=book, site=site, model=model,
                                                           step2=step2_changes(book),
                                                           build={"template_version": TOOL_VERSION})
    except UndefinedError as e:
        raise BuildStopped("rendering", [Finding("V8.undefined", BLOCKING,
                                                 f"the template uses an undefined value: {e}", where)])
    except RenderRefused as e:
        raise BuildStopped("rendering", [Finding("V8.refused", BLOCKING, str(e), where)])
    except TemplateError as e:
        raise BuildStopped("rendering", [Finding("V8.template", BLOCKING, f"template error: {e}", where)])
    if "\r" in text:
        raise BuildStopped("rendering", [Finding("V8.line-endings", BLOCKING, "output contains CR characters",
                                                 where)])
    return text
