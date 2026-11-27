# Phase 3 Book 3 migration progress

**Target:** تاريخ التفسير
**Published page:** `Tafseer/TareekhTafseerAQU.html`
**Branch:** `codex/phase3-book3-tareekh`
**Boundary:** no merge, deployment, publication, or Supabase/database changes.

## P6 governance closure

P6 was approved in principle as a shorter map-picker label intention. The recovered expression
`m.title.replace(/^الخريطة [^:]+:\s*/,"")` removes a leading «الخريطة …:» prefix, but none of the eight preserved map titles has that prefix. For this migration, the exact eight titles and the payload remain unchanged. Any actual title shortening is deferred to a separate editorial decision and explicit approval.

## Implementation scope

- Reconstruct content mechanically from `tests/fixtures/extracts/TareekhTafseerAQU.data.json`, SHA-256 `3127b115fc8b5b852ee29bdbab23698ba0141c78c3802eed8cee22b5e7708e93`.
- Preserve 179 card IDs, 354 question IDs, displayed option order, 43 topic IDs, and eight map IDs.
- Retain D1 favicon compatibility through the shared page head and D3 folded witnesses through the book-specific `fold_examples` feature.
- Keep question 330 unchanged; its three options are supported by the `في أي قرن؟` type shape.
- Do not implement P6 title shortening or edit academic content.

## Status

The implementation remains local on `codex/phase3-book3-tareekh`. Scope reduction restored Book 3's baseline palette, search and welcome copy, dedication, example labels, visible title, author affiliation, table-count suffix, and disclosure labels using values present in the preserved page. The document title remains separately configured from the visible title. No academic source, map title, ID, answer, or option order was edited.

The generated page is 632,828 bytes, SHA-256 `56263357d111ae15cccda465055d59220163c341ebe6437fc5fcc8de836ffb34`. Two clean builds produced identical bytes. The embedded payload equals the archived baseline payload recursively. It contains 179 cards, 354 questions, 43 topics, and eight maps; Q330 still has its original three options and all map titles remain exact.

The existing non-browser suite passes: 374 passed, 28 browser tests deselected. The browser runtime is unavailable in this environment (Python Playwright is absent), so no browser check was completed. The `ids invariants` CLI reported self-check only because no `origin/main` lock exists; the baseline archive payload and the generated payload were compared directly and are identical.

The generated HTML differs from the formal page baseline in three hunks (27 changed lines): the standard shared head adds platform metadata and absolute asset links (including approved D1 favicon paths); the privacy link is absolute; and shared styling emits the Book 3 plain-example rule plus the platform's disclosure styling. The folded witness block is present. The table-count suffix and both disclosure labels now match the baseline. The two unreviewed page-reference exceptions remain documented in `page-references.json`, and the build continues to warn about them.

Verification gate: PASS for the requested preservation checks; browser verification was unavailable. No commit, PR, merge, deployment, publication, or database operation occurred.
