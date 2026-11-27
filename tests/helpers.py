"""Shared test helpers."""
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PILOT = "munazara-rashidiya"
PILOT_PAGE = "mantiq/MunazaraRashidiyaAQU.html"
PILOT_SHA256 = "a91018ea392c1b39d8af7583f18d792e9f3467e63e4c91c13183545ce016aaf3"
GOLDEN = REPO / "tests" / "golden"


def make_repo(tmp_path, books=(), published=True):
    """A scratch repository holding platform/, _config.yml, the named fixture or real
    books and (by default) every published file of the baseline, as in the real one."""
    import json
    root = tmp_path / "repo"
    shutil.copytree(REPO / "platform", root / "platform")
    shutil.copy(REPO / "_config.yml", root / "_config.yml")
    (root / "books").mkdir()
    for slug, source in books:
        shutil.copytree(source, root / "books" / slug)
    if published:
        for p in json.loads((REPO / "platform" / "published-paths.json").read_text(encoding="utf-8"))["paths"]:
            (root / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / p, root / p)
    return root


EXTRACTS = {
    "MadkhalFiqhAQU": REPO / "tests" / "fixtures" / "extracts" / "MadkhalFiqhAQU.data.json",
    "MunazaraRashidiyaAQU": GOLDEN / "MunazaraRashidiyaAQU.data.json",
    "TafseerMaqaranAQU": REPO / "tests" / "fixtures" / "extracts" / "TafseerMaqaranAQU.data.json",
    "TakhreejAsaneedAQU": REPO / "tests" / "fixtures" / "extracts" / "TakhreejAsaneedAQU.data.json",
    "TareekhTafseerAQU": REPO / "tests" / "fixtures" / "extracts" / "TareekhTafseerAQU.data.json",
}
TF = ["صح", "خطأ"]


def register_extract_types(monkeypatch, data):
    """The other books use type labels the pilot registry doesn't have yet (they are
    registered at each book's migration). For read-only tests, register them here."""
    from mudhakarah import model
    for q in data["QUIZ_BANK"]:
        label = q["type"]
        if label in model.LABEL_TO_KEY:
            continue
        key = ("x-tf:" if q["options"] == TF else "x:") + label
        monkeypatch.setitem(model.TYPE_REGISTRY, key, {"labels": [label],
                                                       "shape": "true-false" if q["options"] == TF else "options"})
        monkeypatch.setitem(model.LABEL_TO_KEY, label, key)


def raw_from_extract(data, slug="extract"):
    """Raw content and a book config that reproduce an extract's data: each question's
    source slots are its correct answer, then its wrong answers in display order."""
    questions = []
    for q in data["QUIZ_BANK"]:
        r = {"type": q["type"], "q": q["q"]}
        if q["options"] == TF:
            r["tf"] = q["correct"] == 0
        else:
            r["correct"] = q["options"][q["correct"]]
            r["wrong"] = [o for i, o in enumerate(q["options"]) if i != q["correct"]]
        r["exp"] = q.get("exp")
        if "topic" in q:
            r["topic"] = q["topic"]
        questions.append(r)
    raw = {"meta": data["BOOK_METADATA"], "chapters": data["DEEP_STUDY_DATA"], "examples": data["QURANIC_EXAMPLES"],
           "cards": [dict(c) for c in data["FLASHCARDS"]], "questions": questions,
           "tables": data["COMPARISON_TABLES"], "maps": data["MIND_MAPS"], "capsules": data["CAPSULES"],
           "extras": {}}
    names = list(dict.fromkeys(q["chapter"] for q in data["QUIZ_BANK"]))
    book = {"slug": slug, "storage_key": slug + "-v1", "output": f"x/{slug}.html",
            "content": {"chapters": [{"symbol": f"CH{i}", "quiz_name": n} for i, n in enumerate(names, 1)]},
            "quiz": {"shuffle": "sequential", "seed": 1447}}
    return raw, book


def extract_lock(data, slug="extract"):
    from mudhakarah.ids import bootstrap
    raw, book = raw_from_extract(data, slug)
    info = {"from": book["output"], "commit": "0" * 40, "sha256": "0" * 64}
    lock = bootstrap(raw, book, data, info, "Test", 0, "2026-11-27", slug, check_sequence=False)
    return raw, book, lock
