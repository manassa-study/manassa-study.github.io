# Runbook: the signed-in Supabase sync check (R5)

**Status: not run.** R5 (master plan, reconciliation choices) says the check runs only with
Bilal's approval of the account and of the check. It is a manual check on the live page
(master plan, section H: "Supabase sync | A test account's row loads and saves unchanged |
Manual signed-in check").

No automated test or CI job contacts Supabase, and none should. This runbook uses only the
live page, a test account, and read-only viewing of that account's own row.

## Why it matters

Each book saves the student's progress in the browser under its storage key (for the pilot,
`munazara-rashidiya-v1`). A signed-in student's progress is also kept in the Supabase
`progress` table, one row per student and course, with `course` equal to the storage key.
Phase 2 changed where the app script reads the storage key (S2-3). The key's value did not
change, and the browser tests check local saving. Only a signed-in check shows that the
account copy still loads and saves.

## What you need

- A **test account** that is not a student's: a Google account or email address used only for
  testing. Best case: an account that already saved progress on this book **before** Phase 2
  (before 27 November 2026, 08:17 Dubai time). Then you can check that the old row still loads.
- Two browsers or devices, for example a phone and a private window on a computer.
- Optional, for step 6: read-only access to the Supabase dashboard's table editor.

Do not change RLS policies, tables, auth settings or other users' rows during this check.

## Steps

Page: `https://manassa-study.github.io/mantiq/MunazaraRashidiyaAQU.html`

| # | Do | Expected |
| --- | --- | --- |
| 1 | In browser A, open the page, open the account dialog (person icon), sign in with the test account | "مسجّل الدخول ✓" with the test email; then "حُفظ تقدّمك في حسابك ✓" |
| 2 | If the account had progress from before Phase 2: open the account dialog | The counts (lessons done, cards mastered, quizzes) match what it had before |
| 3 | Mark one lesson done, mark one card mastered, finish a 10-question practice quiz; wait 3 seconds | The account dialog counts go up; the message says "حُفظ تقدّمك في حسابك ✓" |
| 4 | In browser B (private window or another device), open the page and sign in with the same account | The same counts appear as in browser A after step 3 |
| 5 | In browser B, switch off the network (airplane mode), mark another lesson done, then reconnect and mark one more | While offline, progress stays on the device, and the page says "تعذّر حفظ التقدّم في حسابك الآن، وهو محفوظ على هذا الجهاز." if a save was tried. After reconnecting and the next action, "حُفظ تقدّمك في حسابك ✓" |
| 6 | Optional: in the Supabase dashboard, look (read only) at the `progress` rows for the test account | One row with `course` = `munazara-rashidiya-v1`; its `state` holds the same `done` and `mastered` entries |
| 7 | Sign out in both browsers | Progress made on each device stays on that device |
| 8 | Optional clean-up: sign in, use "مسح تقدّمي في هذا المقرر" in the account dialog | The test account's progress is reset, on the device and in the account |

## Record

| Step | Result (pass, fail, not done) | Note |
| --- | --- | --- |
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | | |

Checked by: ______  Date: ______  Test account (not a student's): ______

## If a step fails

Do not change Supabase settings to make it pass. Record what you saw, the time, and the
browser. A failed step 2 or 4 means the account copy does not load as before. Roll the pilot
back by removing `S2-3` from `features.step2` (see `rolling-back-a-book.md`) while the cause is
found, because S2-3 is the only Phase 2 change that touches the storage key's code.
