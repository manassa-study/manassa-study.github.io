# Runbook: onboarding a book

Use this procedure for a newly authorized book. Adding a book is routine repository work; it does not reopen Phase 3 or change the content of existing books.

## 1. Confirm identity and source

- Record the approved Arabic title, stable slug, scope, and source repository/path.
- Pin the source commit or immutable release. Record the exact page/file path and SHA-256.
- Distinguish an original source text from a rendered page, a derived payload extract, and supplementary study material. State what each file represents.
- If the source, scope, or provenance is uncertain, stop for clarification. Do not infer academic content or page references.

## 2. Prepare the baseline

Create a concise record under `docs/migrations/` with the source identity, pinned revision, file hashes, payload/fixture hashes, extraction method, counts, and known limitations. Keep an immutable fixture under `tests/fixtures/` when it is needed to verify a rendered payload. Add a fail-closed preservation check when the source is external or exact payload identity needs a guard.

Do not normalize or rewrite academic content to satisfy a check. Baseline mismatches require investigation and review.

## 3. Add the book using the existing layout

Create `books/<slug>/` with:

- `book.json`: title, slug, output path, storage key, content loader and book-specific settings.
- `content/`: structured source data used by the existing renderer.
- `ids.lock.json`: IDs and any captured ordering invariants.
- `README.md`: source edition/provenance, page numbering, reviewers, published path, and links to baseline and exceptions.
- `page-references.json` only when inherited or reviewed exceptions actually exist.

There is no separate central book registry: the build discovers book directories containing `book.json`. Do not edit generated published HTML by hand. The output path must remain within the current platform allow-list in `tools/mudhakarah/config.py`; a new publication path needs a separately reviewed platform change.

## 4. Store supplementary resources without confusing their role

When book-associated study materials exist, place repository-owned copies under the optional `books/<slug>/resources/` directory. Index each item in that book's `README.md` with its title, type (mind map, PDF summary, note, etc.), canonical source URL/repository and revision, file hash, and any known rights or review status.

Do not copy a file that already has a suitable canonical home. Link to that source and record its revision/hash instead. Keep supplementary materials distinct from original source texts, migration baselines, renderer content, fixtures, and generated pages. The `books/` tree is not published by Jekyll.

## 5. IDs, references, and tests

- Bootstrap IDs only from the verified baseline, then review the lock. Preserve IDs and displayed option order. Follow [the ID-change approval runbook](approving-id-changes.md) for any intentional change.
- Preserve existing page references. Never invent a page number. Record a genuine exception with a reason and obtain review before marking it reviewed.
- Add or extend `tests/integration/test_<slug>.py`, `tests/browser/test_<slug>_page.py`, and fixtures only as needed for the book's content and behavior. Keep test material under `tests/`, not in published folders.

## 6. Build, validate, and review

From a clean branch, run:

```sh
python3 tools/build.py build <slug>
python3 tools/build.py check --all --baseline-data
python3 tools/check_reproducible.py
python3 -m pytest
```

Run the book's browser coverage and review the generated page at desktop and mobile widths. Review the ID invariants, baseline guard, page-reference warnings, all content/option ordering, generated output, and cross-book results. Fix implementation defects without weakening guards or changing academic material.

Open a PR with the baseline/provenance record, content-change report, validation evidence, and any remaining exceptions. Required main-branch checks are `test`, `build-check`, `reproducibility`, `id-invariants`, and `browser`. Do not push directly to `main`, force-push, or modify Supabase. Merge only after source integrity, academic preservation, output review, and required checks pass; then verify the GitHub Pages deployment and live page.
