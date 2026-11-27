# Required CI checks (O-12)

Status: **list defined (M1) and stable; not switched on.** Turning it on is a repository
setting only Bilal can change (spec section 10, O-12). Switching it on ends the main
repository's direct-push freeze (decision of 27 November 2026).

| Check (job in `.github/workflows/ci.yml`) | Required | Why |
| --- | --- | --- |
| `test` | Yes | Unit, integration, ID and failure-condition tests |
| `build-check` | Yes | Every committed book page equals a fresh build; all validators pass |
| `reproducibility` | Yes | Two clean builds give identical bytes and manifests |
| `id-invariants` | Yes | The pull request's ID lock never removes an item, reuses an ID or rewrites history |
| `browser` | Yes (from Phase 2) | Playwright tests of the built pages; blocking in CI since Phase 2 |

Not required: `reports` (advisory by design, `continue-on-error`), and `Supabase Preview`
(a Supabase app check outside this workflow, skipped on these pull requests).

The names are the job ids: none of the jobs sets a `name:`, so GitHub shows each check under
its job id. All five ran green on pull requests #10 and #11 and on `main` after each merge.
The workflow runs on every pull request to `main` and on every push to `main`, with no path
filter, so a required check is never left waiting on a pull request that doesn't trigger it.

## How to switch it on (Bilal)

GitHub: repository **Settings → Rules → Rulesets → New ruleset → New branch ruleset**.

1. **Ruleset name:** `main`. **Enforcement status:** Active.
2. **Target branches:** Add target → Include default branch (`main`).
3. **Bypass list:** add **Repository admin**, set to **For pull requests only**. An urgent fix
   can then still be merged by an admin who chooses to, knowingly (spec: "or an admin must
   override knowingly"), but nobody can push to `main` without a pull request.
4. **Rules**, tick:
   - **Restrict deletions**
   - **Block force pushes**
   - **Require a pull request before merging**, with **Required approvals: 0**. The pull
     requests come from Bilal's own account, and GitHub does not let an author approve their
     own pull request, so 1 would block every merge. Bilal's merge is the approval (O-10).
   - **Require status checks to pass**: tick **Require branches to be up to date before
     merging**, then add the five checks `test`, `build-check`, `reproducibility`,
     `id-invariants`, `browser` (choose the GitHub Actions source for each).
5. Leave everything else as it is: no other rule, no change to Pages, Actions or other
   settings. **Create.**

Equivalent with classic branch protection (Settings → Branches → Add rule for `main`):
require a pull request (0 approvals), require the five status checks and up-to-date branches,
do not allow force pushes or deletions.

## How to check it worked

- The ruleset page lists the five checks.
- On the next pull request, the merge button stays disabled until all five checks are green.
- A direct `git push` to `main` is refused.
