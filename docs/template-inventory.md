# Template inventory: the other four books against the pilot template

Read-only comparison (spec section 12, risk "the shared template is really the
pilot's"). No page was changed. Each live baseline page's code outside the data
line was compared line by line with the pilot's.

| Book | Lines | Similarity to the pilot | Differing blocks | Lines that differ (pilot / other) |
| --- | --- | --- | --- | --- |
| المدخل إلى الفقه الإسلامي (`fiqh/MadkhalFiqhAQU.html`) | 1,573 | 97.6% | 32 | 35 / 39 |
| التخريج ودراسة الأسانيد (`hadith/TakhreejAsaneedAQU.html`) | 1,573 | 97.6% | 31 | 35 / 39 |
| تاريخ التفسير (Tafseer repository) | 1,552 | 96.6% | 37 | 61 / 44 |
| التفسير المقارن (Tafseer repository) | 1,679 | 80.0% | 89 | 269 / 379 |

Known differences beyond the values `book.json` already holds:

- المدخل إلى الفقه: the dedication card and its own `attach()` without the pilot's
  topic patch. **Migrated in Phase 3 (book 1):** both are now feature blocks of the
  template (`features.dedication_card` with `dedication.teacher`, and `item_topics`,
  which follows `content.anchor`), and the book builds byte for byte.
- Tafseer-repository pages: titles without the platform suffix, no `og:url`,
  different card and question shapes without `topic` (fingerprint anchor O-3),
  other question types (for example «صح وخطأ», «الترتيب الزمني») that join the
  type registry at migration.
- التفسير المقارن: a substantially different app script, an extra `DRILL`
  structure (`content.extras`), blocks with `ayah`, `key` and `table`, and maps
  without a `type`. It needs the most work and should migrate last.

These numbers come from the Phase 0 package pages (`03-deployed-books-at-baseline`).
