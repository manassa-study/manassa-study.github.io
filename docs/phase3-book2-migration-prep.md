# Phase 3 Book 2 — Migration package preparation

**Book:** التخريج ودراسة الأسانيد (legacy title: أصول التخريج ودراسة الأسانيد)
**Target page:** `hadith/TakhreejAsaneedAQU.html`
**Status:** Preparation findings only; not a build-ready migration package.

## Confirmed baseline facts

- Embedded `const D` and the extract fixture are equal at parsed JSON level (verified in the baseline report).
- Source fixture: `tests/fixtures/extracts/TakhreejAsaneedAQU.data.json`.
- Payload inventory: 2 deep-study chapters, 12 examples, 163 flashcards, 13 tables, 7 mind maps, 249 quiz items, 4 capsules.
- Existing progress key: `takhreej-asaneed-v1` (must be preserved).
- Published path: `hadith/TakhreejAsaneedAQU.html` (must be preserved).
- Legacy script/style ordering: the deferred `report.js` script follows the expand/collapse CSS block. This relative placement is a migration invariant.

## Step 3 investigation findings

The shared book system supports the Python content loader, configurable chapter mapping, quiz configuration, output path, storage key, and the ID lock. However, the verified fixture is a *rendered payload extract*, not yet the book's original structured source files. The content-loader schema expects source symbols (metadata, cards, questions, examples, tables, maps, capsules and chapter objects) and the ID lock bootstrap depends on a real assembled raw-source model.

A direct transformation from the rendered fixture into source modules would require reconstructing source-option ordering, chapter mapping and raw content conventions. That reconstruction must be generated and validated using the repository's executable tooling, not guessed or hand-authored through this API-only environment.

## Safe next actions / blockers

1. Obtain an executable working checkout and run the project's extraction/assembly helpers against the fixture and legacy page.
2. Reconstruct source modules mechanically and retain the fixture hash / payload equality as a guard.
3. Configure the book with the exact output path and storage key, preserving the legacy report-script placement invariant.
4. Generate the ID lock using the official `tools/build.py ids bootstrap` workflow against the actual baseline commit and page.
5. Run `build.py check`, reproducibility checks, the suite, and browser comparison; review the diff before proposing a migration PR.

## Not performed

- No source modules or book configuration were fabricated.
- No ID lock was generated or manually assigned.
- No published page was changed.
- No content was edited or normalized.
- No Supabase action, merge, or deployment was performed.

**Environment limitation:** repository API access is available for inspection and branch/document creation, but this session's container cannot resolve GitHub to clone the repository or execute its project tooling. Therefore Step 3 cannot be safely completed to build-ready status in this environment.


## Concrete migration execution checklist (next working environment)

This checklist is deliberately executable-order oriented. It does not authorize content edits or deployment.

1. **Checkout and establish identity:** checkout `phase3-book2-migration-prep`; confirm `git status` is clean, record the baseline commit and page SHA-256, and verify fixture SHA-256 against `tests/integration/test_ids_extracts.py`.
2. **Inspect preservation/source conventions:** inspect `books/madkhal-fiqh/content/`, its `book.json`, and `tools/mudhakarah/loaders.py`; identify the required raw symbol conventions. Do not use the fixture as a substitute for an original manuscript/content source.
3. **Mechanical reconstruction:** write a temporary extraction/reconstruction script outside committed source first. Convert the fixture to raw source with quiz answers represented as source correct-answer plus wrong-answer slots, preserving display order; for true/false use the repository's exact convention. Derive chapter mapping from the page's question chapter names, and validate every item maps exactly once.
4. **Run helper tests:** use `register_extract_types`, `raw_from_extract`, and `extract_lock` only as test helpers to check payload shape and collision behavior—not as a production migration shortcut. Confirm the source model assembles back to the exact fixture data.
5. **Book config and content files:** only after those checks, author the book config and structured content modules following the real loader schema. Preserve title/description, output, storage key, welcome key, labels, theme, and special script placement.
6. **ID bootstrap:** use the repository's CLI against the actual baseline page/commit, never manually author IDs or lock JSON. Verify bootstrap invariants and question option order.
7. **Build and equivalence:** run `python3 tools/build.py check takhreej-asaneed`, diff output, data-line identity and reproducibility checks. Expected page difference must be zero unless an explicitly approved migration difference is documented.
8. **Tests:** run unit, integration, failure-condition and browser tests; exercise route navigation, card review, quiz modes, progress persistence key, theme/preferences, registration/welcome gates, and responsive RTL layouts.
9. **Review boundary:** create a PR only with reproducible evidence, migration report and clearly scoped files. Do not merge or deploy without explicit approval.

### Specific reconstruction risks to watch

- Quiz type labels and their registry keys must be supported; do not invent type mappings.
- Correct-answer source slots and option order must preserve the rendered answer order and correct index.
- Chapter names are embedded in the rendered quiz bank and must be mapped without silently reclassifying questions.
- Cards/questions may have no explicit topic; anchor/fingerprint policy must be selected according to the governing decisions and confirmed against the actual model.
- Exact equality of the data payload is necessary but not sufficient: script ordering, runtime interactions, and browser equivalence remain unverified.
