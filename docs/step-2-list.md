# Step-2 list for the pilot (approved, decision N3)

Approved by Bilal on 27 November 2026, with S2-3 (O-5) included for the pilot.

Step 1 (Phase 1) changed no published byte. Step 2 is the list of deliberate
changes to the pilot page, each approved by Bilal before Phase 2 starts, each in
its own commit with its own diff and test. Anything not on the approved list
must not change.

| # | Change | Why | Test that comes with it |
| --- | --- | --- | --- |
| S2-1 | `<html lang="ar" dir="rtl">` instead of a bare `<html>` (today the page sets them from a script) | Correct language and direction before scripts run: screen readers, search engines, first paint | V8 switches from "opening equals the baseline" to "lang and dir required"; golden file updated in the same PR; browser smoke test |
| S2-2 | Template version tag `<meta name="mudhakarah:template" content="…">` (R2) | Shows which template built a live page | Lint test that the tag is present and matches the tool version |
| S2-3 | O-5: the book-specific words in the app script (storage key, welcome key, example labels, search suggestions) move into one config object at the top of the script | One place for book values; makes the next book's migration simpler | Golden diff limited to the script head; browser tests for search suggestions, welcome popup and saved progress |

Not on the list (they don't change output and are already in step 1): locked
IDs and the option-order lock (design A).

Decided on approval: S2-3 is done in the pilot (O-5).
