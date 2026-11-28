"""V8 HTML output (blocking), beyond the data-line checks in mudhakarah.output:
the doctype and opening <html> tag are exactly the step-1 baseline's, or, once the
book turns on S2-1, carry lang="ar" dir="rtl"; and no
leftover words of another book appear outside the data line (the generalized form
of the legacy build's `leftover` asserts). Page size is a warning (R1)."""
from ..config import step2_changes
from ..errors import BLOCKING, WARNING, Finding
from ..output import DATA_PREFIX

STEP1_OPENING = "<!doctype html><html><head>"  # today's pages have a bare <html> (V8 correction)
SIZE_BUDGET = 800_000      # bytes, the master plan's 800 KB budget
STEP2_OPENING = '<!doctype html><html lang="ar" dir="rtl"><head>'  # S2-1
GROWTH_LIMIT = 1.10        # more than 10% above the previous build

# Words that identify each deployed book, from the five baseline pages (Phase 0
# package): title, storage key, welcome key, page name and accent colours. Each
# marker appears in its own page and in none of the other four (checked when this
# list was made; colours shared between books, such as 6ea8ec, are left out).
BOOK_MARKERS = {
    "madkhal-fiqh-v1": ["المدخل إلى الفقه الإسلامي", "madkhal-fiqh-v1", "fiqh-wel", "MadkhalFiqhAQU",
                        "6d2f63", "e3a0d6", "3a1235"],
    "munazara-rashidiya-v1": ["المناظرة الرشيدية", "munazara-rashidiya-v1", "munazara-wel",
                              "MunazaraRashidiyaAQU", "8a4b14", "efb57c", "3b1d06"],
    "tafsir-muqaran-v1": ["دراسة التفسير المقارن", "tafsir-muqaran-v1", "tafsir-wel", "0d5b49", "5fc4a6"],
    "takhreej-asaneed-v1": ["التخريج ودراسة الأسانيد", "takhreej-asaneed-v1", "takhreej-wel",
                            "TakhreejAsaneedAQU", "5fcfae"],
    "tareekh-tafseer-v1": ["دراسة تاريخ التفسير", "tareekh-tafseer-v1", "tareekh-wel", "1a4f8b"],
}


def chrome(text):
    without_data = "\n".join(line for line in text.split("\n") if not line.startswith(DATA_PREFIX))
    # The reader switch intentionally names and links to other books. Exclude
    # that known navigation menu from the legacy cross-book-content check.
    import re
    return re.sub(r'<nav class="book-switch-menu"[^>]*>.*?</nav>', "", without_data, flags=re.DOTALL)


def check(text, book, where, previous_size=None):
    out = []
    if "S2-1" in step2_changes(book):
        opening, rule = STEP2_OPENING, "once S2-1 is on (lang and dir are required)"
    else:
        opening, rule = STEP1_OPENING, "in step 1"
    if not text.startswith(opening):
        out.append(Finding("V8.opening", BLOCKING, f"the page must start with '{opening}' exactly {rule}", where))
    rest = chrome(text)
    for key, markers in BOOK_MARKERS.items():
        if key == book["storage_key"]:
            continue
        for word in markers:
            if word in rest:
                out.append(Finding("V8.leftover", BLOCKING,
                                   f"'{word}' from another book ({key}) appears outside the data line", where))
    size = len(text.encode("utf-8"))
    if size > SIZE_BUDGET:
        out.append(Finding("V8.size", WARNING, f"the page is {size:,} bytes, above the {SIZE_BUDGET:,} budget", where))
    if previous_size and size > previous_size * GROWTH_LIMIT:
        out.append(Finding("V8.size", WARNING,
                           f"the page grew from {previous_size:,} to {size:,} bytes (more than 10%)", where))
    return out
