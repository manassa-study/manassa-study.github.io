# Phase 3 Book 2 migration progress

**Target:** التخريج ودراسة الأسانيد
**Published page:** `hadith/TakhreejAsaneedAQU.html`
**Branch:** `codex/phase3-book2-takhreej`
**Boundary:** no merge, deployment, or Supabase changes.

| Work item | Status | Evidence / next step |
| --- | --- | --- |
| Verify uploaded ZIP and Git checkout | Done | `.git` present; clean checkout at `32aef51`; branch created from `main`. |
| Establish immutable payload baseline | Done | Page SHA-256 `3d96dae58c31fd3ad7b41e2375c4df5a979dae4176f098367858f35a1e34ab80`; extract SHA-256 `3e4f61186fa0df8dbc3c91951f997afb397efb174636c78e678f3e8090ba1f96`. |
| Reconstruct structured source from verified page extract | Done | Round-trips to the fixture exactly; 2 chapters, 12 examples, 163 cards, 13 tables, 7 maps, 249 questions, 4 capsules. |
| Configure book and preserve runtime invariants | Done | URL, storage key and deferred report script position preserved; generated page is byte-identical to baseline. |
| Generate ID lock from baseline | Done | CLI bootstrap from `32aef51`; all live IDs and option orders retained. |
| Build, reproducibility, tests, browser checks | Done with browser limit | 371 unit/integration/failure tests passed; all-book build check and two-copy reproducibility passed. Browser tests remain blocked: Playwright startup stalls before launching Chrome under both Python 3.15 and an isolated Python 3.12 environment. The repository-pinned Windows dependency hashes also omit a compatible Greenlet wheel, so no project lock was changed. |
| Review migration diff | Done | Empty outside-data diff and empty data diff; report at `docs/migrations/takhreej-asaneed.md`. No merge or deployment. |

## Reconstruction checks observed

- `tests/fixtures/extracts/TakhreejAsaneedAQU.data.json` has the same SHA-256 recorded in `tests/integration/test_ids_extracts.py`.
- The embedded `const D` payload and fixture were previously verified equal; local page payload SHA and fixture hash are recorded above.
- Quiz labels are `اختيار من متعدد`, `الرمز ودلالته`, `الكتاب ومؤلفه`, and `صح أو خطأ`.
- The two quiz chapters have first-page ranges 7–132 and 137–203; a threshold at printed page 134 matches every quiz item's chapter label.
