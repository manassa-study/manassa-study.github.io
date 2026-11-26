"""V13 Published paths (blocking): every file path published at the baseline
commit still exists and is still served, or appears in the approved redirect list.
Replaces the master plan's urls.csv (R3). The list is platform/published-paths.json."""
import json
from pathlib import Path

from ..errors import BLOCKING, Finding

LIST = Path("platform") / "published-paths.json"


def excluded_folders(repo_root):
    """The `exclude:` entries of _config.yml (a plain list, as written for O-1)."""
    path = Path(repo_root) / "_config.yml"
    out, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        if line.startswith("exclude:"):
            inside = True
            continue
        if inside:
            s = line.strip()
            if s.startswith("- "):
                out.append(s[2:].strip())
            elif s and not s.startswith("#"):
                inside = False
    return out


def check(repo_root, where=str(LIST)):
    repo_root = Path(repo_root)
    path = repo_root / LIST
    if not path.is_file():
        return [Finding("V13.list", BLOCKING, "the published-paths list is missing", where)]
    data = json.loads(path.read_text(encoding="utf-8"))
    redirects = {r["from"] for r in data.get("redirects", []) if r.get("approved_by") and r.get("pull_request")}
    excluded = excluded_folders(repo_root)
    out = []
    for p in data["paths"]:
        if p in redirects:
            continue
        if not (repo_root / p).is_file():
            out.append(Finding("V13.path-missing", BLOCKING,
                               f"'{p}' was published at {data['baseline_commit'][:7]} and no longer exists "
                               "(restore it, or add an approved redirect)", where))
        elif any(p == e or p.startswith(e.rstrip("/") + "/") for e in excluded):
            out.append(Finding("V13.path-unserved", BLOCKING,
                               f"'{p}' was published at {data['baseline_commit'][:7]} but _config.yml now "
                               "excludes it from the site", where))
    return out
