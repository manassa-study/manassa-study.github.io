# Required CI checks (O-12): proposed list

Status: **defined in M1 for Bilal's approval. Not switched on.** Turning on branch
protection is a repository setting only Bilal can approve. Switching it on ends the
main repository's direct-push freeze (decision of 27 November 2026).

| Check (job in `.github/workflows/ci.yml`) | Required from | Why |
| --- | --- | --- |
| `test` | Now | Unit, integration, ID and failure-condition tests |
| `build-check` | Now | The committed pilot page equals a fresh build; all validators pass |
| `reproducibility` | Now | Two clean builds give identical bytes and manifests |
| `id-invariants` | Now | The pull request's ID lock never removes an item, reuses an ID or rewrites history |
| `browser` | Phase 2 | Playwright tests; advisory in Phase 1, blocking from the pilot migration |

The `reports` job never fails and is not a required check.

Branch protection settings to request at the same time: require a pull request before
merging, require the checks above to pass, and require branches to be up to date.
