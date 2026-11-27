# Migration report: المناظرة الرشيدية (pilot, Phase 2)

Status: built and tested on `claude/project-thread-jkwb0r`. **Not published.** The page
goes live only when Bilal approves and merges the pull request.

## What changed on the published page

Only the three approved step-2 changes (`docs/step-2-list.md`, decision N3). Each is a switch in
`books/munazara-rashidiya/book.json` (`features.step2`), made in its own commit with its own test.

| Change | Commit | What the page gets | Size |
| --- | --- | --- | --- |
| S2-1 | P2-2 | `<html lang="ar" dir="rtl">` instead of a bare `<html>` | +20 bytes |
| S2-2 | P2-3 | `<meta name="mudhakarah:template" content="1.1.0">` after the viewport tag | +49 bytes |
| S2-3 | P2-4 | `const BOOK={…}` as the app script's first line; 8 lines read their book words from it | +355 bytes |

| | Baseline (de019d2) | Phase 2 build |
| --- | --- | --- |
| SHA-256 | `a91018ea392c1b39d8af7583f18d792e9f3467e63e4c91c13183545ce016aaf3` | `6dd0eff79b15fd2f7b72ae26fdde072c123c633861086275f5a27ca2a938085d` |
| Bytes | 408,561 | 408,985 |
| Lines | 1,569 | 1,570 |

The exact before and after text of every change is written out in
`tests/integration/test_step2.py`, which checks that the page differs from the baseline by
those replacements and nothing else.

## What did not change

- **Data line** (line 717, `const D = …;`): identical to the baseline, so every lesson, quotation,
  reference, card, question and option order is unchanged. CI still runs
  `check --all --baseline-data`, which enforces this.
- **IDs and student progress:** the storage key `munazara-rashidiya-v1`, the welcome key, and all
  IDs (169 cards, 177 questions, 27 topics, 8 maps) are unchanged; `ids invariants` holds against
  `main`. The saved-progress fixture from the live page loads unchanged (browser test).
- **Everything else in the site:** a Jekyll build of the branch serves the same 18 files as the
  baseline, except this one page.
- **Not on the approved list, so left as they are:** the inline head script that also sets `dir`
  and `lang` (and reads the theme from the storage key), the title, structure summary and review
  subtitle in the app script.

## Validation

| Check | Result |
| --- | --- |
| Test suite (unit, integration, failure conditions, browser) | 363 passed |
| `build.py check --all --baseline-data` | OK (one warning: 43 unreviewed page-reference exceptions, unchanged since Phase 1) |
| `check_reproducible.py` (two clean builds) | reproducible |
| `ids invariants` against `origin/main` | hold |
| Served site (Jekyll) | only `mantiq/MunazaraRashidiyaAQU.html` differs |
| Screenshots, baseline vs build (8 routes, search, welcome popup; 360 and 1280 px; light and dark) | 37 screens pixel-identical. The 1280 px home screen also varies between two runs of the baseline itself, so it is not a reliable comparison on its own. |

New tests in Phase 2: the step-2 switch schema, V8's opening rule per switch, the expected diff
of each change alone and together, template lint for the switch statements, the template
version tag, the app config object's contents and refusals, and browser tests for language and
direction with JavaScript off, search suggestions, the welcome popup, progress saved under the
storage key, and the book words a student sees (baseline and build compared).

CI: the `browser` job is now blocking (it was advisory in Phase 1). Making it a required check
on `main` is a repository setting (O-12) that only Bilal can turn on.

## Rollback

Remove an id from `features.step2` and rebuild; with none left the page is the baseline byte for
byte. See `docs/runbooks/rolling-back-a-book.md`.

## Not done here (needs Bilal)

- Merging and publishing this page.
- The signed-in Supabase sync check with a test account (R5): not run; no network or Supabase
  access was used by any test.
- Required checks on `main` (O-12).
