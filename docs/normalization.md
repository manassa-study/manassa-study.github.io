# Normalization `ar-norm-1` and fingerprints

This is the rule set the ID lock uses to recognise an item after an edit
(Architecture Specification, section 6). The code is
`tools/mudhakarah/normalize.py`, and every rule has test cases in
`tests/unit/test_normalize.py`.

The goal: edits that don't change meaning (diacritics, spacing, punctuation,
letter-form variants) keep a fingerprint, and different words change it. A
fingerprint helps find a match. It never proves identity: the lock is
authoritative, and anything uncertain stops the build for a person to decide.

## Rules, in the order applied

| # | Rule | Example (before → after) |
| --- | --- | --- |
| 1 | Unicode NFKC (folds presentation forms and compatibility characters) | ﷲ → الله |
| 2 | Remove diacritics U+064B–U+065F, superscript alef U+0670, Qur'anic annotation marks U+06D6–U+06ED and tatweel U+0640 | عَلِمَ → علم; الكتـــاب → الكتاب |
| 3 | Fold alef forms أ إ آ ٱ to ا; ى to ي; Persian and Urdu ی to ي, ک to ك, ہ ھ to ه | أحمد إلى → احمد الي; کتاب → كتاب |
| 4 | Arabic-Indic and Persian digits to 0–9 | ٢٢ → 22; ۱۲۳ → 123 |
| 5 | Punctuation and symbols (Unicode categories P and S), including « » ( ) [ ] ، ؛ ؟ . : ! and dashes, are removed. Each becomes a space first, so two words are never joined | «المنع»، → المنع; ابن-سينا → ابن سينا |
| 6 | Remove zero-width and direction marks U+200B–U+200F | |
| 7 | Collapse all whitespace to single spaces and trim | |

Kept distinct on purpose: ة and ه, ؤ, ئ, and a lone hamza. Search may fold
them so students find words however they type; identity does not, because
folding raises the chance that two different items collide.

Rule 5's "becomes a space" is how "remove" is implemented, so that removing a
dash or a comma between two words never merges them into one word.

## Fingerprints

Each field is normalized, the fields are joined with U+001F, and the UTF-8
bytes are hashed with SHA-1 (a short stable label, not a security measure).

- Card: topic, front (`q`).
- Question: topic, the stable type key from the assembler's type registry
  (`mc`, `tf`, `name-it`; never the Arabic label, F2), the stem, the options as
  a sorted list joined with U+001E (empty for true/false, whose options are
  fixed), and the correct answer's text (never its position).

Two more hashes are kept in the lock:

- `content`: SHA-1 of the whole raw item exactly as written (compact JSON,
  every field, before normalization; a card's positional `id` is left out
  because the lock replaces it). A change here with the same fingerprint is a
  warning (F1).
- `shown` (multiple-choice only): the normalized options in display order. If
  it no longer matches while the fingerprint is the same, the source's wrong
  answers were reordered, and the build stops (F4).

## Versioning

Changing any rule means a new name (`ar-norm-2`) and a migration that shows
every active ID still maps to exactly one item. The lock records the name, and
the build stops if the lock's settings differ from the tool's.
