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
