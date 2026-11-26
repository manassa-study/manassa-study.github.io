# Minimal fixture book (spec section 4): two topics, three cards, one question of
# each type, one map. Its words are deliberately unlike the pilot's.
META = {"title": "كتاب الاختبار", "authors": "مؤلف الاختبار", "institution": "", "originNote": "", "objectives": ["هدف"]}
CH1 = {"id": "ch1", "badge": "الأول", "title": "الفصل الأول", "subtitle": "", "sections": [
    {"id": "ch1-s1", "title": "القسم", "tag": "الأول", "topics": [
        {"id": "t1", "title": "الدرس الأول", "pages": "ص ١", "blocks": [{"label": "نص", "text": "نص الدرس الأول"}], "sum": ["خلاصة"]},
        {"id": "t2", "title": "الدرس الثاني", "pages": "ص ٢", "blocks": [{"label": "نص", "text": "نص الدرس الثاني"}], "sum": ["خلاصة"]},
    ]}]}
FC = []
def C(tp, cat, q, a):
    FC.append({"id": len(FC) + 1, "cat": cat, "q": q, "a": a, "topic": tp})
C("t1", "تعريفات", "سؤال البطاقة الأولى؟", "جواب الأولى")
C("t1", "تعريفات", "سؤال البطاقة الثانية؟", "جواب الثانية")
C("t2", "أقسام", "سؤال البطاقة الثالثة؟", "جواب الثالثة")
QRAW = [
    {"type": "اختيار من متعدد", "q": "سؤال الاختيار؟", "correct": "أ", "wrong": ["ب", "ج", "د"], "exp": "شرح", "topic": "t1"},
    {"type": "صح أو خطأ", "q": "عبارة صحيحة.", "tf": True, "exp": "شرح", "topic": "t1"},
    {"type": "ما اسم هذا؟", "q": "ما اسم هذا الشيء؟", "correct": "اسم", "wrong": ["آخر", "ثالث", "رابع"], "exp": "شرح", "topic": "t2"},
]
EX = [{"ayah": "مثال", "surah": "مصدر", "category": "فئة", "detail": "تفصيل", "topic": "t2"}]
TB = [{"title": "جدول", "headers": ["أ", "ب"], "rows": [["١", "٢"]]}]
MM = [{"id": "m1", "type": "tree", "group": "الأول", "title": "خريطة", "sub": "ص ١", "branches": [{"t": "فرع", "p": "ص ١", "n": "١", "c": ["عنصر"]}]}]
CAPS = [{"title": "للحفظ", "items": [{"k": "مفتاح", "v": "قيمة"}]}]
