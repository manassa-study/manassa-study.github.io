"""The assembler (spec section 2, layer 3): raw content to the book model.

The book model is exactly the object written into the page as `const D = …;`,
with its eight keys in this order and nothing else.
"""
import random
import re

from .errors import BLOCKING, BuildStopped, Finding

MODEL_KEYS = ("BOOK_METADATA", "DEEP_STUDY_DATA", "QURANIC_EXAMPLES", "FLASHCARDS",
              "COMPARISON_TABLES", "MIND_MAPS", "QUIZ_BANK", "CAPSULES")

TRUE_FALSE_OPTIONS = ("صح", "خطأ")

# Type registry (spec section 4). Each question type is defined once: its stable
# internal key (used in fingerprints, F2), the Arabic labels that name it in content
# (a renamed label is added here as another label of the same key), and its shape.
TYPE_REGISTRY = {
    "mc": {"labels": ["اختيار من متعدد"], "shape": "options"},
    "name-it": {"labels": ["ما اسم هذا؟"], "shape": "options"},
    "figures-views": {"labels": ["الأعلام والآراء"], "shape": "options"},  # المدخل إلى الفقه
    "symbol-meaning": {"labels": ["الرمز ودلالته"], "shape": "options"},  # التخريج ودراسة الأسانيد
    "book-author": {"labels": ["الكتاب ومؤلفه"], "shape": "options"},  # التخريج ودراسة الأسانيد
    "tf": {"labels": ["صح أو خطأ"], "shape": "true-false"},
    "binary-judgment": {"labels": ["صح وخطأ"], "shape": "options", "option_counts": [2]},
    "quran-evidence-analysis": {"labels": ["تحليل الشواهد القرآنية"], "shape": "options"},
    "chronology": {"labels": ["الترتيب الزمني"], "shape": "options"},  # تاريخ التفسير
    "century": {"labels": ["في أي قرن؟"], "shape": "options", "option_counts": [3, 4]},  # تاريخ التفسير
}
LABEL_TO_KEY = {label: key for key, t in TYPE_REGISTRY.items() for label in t["labels"]}


def type_key(question):
    return LABEL_TO_KEY.get(question.get("type"))


# Anchors (O-3). A book whose cards and questions carry a `topic` anchors them to it;
# a book without topics ("anchor": "chapter" in book.json) anchors each card and question
# to its chapter, found from the first «ص N» in the question's explanation or the card's
# answer and the chapters' `from_page`, exactly as that book's legacy build named quiz
# chapters. Examples are not anchored in such a book.
ANCHORS = ("topic", "chapter")
ANCHOR_TEXT = {"cards": "a", "questions": "exp"}
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_PAGE_RE = re.compile(r"ص\s*(\d+)")


def anchor_kind(book):
    return book["content"].get("anchor", "topic")


def first_page(text):
    """The first page number «ص N» in a text (Arabic-Indic or ASCII digits), or None."""
    if not isinstance(text, str):
        return None
    ascii_text = "".join(str(_ARABIC_DIGITS.index(c)) if c in _ARABIC_DIGITS else c for c in text)
    m = _PAGE_RE.search(ascii_text)
    return int(m.group(1)) if m else None


def page_chapter(book, text):
    """The quiz name of the chapter a page falls in: the last chapter whose from_page is at
    or below it (the first chapter has none). None if the text has no page."""
    page = first_page(text)
    if page is None:
        return None
    name = None
    for ch in book["content"]["chapters"]:
        if ch.get("from_page") is None or page >= ch["from_page"]:
            name = ch["quiz_name"]
    return name


def item_anchor(book, collection, item):
    """The value a card or question is anchored to in its fingerprint (O-2, O-3)."""
    if anchor_kind(book) == "topic":
        return item.get("topic")
    return page_chapter(book, item.get(ANCHOR_TEXT[collection]))


def chapter_names(raw, book):
    """Topic id -> chapter quiz name, from book.json's chapter list (as the legacy build)."""
    names = {}
    for ch_cfg, ch in zip(book["content"]["chapters"], raw["chapters"]):
        for section in ch["sections"]:
            for topic in section["topics"]:
                names[topic["id"]] = ch_cfg["quiz_name"]
    return names


def source_options(q):
    """The options in source-slot order: slot 0 is the correct answer, then the wrong ones as written."""
    if TYPE_REGISTRY[type_key(q)]["shape"] == "true-false":
        return list(TRUE_FALSE_OPTIONS)
    return [q["correct"]] + list(q["wrong"])


def sequential_orders(raw, book):
    """Today's option order: one random sequence seeded with quiz.seed, shared by all
    multiple-choice questions in content order (the legacy build). Returns, per
    question index, the display order as a permutation of source slots, or None for
    true/false. Used to bootstrap the option-order lock and as the step-1 reference."""
    rng = random.Random(book["quiz"]["seed"])
    orders = []
    for q in raw["questions"]:
        if TYPE_REGISTRY[type_key(q)]["shape"] == "true-false":
            orders.append(None)
            continue
        slots = list(range(1 + len(q["wrong"])))
        opts = source_options(q)
        shuffled = list(opts)
        rng.shuffle(shuffled)
        # map each displayed option back to its source slot (options are distinct, checked by V2)
        orders.append([opts.index(o) for o in shuffled])
        assert sorted(orders[-1]) == slots
    return orders


def check_question_types(raw, where):
    findings = []
    for i, q in enumerate(raw["questions"], 1):
        key = type_key(q)
        if key is None:
            findings.append(Finding("V2.unknown-type", BLOCKING,
                                    f"question {i}: unknown type '{q.get('type')}' (add it to the type registry)",
                                    where))
            continue
        if TYPE_REGISTRY[key]["shape"] == "true-false":
            if not isinstance(q.get("tf"), bool):
                findings.append(Finding("V2.question", BLOCKING, f"question {i}: true/false needs 'tf'", where))
        else:
            opts = [q.get("correct")] + list(q.get("wrong") or [])
            allowed = TYPE_REGISTRY[key].get("option_counts")
            bad_count = len(opts) not in allowed if allowed else len(opts) != 4
            if bad_count or any(not isinstance(o, str) or not o for o in opts) or len(set(opts)) != len(opts):
                message = (f"needs {', '.join(map(str, allowed))} distinct options" if allowed else
                           "needs one correct and three distinct wrong options")
                findings.append(Finding("V2.question", BLOCKING, f"question {i}: {message}", where))
    return findings


def check_raw(raw, book, where):
    """The checks the assembler needs before it can use an item: known question types
    and valid options (V2), and every item's topic exists (V5)."""
    findings = check_question_types(raw, where)
    if anchor_kind(book) == "chapter":
        for collection, kind in (("questions", "question"), ("cards", "card")):
            for i, x in enumerate(raw[collection], 1):
                if item_anchor(book, collection, x) is None:
                    findings.append(Finding("V5.anchor", BLOCKING,
                                            f"{kind} {i}: no «ص» page in its {ANCHOR_TEXT[collection]}, so its "
                                            "chapter (its ID anchor, O-3) can't be found", where))
        return findings
    names = chapter_names(raw, book)
    for i, q in enumerate(raw["questions"], 1):
        if q.get("topic") not in names:
            findings.append(Finding("V5.topic", BLOCKING, f"question {i}: topic '{q.get('topic')}' does not exist",
                                    where))
    for kind in ("cards", "examples"):
        for i, x in enumerate(raw[kind], 1):
            if x.get("topic") not in names:
                findings.append(Finding("V5.topic", BLOCKING,
                                        f"{kind[:-1]} {i}: topic '{x.get('topic')}' does not exist", where))
    return findings


def assemble(raw, book, ids=None, where="assembler"):
    """Build the book model.

    `ids` is the ID binding from the lock (section 6): {"cards": [id…], "questions": [id…],
    "orders": [order or None…]}. Without it (M2, before the lock exists) cards keep the
    ids written by the content and questions are numbered by position, with today's
    shared-sequence option order, exactly as the legacy build.
    """
    findings = check_raw(raw, book, where)
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("assembly", findings)
    names = chapter_names(raw, book)

    if ids is None:
        card_ids = [c["id"] for c in raw["cards"]]
        question_ids = list(range(1, len(raw["questions"]) + 1))
        orders = sequential_orders(raw, book)
    else:
        card_ids, question_ids, orders = ids["cards"], ids["questions"], ids["orders"]

    cards = []
    for card, cid in zip(raw["cards"], card_ids):
        c = dict(card)
        c["id"] = cid  # replaces the positional id in place; key order is kept
        cards.append(c)

    bank = []
    for q, qid, order in zip(raw["questions"], question_ids, orders):
        opts = source_options(q)
        if order is None:
            options, correct = opts, (0 if q["tf"] else 1)
        else:
            options = [opts[s] for s in order]
            correct = order.index(0)
        if anchor_kind(book) == "topic":
            bank.append({"id": qid, "chapter": names[q["topic"]], "type": q["type"], "q": q["q"],
                         "options": options, "correct": correct, "exp": q["exp"], "topic": q["topic"]})
        else:  # no topic in the content: the chapter comes from the page (the book's legacy build)
            bank.append({"id": qid, "chapter": page_chapter(book, q["exp"]), "type": q["type"], "q": q["q"],
                         "options": options, "correct": correct, "exp": q["exp"]})
        # invariant (section 6): the option at `correct` is the source's correct answer
        expected = q["correct"] if order is not None else (TRUE_FALSE_OPTIONS[0] if q["tf"] else TRUE_FALSE_OPTIONS[1])
        if options[correct] != expected:
            raise BuildStopped("assembly", [Finding("V3.answer-invariant", BLOCKING,
                                                    f"question {qid}: options[correct] is not the source answer",
                                                    where)])

    model = {
        "BOOK_METADATA": raw["meta"],
        "DEEP_STUDY_DATA": raw["chapters"],
        "QURANIC_EXAMPLES": raw["examples"],
        "FLASHCARDS": cards,
        "COMPARISON_TABLES": raw["tables"],
        "MIND_MAPS": raw["maps"],
        "QUIZ_BANK": bank,
        "CAPSULES": raw["capsules"],
    }
    for name, value in raw.get("extras", {}).items():
        model[name] = value
    return model, findings
