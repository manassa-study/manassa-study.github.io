# Runbook: rolling back a book

Use when a merged change broke a published book page. GitHub Pages serves
whatever is on `main`, so a rollback is a normal pull request that restores the
previous page and its sources.

1. Find the last good commit: `git log --oneline -- <output path>` (for the pilot,
   `mantiq/MunazaraRashidiyaAQU.html`). The Phase 0 baseline is `de019d2`; the
   preservation package also holds every baseline page.
2. On a new branch, restore the page **and** everything it was built from at that
   commit:
   `git checkout <good> -- <output path> books/<slug>/ platform/templates/`
3. Lock caution: `ids.lock.json` only grows. If the bad change added IDs or
   retired some, do **not** restore an older lock (CI's `id-invariants` would
   fail, and IDs could be reused). Keep the current lock and, if needed, record
   decisions with `ids review`/`ids apply` so the restored content binds.
4. `python3 tools/build.py check <slug>` must pass (the restored page equals a
   fresh build from the restored sources). `--baseline-data` also passes when
   rolling back to the baseline.
5. Open a pull request saying what is rolled back and why; urgent fixes still go
   through a pull request approved by Bilal (freeze rule).
6. After merging, confirm the live page's SHA-256 equals the restored file's and
   that a saved progress state still loads (the browser test
   `test_saved_progress_from_the_live_page_loads_unchanged` uses the same check).

## Rolling back one step-2 change

The template keeps the step-1 text for every step-2 change, so a single change
can be undone without restoring old files: remove its id from
`features.step2` in the book's `book.json`, run
`python3 tools/build.py build <slug>`, and open a pull request with the
regenerated page. With no id left, the pilot builds to the Phase 1 baseline
byte for byte (`tests/integration/test_step2.py`). The golden page
`tests/golden/MunazaraRashidiyaAQU.step2.html` and the expected diffs in that
test are updated in the same pull request.

Student progress is safe in a rollback as long as the storage key and the IDs
are unchanged, which the build enforces.
