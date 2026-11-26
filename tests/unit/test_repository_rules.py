"""Repository rules from the approved plan that do not depend on a build."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# O-1 (approved 27 November 2026): the folders Jekyll must not publish.
EXPECTED_EXCLUDES = ["books/", "platform/", "tools/", "tests/", "references/", "reports/", "docs/",
                     # root tooling files, same reason
                     "requirements.txt", "requirements-dev.txt"]


def test_config_yml_excludes_non_published_folders():
    text = (REPO / "_config.yml").read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert lines[0] == "exclude:"
    assert [ln.strip()[2:] for ln in lines[1:]] == EXPECTED_EXCLUDES
    assert all(ln.startswith("  - ") for ln in lines[1:]), "_config.yml holds only the exclude list"


def _requirements(name):
    entries, current = [], None
    for raw in (REPO / name).read_text(encoding="utf-8").splitlines():
        line = raw.strip().rstrip("\\").strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--hash=sha256:"):
            assert re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", line), line
            current[1].append(line)
        else:
            m = re.fullmatch(r"([A-Za-z0-9_.-]+)==([0-9][0-9A-Za-z.]*)", line)
            assert m, f"{name}: every requirement is pinned with ==: {line}"
            current = (m.group(1).lower(), [])
            entries.append(current)
    return entries


def test_runtime_dependencies_are_jinja2_only():
    entries = _requirements("requirements.txt")
    assert [n for n, _ in entries] == ["jinja2", "markupsafe"]  # markupsafe is Jinja2's own dependency
    assert all(h for _, h in entries), "every runtime requirement has hashes"


def test_dev_dependencies_are_pinned_with_hashes():
    entries = _requirements("requirements-dev.txt")
    names = [n for n, _ in entries]
    assert {"pytest", "playwright", "jinja2"} <= set(names)
    assert all(h for _, h in entries)
