"""The build pipeline (spec section 5): stages 1 to 7 for one book.

`run_book` builds into memory and returns the result; only `write_result` touches
the published path. Inputs are only read.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .config import load_book, load_site
from .errors import BLOCKING, BuildStopped, Finding, Report
from .ids import LOCK_NAME, bind, check_lock_identity, check_output_ids, read_lock
from .loaders import load_content
from .model import assemble, check_raw
from .output import manifest, manifest_bytes, sha256_bytes, verify_output, write_atomic
from .render import TEMPLATE_DIR, render, template_files
from .validate import model_findings, v07_assets, v08_html, v11_integrity


@dataclass
class BuildResult:
    slug: str
    output_path: str            # repository-relative published path, from book.json
    html: bytes
    model: dict
    manifest: dict
    report: Report = field(default_factory=Report)


def _rel(repo_root, path):
    return Path(path).resolve().relative_to(Path(repo_root).resolve()).as_posix()


def run_book(repo_root, slug):
    repo_root = Path(repo_root)
    report = Report()
    where = f"books/{slug}"

    # Stage 1: input discovery and configuration
    site, site_findings = load_site(repo_root)
    book, book_findings = load_book(repo_root, slug)
    report.stop_if_blocking("configuration", site_findings + book_findings)
    lock = read_lock(repo_root, slug)
    if lock is None:
        report.stop_if_blocking("configuration", [Finding(
            "V3.no-lock", BLOCKING, f"{LOCK_NAME} not found; a published book is bootstrapped from its live page "
            "(ids bootstrap), a new book gets its first IDs through ids review and ids apply", where)])
    report.stop_if_blocking("configuration", check_lock_identity(lock, book, f"{where}/{LOCK_NAME}"))

    # Stage 2: content loading
    raw, content_hashes, findings = load_content(repo_root, slug, book)
    report.stop_if_blocking("content loading", findings)

    # Stage 3: assembly and ID binding (section 6)
    report.stop_if_blocking("assembly and ID binding", check_raw(raw, book, where))
    ids, findings, _cases = bind(raw, book, lock, where)
    if any(f.severity == BLOCKING for f in findings):
        findings = findings + [Finding("V3.review", BLOCKING,
                                       f"run 'python3 tools/build.py ids review {slug}' to decide these cases", where)]
    report.stop_if_blocking("assembly and ID binding", findings)
    model, findings = assemble(raw, book, ids=ids, where=where)
    report.stop_if_blocking("assembly and ID binding", findings)

    # Stage 4: model validation (section 7)
    report.stop_if_blocking("model validation", model_findings(raw, model, book, where))

    # Stage 5: rendering
    text = render(repo_root, book, site, model, where=where)

    # Stage 6: output verification
    report.stop_if_blocking("output verification", verify_output(text, model, where))
    report.stop_if_blocking("output verification", check_output_ids(model, lock, where))
    committed = repo_root / book["output"]
    previous_size = committed.stat().st_size if committed.is_file() else None
    report.stop_if_blocking("output verification", v07_assets.check(text, repo_root, site, where, book["output"]))
    report.stop_if_blocking("output verification", v08_html.check(text, book, where, previous_size))
    after = {name: sha256_bytes((repo_root / "books" / slug / "content" / name).read_bytes())
             for name in content_hashes}
    report.stop_if_blocking("output verification", v11_integrity.files_unchanged(content_hashes, after, where))

    html = text.encode("utf-8")
    inputs = {
        "platform/site.json": sha256_bytes((repo_root / "platform" / "site.json").read_bytes()),
        f"books/{slug}/book.json": sha256_bytes((repo_root / "books" / slug / "book.json").read_bytes()),
    }
    for name, digest in content_hashes.items():
        inputs[f"books/{slug}/content/{name}"] = digest
    inputs[f"books/{slug}/{LOCK_NAME}"] = sha256_bytes((repo_root / "books" / slug / LOCK_NAME).read_bytes())
    for path in template_files(repo_root):
        inputs[_rel(repo_root, path)] = sha256_bytes(path.read_bytes())
    m = manifest(repo_root, slug, inputs, book["output"], html, report.findings)
    return BuildResult(slug, book["output"], html, model, m, report)


def write_result(repo_root, result):
    """Stage 7: write the page atomically, then its manifest under reports/build/."""
    repo_root = Path(repo_root)
    write_atomic(repo_root / result.output_path, result.html)
    write_atomic(repo_root / "reports" / "build" / f"{result.slug}.manifest.json", manifest_bytes(result.manifest))


__all__ = ["BuildResult", "BuildStopped", "BLOCKING", "TEMPLATE_DIR", "run_book", "write_result"]
