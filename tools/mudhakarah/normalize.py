"""Normalization `ar-norm-1` and fingerprints (spec section 6; docs/normalization.md).

Edits that don't change meaning (diacritics, spacing, punctuation, letter-form
variants) keep a fingerprint; different words change it. The rules are versioned:
changing any of them means a new version name and a migration.
"""
import hashlib
import json
import re
import unicodedata

NORMALIZATION = "ar-norm-1"
ALGORITHM = "sha1"
SEP = "\u001f"        # between fingerprint fields (spec)
LIST_SEP = "\u001e"   # between the options inside the options field

CARD_FIELDS = ["topic", "q"]
QUESTION_FIELDS = ["topic", "type_key", "q", "options_sorted", "correct"]

_DIACRITICS = re.compile("[ً-ٰٟۖ-ۭـ]")
_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",  # أ إ آ ٱ -> ا
    "ى": "ي",                                                               # ى -> ي
    "ی": "ي",                                                               # Persian/Urdu ی -> ي
    "ک": "ك",                                                               # ک -> ك
    "ہ": "ه", "ھ": "ه",                                           # ہ ھ -> ه
})
_DIGITS = str.maketrans({**{chr(0x0660 + i): str(i) for i in range(10)},
                         **{chr(0x06f0 + i): str(i) for i in range(10)}})
_ZERO_WIDTH = re.compile("[​-‏]")
_SPACE = re.compile(r"\s+")


def normalize(text):
    """ar-norm-1. Rules applied in this order:
    1. Unicode NFKC.
    2. Remove diacritics U+064B-U+065F, superscript alef U+0670, Qur'anic marks U+06D6-U+06ED, tatweel U+0640.
    3. Fold alef forms to ا; ى to ي; ی to ي; ک to ك; ہ ھ to ه.
    4. Arabic-Indic and Persian digits to 0-9.
    5. Punctuation and symbols (Unicode categories P* and S*) are removed: each becomes a space,
       so two words never join, and step 7 then drops the space.
    6. Remove zero-width and direction marks U+200B-U+200F.
    7. Collapse all whitespace to single spaces and trim.
    ة/ه, ؤ, ئ and a lone hamza stay distinct."""
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = unicodedata.normalize("NFKC", text)
    text = _DIACRITICS.sub("", text)
    text = text.translate(_FOLD)
    text = text.translate(_DIGITS)
    text = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in text)
    text = _ZERO_WIDTH.sub("", text)
    return _SPACE.sub(" ", text).strip()


def _hash(parts):
    return hashlib.sha1(SEP.join(parts).encode("utf-8")).hexdigest()


def card_fingerprint(topic, q):
    return _hash([normalize(topic), normalize(q)])


def question_fingerprint(topic, type_key, q, options, correct):
    """`options` is the type's own option texts (any order), or None for a type without
    options (true/false); `correct` is the correct answer's text, never its position."""
    opts = "" if options is None else LIST_SEP.join(sorted(normalize(o) for o in options))
    return _hash([normalize(topic), type_key, normalize(q), opts, normalize(correct)])


def shown_hash(display_options):
    """F4: the option texts in the order students see them."""
    return _hash([normalize(o) for o in display_options])


def content_hash(item, exclude=()):
    """F1: the whole raw item exactly as written, every field, before normalization.
    `exclude` names fields that are not content (a card's positional `id`, which the
    lock replaces)."""
    data = {k: v for k, v in item.items() if k not in exclude}
    return hashlib.sha1(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
