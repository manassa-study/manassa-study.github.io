"""Every blocking check really blocks (spec sections 7 and 9).

CASES has one entry per blocking finding code in tools/. Each entry triggers that
code from a fixture or a small mutation and must produce it as a blocking finding.
test_every_blocking_code_has_a_failure_test fails if a blocking code is added to
the tools without a case here, so the number of blocking checks always equals the
number of failure-condition tests."""
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import PILOT, REPO, make_repo
from mudhakarah import config, ids, model, output, render
from mudhakarah.errors import BLOCKING, BuildStopped
from mudhakarah.loaders import load_content
from mudhakarah.pipeline import run_book
from mudhakarah.validate import (v02_structure, v04_duplicates, v05_links, v07_assets, v08_html,
                                 v10_reproducibility, v11_integrity, v13_paths)

TOOLS = REPO / "tools"
W = "fixture"
FIXTURE = REPO / "tests" / "fixtures" / "minimal-book"


def blocking_codes_in_source():
    found = set()
    for path in TOOLS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found |= set(re.findall(r'Finding\(\s*"(V[0-9]+\.[a-z-]+)",\s*BLOCKING', text))
        found |= set(re.findall(r"\[BLOCKING\] (V[0-9]+\.[a-z-]+)", text))
    return found


# ------------------------------------------------------------------ helpers

def _pilot():
    book, _ = config.load_book(REPO, PILOT)
    raw, _, _ = load_content(REPO, PILOT, book)
    lock = ids.read_lock(REPO, PILOT)
    live = output.parse_data_line((REPO / book["output"]).read_text(encoding="utf-8"))
    return book, raw, lock, live


PILOT_DATA = _pilot()


def pilot():
    return copy.deepcopy(PILOT_DATA)


def findings_of(fn):
    try:
        result = fn()
    except BuildStopped as e:
        return e.findings
    if isinstance(result, tuple):
        result = result[1]
    return result


def scratch(tmp_path, books=((PILOT, REPO / "books" / PILOT),)):
    return make_repo(tmp_path, list(books))


def edit_json(path, fn):
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def build_with(tmp_path, change):
    root = scratch(tmp_path)
    change(root)
    return lambda: run_book(root, PILOT)


def book_json(root):
    return root / "books" / PILOT / "book.json"


def lock_json(root):
    return root / "books" / PILOT / "ids.lock.json"


def append_content(root, code):
    f = root / "books" / PILOT / "content" / "m5.py"
    f.write_text(f.read_text(encoding="utf-8") + "\n" + code + "\n", encoding="utf-8")


def bind_mut(fn):
    book, raw, lock, live = pilot()
    fn(book, raw, lock, live)
    return lambda: ids.bind(raw, book, lock, W)


def boot_mut(fn):
    book, raw, lock, live = pilot()
    fn(raw, live)
    return lambda: ids.bootstrap(raw, book, live, lock["bootstrap"], "x", 0, "2026-11-27", W)


def first_mc(raw):
    return next(i for i, q in enumerate(raw["questions"]) if "correct" in q)


def template_repo(tmp_path, text):
    (tmp_path / "platform" / "templates").mkdir(parents=True)
    (tmp_path / "platform" / "templates" / "book.html.j2").write_text(text, encoding="utf-8")
    return tmp_path


def cli(root, *args):
    shutil.copytree(REPO / "tools", root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    r = subprocess.run([sys.executable, str(root / "tools" / "build.py"), *args], capture_output=True, text=True)
    return r


# ------------------------------------------------------------------ the cases

def c_v1(tmp_path, change):
    return build_with(tmp_path, lambda r: edit_json(book_json(r), change))


CASES = {
    # V1 configuration
    "V1.unknown-field": lambda t: c_v1(t, lambda b: b.update(titel="x")),
    "V1.missing-field": lambda t: c_v1(t, lambda b: b.pop("title")),
    "V1.type": lambda t: c_v1(t, lambda b: b.update(title=5)),
    "V1.empty": lambda t: c_v1(t, lambda b: b.update(title="")),
    "V1.value": lambda t: c_v1(t, lambda b: b["theme"]["light"].update(accent="#8A4B14")),
    "V1.slug-folder": lambda t: c_v1(t, lambda b: b.update(slug="other")),
    "V1.duplicate-chapter": lambda t: c_v1(t, lambda b: b["content"]["chapters"][1].update(quiz_name="المدخل")),
    "V1.duplicate-file": lambda t: c_v1(t, lambda b: b["content"]["files"].append("m1.py")),
    "V1.json": lambda t: build_with(t, lambda r: book_json(r).write_text("{not json", encoding="utf-8")),
    "V1.encoding": lambda t: build_with(t, lambda r: book_json(r).write_bytes(b'{"title": "\xff"}')),
    "V1.missing-file": lambda t: build_with(t, lambda r: book_json(r).unlink()),
    "V1.duplicate-switch": lambda t: c_v1(t, lambda b: b["features"].update(step2=["S2-1", "S2-1"])),
    "V1.chapter-pages": lambda t: c_v1(t, lambda b: b["content"]["chapters"][1].update(from_page=5)),
    # V2 content structure
    "V5.anchor": lambda t: (lambda d=pilot(): (
        d[0]["content"].update(anchor="chapter"),
        [c.update(from_page=p) for c, p in zip(d[0]["content"]["chapters"][1:], (30, 40, 90))],
        d[1]["questions"][0].update(exp="بلا رقم صفحة"),
        lambda: model.assemble(d[1], d[0]))[3])(),
    "V2.missing-file": lambda t: c_v1(t, lambda b: b["content"]["files"].append("m9.py")),
    "V2.content-error": lambda t: build_with(t, lambda r: append_content(r, "1/0")),
    "V2.missing-symbol": lambda t: c_v1(t, lambda b: b["content"]["symbols"].update(cards="NOPE")),
    "V2.unknown-type": lambda t: build_with(t, lambda r: append_content(r, 'QRAW[0]["type"] = "نوع"')),
    "V2.question": lambda t: build_with(t, lambda r: append_content(
        r, 'q = next(x for x in QRAW if "wrong" in x); q["wrong"] = q["wrong"][:2]')),
    "V2.structure": lambda t: build_with(t, lambda r: append_content(r, 'TB[0]["rows"][0].append("x")')),
    # V3 IDs
    "V3.no-lock": lambda t: build_with(t, lambda r: lock_json(r).unlink()),
    "V3.lock-schema": lambda t: build_with(t, lambda r: edit_json(lock_json(r), lambda l: l.update(
        schema_version=2))),
    "V3.storage-key": lambda t: c_v1(t, lambda b: b.update(storage_key="munazara-rashidiya-v2")),
    "V3.output-path": lambda t: c_v1(t, lambda b: b.update(output="mantiq/Other.html")),
    "V3.fingerprint-settings": lambda t: build_with(t, lambda r: edit_json(lock_json(r), lambda l: l[
        "fingerprint"].update(normalization="ar-norm-2"))),
    "V3.topic-removed": lambda t: bind_mut(lambda b, raw, l, v: raw["chapters"][0]["sections"][0]["topics"].pop()),
    "V3.topic-new": lambda t: bind_mut(lambda b, raw, l, v: raw["chapters"][0]["sections"][0]["topics"].append(
        {"id": "t99", "title": "جديد"})),
    "V3.unbound": lambda t: bind_mut(lambda b, raw, l, v: raw["cards"].append(
        {"id": 0, "cat": "x", "q": "جديدة", "a": "y", "topic": "t1"})),
    "V3.missing": lambda t: bind_mut(lambda b, raw, l, v: raw["cards"].pop()),
    "V3.retired-match": lambda t: bind_mut(lambda b, raw, l, v: l["cards"]["items"].append(
        dict(l["cards"]["items"].pop(0), status="retired"))),
    "V3.ambiguous": lambda t: bind_mut(lambda b, raw, l, v: l["cards"]["items"].append(
        dict(l["cards"]["items"][0], id=999))),
    "V3.group": lambda t: bind_mut(lambda b, raw, l, v: l["duplicate_groups"].append(
        {"collection": "cards", "fp": l["cards"]["items"][0]["fp"],
         "items": [{"id": 999, "content": l["cards"]["items"][0]["content"]}]})),
    "V3.order-missing": lambda t: bind_mut(lambda b, raw, l, v: l["questions"]["items"][first_mc(raw)].pop(
        "order")),
    "V3.options-reordered": lambda t: bind_mut(lambda b, raw, l, v: raw["questions"][first_mc(raw)].update(
        wrong=raw["questions"][first_mc(raw)]["wrong"][::-1])),
    "V3.review": lambda t: build_with(t, lambda r: append_content(r, "FC.pop()")),
    "V3.output-ids": lambda t: (lambda d=pilot(): lambda: ids.check_output_ids(
        {"FLASHCARDS": d[3]["FLASHCARDS"][1:], "QUIZ_BANK": d[3]["QUIZ_BANK"]}, d[2], W))(),
    # a guard that holds by construction; proven by breaking slot 0 of the options
    "V3.answer-invariant": lambda t: _broken_slots,
    "V3.bootstrap-bind": lambda t: boot_mut(lambda raw, v: v["FLASHCARDS"][0].update(q="مختلف")),
    "V3.bootstrap-order": lambda t: boot_mut(lambda raw, v: v["QUIZ_BANK"][first_mc(raw)].update(
        options=v["QUIZ_BANK"][first_mc(raw)]["options"][::-1],
        correct=3 - v["QUIZ_BANK"][first_mc(raw)]["correct"])),
    "V3.bootstrap-topics": lambda t: boot_mut(lambda raw, v: v["DEEP_STUDY_DATA"][0]["sections"][0]["topics"][0]
                                              .update(id="t0")),
    "V3.bootstrap-maps": lambda t: boot_mut(lambda raw, v: v["MIND_MAPS"].reverse()),
    "V3.bootstrap-chapters": lambda t: boot_mut(lambda raw, v: v["QUIZ_BANK"][0].update(chapter="فصل آخر")),
    "V3.bootstrap": lambda t: (lambda root=scratch(t): lambda: _cli_findings(cli(
        root, "ids", "bootstrap", PILOT, "--commit", "HEAD", "--approver", "x", "--pull-request", "1",
        "--date", "2026-11-28")))(),
    "V3.apply": lambda t: (lambda d=pilot(): lambda: ids.apply(d[1], d[0], d[2], {"cases": []}, "", 1, "d", W))(),
    "V3.invariant": lambda t: (lambda d=pilot(): lambda: ids.invariants(
        d[2], dict(copy.deepcopy(d[2]), storage_key="x"), W))(),
    # V4 duplicates
    "V4.duplicate": lambda t: bind_mut(lambda b, raw, l, v: raw["cards"].append(dict(raw["cards"][0]))),
    "V4.duplicate-id": lambda t: (lambda d=pilot(): (d[1]["maps"].append(dict(d[1]["maps"][0])),
                                                    lambda: v04_duplicates.check(d[1], W))[1])(),
    # V5 internal links
    "V5.topic": lambda t: build_with(t, lambda r: append_content(r, 'FC[0]["topic"] = "t999"')),
    "V5.link": lambda t: (lambda d=pilot(): (d[3]["FLASHCARDS"][0].update(a="انظر #study-t999"),
                                            lambda: v05_links.check(d[3], W))[1])(),
    # V6 references (rule N4)
    "V6.page-reference-missing": lambda t: build_with(t, lambda r: edit_json(
        r / "books" / PILOT / "page-references.json", lambda e: e["exceptions"].pop(0))),
    "V6.exceptions-invalid": lambda t: build_with(t, lambda r: (
        r / "books" / PILOT / "page-references.json").write_text("{not json", encoding="utf-8")),
    # V7 assets
    "V7.missing-asset": lambda t: build_with(t, lambda r: (r / "mantiq" / "og-munazara.jpg").unlink()),
    # V8 HTML output
    "V8.data-line": lambda t: lambda: output.verify_output("<p>no data</p>", {}, W),
    "V8.data-parse": lambda t: lambda: output.verify_output("const D = {not json};", {}, W),
    "V8.data-roundtrip": lambda t: lambda: output.verify_output('const D = {"a": 1};', {"a": 2}, W),
    "V8.script-breaker": lambda t: lambda: output.verify_output('const D = {"a": "<!-- x"};', {"a": "<!-- x"}, W),
    "V8.undefined": lambda t: lambda: render.render(template_repo(t, "{{ book.nope }}"), {"features": {}}, {}, {}),
    "V8.refused": lambda t: lambda: render.render(template_repo(t, "{{ model|data_json }}"), {"features": {}}, {},
                                                  {"x": "</script>"}),
    "V8.template": lambda t: lambda: render.render(template_repo(t, "{% if %}"), {"features": {}}, {}, {}),
    "V8.line-endings": lambda t: lambda: render.render(template_repo(t, "{{ book.x }}"),
                                                       {"features": {}, "x": "a\rb"}, {}, {}),
    "V8.opening": lambda t: lambda: v08_html.check('<!doctype html><html lang="ar"><head>', {"storage_key": "k"},
                                                   W),
    "V8.leftover": lambda t: lambda: v08_html.check("<!doctype html><html><head>madkhal-fiqh-v1",
                                                    {"storage_key": "munazara-rashidiya-v1"}, W),
    # V9 committed output
    "V9.committed-output": lambda t: (lambda root=scratch(t): (
        (root / "mantiq" / "MunazaraRashidiyaAQU.html").write_bytes(
            (REPO / "mantiq" / "MunazaraRashidiyaAQU.html").read_bytes().replace(b"</title>", b" </title>", 1)),
        lambda: _cli_findings(cli(root, "check", PILOT)))[1])(),
    # V10 reproducibility
    "V10.reproducibility": lambda t: lambda: v10_reproducibility.compare({"output": 1}, {"output": 2}, W),
    # V11 content integrity
    "V11.content-modified": lambda t: lambda: v11_integrity.files_unchanged({"m1.py": "a"}, {"m1.py": "b"}, W),
    "V11.data-changed": lambda t: lambda: v11_integrity.step1_data_identity('const D = {"a":1};',
                                                                            'const D = {"a":2};', W),
    # V13 published paths
    "V13.list": lambda t: (lambda root=scratch(t): ((root / "platform" / "published-paths.json").unlink(),
                                                    lambda: v13_paths.check(root))[1])(),
    "V13.path-missing": lambda t: (lambda root=scratch(t): ((root / "fiqh.html").unlink(),
                                                            lambda: v13_paths.check(root))[1])(),
    "V13.path-unserved": lambda t: (lambda root=scratch(t): (
        (root / "_config.yml").write_text((root / "_config.yml").read_text(encoding="utf-8") + "  - shots/\n",
                                          encoding="utf-8"), lambda: v13_paths.check(root))[1])(),
}


def _broken_slots():
    from unittest import mock
    book, raw, lock, live = pilot()
    with mock.patch.object(model, "source_options", lambda q: (
            list(model.TRUE_FALSE_OPTIONS) if "tf" in q else list(q["wrong"]) + [q["correct"]])):
        return model.assemble(raw, book)


class _F:
    def __init__(self, code):
        self.code, self.severity = code, BLOCKING


def _cli_findings(r):
    """A CLI run's blocking findings, read from its output."""
    assert r.returncode == 1, r.stdout + r.stderr
    return [_F(c) for c in re.findall(r"\[BLOCKING\] (V[0-9]+\.[a-z-]+)", r.stdout + r.stderr)]


def test_every_blocking_code_has_a_failure_test():
    in_source = blocking_codes_in_source()
    assert in_source - set(CASES) == set(), "blocking codes without a failure test"
    assert set(CASES) - in_source == set(), "failure tests for codes that no longer exist"


@pytest.mark.parametrize("code", sorted(CASES))
def test_blocking_check_blocks(code, tmp_path):
    trigger = CASES[code](tmp_path)
    found = findings_of(trigger)
    assert code in {f.code for f in found if f.severity == BLOCKING}, [str(f) for f in found]


def test_a_failed_build_writes_nothing(tmp_path):
    root = scratch(tmp_path)
    append_content(root, 'TB[0]["rows"][0].append("x")')
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    r = cli(root, "build", PILOT)
    assert r.returncode == 1
    after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and "tools" not in p.parts}
    assert after == {p: b for p, b in before.items()}
