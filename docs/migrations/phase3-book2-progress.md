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

## Owner decision evidence — accepted 2026-11-27

The owner accepted proposed decisions 1–5 in the “Proposed Book 2 Owner Decisions” record in the associated chat on 2026-11-27. This section records that acceptance as evidence only. Per `docs/README.md`, the Phase 1 Architecture Specification, Master Plan, and Decision Register remain external governing documents; this progress record does not replace or amend them. Their current versions and statuses remain unverified.

1. **Sequence and scope:** Book 2 is designated as the next Phase 3 migration in this review sequence. PR #16 scope is the Book 2 source reconstruction and supporting configuration, ID lock, page-reference record, tests, and rendering support needed to reproduce the preserved page. This does not assert or amend the unavailable Master Plan, approve academic content, or approve PR #16 for merge.
2. **Rendering:** `example_ayah_plain` and `author_first_segment` are accepted for Book 2 only to reproduce the preserved page. This is not a general authorization for rendering flags on other books.
3. **ID bootstrap:** `--allow-reconstructed-option-order` is accepted solely for the one-time initial capture of Book 2's displayed option order from the preserved baseline, recorded as `captured-from-baseline`. No future bootstrap, lock update, book, or migration bypass is authorized. O-8 is reconfirmed as stated by the repository runbook: “Until Bilal names someone else in writing, Bilal approves every lock change; merging the pull request is the approval, and each `changes` entry records the approver and the pull request.” This entry is not approval of the lock change for merge.
4. **Content/PR sign-off:** O-10 is reconfirmed as stated by the repository runbook: “Sign-off follows decision O-10 (decided 27 November 2026): Bilal's approval of the pull request that references the content-change report is the sign-off, until he names subject reviewers in writing.” This confirms the process only; it does not approve academic content, submit a GitHub review, approve PR #16, or authorize merging it.
5. **Preservation and page references:** Existing Book 2 content and displayed page output are to be preserved. Only the two existing page-reference exceptions may be carried forward as documented and unreviewed. No page references may be inferred or added under this decision. Their carry-forward is not academic verification.
