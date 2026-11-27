# Phase 3 Book 4 preparation — التفسير المقارن

**Status:** baseline and extraction guard prepared. No academic content was migrated or edited.

## Preservation baseline

- Source repository: [manassa-study/Tafseer](https://github.com/manassa-study/Tafseer)
- Source commit: [fbbbae5b51e526d6f5e27e3f6dac7d8fdf22f6b2](https://github.com/manassa-study/Tafseer/commit/fbbbae5b51e526d6f5e27e3f6dac7d8fdf22f6b2)
- Source page: TafseerMaqaranAQU.html
- Source-page SHA-256: 18cffb3b449490d3c8613411a2db2ef945244da98bc2ea49147fa287e81f9b27
- Phase 0 extract: tests/fixtures/extracts/TafseerMaqaranAQU.data.json
- Extract SHA-256: 412786e767e5ca520af023965f9cd368aad7d320461cd0a5bc0310a284986b81
- The page payload was compared with the parsed Phase 0 extract; every top-level section matched.

## Scope captured

Published path Tafseer/TafseerMaqaranAQU.html; storage key tafsir-muqaran-v1.

| Data section | Items |
| --- | ---: |
| DEEP_STUDY_DATA | 2 |
| QURANIC_EXAMPLES | 28 |
| FLASHCARDS | 26 |
| COMPARISON_TABLES | 13 |
| MIND_MAPS | 7 |
| QUIZ_BANK | 44 |
| CAPSULES | 4 |
| DRILL | 12 |

The existing extraction tests note explicit question IDs with gaps. Any migration must preserve those IDs. The template inventory identifies Book 4 as the most structurally distinct title and recommends migrating it last.

## Preservation guard

tools/check_book4_baseline.py verifies the source checkout commit, source-page hash, fixture hash, exact parsed payload identity, and recorded section counts. CI runs it in build-check, using the existing read-only checkout of manassa-study/Tafseer at the pinned commit.

This only establishes and checks the baseline. Content conversion, Book 4 book.json/ID-lock bootstrapping, review, merge, deployment, publication, and database changes remain outside this preparation.
