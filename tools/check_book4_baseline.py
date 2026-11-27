#!/usr/bin/env python3
"""Fail closed unless Book 4's pinned page and Phase 0 extract still match."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PREFIX = "const D = "


def parse_data_line(text):
    lines = [line for line in text.splitlines() if line.startswith(DATA_PREFIX)]
    if len(lines) != 1 or not lines[0].endswith(";"):
        raise ValueError("expected exactly one parseable const D data line")
    return json.loads(lines[0][len(DATA_PREFIX):-1])


def same(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        return list(left) == list(right) and all(
            same(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            same(a, b) for a, b in zip(left, right)
        )
    return type(left) is type(right) and left == right


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    record_path = ROOT / "docs" / "migrations" / "phase3-book4-baseline.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    source = record["source"]
    source_repo = ROOT / source["checkout_path"]

    if not source_repo.is_dir():
        raise SystemExit(
            f"BLOCKING: pinned source checkout is missing: {source_repo}"
        )

    commit = subprocess.run(
        ["git", "-C", str(source_repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if commit.returncode != 0 or commit.stdout.strip() != source["commit"]:
        actual = commit.stdout.strip() if commit.returncode == 0 else "unavailable"
        raise SystemExit(
            f"BLOCKING: expected {source['repository']} at "
            f"{source['commit']}, found {actual}"
        )

    page = source_repo / source["page"]
    if not page.is_file():
        raise SystemExit(f"BLOCKING: pinned source page is missing: {page}")
    if sha256(page) != source["sha256"]:
        raise SystemExit(f"BLOCKING: pinned source page hash changed: {page}")

    fixture = ROOT / record["fixture"]["path"]
    if not fixture.is_file():
        raise SystemExit(f"BLOCKING: Phase 0 fixture is missing: {fixture}")
    if sha256(fixture) != record["fixture"]["sha256"]:
        raise SystemExit(f"BLOCKING: Phase 0 fixture hash changed: {fixture}")

    try:
        page_data = parse_data_line(page.read_text(encoding="utf-8"))
        fixture_data = json.loads(fixture.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"BLOCKING: baseline data cannot be parsed: {exc}") from exc

    if not same(page_data, fixture_data):
        raise SystemExit(
            "BLOCKING: embedded Book 4 data differs from the Phase 0 fixture"
        )

    counts = {
        key: len(page_data.get(key, []))
        for key in record["section_counts"]
    }
    if counts != record["section_counts"]:
        raise SystemExit(
            f"BLOCKING: Book 4 section counts differ: {counts}"
        )

    print(
        "Book 4 baseline OK: pinned source page, SHA-256, fixture, "
        "payload identity, and section counts match."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
