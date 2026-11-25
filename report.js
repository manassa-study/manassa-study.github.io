/* منصة المذاكرة: زر «أبلغ عن خطأ / اقتراح»
 * One shared script for every course page. Each page loads it with:
 *   <script src="https://manassa-study.github.io/report.js" defer></script>
 * The student picks a type and writes the note; the course, the place in the
 * course and the page link are filled in automatically, then the note is sent
 * to the platform's Google Form (answers land in its Google Sheet).
 *
 * To connect the Google Form, fill FORM below:
 *   id      the long id in the form's link: docs.google.com/forms/d/e/<id>/viewform
 *   entries the entry.NNN number of each question
 *   types   the exact choices of the «نوع الملاحظة» question, in this order
 */
(function () {
  "use strict";
  if (window.__msReport) return;
  window.__msReport = true;

  var FORM = {
    id: "1FAIpQLSfQZEaQiFQ7JAS-BIwYuceFYHmGIogB3yzZziDiCmxGqJWdZQ",
    entries: { course: "1591633300", place: "326955045", type: "1696159737", details: "485428648", contact: "34760340" },
    types: ["خطأ في المعلومة", "خطأ إملائي أو طباعي", "نقص أو شيء مفقود", "مشكلة في الموقع", "اقتراح"]
  };
  var TYPES = [
    { k: 0, t: "خطأ في المعلومة", i: "⚠️" },
    { k: 1, t: "خطأ إملائي أو طباعي", i: "✏️" },
    { k: 2, t: "نقص أو شيء مفقود", i: "🧩" },
    { k: 3, t: "مشكلة في الموقع", i: "🛠️" },
    { k: 4, t: "اقتراح", i: "💡" }
  ];
  var READY = !!(FORM.id && FORM.entries.details);

  function txt(el) { return el ? (el.textContent || "").replace(/\s+/g, " ").trim() : ""; }
  function q(s, r) { return (r || document).querySelector(s); }

  function course() {
    return txt(q(".brand-t")) || txt(q("#title")) || (document.title || "").split(/\s[—·|-]\s/)[0].trim();
  }

  function place() {
    if (typeof window.reportPlace === "function") { try { var p = window.reportPlace(); if (p) return p; } catch (e) {} }
    var view = q("#view");
    if (view) {
      var crumb = Array.prototype.map.call(view.querySelectorAll(".crumb span"), txt).filter(Boolean);
      var h = txt(q(".h1", view)) || txt(q("h1,h2", view));
      return crumb.concat(h ? [h] : []).join(" › ");
    }
    var mid = innerHeight / 2, best = null, bestD = 1e9;
    var pages = document.querySelectorAll(".page");
    if (pages.length) {
      Array.prototype.forEach.call(pages, function (el) {
        var r = el.getBoundingClientRect(), d = r.top > mid ? r.top - mid : (r.bottom < mid ? mid - r.bottom : 0);
        if (d < bestD) { bestD = d; best = el; }
      });
      var n = best && txt(q(".n", best));
      if (n) return "صفحة " + n;
    }
    var heads = document.querySelectorAll("main h1, main h2, main h3"), last = "";
    Array.prototype.forEach.call(heads, function (el) { if (el.getBoundingClientRect().top < mid) last = txt(el); });
    return last || txt(q("main h1, main h2, h1"));
  }

  var css = "" +
    ".msr-fab{position:fixed;z-index:56;left:max(14px,env(safe-area-inset-left,0px));bottom:calc(var(--msr-b,0px) + 14px + env(safe-area-inset-bottom,0px));" +
    "display:inline-flex;align-items:center;gap:6px;height:40px;padding:0 14px 0 12px;border-radius:999px;border:1px solid var(--msr-line);" +
    "background:var(--msr-bg);color:var(--msr-ink);font:600 13px/1 'Tajawal','IBM Plex Sans Arabic','Noto Kufi Arabic',system-ui,sans-serif;" +
    "box-shadow:0 4px 14px rgba(0,0,0,.16);cursor:pointer;opacity:.94;-webkit-tap-highlight-color:transparent}" +
    ".msr-fab:hover,.msr-fab:focus-visible{opacity:1;border-color:var(--msr-acc);outline:none}" +
    ".msr-fab svg{width:17px;height:17px;flex:none;stroke:var(--msr-acc);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}" +
    ".msr-wrap{position:fixed;inset:0;z-index:100;display:flex;align-items:flex-end;justify-content:center;background:rgba(5,12,20,.5);" +
    "padding:16px;padding-bottom:max(16px,env(safe-area-inset-bottom,0px))}" +
    "@media(min-width:640px){.msr-wrap{align-items:center}}" +
    ".msr-box{direction:rtl;width:100%;max-width:460px;max-height:calc(100vh - 32px);overflow:auto;background:var(--msr-bg);color:var(--msr-ink);" +
    "border:1px solid var(--msr-line);border-radius:16px;padding:18px 18px 16px;box-shadow:0 20px 50px rgba(0,0,0,.3);" +
    "font:400 14.5px/1.7 'Tajawal','IBM Plex Sans Arabic','Noto Kufi Arabic',system-ui,sans-serif}" +
    ".msr-box *{box-sizing:border-box;font-family:inherit}" +
    ".msr-h{display:flex;align-items:center;gap:8px;margin:0 0 2px}" +
    ".msr-h b{flex:1;font-size:17px}" +
    ".msr-x{width:34px;height:34px;border-radius:50%;border:0;background:transparent;color:var(--msr-mute);font-size:22px;line-height:1;cursor:pointer}" +
    ".msr-x:hover{background:var(--msr-soft)}" +
    ".msr-sub{margin:0 0 12px;color:var(--msr-mute);font-size:13px}" +
    ".msr-where{background:var(--msr-soft);border-radius:10px;padding:8px 12px;margin:0 0 14px;font-size:13px;line-height:1.6}" +
    ".msr-where span{display:block;color:var(--msr-mute);font-size:12px}" +
    ".msr-l{display:block;font-weight:700;font-size:13.5px;margin:0 0 6px}" +
    ".msr-l i{font-style:normal;font-weight:400;color:var(--msr-mute)}" +
    ".msr-types{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}" +
    ".msr-t{border:1px solid var(--msr-line);background:transparent;color:var(--msr-ink);border-radius:999px;padding:6px 11px;font-size:13px;cursor:pointer}" +
    ".msr-t[aria-pressed=true]{background:var(--msr-acc);border-color:var(--msr-acc);color:#fff}" +
    ".msr-box textarea,.msr-box input{width:100%;border:1px solid var(--msr-line);border-radius:10px;background:var(--msr-field);color:var(--msr-ink);" +
    "padding:9px 11px;font-size:15px;line-height:1.7;margin:0 0 12px}" +
    ".msr-box textarea{min-height:110px;resize:vertical}" +
    ".msr-box textarea:focus,.msr-box input:focus{outline:2px solid var(--msr-acc);outline-offset:-1px;border-color:transparent}" +
    ".msr-go{width:100%;height:46px;border:0;border-radius:12px;background:var(--msr-acc);color:#fff;font-size:15.5px;font-weight:700;cursor:pointer}" +
    ".msr-go[disabled]{opacity:.55;cursor:default}" +
    ".msr-err{color:#c0392b;font-size:13px;margin:-4px 0 10px;min-height:0}" +
    ".msr-ok{text-align:center;padding:10px 4px 4px}" +
    ".msr-ok .msr-big{font-size:42px;line-height:1.2}" +
    ".msr-ok b{display:block;font-size:17px;margin:6px 0 4px}" +
    ".msr-ok p{margin:0 0 16px;color:var(--msr-mute)}" +
    ":root{--msr-bg:#fff;--msr-ink:#18222f;--msr-mute:#5d6b7c;--msr-line:#d6dee8;--msr-soft:#eef2f6;--msr-field:#fbfcfd;--msr-acc:#1f7a5c}" +
    "@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--msr-bg:#152030;--msr-ink:#e6edf5;--msr-mute:#9db0c4;--msr-line:#2c3c52;--msr-soft:#1d2b3e;--msr-field:#101a28;--msr-acc:#3fae86}}" +
    ":root[data-theme=dark]{--msr-bg:#152030;--msr-ink:#e6edf5;--msr-mute:#9db0c4;--msr-line:#2c3c52;--msr-soft:#1d2b3e;--msr-field:#101a28;--msr-acc:#3fae86}" +
    "@media print{.msr-fab,.msr-wrap{display:none!important}}";

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  var fab, wrap, lastFocus;

  function lift() {
    var b = q(".bnav"), h = 0;
    if (b && getComputedStyle(b).display !== "none") h = b.getBoundingClientRect().height - (parseFloat(getComputedStyle(b).paddingBottom) || 0);
    fab.style.setProperty("--msr-b", Math.max(0, h) + "px");
  }

  function close() {
    if (!wrap) return;
    wrap.remove(); wrap = null;
    document.removeEventListener("keydown", onKey, true);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function onKey(e) { if (e.key === "Escape") { e.stopPropagation(); close(); } }

  function open() {
    if (wrap) return;
    lastFocus = document.activeElement;
    var c = course(), p = place(), type = null;
    wrap = el("div", { "class": "msr-wrap" });
    var box = el("div", { "class": "msr-box", role: "dialog", "aria-modal": "true", "aria-labelledby": "msr-h" });
    box.innerHTML =
      '<div class="msr-h"><b id="msr-h">أبلغ عن خطأ أو اقترح</b><button class="msr-x" type="button" aria-label="إغلاق">×</button></div>' +
      '<p class="msr-sub">رأيت خطأً أو شيئاً ناقصاً؟ اكتبه هنا، وسنراجعه ونصلحه بإذن الله.</p>' +
      '<div class="msr-where"><span>الموضع (يُرسل تلقائياً)</span>' + esc(c) + (p ? " · " + esc(p) : "") + "</div>" +
      '<span class="msr-l">نوع الملاحظة</span><div class="msr-types">' +
      TYPES.map(function (t) { return '<button type="button" class="msr-t" aria-pressed="false" data-k="' + t.k + '">' + t.i + " " + esc(t.t) + "</button>"; }).join("") +
      "</div>" +
      '<label class="msr-l" for="msr-d">التفاصيل</label>' +
      '<textarea id="msr-d" maxlength="3000" placeholder="مثال: في الفقرة الثانية، سنة الوفاة مكتوبة ٣١٠ والصواب ٣١١."></textarea>' +
      '<label class="msr-l" for="msr-c">اسمك أو وسيلة للتواصل <i>(اختياري)</i></label>' +
      '<input id="msr-c" maxlength="200" autocomplete="off" placeholder="إن أحببت أن نرد عليك">' +
      '<div class="msr-err" role="alert"></div>' +
      '<button class="msr-go" type="button">إرسال</button>';
    wrap.appendChild(box);
    document.body.appendChild(wrap);
    document.addEventListener("keydown", onKey, true);
    wrap.addEventListener("click", function (e) { if (e.target === wrap) close(); });
    q(".msr-x", box).onclick = close;

    var d = q("#msr-d", box), ct = q("#msr-c", box), err = q(".msr-err", box), go = q(".msr-go", box);
    Array.prototype.forEach.call(box.querySelectorAll(".msr-t"), function (b) {
      b.onclick = function () {
        type = +b.getAttribute("data-k");
        Array.prototype.forEach.call(box.querySelectorAll(".msr-t"), function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      };
    });
    setTimeout(function () { d.focus(); }, 30);

    go.onclick = function () {
      var details = d.value.trim();
      if (!details) { err.textContent = "اكتب ملاحظتك أولاً."; d.focus(); return; }
      err.textContent = "";
      if (type == null) type = 0;
      var link = location.href;
      if (!READY) { err.textContent = "النموذج قيد الإعداد، جرّب لاحقاً إن شاء الله."; return; }
      var f = new URLSearchParams(), E = FORM.entries;
      f.append("entry." + E.course, c);
      f.append("entry." + E.place, (p ? p + "\n" : "") + link);
      if (E.type) f.append("entry." + E.type, FORM.types[type]);
      f.append("entry." + E.details, details);
      if (E.contact && ct.value.trim()) f.append("entry." + E.contact, ct.value.trim());
      go.disabled = true; go.textContent = "جارٍ الإرسال…";
      fetch("https://docs.google.com/forms/d/e/" + FORM.id + "/formResponse", { method: "POST", mode: "no-cors", body: f })
        .then(function () {
          box.innerHTML = '<div class="msr-ok"><div class="msr-big">🌿</div><b>وصلت ملاحظتك، جزاك الله خيراً</b>' +
            "<p>سنراجعها ونصلح ما يلزم بإذن الله.</p>" +
            '<button class="msr-go" type="button">إغلاق</button></div>';
          q(".msr-go", box).onclick = close;
          q(".msr-go", box).focus();
        })
        .catch(function () {
          go.disabled = false; go.textContent = "إرسال";
          err.textContent = "تعذّر الإرسال. تأكد من اتصالك بالإنترنت ثم أعد المحاولة.";
        });
    };
  }

  function init() {
    document.head.appendChild(el("style", { id: "msr-css" }, css));
    fab = el("button", { "class": "msr-fab", type: "button", "aria-label": "أبلغ عن خطأ أو اقترح" },
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 21V4M5 4h11l-2 4 2 4H5"/></svg><span>أبلغ عن خطأ</span>');
    fab.onclick = open;
    document.body.appendChild(fab);
    lift();
    addEventListener("resize", lift);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
