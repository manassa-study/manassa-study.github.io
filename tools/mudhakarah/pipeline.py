"""The build pipeline (spec section 5): stages 1 to 7 for one book.

`run_book` builds into memory and returns the result; only `write_result` touches
the published path. Inputs are only read.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .config import load_book, load_site
from .errors import BLOCKING, BuildStopped, Report
from .loaders import load_content
from .model import assemble
from .output import manifest, manifest_bytes, sha256_bytes, verify_output, write_atomic
from .render import TEMPLATE_DIR, render, template_files


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

    # Stage 2: content loading
    raw, content_hashes, findings = load_content(repo_root, slug, book)
    report.stop_if_blocking("content loading", findings)

    # Stage 3: assembly (ID binding joins this stage in M3)
    model, findings = assemble(raw, book, where=where)
    report.stop_if_blocking("assembly", findings)

    # Stage 4: model validation (the section 7 validators join this stage in M4)

    # Stage 5: rendering
    text = render(repo_root, book, site, model, where=where)

    # Stage 6: output verification
    report.stop_if_blocking("output verification", verify_output(text, model, where))

    html = text.encode("utf-8")
    inputs = {
        "platform/site.json": sha256_bytes((repo_root / "platform" / "site.json").read_bytes()),
        f"books/{slug}/book.json": sha256_bytes((repo_root / "books" / slug / "book.json").read_bytes()),
    }
    for name, digest in content_hashes.items():
        inputs[f"books/{slug}/content/{name}"] = digest
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
