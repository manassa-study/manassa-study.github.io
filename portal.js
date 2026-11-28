(function(){
"use strict";
var SUPABASE_URL="https://bkqyroqdhkfofoevicjg.supabase.co";
var SUPABASE_KEY="sb_publishable_mmRkRsFroni2dgiF8eTXtQ__WGqONmH";
var BOOKS=[
 {key:"madkhal-fiqh-v1",title:"المدخل إلى الفقه الإسلامي",href:"/fiqh/MadkhalFiqhAQU.html"},
 {key:"munazara-rashidiya-v1",title:"المناظرة الرشيدية",href:"/mantiq/MunazaraRashidiyaAQU.html"},
 {key:"tafsir-muqaran-v1",title:"دراسة التفسير المقارن",href:"/Tafseer/TafseerMaqaranAQU.html"},
 {key:"takhreej-asaneed-v1",title:"التخريج ودراسة الأسانيد",href:"/hadith/TakhreejAsaneedAQU.html"},
 {key:"tareekh-tafseer-v1",title:"دراسة تاريخ التفسير",href:"/Tafseer/TareekhTafseerAQU.html"}
];
var $=function(id){return document.getElementById(id)};
var client=null,currentUser=null,loadingFor=null;
var authBox=$("auth-summary"),signedOut=$("signed-out"),signedIn=$("signed-in");
var dashboard=$("dashboard"),status=$("portal-status"),emailMessage=$("email-message");
function number(n){return new Intl.NumberFormat("ar").format(n||0)}
function message(text,isError){status.textContent=text;status.classList.toggle("error",!!isError);status.hidden=!text}
function object(value){return value&&typeof value==="object"&&!Array.isArray(value)?value:{}}
function countTrue(value){var o=object(value);return Object.keys(o).filter(function(key){return !!o[key]}).length}
function quizStats(history){
 var list=Array.isArray(history)?history:[],correct=0,total=0;
 list.forEach(function(item){if(!item||!Number.isFinite(Number(item.c))||!Number.isFinite(Number(item.n))||Number(item.n)<=0)return;correct+=Math.min(Number(item.n),Math.max(0,Number(item.c)));total+=Number(item.n)});
 return {attempts:list.length,correct:correct,total:total,accuracy:total?Math.round(correct/total*100):null}
}
function stateFromRow(row){
 var value=row&&row.state;
 if(typeof value==="string"){try{value=JSON.parse(value)}catch(e){value={}}}
 return object(value);
}
function metric(value,label){
 var box=document.createElement("div");box.className="metric";
 var numberNode=document.createElement("strong");numberNode.textContent=value;
 var labelNode=document.createElement("span");labelNode.textContent=label;
 box.appendChild(numberNode);box.appendChild(labelNode);return box;
}
function bookMetric(value,label){
 var box=document.createElement("div");box.className="book-stat";
 var n=document.createElement("b");n.textContent=value;
 var caption=document.createElement("span");caption.textContent=label;
 box.appendChild(n);box.appendChild(caption);return box;
}
function render(rows){
 var byCourse={};(rows||[]).forEach(function(row){if(row&&typeof row.course==="string")byCourse[row.course]=row});
 var totals={done:0,mastered:0,attempts:0,correct:0,answers:0};
 var grid=$("book-grid"),summary=$("summary-grid");grid.textContent="";summary.textContent="";
 BOOKS.forEach(function(book){
  var state=stateFromRow(byCourse[book.key]);
  var done=countTrue(state.done),mastered=countTrue(state.mastered),quiz=quizStats(state.quizHist);
  totals.done+=done;totals.mastered+=mastered;totals.attempts+=quiz.attempts;totals.correct+=quiz.correct;totals.answers+=quiz.total;
  var card=document.createElement("article");card.className="book-card";
  var title=document.createElement("h3");title.textContent=book.title;card.appendChild(title);
  var stats=document.createElement("div");stats.className="book-stats";
  stats.appendChild(bookMetric(number(done),"مطالب مكتملة"));
  stats.appendChild(bookMetric(number(mastered),"بطاقات متقنة"));
  stats.appendChild(bookMetric(number(quiz.attempts),"محاولات اختبار"));
  card.appendChild(stats);
  var foot=document.createElement("div");foot.className="book-foot";
  var accuracy=document.createElement("span");accuracy.textContent=quiz.accuracy===null?"لا تتوفر نتيجة محفوظة":"دقة الإجابات: "+number(quiz.accuracy)+"٪";
  var link=document.createElement("a");link.className="book-link";link.href=book.href;link.textContent="تابع المذاكرة ←";
  foot.appendChild(accuracy);foot.appendChild(link);card.appendChild(foot);grid.appendChild(card);
 });
 var accuracy=totals.answers?Math.round(totals.correct/totals.answers*100):null;
 summary.appendChild(metric(number(totals.done),"مطالب مكتملة عبر الكتب"));
 summary.appendChild(metric(number(totals.mastered),"بطاقات أتقنتها"));
 summary.appendChild(metric(number(totals.attempts),"محاولات الاختبار"));
 summary.appendChild(metric(accuracy===null?"—":number(accuracy)+"٪","دقة الإجابات في المحاولات المحفوظة"));
 dashboard.hidden=false;
}
function signedOutState(text){
 currentUser=null;dashboard.hidden=true;signedOut.hidden=false;signedIn.hidden=true;
 $("account-email").textContent="";
 authBox.textContent=text||"سجّل الدخول لعرض التقدم المحفوظ في حسابك.";
 message("",false);
}
function loadProgress(user){
 if(!user||!client)return;
 if(loadingFor===user.id)return;
 loadingFor=user.id;currentUser=user;dashboard.hidden=true;signedOut.hidden=true;signedIn.hidden=false;
 $("account-email").textContent=user.email||"";
 authBox.textContent="سيُعرض هنا التقدم المتزامن المحفوظ في حسابك.";
 message("جارٍ تحميل تقدمك…",false);
 client.from("progress").select("course,state").eq("user_id",user.id).in("course",BOOKS.map(function(book){return book.key}))
 .then(function(result){
   loadingFor=null;
   if(!currentUser||currentUser.id!==user.id)return;
   if(result.error){message("تعذّر تحميل التقدم الآن. حاول مرة أخرى بعد قليل.",true);return}
   render(result.data||[]);message("",false);
 }).catch(function(){loadingFor=null;if(currentUser&&currentUser.id===user.id)message("تعذّر تحميل التقدم الآن. حاول مرة أخرى بعد قليل.",true)});
}
function authChanged(session){
 var user=session&&session.user;
 if(user){loadProgress(user)}else{loadingFor=null;signedOutState("سجّل الدخول لعرض التقدم المتزامن في حسابك.")}
}
function init(){
 if(!window.supabase||!window.supabase.createClient){signedOutState("تعذّر تجهيز تسجيل الدخول. أعد تحميل الصفحة أو حاول لاحقاً.");return}
 try{client=window.supabase.createClient(SUPABASE_URL,SUPABASE_KEY,{auth:{persistSession:true,detectSessionInUrl:true,flowType:"pkce",storageKey:"study-auth"}})}
 catch(e){signedOutState("تعذّر تجهيز تسجيل الدخول. أعد تحميل الصفحة أو حاول لاحقاً.");return}
 client.auth.onAuthStateChange(function(event,session){authChanged(session)});
 client.auth.getSession().then(function(result){if(result.error){signedOutState("تعذّر التحقق من الجلسة. حاول تسجيل الدخول مجدداً.");return}authChanged(result.data&&result.data.session)}).catch(function(){signedOutState("تعذّر التحقق من الجلسة. حاول تسجيل الدخول مجدداً.")});
 $("google-login").addEventListener("click",function(){
  client.auth.signInWithOAuth({provider:"google",options:{redirectTo:location.origin+location.pathname,queryParams:{prompt:"select_account"}}}).then(function(result){if(result.error)emailMessage.textContent="تعذّر بدء تسجيل الدخول. حاول مرة أخرى."});
 });
 $("email-form").addEventListener("submit",function(event){
  event.preventDefault();var email=$("email").value.trim();if(!email)return;
  $("send-code").disabled=true;emailMessage.textContent="جارٍ إرسال الرمز…";
  client.auth.signInWithOtp({email:email,options:{shouldCreateUser:true,emailRedirectTo:location.origin+location.pathname}}).then(function(result){
   $("send-code").disabled=false;
   if(result.error){emailMessage.textContent="تعذّر إرسال الرمز. تحقق من البريد وحاول لاحقاً.";return}
   $("code-wrap").hidden=false;emailMessage.textContent="أرسلنا رمز الدخول إلى بريدك الإلكتروني."; $("code").focus();
  }).catch(function(){$("send-code").disabled=false;emailMessage.textContent="تعذّر إرسال الرمز الآن."});
 });
 $("verify-code").addEventListener("click",function(){
  var email=$("email").value.trim(),code=$("code").value.replace(/\D/g,"");
  if(!email||code.length<6){emailMessage.textContent="أدخل البريد ورمز الدخول كاملين.";return}
  $("verify-code").disabled=true;emailMessage.textContent="جارٍ التحقق…";
  client.auth.verifyOtp({email:email,token:code,type:"email"}).then(function(result){
   $("verify-code").disabled=false;
   if(result.error){emailMessage.textContent="الرمز غير صحيح أو انتهت صلاحيته. اطلب رمزاً جديداً.";return}
   emailMessage.textContent="تم تسجيل الدخول.";
  }).catch(function(){$("verify-code").disabled=false;emailMessage.textContent="تعذّر التحقق من الرمز."});
 });
 $("logout").addEventListener("click",function(){client.auth.signOut().then(function(){signedOutState("سجّلت الخروج.")})});
}
init();
})();