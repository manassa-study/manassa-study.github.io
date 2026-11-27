"""The CI workflow may only build and validate (spec section 10).

This test reads every workflow file as text (no YAML library is a dependency)
and fails if a boundary is loosened: write permissions, pull_request_target,
secrets, a commit, push or deploy step, or a third-party action not pinned to a
full commit SHA.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.y*ml"))


def test_there_is_exactly_one_workflow():
    assert [p.name for p in WORKFLOWS] == ["ci.yml"]


@pytest.fixture(params=WORKFLOWS, ids=lambda p: p.name)
def text(request):
    return request.param.read_text(encoding="utf-8")


def code_lines(text):
    return [ln.split(" #")[0] for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def test_permissions_are_read_only(text):
    lines = code_lines(text)
    perm_lines = [i for i, ln in enumerate(lines) if re.match(r"^\s*permissions\s*:", ln)]
    assert len(perm_lines) == 1, "exactly one permissions block, at the top level"
    i = perm_lines[0]
    assert lines[i] == "permissions:", "permissions must be declared at the top level"
    block = []
    for ln in lines[i + 1:]:
        if ln.startswith("  ") and ln.strip():
            block.append(ln.strip())
        else:
            break
    assert block == ["contents: read"]
    assert not re.search(r"\bwrite\b", "\n".join(lines)), "no write access of any kind"


def test_no_dangerous_triggers_or_secrets(text):
    body = "\n".join(code_lines(text))
    assert "pull_request_target" not in body
    assert "secrets." not in body and "secrets[" not in body
    assert "GITHUB_TOKEN" not in body


@pytest.mark.parametrize("pattern", [
    r"git\s+commit", r"git\s+push", r"gh\s+pr", r"gh\s+release", r"deploy-pages", r"upload-pages-artifact",
    r"peaceiris", r"JamesIves", r"gh-pages", r"actions/create-release",
])
def test_no_commit_push_or_deploy(text, pattern):
    assert not re.search(pattern, "\n".join(code_lines(text)), re.I)


def test_actions_pinned_to_full_sha(text):
    uses = re.findall(r"uses:\s*([^\s#]+)", "\n".join(code_lines(text)))
    assert uses, "the workflow uses at least checkout"
    for ref in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), f"not pinned to a commit SHA: {ref}"


def test_checkout_does_not_keep_credentials(text):
    assert text.count("actions/checkout@") == text.count("persist-credentials: false")


def test_every_job_has_a_timeout(text):
    jobs = re.findall(r"^  ([\w-]+):\n", text.split("\njobs:\n", 1)[1], re.M)
    assert jobs
    assert text.count("timeout-minutes:") == len(jobs)


def test_installs_use_hashes(text):
    for ln in code_lines(text):
        if "pip install" in ln:
            assert "--require-hashes" in ln, ln


def test_book4_build_job_uses_its_pinned_baseline_guard():
    lines = code_lines((REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    assert "        run: python tools/check_book4_baseline.py" in lines
    assert "        run: python tools/build.py check --all" in lines
    assert "        run: python tools/build.py check --all --baseline-data" not in lines


def test_only_the_reports_job_is_advisory():
    """From Phase 2 the browser job blocks (spec section 9); only the report job may fail softly."""
    lines = code_lines((REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    job, advisory = None, []
    for ln in lines:
        m = re.match(r"^  ([a-z][a-z0-9-]*):\s*$", ln)
        if m:
            job = m.group(1)
        if re.match(r"^\s+continue-on-error:\s*true\s*$", ln):
            advisory.append(job)
    assert advisory == ["reports"]
