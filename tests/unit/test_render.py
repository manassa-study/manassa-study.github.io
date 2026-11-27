"""Renderer filters and environment rules (spec section 4)."""
import json

import pytest

from helpers import REPO
from mudhakarah.errors import BuildStopped
from mudhakarah.render import RenderRefused, app_config, data_json, js_array, make_environment, pct_hex, render, url

SAMPLE = {"BOOK_METADATA": {"title": "«عنوان» \"مقتبس\" & <b>"}, "n": [1, 2.5, True, None], "ar": "ﷺ ٔ"}


def test_data_json_is_exactly_json_dumps():
    assert str(data_json(SAMPLE)) == json.dumps(SAMPLE, ensure_ascii=False)


@pytest.mark.parametrize("bad", ["</script>", "</SCRIPT >", "<!-- x"])
def test_data_json_refuses_script_breakers(bad):
    with pytest.raises(RenderRefused):
        data_json({"x": "before " + bad})


def test_js_array_is_compact():
    assert str(js_array(["أ", "ب ج"])) == '["أ","ب ج"]'
    with pytest.raises(RenderRefused):
        js_array(["</script>"])
    with pytest.raises(RenderRefused):
        js_array("not a list")


def test_url_filter_keeps_ampersand_and_refuses_breakouts():
    assert str(url("https://a.example/x?a=1&b=2")) == "https://a.example/x?a=1&b=2"
    for bad in ['https://a.example/"onload', "http://a.example/", "javascript:alert(1)", "https://a b", "https://a/<"]:
        with pytest.raises(RenderRefused):
            url(bad)


def test_pct_hex():
    assert str(pct_hex("#8a4b14")) == "%238a4b14"
    with pytest.raises(RenderRefused):
        pct_hex("#8A4B14")


def test_environment_settings():
    env = make_environment(REPO)
    assert env.keep_trailing_newline and not env.trim_blocks and not env.lstrip_blocks
    assert env.newline_sequence == "\n"
    assert env.autoescape is True


def test_autoescape_is_on_for_plain_values():
    env = make_environment(REPO)
    assert env.from_string("{{ v }}").render(v='<a "b">') == "&lt;a &#34;b&#34;&gt;"


def test_undefined_value_stops_the_build(tmp_path):
    (tmp_path / "platform" / "templates").mkdir(parents=True)
    (tmp_path / "platform" / "templates" / "book.html.j2").write_text("{{ book.missing }}", encoding="utf-8")
    with pytest.raises(BuildStopped) as e:
        render(tmp_path, {"features": {}}, {}, {})
    assert e.value.findings[0].code == "V8.undefined"


def test_refused_value_stops_the_build(tmp_path):
    (tmp_path / "platform" / "templates").mkdir(parents=True)
    (tmp_path / "platform" / "templates" / "book.html.j2").write_text("{{ model|data_json }}", encoding="utf-8")
    with pytest.raises(BuildStopped) as e:
        render(tmp_path, {"features": {}}, {}, {"x": "</script>"})
    assert e.value.findings[0].code == "V8.refused"


def test_feature_blocks_follow_the_book():
    """The dedication card and attach()'s topic patch are the template's feature blocks."""
    from mudhakarah.render import FEATURES, page_features
    assert FEATURES == ("dedication_card", "item_topics", "example_ayah_plain", "author_first_segment")
    pilot = json.loads((REPO / "books" / "munazara-rashidiya" / "book.json").read_text(encoding="utf-8"))
    fiqh = json.loads((REPO / "books" / "madkhal-fiqh" / "book.json").read_text(encoding="utf-8"))
    takhreej = json.loads((REPO / "books" / "takhreej-asaneed" / "book.json").read_text(encoding="utf-8"))
    assert page_features(pilot) == {"dedication_card": False, "item_topics": True,
                                    "example_ayah_plain": False, "author_first_segment": False}
    assert page_features(fiqh) == {"dedication_card": True, "item_topics": False,
                                   "example_ayah_plain": False, "author_first_segment": False}
    assert page_features(takhreej) == {"dedication_card": True, "item_topics": False,
                                       "example_ayah_plain": True, "author_first_segment": True}


def test_app_config_holds_exactly_the_listed_words():
    """S2-3: storage key, welcome key, the four example labels and the search suggestions."""
    book = json.loads((REPO / "books" / "munazara-rashidiya" / "book.json").read_text(encoding="utf-8"))
    config = json.loads(str(app_config(book)))
    assert config == {
        "storage_key": book["storage_key"], "welcome_session_key": book["welcome_session_key"],
        "labels": {k: book["labels"][k] for k in
                   ("examples_title", "examples_short", "examples_count_noun", "examples_in_lesson")},
        "search": {"suggestions": book["search"]["suggestions"]},
    }
    assert "\n" not in str(app_config(book)) and " :" not in str(app_config(book))


@pytest.mark.parametrize("change", [
    lambda b: b["search"]["suggestions"].append("</script>"),
    lambda b: b["labels"].update(examples_title="<!-- x"),
    lambda b: b.pop("welcome_session_key"),
    lambda b: b.update(storage_key=5),
])
def test_app_config_refuses_bad_values(change):
    book = json.loads((REPO / "books" / "munazara-rashidiya" / "book.json").read_text(encoding="utf-8"))
    change(book)
    with pytest.raises(RenderRefused):
        app_config(book)
