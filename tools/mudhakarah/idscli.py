"""`tools/build.py ids …` (spec section 6, human approval workflow).

    ids review <slug> [--out FILE]          write a proposal (outside the repository by default)
    ids apply <slug> --proposal FILE --approver NAME --pull-request N [--date YYYY-MM-DD]
    ids bootstrap <slug> --commit SHA --approver NAME --pull-request N --date YYYY-MM-DD
        [--allow-reconstructed-option-order]
    ids invariants <slug> [--base REF]      compare the lock with the one at REF (CI: origin/main)

Only `apply` and `bootstrap` write, and only the lock file.
"""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import load_book
from .errors import BLOCKING, BuildStopped, Finding
from .ids import LOCK_NAME, apply, bootstrap, dumps_lock, invariants, lock_path, read_lock, review
from .loaders import load_content
from .model import check_raw
from .output import parse_data_line, write_atomic


def _load(repo, slug):
    book, findings = load_book(repo, slug)
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("configuration", findings)
    raw, _, findings = load_content(repo, slug, book)
    findings = check_raw(raw, book, f"books/{slug}")
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("assembly", findings)
    return book, raw


def _previous(repo, book):
    """The data of the committed page, to show old items in review cases."""
    page = Path(repo) / book["output"]
    if not page.is_file():
        return None
    try:
        return parse_data_line(page.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _git_show(repo, ref, path):
    r = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main(repo, argv):
    p = argparse.ArgumentParser(prog="build.py ids")
    sub = p.add_subparsers(dest="action", required=True)
    r = sub.add_parser("review")
    r.add_argument("slug")
    r.add_argument("--out")
    a = sub.add_parser("apply")
    a.add_argument("slug")
    a.add_argument("--proposal", required=True)
    a.add_argument("--approver", required=True)
    a.add_argument("--pull-request", type=int, required=True)
    a.add_argument("--date", default=None)
    b = sub.add_parser("bootstrap")
    b.add_argument("slug")
    b.add_argument("--commit", required=True)
    b.add_argument("--approver", required=True)
    b.add_argument("--pull-request", type=int, required=True)
    b.add_argument("--date", required=True)
    b.add_argument("--allow-reconstructed-option-order", action="store_true",
                   help="capture exact displayed option order from the baseline when original source slots are unavailable")
    i = sub.add_parser("invariants")
    i.add_argument("slug")
    i.add_argument("--base", default="origin/main")
    args = p.parse_args(argv)
    where = f"books/{args.slug}/{LOCK_NAME}"
    try:
        if args.action == "invariants":
            new = read_lock(repo, args.slug)
            if new is None:
                raise BuildStopped("ID invariants", [Finding("V3.no-lock", BLOCKING, "no lock", where)])
            old_bytes = _git_show(repo, args.base, f"books/{args.slug}/{LOCK_NAME}")
            old = json.loads(old_bytes) if old_bytes else None
            problems = invariants(old, new, where)
            if problems:
                raise BuildStopped("ID invariants", problems)
            base = f"the lock at {args.base}" if old else f"no lock at {args.base} (first lock: self-check only)"
            print(f"{args.slug}: lock invariants hold against {base}")
            return 0

        book, raw = _load(repo, args.slug)
        lock = read_lock(repo, args.slug)
        if args.action == "review":
            proposal = review(raw, book, lock, where, _previous(repo, book))
            out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="mudhakarah-ids-")) / \
                f"{args.slug}.proposal.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            kinds = {}
            for c in proposal["cases"]:
                kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
            print(f"{args.slug}: {len(proposal['cases'])} case(s) {kinds or ''}; proposal written to {out}")
            for m in proposal["other_findings"]:
                print(f"{args.slug}: {m}", file=sys.stderr)
            return 1 if proposal["other_findings"] else 0

        if args.action == "apply":
            proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
            date = args.date or datetime.date.today().isoformat()
            new_lock, summary = apply(raw, book, lock, proposal, args.approver, args.pull_request, date, where,
                                      _previous(repo, book))
            write_atomic(lock_path(repo, args.slug), dumps_lock(new_lock).encode("utf-8"))
            text = ", ".join(f"{n} {k}" for k, n in summary.items()) or "no changes"
            print(f"{args.slug}: IDs: {text}; lock updated")
            return 0

        # bootstrap
        if lock is not None:
            raise BuildStopped("ID bootstrap", [Finding("V3.bootstrap", BLOCKING,
                                                        "a lock already exists; bootstrap runs once", where)])
        page = _git_show(repo, args.commit, book["output"])
        if page is None:
            raise BuildStopped("ID bootstrap", [Finding("V3.bootstrap", BLOCKING,
                                                        f"{book['output']} not found at {args.commit}", where)])
        commit = subprocess.run(["git", "-C", str(repo), "rev-parse", args.commit], capture_output=True,
                                text=True, check=True).stdout.strip()
        info = {"from": book["output"], "commit": commit, "sha256": hashlib.sha256(page).hexdigest()}
        if args.allow_reconstructed_option_order:
            info["option_order"] = "captured-from-baseline"
        live = parse_data_line(page.decode("utf-8"))
        new_lock = bootstrap(raw, book, live, info, args.approver, args.pull_request, args.date, where,
                             check_sequence=not args.allow_reconstructed_option_order)
        write_atomic(lock_path(repo, args.slug), dumps_lock(new_lock).encode("utf-8"))
        print(f"{args.slug}: lock bootstrapped from {info['from']} at {commit[:7]} (sha256 {info['sha256'][:12]}…): "
              f"{len(new_lock['cards']['items'])} cards, {len(new_lock['questions']['items'])} questions, "
              f"{len(new_lock['topics'])} topics, {len(new_lock['maps'])} maps")
        return 0
    except BuildStopped as e:
        print(f"{args.slug}: {e}", file=sys.stderr)
        return 1
