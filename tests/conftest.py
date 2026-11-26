import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "browser: Playwright browser tests (advisory in Phase 1, blocking from Phase 2)")
