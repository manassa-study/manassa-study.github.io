import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pagekit import block_outside, launch, seed_script, serve  # noqa: E402


def pytest_collection_modifyitems(items):
    for item in items:
        if HERE in Path(str(item.fspath)).parents:
            item.add_marker(pytest.mark.browser)


@pytest.fixture(scope="session")
def built_page():
    from helpers import PILOT, REPO
    from mudhakarah.pipeline import run_book
    return run_book(REPO, PILOT).html


@pytest.fixture(scope="session")
def page_url(built_page):
    with tempfile.TemporaryDirectory() as tmp, serve(built_page, tmp) as url:
        yield url


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = launch(p)
        yield b
        b.close()


@pytest.fixture
def open_page(browser):
    """open_page(width=390, state=None, theme=None) -> (page, errors, blocked)."""
    contexts = []

    def _open(width=390, height=844, state=None, color_scheme="light"):
        ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=color_scheme)
        contexts.append(ctx)
        blocked = []
        block_outside(ctx, blocked)
        ctx.add_init_script(seed_script(state))
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        return page, errors, blocked

    yield _open
    for c in contexts:
        c.close()
