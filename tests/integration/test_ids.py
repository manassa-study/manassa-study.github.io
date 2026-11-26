"""ID scenario tests on the pilot's real content (spec sections 6 and 9).
Each case: the build stops, writes nothing and lists the item for a person,
or (where the spec says so) binds silently to the same ID."""
import copy
import json
import random

import pytest

from helpers import PILOT, REPO, make_repo
from mudhakarah import model as model_mod
from mudhakarah.config import load_book
from mudhakarah.errors import BuildStopped
from mudhakarah.ids import apply, bind, bootstrap, invariants, read_lock, review, seeded_order
from mudhakarah.loaders import load_content
from mudhakarah.model import assemble
from mudhakarah.output import parse_data_line
from mudhakarah.pipeline import run_book

W = "test"


@pytest.fixture(scope="module")
def base():
    book, _ = load_book(REPO, PILOT)
    raw, _, _ = load_content(REPO, PILOT, book)
    lock = read_lock(REPO, PILOT)
    live = parse_data_line((REPO / book["output"]).read_text(encoding="utf-8"))
    return book, raw, lock, live


@pytest.fixture
def ctx(base):
    book, raw, lock, live = base
    return book, copy.deepcopy(raw), copy.deepcopy(lock), live


def codes(findings):
    return sorted({f.code for f in findings if f.severity == "blocking"})


def decide(proposal, **by_kind):
    """Fill every case: by_kind maps a kind to (decision, extra fields)."""
    for c in proposal["cases"]:
        decision, extra = by_kind[c["kind"]]
        c.update(decision=decision, reason="test: " + decision, **extra)
    return proposal


def test_lock_matches_the_live_page(base):
    book, raw, lock, live = base
    assert [c["id"] for c in lock["cards"]["items"]] == [c["id"] for c in live["FLASHCARDS"]] == list(range(1, 170))
    assert [q["id"] for q in lock["questions"]["items"]] == list(range(1, 178))
    assert lock["cards"]["next_id"] == 170 and lock["questions"]["next_id"] == 178
    topics = [t["id"] for ch in live["DEEP_STUDY_DATA"] for s in ch["sections"] for t in s["topics"]]
    assert [t["id"] for t in lock["topics"]] == topics and len(topics) == 27
    assert [m["id"] for m in lock["maps"]] == [m["id"] for m in live["MIND_MAPS"]] and len(lock["maps"]) == 8
    assert sum(1 for q in lock["questions"]["items"] if "order" in q) == 113
    assert lock["bootstrap"]["sha256"] == "a91018ea392c1b39d8af7583f18d792e9f3467e63e4c91c13183545ce016aaf3"
    assert lock["bootstrap"]["commit"] == "de019d25ba8ea2be7f3dbc56b98de2a63248ea31"


def test_exact_rebind_reproduces_today(ctx):
    book, raw, lock, live = ctx
    ids, findings, cases = bind(raw, book, lock, W)
    assert codes(findings) == [] and cases == []
    m, _ = assemble(raw, book, ids)
    assert m["QUIZ_BANK"] == live["QUIZ_BANK"] and m["FLASHCARDS"] == live["FLASHCARDS"]


def test_bootstrap_regenerates_the_committed_lock(base):
    book, raw, lock, live = base
    again = bootstrap(raw, book, live, lock["bootstrap"], "Bilal", 10, "2026-11-27", W)
    assert again == lock


def test_bootstrap_refuses_when_source_and_live_disagree(base):
    book, raw, lock, live = base
    bad = copy.deepcopy(live)
    bad["FLASHCARDS"][41]["q"] += " (معدّل)"
    with pytest.raises(BuildStopped) as e:
        bootstrap(raw, book, bad, lock["bootstrap"], "Bilal", 10, "2026-11-27", W)
    assert "V3.bootstrap-bind" in codes(e.value.findings)
    bad = copy.deepcopy(live)
    q = next(q for q in bad["QUIZ_BANK"] if len(q["options"]) == 4)
    q["options"] = q["options"][::-1]
    q["correct"] = 3 - q["correct"]
    with pytest.raises(BuildStopped) as e:
        bootstrap(raw, book, bad, lock["bootstrap"], "Bilal", 10, "2026-11-27", W)
    assert "V3.bootstrap-order" in codes(e.value.findings)


def test_inserted_card_keeps_every_later_id(ctx):
    book, raw, lock, live = ctx
    new = {"id": 999, "cat": "تجربة", "q": "بطاقة جديدة؟", "a": "نعم", "topic": raw["cards"][40]["topic"]}
    raw["cards"].insert(41, new)
    ids, findings, cases = bind(raw, book, lock, W)
    assert ids is None and codes(findings) == ["V3.unbound"] and [c["kind"] for c in cases] == ["unbound"]
    new_lock, summary = apply(raw, book, lock, decide(review(raw, book, lock, W), unbound=("new", {})),
                              "Bilal", 1, "2026-11-28", W)
    assert summary == {"new": 1}
    ids, findings, _ = bind(raw, book, new_lock, W)
    assert ids["cards"][:41] == list(range(1, 42)) and ids["cards"][41] == 170 and ids["cards"][42:] == list(
        range(42, 170))
    assert invariants(lock, new_lock, W) == []


def test_deleted_card_retires_its_id_forever(ctx):
    book, raw, lock, live = ctx
    removed = raw["cards"].pop(10)
    ids, findings, cases = bind(raw, book, lock, W)
    assert codes(findings) == ["V3.missing"] and cases[0]["id"] == 11
    lock2, _ = apply(raw, book, lock, decide(review(raw, book, lock, W), missing=("retire", {})), "Bilal", 1,
                     "2026-11-28", W)
    assert next(i for i in lock2["cards"]["items"] if i["id"] == 11)["status"] == "retired"
    raw["cards"].append({"id": 0, "cat": "x", "q": "بطاقة أخرى", "a": "y", "topic": "t1"})
    lock3, _ = apply(raw, book, lock2, decide(review(raw, book, lock2, W), unbound=("new", {})), "Bilal", 2,
                     "2026-11-28", W)
    assert lock3["cards"]["items"][-1]["id"] == 170  # 11 is never issued again
    # the retired card returns: stop for restore or new
    raw["cards"].insert(10, removed)
    _, findings, cases = bind(raw, book, lock3, W)
    assert codes(findings) == ["V3.retired-match"] and cases[0]["retired_ids"] == [11]
    lock4, _ = apply(raw, book, lock3, decide(review(raw, book, lock3, W), **{"retired-match": ("restore", {})}),
                     "Bilal", 3, "2026-11-28", W)
    ids, _, _ = bind(raw, book, lock4, W)
    assert ids["cards"][10] == 11
    assert invariants(lock3, lock4, W) == []


def _first_mc(raw):
    return next(i for i, q in enumerate(raw["questions"]) if "correct" in q)


@pytest.mark.parametrize("edit", ["stem-word", "wrong-option", "correct-text"])
def test_changed_question_stops_with_suggested_pair(ctx, edit):
    book, raw, lock, live = ctx
    i = _first_mc(raw)
    q = raw["questions"][i]
    if edit == "stem-word":
        q["q"] = q["q"].replace(q["q"].split()[0], "كلمةمختلفة", 1)
    elif edit == "wrong-option":
        q["wrong"][1] = "خيار جديد تماماً"
    else:
        q["correct"] = q["correct"] + " وزيادة"
    _, findings, cases = bind(raw, book, lock, W, previous=live)
    assert codes(findings) == ["V3.missing", "V3.unbound"]
    unbound = next(c for c in cases if c["kind"] == "unbound")
    assert unbound["suggestions"][0]["id"] == i + 1
    missing = next(c for c in cases if c["kind"] == "missing")
    assert missing["old_item"]["options"] == live["QUIZ_BANK"][i]["options"]  # shown side by side


def test_same_decision_keeps_id_and_option_position(ctx):
    book, raw, lock, live = ctx
    i = _first_mc(raw)
    raw["questions"][i]["wrong"][1] = "خيار جديد تماماً"
    proposal = review(raw, book, lock, W, live)
    proposal = decide(proposal, unbound=("same", {"same_as": i + 1}), missing=("same", {}))
    new_lock, summary = apply(raw, book, lock, proposal, "Bilal", 4, "2026-11-28", W, live)
    assert summary == {"rebind": 1}
    ids, findings, _ = bind(raw, book, new_lock, W)
    assert codes(findings) == []
    m, _ = assemble(raw, book, ids)
    before, after = live["QUIZ_BANK"][i], m["QUIZ_BANK"][i]
    assert after["id"] == before["id"] and after["correct"] == before["correct"]
    changed = [k for k, (a, b) in enumerate(zip(after["options"], before["options"])) if a != b]
    assert len(changed) == 1 and after["options"][changed[0]] == "خيار جديد تماماً"  # same position as before
    assert m["QUIZ_BANK"][:i] + m["QUIZ_BANK"][i + 1:] == live["QUIZ_BANK"][:i] + live["QUIZ_BANK"][i + 1:]
    assert invariants(lock, new_lock, W) == []


def test_true_false_flipped_stops(ctx):
    book, raw, lock, live = ctx
    q = next(q for q in raw["questions"] if "tf" in q)
    q["tf"] = not q["tf"]
    _, findings, _ = bind(raw, book, lock, W)
    assert codes(findings) == ["V3.missing", "V3.unbound"]


def test_absorbed_wording_binds_silently_but_reports_content(ctx):
    book, raw, lock, live = ctx
    raw["cards"][5]["q"] = raw["cards"][5]["q"].replace("ا", "أ", 1) + "  "
    i = _first_mc(raw)
    raw["questions"][i]["q"] = raw["questions"][i]["q"] + "؟؟"
    ids, findings, cases = bind(raw, book, lock, W)
    assert ids is not None and ids["cards"][5] == 6 and ids["questions"][i] == i + 1
    assert [f.code for f in findings if f.severity == "warning"] == ["V3.content-changed"] * 2
    assert [c["kind"] for c in cases] == ["content-changed"] * 2


def test_meaning_changing_diacritic_edit_is_reported_f1(ctx):
    book, raw, lock, live = ctx
    raw["cards"][0]["q"] = raw["cards"][0]["q"] + " عَلِمَ"
    raw2 = copy.deepcopy(raw)
    raw2["cards"][0]["q"] = raw["cards"][0]["q"].replace("عَلِمَ", "عُلِّمَ")
    lock2, _ = apply(raw, book, lock, decide(review(raw, book, lock, W, live), unbound=("same", {"same_as": 1}),
                                             missing=("same", {})), "Bilal", 5, "2026-11-28", W, live)
    ids, findings, cases = bind(raw2, book, lock2, W)
    assert ids["cards"][0] == 1
    assert [f.code for f in findings if f.severity == "warning"] == ["V3.content-changed"]


def test_card_back_or_explanation_change_is_reported_f1(ctx):
    book, raw, lock, live = ctx
    raw["cards"][3]["a"] += " (تصحيح)"
    raw["questions"][3]["exp"] += " (تصحيح)"
    ids, findings, _ = bind(raw, book, lock, W)
    assert ids is not None and [f.code for f in findings if f.severity == "warning"] == ["V3.content-changed"] * 2


def test_reordered_options_in_source_f4(ctx):
    book, raw, lock, live = ctx
    i = _first_mc(raw)
    raw["questions"][i]["wrong"] = raw["questions"][i]["wrong"][::-1]
    ids, findings, cases = bind(raw, book, lock, W)
    assert codes(findings) == ["V3.options-reordered"] and cases[0]["id"] == i + 1  # same fingerprint, same ID
    lock2, summary = apply(raw, book, lock, decide(review(raw, book, lock, W),
                                                   **{"reordered-options": ("keep-display", {}),
                                                      "content-changed": ("accept", {})}),
                           "Bilal", 6, "2026-11-28", W)
    ids, findings, _ = bind(raw, book, lock2, W)
    m, _ = assemble(raw, book, ids)
    assert m["QUIZ_BANK"][i]["options"] == live["QUIZ_BANK"][i]["options"]  # students see no change
    assert invariants(lock, lock2, W) == []


def test_label_rename_changes_no_id_f2(ctx, monkeypatch):
    book, raw, lock, live = ctx
    monkeypatch.setitem(model_mod.LABEL_TO_KEY, "صح وخطأ", "tf")
    for q in raw["questions"]:
        if q["type"] == "صح أو خطأ":
            q["type"] = "صح وخطأ"
    ids, findings, _ = bind(raw, book, lock, W)
    assert codes(findings) == [] and ids["questions"] == list(range(1, 178))


def test_duplicate_fingerprints_stop_then_an_approved_group_works(ctx):
    book, raw, lock, live = ctx
    dup = dict(raw["cards"][20], a="جواب آخر")
    raw["cards"].insert(21, dup)
    _, findings, cases = bind(raw, book, lock, W)
    assert codes(findings) == ["V4.duplicate"] and cases[0]["positions"] == [21, 22]
    proposal = decide(review(raw, book, lock, W), duplicate=("group", {"ids": [21, None]}))
    lock2, summary = apply(raw, book, lock, proposal, "Bilal", 7, "2026-11-28", W)
    assert summary == {"new": 1, "group": 1}
    ids, findings, _ = bind(raw, book, lock2, W)
    assert codes(findings) == [] and ids["cards"][20:22] == [21, 170]
    raw["cards"][20], raw["cards"][21] = raw["cards"][21], raw["cards"][20]  # reorder inside the group
    _, findings, _ = bind(raw, book, lock2, W)
    assert codes(findings) == ["V4.duplicate"]


def test_new_question_gets_its_own_seeded_order_and_others_dont_move(ctx):
    book, raw, lock, live = ctx
    raw["questions"].insert(0, {"type": "اختيار من متعدد", "q": "سؤال جديد؟", "correct": "أ", "wrong": ["ب", "ج", "د"],
                                "exp": "", "topic": "t1"})
    lock2, _ = apply(raw, book, lock, decide(review(raw, book, lock, W), unbound=("new", {})), "Bilal", 8,
                     "2026-11-28", W)
    entry = lock2["questions"]["items"][-1]
    assert entry["id"] == 178 and entry["order"] == seeded_order(1447, 178, 4)
    ids, _, _ = bind(raw, book, lock2, W)
    m, _ = assemble(raw, book, ids)
    assert m["QUIZ_BANK"][1:] == live["QUIZ_BANK"]  # stability on insert: nothing else changed
    assert m["QUIZ_BANK"][0]["options"][m["QUIZ_BANK"][0]["correct"]] == "أ"


def test_new_question_orders_place_the_answer_fairly():
    counts = [0, 0, 0, 0]
    for qid in range(1, 4001):
        counts[seeded_order(1447, qid, 4).index(0)] += 1
    assert all(800 < c < 1200 for c in counts), counts


def test_topic_removed_or_new_stops(ctx):
    book, raw, lock, live = ctx
    raw["chapters"][0]["sections"][0]["topics"][0]["id"] = "t1-renamed"
    _, findings, _ = bind(raw, book, lock, W)
    assert {"V3.topic-removed", "V3.topic-new"} <= set(codes(findings))


def test_renamed_chapter_and_reordered_maps_warn_only(ctx):
    book, raw, lock, live = ctx
    book = copy.deepcopy(book)
    book["content"]["chapters"][0]["quiz_name"] = "المدخل العام"
    raw["maps"] = raw["maps"][::-1]
    ids, findings, _ = bind(raw, book, lock, W)
    assert ids is not None
    assert sorted(f.code for f in findings) == ["V3.chapters-changed", "V3.maps-changed"]


def test_apply_requires_every_decision_with_a_reason(ctx):
    book, raw, lock, live = ctx
    raw["cards"].pop(0)
    proposal = review(raw, book, lock, W)
    with pytest.raises(BuildStopped):
        apply(raw, book, lock, proposal, "Bilal", 1, "2026-11-28", W)  # undecided
    proposal["cases"][0].update(decision="retire", reason=" ")
    with pytest.raises(BuildStopped):
        apply(raw, book, lock, proposal, "Bilal", 1, "2026-11-28", W)  # no reason
    proposal["cases"][0]["reason"] = "removed"
    with pytest.raises(BuildStopped):
        apply(raw, book, lock, proposal, "", 1, "2026-11-28", W)  # no approver
    new_lock, _ = apply(raw, book, lock, proposal, "Bilal", 1, "2026-11-28", W)
    assert new_lock["changes"][-1] == {"seq": 2, "date": "2026-11-28", "collection": "cards", "action": "retire",
                                       "id": 1, "old_fp": lock["cards"]["items"][0]["fp"], "reason": "removed",
                                       "approved_by": "Bilal", "pull_request": 1}


def test_stale_proposal_is_refused(ctx):
    book, raw, lock, live = ctx
    raw["cards"].pop(0)
    proposal = decide(review(raw, book, lock, W), missing=("retire", {}))
    raw["cards"].pop(0)
    with pytest.raises(BuildStopped):
        apply(raw, book, lock, proposal, "Bilal", 1, "2026-11-28", W)


# ------------------------------------------------------------------ invariants

def _mutated(lock, fn):
    new = copy.deepcopy(lock)
    fn(new)
    return invariants(lock, new, W)


@pytest.mark.parametrize("name, fn", [
    ("item removed", lambda l: l["cards"]["items"].pop()),
    ("id reused", lambda l: l["cards"]["items"].append(dict(l["cards"]["items"][0]))),
    ("next_id decreased", lambda l: l["questions"].update(next_id=100)),
    ("change edited", lambda l: l["changes"][0].update(reason="x")),
    ("change removed", lambda l: l["changes"].pop()),
    ("silent edit", lambda l: l["cards"]["items"][0].update(fp="0" * 40)),
    ("storage key", lambda l: l.update(storage_key="other")),
    ("output", lambda l: l.update(output="mantiq/Other.html")),
    ("topic removed", lambda l: l["topics"].pop(0)),
    ("added without record", lambda l: (l["cards"]["items"].append(
        {"id": 170, "fp": "1" * 40, "content": "2" * 40, "topic": "t1", "status": "active"}),
        l["cards"].update(next_id=171))),
])
def test_invariants_catch(base, name, fn):
    _, _, lock, _ = base
    assert _mutated(lock, fn) != [], name


def test_retired_to_active_needs_restore(ctx):
    book, raw, lock, live = ctx
    raw["cards"].pop(0)
    lock2, _ = apply(raw, book, lock, decide(review(raw, book, lock, W), missing=("retire", {})), "Bilal", 1,
                     "2026-11-28", W)
    lock3 = copy.deepcopy(lock2)
    lock3["cards"]["items"][0]["status"] = "active"
    assert invariants(lock2, lock3, W) != []


# ------------------------------------------------------------------ the build

def test_build_never_writes_the_lock_and_stops_cleanly(tmp_path):
    root = make_repo(tmp_path, [(PILOT, REPO / "books" / PILOT)])
    lock_file = root / "books" / PILOT / "ids.lock.json"
    before = lock_file.read_bytes()
    content = root / "books" / PILOT / "content" / "m5.py"
    content.write_text(content.read_text(encoding="utf-8") + "\nFC.pop(0)\n", encoding="utf-8")
    with pytest.raises(BuildStopped) as e:
        run_book(root, PILOT)
    assert "V3.missing" in codes(e.value.findings)
    assert lock_file.read_bytes() == before
    assert not (root / "mantiq").exists()


@pytest.mark.parametrize("field, value, code", [
    ("storage_key", "munazara-rashidiya-v2", "V3.storage-key"),
    ("output", "mantiq/Other.html", "V3.output-path"),
])
def test_identity_changes_stop(tmp_path, field, value, code):
    root = make_repo(tmp_path, [(PILOT, REPO / "books" / PILOT)])
    path = root / "books" / PILOT / "book.json"
    book = json.loads(path.read_text(encoding="utf-8"))
    book[field] = value
    path.write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(BuildStopped) as e:
        run_book(root, PILOT)
    assert code in codes(e.value.findings)


def test_no_lock_stops(tmp_path):
    root = make_repo(tmp_path, [(PILOT, REPO / "books" / PILOT)])
    (root / "books" / PILOT / "ids.lock.json").unlink()
    with pytest.raises(BuildStopped) as e:
        run_book(root, PILOT)
    assert codes(e.value.findings) == ["V3.no-lock"]


def test_random_edits_never_move_an_id_silently(ctx):
    """Property check: any single change to a stem binds or stops; it never takes another item's ID."""
    book, raw, lock, live = ctx
    rng = random.Random(5)
    for _ in range(40):
        r = copy.deepcopy(raw)
        i = rng.randrange(len(r["questions"]))
        r["questions"][i]["q"] = "نص عشوائي " + str(rng.random())
        ids, findings, _ = bind(r, book, lock, W)
        assert ids is None and codes(findings) == ["V3.missing", "V3.unbound"]


def test_deleting_a_question_changes_no_other_question(ctx):
    book, raw, lock, live = ctx
    raw["questions"].pop(0)
    lock2, _ = apply(raw, book, lock, decide(review(raw, book, lock, W), missing=("retire", {})), "Bilal", 9,
                     "2026-11-28", W)
    ids, _, _ = bind(raw, book, lock2, W)
    m, _ = assemble(raw, book, ids)
    assert m["QUIZ_BANK"] == live["QUIZ_BANK"][1:]  # options, correct and IDs of the rest unchanged
