#!/usr/bin/env python3
"""Build the study pages (spec section 5).

    python3 tools/build.py build <slug>|--all   write the page to its published path
    python3 tools/build.py check <slug>|--all   build in memory and compare with the committed page
    python3 tools/build.py diff  <slug>|--all   build in memory and write a readable diff report

Exit code 0 on success, 1 when a blocking check fails, 2 on a usage error.
"""
import argparse
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from mudhakarah.config import discover_books  # noqa: E402
from mudhakarah.diffreport import diff_report  # noqa: E402
from mudhakarah.errors import BuildStopped  # noqa: E402
from mudhakarah.pipeline import run_book, write_result  # noqa: E402


def _books(args):
    found = discover_books(REPO)
    if args.all:
        return found
    if args.slug not in found:
        print(f"error: no book '{args.slug}' (known: {', '.join(found) or 'none'})", file=sys.stderr)
        sys.exit(2)
    return [args.slug]


def main(argv=None):
    p = argparse.ArgumentParser(prog="build.py", description=__doc__.splitlines()[0])
    p.add_argument("mode", choices=["build", "check", "diff"])
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("slug", nargs="?")
    target.add_argument("--all", action="store_true")
    p.add_argument("--out", help="diff mode: folder for the report (default: a new temporary folder)")
    args = p.parse_args(argv)

    failed = False
    for slug in _books(args):
        try:
            result = run_book(REPO, slug)
        except BuildStopped as e:
            print(f"{slug}: {e}", file=sys.stderr)
            failed = True
            continue
        for w in result.report.warnings:
            print(f"{slug}: {w}")
        committed_path = REPO / result.output_path
        committed = committed_path.read_bytes() if committed_path.is_file() else None
        if args.mode == "build":
            write_result(REPO, result)
            print(f"{slug}: wrote {result.output_path} ({len(result.html)} bytes, "
                  f"sha256 {result.manifest['output']['sha256']})")
        elif args.mode == "check":
            if committed == result.html:
                print(f"{slug}: OK, {result.output_path} equals a fresh build "
                      f"(sha256 {result.manifest['output']['sha256']})")
            else:
                print(f"{slug}: [BLOCKING] V9.committed-output: {result.output_path} differs from a fresh build; "
                      f"run 'python3 tools/build.py diff {slug}' to see how", file=sys.stderr)
                failed = True
        else:
            out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="mudhakarah-diff-"))
            out.mkdir(parents=True, exist_ok=True)
            old = committed.decode("utf-8") if committed is not None else ""
            report = out / f"{slug}.diff.md"
            report.write_text(diff_report(old, result.html.decode("utf-8"), result.output_path),
                              encoding="utf-8", newline="\n")
            state = "identical" if committed == result.html else "different"
            print(f"{slug}: {state}; report written to {report}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
