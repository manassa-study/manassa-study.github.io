"""The build command's modes (spec section 5): check writes nothing and fails on a
hand-edited page; diff separates the data line from the rest."""
import shutil
import subprocess
import sys

from helpers import PILOT, PILOT_PAGE, REPO, make_repo
from mudhakarah.diffreport import diff_report

CLI = [sys.executable, str(REPO / "tools" / "build.py")]


def test_check_passes_on_the_committed_pilot():
    before = (REPO / PILOT_PAGE).stat().st_mtime_ns
    r = subprocess.run(CLI + ["check", PILOT], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "a91018ea392c1b39d8af7583f18d792e9f3467e63e4c91c13183545ce016aaf3" in r.stdout
    assert (REPO / PILOT_PAGE).stat().st_mtime_ns == before


def test_unknown_book_is_a_usage_error():
    r = subprocess.run(CLI + ["check", "no-such-book"], capture_output=True, text=True)
    assert r.returncode == 2


def test_diff_report_separates_data_from_chrome():
    old = "<p>a</p>\nconst D = {\"x\": [1, 2]};\n<p>b</p>\n"
    new = "<p>a</p>\nconst D = {\"x\": [1, 3]};\n<p>c</p>\n"
    report = diff_report(old, new, "page.html")
    chrome, data = report.split("## Data line")
    assert "-<p>b</p>" in chrome and "+<p>c</p>" in chrome and "[1, 3]" not in chrome
    assert "D.x[1]: 2 -> 3" in data


def test_check_fails_on_a_hand_edited_page(tmp_path):
    root = make_repo(tmp_path, [(PILOT, REPO / "books" / PILOT)])
    shutil.copytree(REPO / "tools", root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    page = root / PILOT_PAGE
    page.parent.mkdir(parents=True)
    page.write_bytes((REPO / PILOT_PAGE).read_bytes().replace("</title>".encode(), " </title>".encode(), 1))
    r = subprocess.run([sys.executable, str(root / "tools" / "build.py"), "check", PILOT],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "V9.committed-output" in r.stderr
