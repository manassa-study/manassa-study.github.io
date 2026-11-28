# Phase 3 closure and operational handover

**Prepared:** 28 November 2026  
**Status:** Operationally closed for the four migrations listed below. This record uses repository and GitHub evidence plus the owner's present closure instruction. It does not recover, replace, or claim authority from the missing original Phase 1 specification, approved Master Plan, or Decision Register.

## Completed migrations

| # | Book | Merge PR and commit | Main CI | GitHub Pages deployment | Preservation and migration record |
| --- | --- | --- | --- | --- | --- |
| 1 | المدخل إلى الفقه الإسلامي | [PR #12](https://github.com/manassa-study/manassa-study.github.io/pull/12), `32aef51b48e2a2ddd058e99006951b9c7d4881c2` | [Run #14: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/45952274515) | [Pages run #13: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/45952274208) | [Migration report](migrations/madkhal-fiqh.md): generated page matched the preserved page byte for byte (SHA-256 `725d5d1f419527abdf8d006cf7e1b1c786020f6ac1076167b9993d2b7adca3ec`). |
| 2 | التخريج ودراسة الأسانيد | [PR #16](https://github.com/manassa-study/manassa-study.github.io/pull/16), `7dc5deb57dccd4f73f65c283a44d8cf1666a474a` | [Run #21: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/46033062186) | [Pages run #14: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/46033060954) | [Migration report](migrations/takhreej-asaneed.md): payload/fixture identity, ID lock, and reproducibility recorded; two unreviewed page-reference exceptions remain. The report's local browser-run limitation was superseded by the successful required browser CI job. |
| 3 | تاريخ التفسير | [PR #17](https://github.com/manassa-study/manassa-study.github.io/pull/17), `6ce433fbc61169774377dfa96e5baf2e961083c0` | [Run #24: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/46037781558) | [Pages run #15: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/46037781194) | [Book 3 preservation record](../books/tareekh-tafseer/README.md) and [page-reference exceptions](../books/tareekh-tafseer/page-references.json): the baseline payload, IDs, option order, and reproducible output were recorded; two unreviewed page-reference exceptions remain. The successful main CI run includes the required browser job. |
| 4 | التفسير المقارن | [PR #18](https://github.com/manassa-study/manassa-study.github.io/pull/18), `8487b21facec6aab82ad4e9ba25edc81553d99fb` | [Run #29: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/46054549139) | [Pages run #16: success](https://github.com/manassa-study/manassa-study.github.io/actions/runs/46054548499) | [Pinned baseline](phase3-book4-baseline.json) and [preparation record](phase3-book4-preparation.md) preserve source/fixture hashes and exact payload identity; PR #18 records the 44-question ID/order lock and special-block, map, and drill support. Forty-five unreviewed page-reference exceptions remain. |

The successful main CI run for each merge reported the required `test`, `build-check`, `reproducibility`, `id-invariants`, and `browser` jobs. The final main run is the evidence for the complete four-book state. Source reports remain useful evidence of each migration's baseline and implementation decisions; their old pre-merge status lines are explicitly superseded by this record.

## Outstanding items

- The original Phase 1 architecture specification, approved Master Plan, and Decision Register remain outside this repository and were not recovered during closure. This record does not infer historical scope beyond the four completed migrations.
- Academic review of inherited page-reference exceptions remains outstanding: 2 for Book 2, 2 for Book 3, and 45 for Book 4. These stay unreviewed; no references were invented. No page-reference exception file exists for Book 1.
- PR [#13](https://github.com/manassa-study/manassa-study.github.io/pull/13) remains open for the separate R5 manual sync-verification record. It records a user-confirmed core manual check; optional read-only row inspection was not done. It is an operational follow-up, not a blocker to closing the four book migrations. No Supabase operation was performed for this handover.
- PRs #14 and #15 are closed as superseded by the completed Book 2 migration in PR #16. Their baseline-preparation work is represented in the merged Book 2 migration report, source fixture checks, and ID lock.

## Ongoing operations

Phase 3 no longer needs to be restarted for another book:

**Future book → [standard onboarding procedure](runbooks/adding-a-book.md) → validation → review → PR merge and GitHub Pages deployment.**

No fifth book was selected or migrated in this closure. The dirty Book 3 checkout was left untouched.
