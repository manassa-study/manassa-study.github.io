# Migration report: المدخل إلى الفقه الإسلامي (Phase 3, book 1)

> **Current status (28 November 2026):** المدخل إلى الفقه الإسلامي was merged in [PR #12](https://github.com/manassa-study/manassa-study.github.io/pull/12) at `32aef51b48e2a2ddd058e99006951b9c7d4881c2`. The pre-merge status and next-step statements below are historical; see [the Phase 3 closure record](../phase3-closure-handover.md) for current status.

Status: built and tested on `claude/project-thread-jkwb0r`. **Not merged.** Merging changes
no published byte of this page (it builds to the same file), but it moves the page under the
build: from then on the page is generated, and hand edits are refused by `build-check`.

Order and scope come from the master plan, section I: book 1 of four, "Pilot signed off",
expected difference from live "None", main risk "chapter names come from page thresholds in
build.py; they move to book.json".

## Result

| | Live page (baseline de019d2) | Build from `books/madkhal-fiqh/` |
| --- | --- | --- |
| SHA-256 | `725d5d1f419527abdf8d006cf7e1b1c786020f6ac1076167b9993d2b7adca3ec` | the same |
| Data line | Phase 0 extract `MadkhalFiqhAQU.data.json` | equal, byte for byte |

The live page has not changed since the baseline (`git log` shows its last change in #8, before
de019d2).

## What was needed

| Difference from the pilot | How it is handled |
| --- | --- |
| No `topic` on cards and questions | `content.anchor: "chapter"` (O-3, decision pending, see below). The lock records the fields as `["chapter", "q"]` and `["chapter", "type_key", …]`, and each entry's `chapter` |
| Quiz chapter names from page thresholds | `from_page` on chapters 2 to 4 (51, 105, 143), the thresholds in the legacy `build.py`. Questions in the page carry no `topic` key, as live |
| Question type «الأعلام والآراء» | Added to the type registry as `figures-views` (options shape) |
| The welcome screen's dedication card | A feature block: `features.dedication_card` and `dedication.teacher` in book.json. The fixed wording stays in the template (التخريج ودراسة الأسانيد has the same card with another teacher) |
| `attach()` without the pilot's topic patch | A feature block, `item_topics`, which follows `content.anchor` |
| Section symbols (`S_T1` …) defined by the content files | No longer reported as unmapped when they are already inside a mapped chapter |

Every other value is in `books/madkhal-fiqh/book.json`, copied from the legacy `build.py`
replacement lists. The content files are copied unchanged from the preservation package.

## ID lock

Bootstrapped from the live page at de019d2: 186 cards, 181 questions, 31 topics, 7 maps. Every
card and question keeps its live ID, and every question keeps its live option order. No
fingerprint collides. Moving an item to another chapter stops the build for review (tested).

## Not changed

No published file changes. The pilot page builds to the same bytes as on `main`, and the
other books are untouched. No content, wording, IDs, storage keys, URLs, design or fonts change.
No step-2 change (S2-1, S2-2, S2-3) is switched on for this book: the approved step-2 list
was for the pilot. Turning them on for this book needs its own approval.

## Validation

| Check | Result |
| --- | --- |
| Test suite (unit, integration, failure conditions, browser) | 392 passed |
| `build.py check --all --baseline-data` | OK for both books (pilot: the 43 unreviewed page-reference exceptions warning, unchanged) |
| `check_reproducible.py` | reproducible, both books |
| `ids invariants` | Fiqh: first lock, self-check holds; pilot: holds against `main` |
| Served site (Jekyll) | the same files as `main` (only the pilot page differs from the Phase 0 baseline, from Phase 2) |

Browser tests for this book: every route opens with no error, Supabase is never reached, the
welcome screen shows the dedication card, quiz chapters are the four chapters, a practice quiz
saves under `madkhal-fiqh-v1`, cards and examples get their topics in the app, and 360 and
390 px in light and dark have no sideways scroll.

## Needs Bilal

- **O-3** for this book: chapter anchor (recommended, implemented here), topics added to the
  content, or no anchor. The pull request waits for this choice.
- Merging.
- Optionally, whether to switch on S2-1, S2-2 and S2-3 for this book in a later pull request.
