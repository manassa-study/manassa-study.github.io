# Phase 3 Book 2 — Source Baseline Verification

**Book:** التخريج ودراسة الأسانيد (published page title: أصول التخريج ودراسة الأسانيد)  
**Published path:** `hadith/TakhreejAsaneedAQU.html`  
**Baseline commit:** `32aef51b48e2a2ddd058e99006951b9c7d4881c2`  
**Verification method:** Read-only GitHub repository inspection; no page, data, database, or deployment changes.

## 1. Exact embedded-data / fixture comparison

The page's embedded `const D` payload was extracted from the HTML and parsed as JSON. It was compared with `tests/fixtures/extracts/TakhreejAsaneedAQU.data.json`.

- JSON parsing: **PASS**
- Parsed JSON equality (all keys, values, ordering as represented by JSON): **PASS**
- Payload size: **224,852 characters in both sources**
- The embedded payload and fixture are identical at the parsed JSON level.

Payload keys:
- `BOOK_METADATA`
- `DEEP_STUDY_DATA`
- `QURANIC_EXAMPLES`
- `FLASHCARDS`
- `COMPARISON_TABLES`
- `MIND_MAPS`
- `QUIZ_BANK`
- `CAPSULES`

Counts:
- Deep study chapters: 2
- Quranic examples: 12
- Flashcards: 163
- Comparison tables: 13
- Mind maps: 7
- Quiz bank entries: 249
- Capsules: 4

**Conclusion:** The existing extraction fixture is verified against the current page's embedded data payload and is a strong candidate for the migration source. This comparison does not by itself prove that the full rendered page or interactive behavior is equivalent.

## 2. Progress key

The page uses the existing local storage key:

`takhreej-asaneed-v1`

This key is a migration invariant. Do not change it.

## 3. Script/style placement invariant

The legacy page ends with the expand/collapse CSS block and then:

`<script src="https://manassa-study.github.io/report.js" defer></script>`

The generated page must preserve the report script's position relative to the legacy expand/collapse styling block, as specified for this migration.

## 4. Migration boundary

- Preserve the published path: `hadith/TakhreejAsaneedAQU.html`.
- Preserve all source data, order, identifiers, and study behavior.
- No academic content editing or normalization as part of technical migration.
- No Supabase schema/data/settings changes.
- No merge or deployment authorization is implied by this baseline document.

## 5. Next verification gates

Before generated output is ready for PR:
1. Create/verify book config and structured source package from the verified fixture.
2. Establish and review the ID lock against the live page.
3. Validate output path, storage key, and script/style ordering.
4. Run build check, reproducibility, ID invariants, content integrity, CI and browser tests.
5. Review any difference report and resolve all unexplained changes.

## 6. Verification limitation

This was a repository-side read-only inspection using GitHub file content. No local build, browser session, live student interaction, or runtime test was performed as part of this baseline verification.
