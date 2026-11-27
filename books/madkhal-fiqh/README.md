# المدخل إلى الفقه الإسلامي

- **Published page:** `fiqh/MadkhalFiqhAQU.html` (generated; do not edit by hand)
- **Storage key:** `madkhal-fiqh-v1` (also the Supabase `progress.course` value; never change it)
- **Page numbering:** references «ص» follow the printed edition used by the course, pages ١٥ to ١٦٩.
- **Content files:** `content/f1.py` to `f7.py`, copied unchanged from the Phase 0 preservation
  package (`05-recovered-sources/fiqh-canvas/source/`), which equals the project folder's
  `fiqh-canvas/source/`. Their SHA-256 values are checked in `tests/integration/test_fiqh.py`.
- **ID anchor (O-3):** the cards and questions have no `topic`, so `content.anchor` is `chapter`.
  Each item's chapter comes from the first «ص» page in its answer (cards) or explanation
  (questions), with the chapters' `from_page` (51, 105, 143), exactly as the legacy `build.py`
  named quiz chapters. Moving an item to another chapter stops the build for review.
- **Migration (Phase 3, book 1):** the build equals the page published at the Phase 0 baseline
  `de019d2` byte for byte (SHA-256 `725d5d1f…`). No step-2 change is switched on for this book.
  The report is `docs/migrations/madkhal-fiqh.md`.
- **Page-reference exceptions:** none needed. Every lesson block and question explanation
  carries «ص» (rule N4).
- **Reviewers:** Bilal approves ID changes (O-8) and signs off content-change reports by
  approving the pull request (O-10), until he names others in writing.
