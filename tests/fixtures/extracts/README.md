# Data extracts of the other four books

The `const D` data of four deployed pages at the Phase 0 baseline, copied
unchanged from the preservation package (`07-derived-data-extracts/`). The
pilot's extract is `tests/golden/MunazaraRashidiyaAQU.data.json`. The ID tests
run against all five, read-only (spec section 9). These books are not migrated,
and nothing here is served (`tests/` is excluded from the site).

SHA-256, equal to the package's `MANIFEST.sha256` and checked by
`tests/integration/test_ids_extracts.py`:

| File | SHA-256 |
| --- | --- |
| MadkhalFiqhAQU.data.json | 1cb977828e29bffb459891c43bfcd688ecc598cfa35365dcc83c61caf35d89b2 |
| TafseerMaqaranAQU.data.json | 412786e767e5ca520af023965f9cd368aad7d320461cd0a5bc0310a284986b81 |
| TakhreejAsaneedAQU.data.json | 3e4f61186fa0df8dbc3c91951f997afb397efb174636c78e678f3e8090ba1f96 |
| TareekhTafseerAQU.data.json | 3127b115fc8b5b852ee29bdbab23698ba0141c78c3802eed8cee22b5e7708e93 |
