# Required CI checks (O-12)

Status: **active on `main`** under the repository ruleset. The ruleset requires a pull request, blocks deletions and force pushes, and strictly requires all five checks below. Repository administrators may bypass only through a pull request.

| Required check | Purpose |
| --- | --- |
| `test` | Unit, integration, ID, and failure-condition tests |
| `build-check` | Every committed page matches a fresh build and validators pass |
| `reproducibility` | Two clean builds produce identical bytes and manifests |
| `id-invariants` | ID locks do not remove items, reuse IDs, or rewrite history |
| `browser` | Playwright checks of built pages |

The `reports` job is advisory. The external Supabase Preview check is not part of this required workflow. This documentation describes CI only; it does not authorize or perform database operations.
