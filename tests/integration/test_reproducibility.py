"""V10 on this machine: two clean copies, different directories and environments."""
import subprocess
import sys

from helpers import PUBLISHED_SHA256, REPO


def test_two_clean_builds_are_identical():
    r = subprocess.run([sys.executable, str(REPO / "tools" / "check_reproducible.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "reproducible" in r.stdout
    assert PUBLISHED_SHA256 in r.stdout
