"""V10 on this machine: two clean copies, different directories and environments."""
import subprocess
import sys

from helpers import REPO


def test_two_clean_builds_are_identical():
    r = subprocess.run([sys.executable, str(REPO / "tools" / "check_reproducible.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "reproducible" in r.stdout
    assert "a91018ea392c1b39d8af7583f18d792e9f3467e63e4c91c13183545ce016aaf3" in r.stdout
