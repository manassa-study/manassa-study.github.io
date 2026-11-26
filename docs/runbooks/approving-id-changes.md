# Runbook: approving ID changes

Student progress (mastered cards, wrong-answer bank) points at card and question
IDs. The build never guesses an ID: anything it can't match with certainty stops
it. This runbook is how a person decides. Rules: Architecture Specification,
section 6. Normalization: [normalization.md](../normalization.md).

Who approves: decision O-8. Until Bilal names someone else in writing, Bilal
approves every lock change; merging the pull request is the approval, and each
`changes` entry records the approver and the pull request.

## Steps

1. `python3 tools/build.py ids review <slug>` writes a proposal file outside the
   repository (or `--out FILE`) and prints how many cases there are.
2. Open the proposal. Each case has a `kind`, the item(s) and, where helpful,
   the old item from the published page and suggested pairings (best first).
   Set `decision` and a `reason` for every case:

   | Kind | Decisions | Meaning |
   | --- | --- | --- |
   | `unbound` (a content item matches no ID) | `same` + `same_as: <ID>`, or `new` | Same item reworded, or a genuinely new item (gets `next_id`) |
   | `missing` (an ID matches no content item) | `same` (paired from an unbound case), or `retire` | Retired IDs are never issued again |
   | `retired-match` | `restore` or `new` | A removed item came back |
   | `duplicate` | `group` + `ids: [ID or null, …]` | Two identical items told apart by their order |
   | `new-topic` | `new` | Topic IDs can never be renamed or removed |
   | `reordered-options` (F4) | `keep-display` | Students keep seeing today's order |
   | `content-changed` (F1, warning) | `accept` | Identity kept, wording changed |

   **The test for `same`:** would a student who mastered the old item have
   mastered the new one? If the meaning changed, it is `new`, and the old ID is
   `retire`d.
3. `python3 tools/build.py ids apply <slug> --proposal FILE --approver NAME
   --pull-request N` checks every case is decided with a reason, updates
   `books/<slug>/ids.lock.json` and appends to `changes`. It refuses a proposal
   that no longer matches the content (run `ids review` again).
4. Build again; it must pass. Commit the lock with the content change. CI's
   `id-invariants` job checks the lock only grew: no ID removed or reused,
   `next_id` never decreases, old `changes` untouched, storage key and output
   path unchanged.
