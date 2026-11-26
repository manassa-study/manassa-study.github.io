"""V6 References (warning only).

Page references («ص …»): until N4 is decided, only their format is checked
(spec section 7, interim rule). A well-formed reference is «ص» followed by a page
number, or a range «ص ٢٢ - ٩٣» whose end is not before its start.

Qur'an references: «سورة البقرة: ١٨٥», «البقرة: ١٨٥» or a range «البقرة: ١٨٥ - ١٨٦»
must name a real surah and verses within its length. Only names that are surahs
are read as Qur'an references, so «المقاصد الحسنة: ١٣٥٦» is ignored. The verse
counts are the standard Hafs (Kufan) count, 6,236 verses in total.
"""
import json
import re

from ..errors import WARNING, Finding
from ..normalize import normalize

SURAHS = [
    ("الفاتحة", 7), ("البقرة", 286), ("آل عمران", 200), ("النساء", 176), ("المائدة", 120), ("الأنعام", 165),
    ("الأعراف", 206), ("الأنفال", 75), ("التوبة", 129), ("يونس", 109), ("هود", 123), ("يوسف", 111),
    ("الرعد", 43), ("إبراهيم", 52), ("الحجر", 99), ("النحل", 128), ("الإسراء", 111), ("الكهف", 110),
    ("مريم", 98), ("طه", 135), ("الأنبياء", 112), ("الحج", 78), ("المؤمنون", 118), ("النور", 64),
    ("الفرقان", 77), ("الشعراء", 227), ("النمل", 93), ("القصص", 88), ("العنكبوت", 69), ("الروم", 60),
    ("لقمان", 34), ("السجدة", 30), ("الأحزاب", 73), ("سبأ", 54), ("فاطر", 45), ("يس", 83),
    ("الصافات", 182), ("ص", 88), ("الزمر", 75), ("غافر", 85), ("فصلت", 54), ("الشورى", 53),
    ("الزخرف", 89), ("الدخان", 59), ("الجاثية", 37), ("الأحقاف", 35), ("محمد", 38), ("الفتح", 29),
    ("الحجرات", 18), ("ق", 45), ("الذاريات", 60), ("الطور", 49), ("النجم", 62), ("القمر", 55),
    ("الرحمن", 78), ("الواقعة", 96), ("الحديد", 29), ("المجادلة", 22), ("الحشر", 24), ("الممتحنة", 13),
    ("الصف", 14), ("الجمعة", 11), ("المنافقون", 11), ("التغابن", 18), ("الطلاق", 12), ("التحريم", 12),
    ("الملك", 30), ("القلم", 52), ("الحاقة", 52), ("المعارج", 44), ("نوح", 28), ("الجن", 28),
    ("المزمل", 20), ("المدثر", 56), ("القيامة", 40), ("الإنسان", 31), ("المرسلات", 50), ("النبأ", 40),
    ("النازعات", 46), ("عبس", 42), ("التكوير", 29), ("الانفطار", 19), ("المطففين", 36), ("الانشقاق", 25),
    ("البروج", 22), ("الطارق", 17), ("الأعلى", 19), ("الغاشية", 26), ("الفجر", 30), ("البلد", 20),
    ("الشمس", 15), ("الليل", 21), ("الضحى", 11), ("الشرح", 8), ("التين", 8), ("العلق", 19),
    ("القدر", 5), ("البينة", 8), ("الزلزلة", 8), ("العاديات", 11), ("القارعة", 11), ("التكاثر", 8),
    ("العصر", 3), ("الهمزة", 9), ("الفيل", 5), ("قريش", 4), ("الماعون", 7), ("الكوثر", 3),
    ("الكافرون", 6), ("النصر", 3), ("المسد", 5), ("الإخلاص", 4), ("الفلق", 5), ("الناس", 6),
]
ALIASES = {"بني إسرائيل": "الإسراء", "براءة": "التوبة", "المؤمن": "غافر", "حم السجدة": "فصلت",
           "القتال": "محمد", "الدهر": "الإنسان", "الانشراح": "الشرح", "اللهب": "المسد", "تبت": "المسد",
           "الزلزال": "الزلزلة"}
VERSES = {normalize(name): n for name, n in SURAHS}
VERSES.update({normalize(a): VERSES[normalize(t)] for a, t in ALIASES.items()})
SHORT_NAMES = {normalize("ص"), normalize("ق")}  # read as a surah only after «سورة»

_D = "[0-9\u0660-\u0669]+"
_L = "\u0621-\u064a\u0671-\u06d3"  # Arabic letters (not digits or punctuation)
PAGE = re.compile(r"(?<![" + _L + r"])ص(?![" + _L + r"])(\s*)(" + _D + r")?(?:\s*-\s*(" + _D + r")?)?")
QREF = re.compile(r"(سورة\s+)?([" + _L + r"]+(?:\s[" + _L + r"]+)?)\s*:\s*(" + _D + r")(?:\s*-\s*(" + _D + r"))?")


def _num(s):
    return int(normalize(s)) if s else None


def _strings(x, path="D"):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _strings(v, f"{path}[{i}]")
    elif isinstance(x, str):
        yield path, x


def page_reference_problems(text):
    """Malformed «ص …» references in one string."""
    out = []
    for m in PAGE.finditer(text):
        space, start, end = m.group(1), m.group(2), m.group(3)
        if start is None:
            continue  # the letter ص on its own, not a reference
        whole = m.group(0).strip()
        if not space:
            out.append(f"«{whole}» has no space after ص")
        elif _num(start) == 0:
            out.append(f"«{whole}» names page 0")
        elif "-" in m.group(0) and end is None:
            out.append(f"«{whole}» has a range with no end")
        elif end is not None and _num(end) < _num(start):
            out.append(f"«{whole}» ends before it starts")
    return out


def quran_reference_problems(text):
    out = []
    for m in QREF.finditer(text):
        prefixed, name, v1, v2 = m.group(1), m.group(2), _num(m.group(3)), _num(m.group(4))
        candidates = [name] + ([name.split()[-1]] if " " in name else [])
        found = None
        for c in candidates:
            key = normalize(c)
            if key in VERSES and (prefixed or key not in SHORT_NAMES):
                found = (c, VERSES[key])
                break
        if found is None:
            if prefixed:
                out.append(f"«{m.group(0).strip()}» names no surah")
            continue
        surah, count = found
        last = v2 if v2 is not None else v1
        if v1 == 0 or last > count or (v2 is not None and v2 < v1):
            out.append(f"«{m.group(0).strip()}»: {surah} has {count} verses")
    return out


def check(model, where):
    out = []
    for path, text in _strings(model):
        for p in page_reference_problems(text):
            out.append(Finding("V6.page-reference", WARNING, f"{path}: {p}", where))
        for p in quran_reference_problems(text):
            out.append(Finding("V6.quran-reference", WARNING, f"{path}: {p}", where))
    return out
