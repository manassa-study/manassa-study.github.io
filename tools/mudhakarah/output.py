"""Output verification (stage 6), the writer and the build manifest (stage 7).

The manifest holds no clock, host, user or absolute path, so two builds from the
same inputs give identical manifests (spec section 5, Reproducibility).
"""
import hashlib
import json
import os
import platform as _platform
import tempfile
from pathlib import Path

from . import TOOL_VERSION
from .errors import BLOCKING, BuildStopped, Finding
from .render import SCRIPT_BREAKERS

DATA_PREFIX = "const D = "


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def data_lines(text):
    lines = text.split("\n")
    return [i for i, line in enumerate(lines) if line.startswith(DATA_PREFIX)], lines


def parse_data_line(text):
    """Return the data object written into a page, or raise ValueError."""
    idx, lines = data_lines(text)
    if len(idx) != 1:
        raise ValueError(f"expected exactly one '{DATA_PREFIX}' line, found {len(idx)}")
    line = lines[idx[0]]
    if not line.endswith(";"):
        raise ValueError("the data line does not end with ';'")
    return json.loads(line[len(DATA_PREFIX):-1])


def _same(a, b):
    """Deep equality that also requires the same key order everywhere."""
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a) == list(b) and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def verify_output(text, model, where):
    """Stage 6: re-read the rendered page."""
    findings = []
    idx, lines = data_lines(text)
    if len(idx) != 1:
        findings.append(Finding("V8.data-line", BLOCKING,
                                f"expected exactly one '{DATA_PREFIX}' line, found {len(idx)}", where))
    else:
        line = lines[idx[0]].lower()
        for bad in SCRIPT_BREAKERS:
            if bad in line:
                findings.append(Finding("V8.script-breaker", BLOCKING, f"the data line contains '{bad}'", where))
        try:
            parsed = parse_data_line(text)
        except ValueError as e:
            findings.append(Finding("V8.data-parse", BLOCKING, f"the data line does not parse back: {e}", where))
        else:
            if not _same(parsed, model):
                findings.append(Finding("V8.data-roundtrip", BLOCKING,
                                        "the data parsed back from the page is not equal to the model", where))
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("output verification", findings)
    return findings


def write_atomic(path, data):
    """Write to a temporary file beside the target, then rename it into place."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _versions():
    from importlib.metadata import version
    return {
        "mudhakarah": TOOL_VERSION,
        "python": ".".join(_platform.python_version_tuple()[:2]),
        "jinja2": version("jinja2"),
        "markupsafe": version("markupsafe"),
    }


def manifest(repo_root, slug, inputs, output_path, output_bytes, findings):
    """`inputs` maps repository-relative paths to their bytes' SHA-256, in reading order."""
    return {
        "manifest_version": 1,
        "book": slug,
        "inputs": dict(inputs),
        "tools": _versions(),
        "output": {"path": output_path, "sha256": sha256_bytes(output_bytes), "bytes": len(output_bytes)},
        "warnings": [str(f) for f in findings if f.severity != BLOCKING],
    }


def manifest_bytes(m):
    return (json.dumps(m, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
