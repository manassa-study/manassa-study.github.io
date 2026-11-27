import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import build as build_cli


COMMIT = "fbbbae5b51e526d6f5e27e3f6dac7d8fdf22f6b2"
PAGE = "Tafseer/TareekhTafseerAQU.html"
SOURCE_PAGE = "TareekhTafseerAQU.html"
REPOSITORY = "manassa-study/Tafseer"
CHECKOUT = ".baseline/tafseer"
DATA = 'const D = {"preserved":1};'


def _set_external_bootstrap(monkeypatch, tmp_path, make_checkout=True):
    repository = tmp_path / "migration"
    repository.mkdir()
    checkout = repository / CHECKOUT
    if make_checkout:
        checkout.mkdir(parents=True)
    lock = {"bootstrap": {
        "commit": COMMIT, "from": PAGE, "repository": REPOSITORY,
        "repository_page": SOURCE_PAGE, "checkout_path": CHECKOUT
    }}
    monkeypatch.setattr(build_cli, "REPO", repository)
    monkeypatch.setattr(build_cli, "read_lock", lambda _repo, _slug: lock)
    return repository, checkout


def test_v11_reads_the_pinned_page_from_the_configured_external_checkout(monkeypatch, tmp_path):
    _, checkout = _set_external_bootstrap(monkeypatch, tmp_path)
    calls = []

    def fake_run(command, capture_output):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=DATA.encode("utf-8"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = SimpleNamespace(html=DATA.encode("utf-8"))

    assert build_cli._baseline_data("tareekh-tafseer", result) == []
    assert calls == [["git", "-C", str(checkout), "show", f"{COMMIT}:{SOURCE_PAGE}"]]


def test_v11_fails_closed_when_the_pinned_external_checkout_is_missing(monkeypatch, tmp_path):
    _set_external_bootstrap(monkeypatch, tmp_path, make_checkout=False)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a) or None)

    findings = build_cli._baseline_data("tareekh-tafseer", SimpleNamespace(html=DATA.encode("utf-8")))

    assert len(findings) == 1
    assert findings[0].code == "V11.data-changed"
    assert findings[0].severity == "blocking"
    assert "pinned checkout is missing" in findings[0].message
    assert not calls


def test_v11_fails_closed_when_the_pinned_commit_or_page_is_unavailable(monkeypatch, tmp_path):
    _set_external_bootstrap(monkeypatch, tmp_path)
    calls = []

    def fake_run(command, capture_output):
        calls.append(command)
        return SimpleNamespace(returncode=128, stdout=b"", stderr=b"not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    findings = build_cli._baseline_data(
        "tareekh-tafseer", SimpleNamespace(html=DATA.encode("utf-8"))
    )

    assert len(findings) == 1
    assert findings[0].code == "V11.data-changed"
    assert findings[0].severity == "blocking"
    assert REPOSITORY in findings[0].message
    assert calls == [[
        "git", "-C", str(tmp_path / "migration" / CHECKOUT), "show", f"{COMMIT}:{SOURCE_PAGE}"
    ]]


def test_ci_checks_out_the_same_repository_and_commit_as_the_book_lock():
    lock = json.loads((REPO / "books/tareekh-tafseer/ids.lock.json").read_text(encoding="utf-8"))
    boot = lock["bootstrap"]
    workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert boot["repository"] == REPOSITORY
    assert boot["commit"] == COMMIT
    assert boot["repository_page"] == SOURCE_PAGE
    assert boot["sha256"] == "f1c593e681ba643e3f7398df2289ee47e278c4e9dbf007ce2b1aa4a106c03323"
    assert f"repository: {boot['repository']}" in workflow
    assert f"ref: {boot['commit']}" in workflow
    assert f"path: {boot['checkout_path']}" in workflow
    assert "persist-credentials: false" in workflow
