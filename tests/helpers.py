"""Shared test helpers."""
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PILOT = "munazara-rashidiya"
PILOT_PAGE = "mantiq/MunazaraRashidiyaAQU.html"
PILOT_SHA256 = "a91018ea392c1b39d8af7583f18d792e9f3467e63e4c91c13183545ce016aaf3"
GOLDEN = REPO / "tests" / "golden"


def make_repo(tmp_path, books=()):
    """A scratch repository holding platform/ and the named fixture or real books."""
    root = tmp_path / "repo"
    shutil.copytree(REPO / "platform", root / "platform")
    (root / "books").mkdir()
    for slug, source in books:
        shutil.copytree(source, root / "books" / slug)
    return root
