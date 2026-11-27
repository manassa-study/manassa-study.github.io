#!/usr/bin/env python3
"""V10 Reproducibility: build every book in two separate clean copies of the
repository, from different working directories and with different environment
variables, and require identical manifests and bytes (spec sections 5 and 9).

    python3 tools/check_reproducible.py [--keep DIR]

Writes nothing in the repository. Prints each manifest's SHA-256, so a run on
another machine can be compared with CI's.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from mudhakarah.config import discover_books  # noqa: E402
from mudhakarah.validate.v10_reproducibility import compare  # noqa: E402

ENVS = [
    {"TZ": "UTC", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "1"},
    {"TZ": "Asia/Dubai", "LANG": "ar_AE.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "4242",
     "MUDHAKARAH_UNRELATED": "x"},
]


def tracked_files(repo):
    r = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], capture_output=True, check=True)
    return [p for p in r.stdout.decode("utf-8").split("\0") if p]


def clean_copy(repo, dest):
    for rel in tracked_files(repo):
        src = repo / rel
        if src.is_file():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)


def build_in(copy, env_extra, cwd):
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "SYSTEMROOT")}
    env.update(env_extra, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, str(copy / "tools" / "build.py"), "build", "--all"], cwd=cwd, env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"build failed in {copy}:\n{r.stdout}{r.stderr}")
    out = {}
    for slug in discover_books(copy):
        m = (copy / "reports" / "build" / f"{slug}.manifest.json").read_bytes()
        page = (copy / json.loads(m)["output"]["path"]).read_bytes()
        out[slug] = (json.loads(m), m, page)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--keep", help="keep the two copies under this folder")
    args = p.parse_args(argv)
    base = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="mudhakarah-repro-"))
    a, b = base / "a" / "repo", base / "b" / "nested" / "repo"
    for d in (a, b):
        d.mkdir(parents=True, exist_ok=True)
        clean_copy(REPO, d)
    ra = build_in(a, ENVS[0], cwd=a)
    rb = build_in(b, ENVS[1], cwd=b.parent)
    failed = False
    for slug in sorted(ra):
        (ma, mbytes_a, pa), (mb, mbytes_b, pb) = ra[slug], rb[slug]
        problems = compare(ma, mb, slug)
        if pa != pb:
            problems.append("pages differ")
        print(f"{slug}: manifest sha256 {hashlib.sha256(mbytes_a).hexdigest()} / "
              f"{hashlib.sha256(mbytes_b).hexdigest()}; page sha256 {hashlib.sha256(pa).hexdigest()}")
        for f in problems:
            print(f"{slug}: {f}", file=sys.stderr)
            failed = True
    if not args.keep:
        shutil.rmtree(base)
    print("reproducible" if not failed else "NOT reproducible")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
