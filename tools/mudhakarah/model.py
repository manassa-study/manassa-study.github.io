"""The assembler (spec section 2, layer 3): raw content to the book model.

The book model is exactly the object written into the page as `const D = …;`,
with its eight keys in this order and nothing else.
"""
import random

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
    "tf": {"labels": ["صح أو خطأ"], "shape": "true-false"},
}
LABEL_TO_KEY = {label: key for key, t in TYPE_REGISTRY.items() for label in t["labels"]}


def type_key(question):
    return LABEL_TO_KEY.get(question.get("type"))


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
            if len(opts) != 4 or any(not isinstance(o, str) or not o for o in opts) or len(set(opts)) != 4:
                findings.append(Finding("V2.question", BLOCKING,
                                        f"question {i}: needs one correct and three distinct wrong options", where))
    return findings


def assemble(raw, book, ids=None, where="assembler"):
    """Build the book model.

    `ids` is the ID binding from the lock (section 6): {"cards": [id…], "questions": [id…],
    "orders": [order or None…]}. Without it (M2, before the lock exists) cards keep the
    ids written by the content and questions are numbered by position, with today's
    shared-sequence option order, exactly as the legacy build.
    """
    findings = check_question_types(raw, where)
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
    if any(f.severity == BLOCKING for f in findings):
        raise BuildStopped("assembly", findings)

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
        bank.append({"id": qid, "chapter": names[q["topic"]], "type": q["type"], "q": q["q"],
                     "options": options, "correct": correct, "exp": q["exp"], "topic": q["topic"]})
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
