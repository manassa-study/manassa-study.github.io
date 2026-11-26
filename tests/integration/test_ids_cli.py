"""`build.py ids …` end to end on a scratch copy of the pilot."""
import json
import shutil
import subprocess
import sys

from helpers import PILOT, REPO, make_repo
from mudhakarah.pipeline import run_book

FIXTURE = REPO / "tests" / "fixtures" / "minimal-book"


def _repo(tmp_path, with_page=False):
    root = make_repo(tmp_path, [(PILOT, REPO / "books" / PILOT)])
    if with_page:
        (root / "mantiq").mkdir()
        shutil.copy(REPO / "mantiq" / "MunazaraRashidiyaAQU.html", root / "mantiq")
    shutil.copytree(REPO / "tools", root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    return root


def _run(root, *args):
    return subprocess.run([sys.executable, str(root / "tools" / "build.py"), *args], capture_output=True, text=True)


def test_review_then_apply_then_build(tmp_path):
    root = _repo(tmp_path)
    m5 = root / "books" / PILOT / "content" / "m5.py"
    m5.write_text(m5.read_text(encoding="utf-8") + "\nFC.pop(0)\n", encoding="utf-8")
    out = tmp_path / "proposal.json"
    r = _run(root, "ids", "review", PILOT, "--out", str(out))
    assert r.returncode == 0, r.stderr
    proposal = json.loads(out.read_text(encoding="utf-8"))
    assert [c["kind"] for c in proposal["cases"]] == ["missing"] and proposal["cases"][0]["id"] == 1
    assert proposal["cases"][0]["old_item"] is None  # the scratch copy has no committed page to show it from
    proposal["cases"][0].update(decision="retire", reason="Card removed in review")
    out.write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
    lock_before = json.loads((root / "books" / PILOT / "ids.lock.json").read_text(encoding="utf-8"))
    r = _run(root, "ids", "apply", PILOT, "--proposal", str(out), "--approver", "Bilal", "--pull-request", "99",
             "--date", "2026-11-28")
    assert r.returncode == 0, r.stderr
    assert "IDs: 1 retire" in r.stdout
    lock = json.loads((root / "books" / PILOT / "ids.lock.json").read_text(encoding="utf-8"))
    assert lock["changes"][:1] == lock_before["changes"] and lock["changes"][1]["action"] == "retire"
    result = run_book(root, PILOT)
    assert [c["id"] for c in result.model["FLASHCARDS"]] == list(range(2, 170))


def test_review_shows_the_old_item_from_the_committed_page(tmp_path):
    root = _repo(tmp_path, with_page=True)
    m5 = root / "books" / PILOT / "content" / "m5.py"
    m5.write_text(m5.read_text(encoding="utf-8") + "\nFC.pop(0)\n", encoding="utf-8")
    out = tmp_path / "proposal.json"
    assert _run(root, "ids", "review", PILOT, "--out", str(out)).returncode == 0
    case = json.loads(out.read_text(encoding="utf-8"))["cases"][0]
    live = json.loads((REPO / "tests" / "golden" / "MunazaraRashidiyaAQU.data.json").read_text(encoding="utf-8"))
    assert case["old_item"]["q"] == live["FLASHCARDS"][0]["q"]


def test_apply_refuses_an_undecided_proposal(tmp_path):
    root = _repo(tmp_path)
    m5 = root / "books" / PILOT / "content" / "m5.py"
    m5.write_text(m5.read_text(encoding="utf-8") + "\nFC.pop(0)\n", encoding="utf-8")
    out = tmp_path / "proposal.json"
    _run(root, "ids", "review", PILOT, "--out", str(out))
    before = (root / "books" / PILOT / "ids.lock.json").read_bytes()
    r = _run(root, "ids", "apply", PILOT, "--proposal", str(out), "--approver", "Bilal", "--pull-request", "1")
    assert r.returncode == 1 and "no valid decision" in r.stderr
    assert (root / "books" / PILOT / "ids.lock.json").read_bytes() == before


def test_review_writes_outside_the_repository_by_default(tmp_path):
    root = _repo(tmp_path)
    r = _run(root, "ids", "review", PILOT)
    assert r.returncode == 0 and "0 case(s)" in r.stdout
    written = r.stdout.rsplit("proposal written to ", 1)[1].strip()
    assert not written.startswith(str(root))


def test_bootstrap_refuses_when_a_lock_exists(tmp_path):
    root = _repo(tmp_path)
    r = _run(root, "ids", "bootstrap", PILOT, "--commit", "HEAD", "--approver", "x", "--pull-request", "1",
             "--date", "2026-11-28")
    assert r.returncode == 1 and "bootstrap runs once" in r.stderr


def test_invariants_hold_for_the_committed_lock():
    r = subprocess.run([sys.executable, str(REPO / "tools" / "build.py"), "ids", "invariants", PILOT,
                        "--base", "HEAD"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_minimal_fixture_lock_comes_from_review_and_apply(tmp_path):
    from mudhakarah.config import load_book
    from mudhakarah.ids import apply, dumps_lock, review
    from mudhakarah.loaders import load_content
    root = make_repo(tmp_path, [("minimal", FIXTURE)])
    (root / "books" / "minimal" / "ids.lock.json").unlink()
    book, _ = load_book(root, "minimal")
    raw, _, _ = load_content(root, "minimal", book)
    proposal = review(raw, book, None, "minimal")
    for c in proposal["cases"]:
        c.update(decision="new", reason="Fixture book: first IDs")
    lock, _ = apply(raw, book, None, proposal, "Test fixture", 0, "2026-11-27", "minimal")
    assert dumps_lock(lock) == (FIXTURE / "ids.lock.json").read_text(encoding="utf-8")
