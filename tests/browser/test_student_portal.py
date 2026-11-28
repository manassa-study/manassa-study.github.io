"""Focused browser coverage for portal session isolation and quiz-history metrics."""
import contextlib
import functools
import http.server
import json
from pathlib import Path
import threading

import pytest

REPO = Path(__file__).resolve().parents[2]

MOCK_SUPABASE = r"""
window.__portalRequests = [];
window.__portalAuthListener = null;
window.__resolvePortalRequest = function(index, result) {
  window.__portalRequests[index].resolve(result);
};
window.__emitPortalAuth = function(event, session) {
  window.__portalAuthListener(event, session);
};
window.supabase = {
  createClient: function() {
    return {
      auth: {
        onAuthStateChange: function(callback) { window.__portalAuthListener = callback; },
        getSession: function() {
          return Promise.resolve({data: {session: window.__initialPortalSession}, error: null});
        },
        signOut: function() { return Promise.resolve({error: null}); },
        signInWithOAuth: function() { return Promise.resolve({error: null}); },
        signInWithOtp: function() { return Promise.resolve({error: null}); },
        verifyOtp: function() { return Promise.resolve({error: null}); }
      },
      from: function(table) {
        var filters = {};
        var resolveRequest;
        var promise = new Promise(function(resolve) { resolveRequest = resolve; });
        window.__portalRequests.push({
          table: table,
          filters: filters,
          resolve: resolveRequest
        });
        return {
          select: function() { return this; },
          eq: function(key, value) { filters[key] = value; return this; },
          in: function(key, value) { filters[key] = value; return this; },
          then: function(resolve, reject) { return promise.then(resolve, reject); },
          catch: function(reject) { return promise.catch(reject); }
        };
      }
    };
  }
};
"""


@contextlib.contextmanager
def serve_repo():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(REPO))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        thread.join()


def session(user_id, email, access_token, refresh_token):
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user_id, "email": email},
    }


def open_portal(browser, base_url, initial_session):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script(
        "window.__initialPortalSession = "
        + json.dumps(initial_session)
        + ";"
        + MOCK_SUPABASE
    )

    def local_only(route):
        if route.request.url.startswith("http://127.0.0.1:"):
            route.continue_()
        else:
            route.abort()

    context.route("**/*", local_only)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base_url + "portal.html", wait_until="domcontentloaded")
    return context, page, errors


def wait_for_requests(page, count):
    page.wait_for_function(
        "(n) => window.__portalRequests.length >= n",
        arg=count,
    )


def resolve_request(page, index, rows):
    page.evaluate(
        "([i, data]) => window.__resolvePortalRequest(i, {data: data, error: null})",
        [index, rows],
    )


def rows_with_done(count):
    return [{
        "course": "madkhal-fiqh-v1",
        "state": {"done": {f"topic-{index}": True for index in range(count)}},
    }]


@pytest.mark.browser
def test_old_account_response_cannot_replace_new_account_progress(browser):
    with serve_repo() as base_url:
        context, page, errors = open_portal(
            browser, base_url, session("account-a", "a@example.test", "token-a", "refresh-a")
        )
        try:
            wait_for_requests(page, 1)
            page.evaluate(
                "(s) => window.__emitPortalAuth('SIGNED_IN', s)",
                session("account-b", "b@example.test", "token-b", "refresh-b"),
            )
            wait_for_requests(page, 2)
            assert page.evaluate("window.__portalRequests[0].filters.user_id") == "account-a"
            assert page.evaluate("window.__portalRequests[1].filters.user_id") == "account-b"

            resolve_request(page, 0, rows_with_done(99))
            page.wait_for_timeout(30)
            assert page.locator("#account-email").inner_text() == "b@example.test"
            assert page.locator("#dashboard").is_hidden()

            resolve_request(page, 1, rows_with_done(7))
            page.wait_for_function("!document.querySelector('#dashboard').hidden")
            assert page.locator(".book-card").first.locator(".book-stat b").first.inner_text() == "7"
            assert errors == []
        finally:
            context.close()


@pytest.mark.browser
def test_old_token_response_cannot_replace_refreshed_session_progress(browser):
    with serve_repo() as base_url:
        context, page, errors = open_portal(
            browser, base_url, session("account-a", "a@example.test", "token-old", "refresh-old")
        )
        try:
            wait_for_requests(page, 1)
            page.evaluate(
                "(s) => window.__emitPortalAuth('TOKEN_REFRESHED', s)",
                session("account-a", "a@example.test", "token-new", "refresh-new"),
            )
            wait_for_requests(page, 2)

            resolve_request(page, 0, rows_with_done(88))
            page.wait_for_timeout(30)
            assert page.locator("#dashboard").is_hidden()

            resolve_request(page, 1, rows_with_done(3))
            page.wait_for_function("!document.querySelector('#dashboard').hidden")
            assert page.locator(".book-card").first.locator(".book-stat b").first.inner_text() == "3"
            assert errors == []
        finally:
            context.close()


@pytest.mark.browser
def test_only_complete_valid_quiz_history_counts_toward_attempts_and_accuracy(browser):
    history = [
        {"mode": "practice", "ch": "الكل", "c": 4, "n": 5, "t": 100},
        {"mode": "exam", "ch": "الفصل الأول", "c": 3, "n": 5, "t": 200},
        # Timestamp was not part of every earlier saved record; it is not needed for these totals.
        {"mode": "practice", "ch": "الكل", "c": 1, "n": 2},
        None,
        [],
        {},
        {"ch": "الكل", "c": 4, "n": 5, "t": 300},  # missing mode
        {"mode": "practice", "c": 4, "n": 5, "t": 300},  # missing chapter
        {"mode": "practice", "ch": "الكل", "n": 5, "t": 300},  # missing correct count
        {"mode": "practice", "ch": "الكل", "c": 4, "t": 300},  # missing total count
        {"mode": "practice", "ch": "الكل", "c": "4", "n": 5, "t": 300},
        {"mode": "practice", "ch": "الكل", "c": 6, "n": 5, "t": 300},
        {"mode": "practice", "ch": "الكل", "c": -1, "n": 5, "t": 300},
        {"mode": "practice", "ch": "الكل", "c": 1, "n": 0, "t": 300},
        {"mode": "practice", "ch": "الكل", "c": 1.5, "n": 5, "t": 300},
        {"mode": "practice", "ch": "الكل", "c": 2, "n": 5, "t": "300"},
        {"mode": "other", "ch": "الكل", "c": 2, "n": 5, "t": 300},
        {"mode": "practice", "ch": "   ", "c": 2, "n": 5, "t": 300},
    ]
    with serve_repo() as base_url:
        context, page, errors = open_portal(
            browser, base_url, session("account-a", "a@example.test", "token-a", "refresh-a")
        )
        try:
            wait_for_requests(page, 1)
            resolve_request(page, 0, [{
                "course": "madkhal-fiqh-v1",
                "state": {"quizHist": history},
            }])
            page.wait_for_function("!document.querySelector('#dashboard').hidden")

            metrics = page.locator(".book-card").first.locator(".book-stat b")
            assert metrics.nth(2).inner_text() == "3"
            assert "دقة الإجابات: 67%" in page.locator(".book-card").first.inner_text()
            summary = page.locator("#summary-grid").inner_text()
            assert "3" in summary
            assert "67%" in summary
            assert errors == []
        finally:
            context.close()
