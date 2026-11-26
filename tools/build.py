#!/usr/bin/env python3
"""Build the study pages (spec section 5).

    python3 tools/build.py build <slug>|--all   write the page to its published path
    python3 tools/build.py check <slug>|--all   build in memory and compare with the committed page
    python3 tools/build.py diff  <slug>|--all   build in memory and write a readable diff report
    python3 tools/build.py ids review|apply|bootstrap|invariants <slug> …   the ID lock (see mudhakarah/idscli.py)

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
from mudhakarah.idscli import main as ids_main  # noqa: E402
from mudhakarah.ids import read_lock  # noqa: E402
from mudhakarah.pipeline import run_book, write_result  # noqa: E402
from mudhakarah.validate import v11_integrity, v13_paths  # noqa: E402


def _books(args):
    found = discover_books(REPO)
    if args.all:
        return found
    if args.slug not in found:
        print(f"error: no book '{args.slug}' (known: {', '.join(found) or 'none'})", file=sys.stderr)
        sys.exit(2)
    return [args.slug]


def _data_or_none(text):
    from mudhakarah.output import parse_data_line
    try:
        return parse_data_line(text) if text else None
    except ValueError:
        return None


def _baseline_data(slug, result):
    """V11 step 1: the data line equals the data line of the page the lock was bootstrapped from."""
    import subprocess
    from mudhakarah.errors import BLOCKING, Finding
    boot = (read_lock(REPO, slug) or {}).get("bootstrap")
    if not boot:
        return [Finding("V11.data-changed", BLOCKING, "the lock has no bootstrap page to compare with", slug)]
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{boot['commit']}:{boot['from']}"], capture_output=True)
    if r.returncode != 0:
        return [Finding("V11.data-changed", BLOCKING, f"cannot read {boot['from']} at {boot['commit'][:7]}", slug)]
    return v11_integrity.step1_data_identity(result.html.decode("utf-8"), r.stdout.decode("utf-8"), slug)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["ids"]:
        return ids_main(REPO, argv[1:])
    p = argparse.ArgumentParser(prog="build.py", description=__doc__.splitlines()[0])
    p.add_argument("mode", choices=["build", "check", "diff"])
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("slug", nargs="?")
    target.add_argument("--all", action="store_true")
    p.add_argument("--out", help="diff mode: folder for the reports (default: a new temporary folder)")
    p.add_argument("--against", help="diff mode: compare with the page at this git ref (default: the committed "
                                      "file in the working tree)")
    p.add_argument("--baseline-data", action="store_true",
                   help="check mode, step 1: also require the data line to equal the bootstrap page's (V11)")
    args = p.parse_args(argv)

    failed = False
    if args.mode == "check":
        for f in v13_paths.check(REPO):
            print(f, file=sys.stderr)
            failed = True
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
            if args.baseline_data:
                for f in _baseline_data(slug, result):
                    print(f"{slug}: {f}", file=sys.stderr)
                    failed = True
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
            if args.against:
                import subprocess
                r = subprocess.run(["git", "-C", str(REPO), "show", f"{args.against}:{result.output_path}"],
                                   capture_output=True)
                committed = r.stdout if r.returncode == 0 else None
            old = committed.decode("utf-8") if committed is not None else ""
            report = out / f"{slug}.diff.md"
            report.write_text(diff_report(old, result.html.decode("utf-8"), result.output_path),
                              encoding="utf-8", newline="\n")
            changes = out / f"{slug}.content-changes.md"
            changes.write_text(v11_integrity.content_change_report(_data_or_none(old), result.model,
                                                                   result.output_path),
                               encoding="utf-8", newline="\n")
            state = "identical" if committed == result.html else "different"
            print(f"{slug}: {state}; reports written to {report} and {changes}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
