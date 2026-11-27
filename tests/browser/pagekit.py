"""Shared browser helpers: serve a page locally and block every other request.

Tests never touch the network or Supabase (spec section 9, R5): each page is
served from 127.0.0.1 and every request to another host is aborted."""
import contextlib
import functools
import http.server
import os
import threading
from pathlib import Path

PAGE_PATH = "mantiq/MunazaraRashidiyaAQU.html"
STORAGE_KEY = "munazara-rashidiya-v1"
WELCOME_KEY = "munazara-wel"


@contextlib.contextmanager
def serve(html_bytes, workdir, page_path=PAGE_PATH):
    root = Path(workdir)
    (root / page_path).parent.mkdir(parents=True, exist_ok=True)
    (root / page_path).write_bytes(html_bytes)
    handler = functools.partial(_Quiet, directory=str(root))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/{page_path}"
    finally:
        httpd.shutdown()


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def launch(playwright):
    exe = os.environ.get("MUDHAKARAH_CHROMIUM")
    return playwright.chromium.launch(**({"executable_path": exe} if exe else {}))


def block_outside(context, blocked):
    def handler(route):
        url = route.request.url
        if url.startswith("http://127.0.0.1:"):
            return route.continue_()
        blocked.append(url)
        return route.abort()
    context.route("**/*", handler)


def seed_script(state=None, welcome_seen=True, storage_key=STORAGE_KEY, welcome_key=WELCOME_KEY):
    """Runs before the page's own scripts on every load: a registered student who has
    seen the welcome popup, optionally with saved progress (only if none is stored yet)."""
    import json
    state = dict(state or {}, registered=True) if state is not None else {"registered": True}
    return (f"(function(){{try{{if(!localStorage.getItem({json.dumps(storage_key)}))"
            f"localStorage.setItem({json.dumps(storage_key)},{json.dumps(json.dumps(state, ensure_ascii=False))});"
            + (f"sessionStorage.setItem({json.dumps(welcome_key)},'1');" if welcome_seen else "")
            + "}catch(e){}})();")
