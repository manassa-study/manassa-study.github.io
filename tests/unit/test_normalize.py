"""ar-norm-1 rule by rule, with Arabic, Persian and Urdu samples (spec section 6)."""
import pytest

from mudhakarah.normalize import (card_fingerprint, content_hash, normalize, question_fingerprint,
                                  shown_hash)


@pytest.mark.parametrize("a, b", [
    ("عَلِمَ", "علم"),                         # diacritics
    ("الرَّحْمٰنِ", "الرحمن"),                  # shadda, superscript alef
    ("ذٰلِكَ ۚ", "ذلك"),                        # Qur'anic annotation mark
    ("الكتـــاب", "الكتاب"),                   # tatweel
    ("أحمد إلى آدم ٱلله", "احمد الي ادم الله"),  # alef forms (and ى)
    ("موسى", "موسي"),                          # alef maqsura
    ("ﷲ", "الله"),                              # presentation form (NFKC)
    ("ص ٢٢ - ٩٣", "ص 22 93"),                  # Arabic-Indic digits, dash
    ("۱۲۳", "123"),                             # Persian digits
    ("«المنع» (السند)، [النقض]؛ ما هو؟ نعم. قال: لا!", "المنع السند النقض ما هو نعم قال لا"),
    ("كلمة‏كلمة​", "كلمةكلمة"),      # direction and zero-width marks
    ("  كثير   من \n المسافات  ", "كثير من المسافات"),
    ("کتاب", "كتاب"),                          # Persian/Urdu kaf
    ("یہ", "يه"),                               # Persian/Urdu yeh and heh goal
    ("ھم", "هم"),                               # Urdu heh doachashmee
])
def test_absorbed(a, b):
    assert normalize(a) == normalize(b) == b


@pytest.mark.parametrize("a, b", [
    ("مدرسة", "مدرسه"),  # ta marbuta stays distinct
    ("مؤمن", "مومن"),    # hamza on waw stays
    ("سئل", "سيل"),      # hamza on yeh stays
    ("شيء", "شي"),        # lone hamza stays
    ("المنع", "النقض"),  # different words
])
def test_kept_distinct(a, b):
    assert normalize(a) != normalize(b)


def test_punctuation_never_joins_words():
    assert normalize("ابن-سينا") == "ابن سينا"


def test_fingerprints_are_stable_labels():
    assert card_fingerprint("t1", "ما المنع؟") == card_fingerprint("t1", "ما المَنْعُ")
    assert card_fingerprint("t1", "س") != card_fingerprint("t2", "س")
    a = question_fingerprint("t1", "mc", "س؟", ["أ", "ب", "ج", "د"], "أ")
    assert a == question_fingerprint("t1", "mc", "س", ["د", "ج", "ب", "أ"], "أ")  # option order ignored
    assert a != question_fingerprint("t1", "mc", "س", ["أ", "ب", "ج", "د"], "ب")  # correct answer counts
    assert a != question_fingerprint("t1", "name-it", "س", ["أ", "ب", "ج", "د"], "أ")  # type key counts
    assert len(a) == 40


def test_shown_hash_follows_display_order():
    assert shown_hash(["أ", "ب"]) != shown_hash(["ب", "أ"])
    assert shown_hash(["أَ", "ب"]) == shown_hash(["أ", "ب"])


def test_content_hash_sees_every_raw_change():
    item = {"id": 3, "q": "عَلِمَ", "a": "x"}
    assert content_hash(item) != content_hash(dict(item, q="عُلِّمَ"))
    assert content_hash(item, ("id",)) == content_hash(dict(item, id=4), ("id",))
