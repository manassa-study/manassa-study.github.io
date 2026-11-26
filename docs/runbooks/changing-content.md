# Runbook: changing a book's content

For an editor changing lessons, cards, questions or other content of a migrated
book (today: المناظرة الرشيدية). Content changes resume only after the pilot
migration (Phase 2); in Phase 1 the content is frozen.

1. Create a branch. Never edit `main` or a published page directly (freeze rule).
2. Edit the content files in `books/<slug>/content/` only. Never edit the
   generated page (`mantiq/…html`): `check` fails on any hand edit (V9).
3. Build locally:
   `python3 tools/build.py build <slug>`
   - If it stops with **ID review** findings (unbound, missing, retired,
     duplicate, reordered options), follow
     [approving ID changes](approving-id-changes.md). Do not work around them.
   - Any other blocking finding names the file, the item and the fix. Fix the
     content, not the validator. There is no skip flag.
   - Warnings (for example a changed card back, F1) are fine but must be
     mentioned in the pull request.
4. Look at what students will see:
   `python3 tools/build.py diff <slug> --against origin/main --out /tmp/review`
   gives `<slug>.diff.md` (page code, separate from the data) and
   `<slug>.content-changes.md` (every changed block, card, question, map, table,
   example and capsule, with matn and Qur'an fields in their own section).
5. Commit the content files, the rebuilt page and any lock change together, and
   open a pull request. Attach the content-change report (CI also publishes it
   as the `build-reports` artifact).
6. Review and sign-off follow decision O-10 (still open: who signs, and how).
   CI must be green: `test`, `build-check`, `reproducibility`, `id-invariants`.
7. Merging deploys through GitHub Pages. Check the live page afterwards.

While Phase 1's step-1 rule is active, `build-check` runs with
`--baseline-data`, which requires the data to equal the baseline page. That flag
is removed from CI in the pull request that resumes content changes.
