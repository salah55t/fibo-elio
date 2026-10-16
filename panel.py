#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
panel.py — لوحة تحكم Fibo-Elio السبرانية (عربية RTL، نيون مشع على أسود متحرك)
[FE1.4.0] إعادة تصميم بأسلوب منصات الهكر: خلفية سوداء متحركة (شبكة + هالات نيون
نابضة + خطوط مسح)، ألوان نيون مشعة بتوهج، خط Orbitron/Share Tech Mono.
[FE1.5.0] قسم «فحص أزواج باينانس (الكون الكامل)»: جدول درجات الملاءمة
للاستراتيجية + زر «فحص الآن» + بطاقة حالة الفحص.
[FE1.5.0] إصلاحات مراجعة اللوحة الحية: تهريب HTML (esc) لكل بيانات API (كان
innerHTML مكشوفًا على XSS مخزّن عبر رسائل الإشعارات)، جداول مغلقة/التقاطات/الفحص
ضمن .tbl-wrap (كانت تفيض على الموبايل بلا تمرير)، عارضة مستقلة لكل قسم (كان خطأ
واحد يجمّد تحديث اللوحة كاملة صامتًا)، usd/cls آمنة ضد null، حارس تكرار refresh
+ إيقاف عند إخفاء التبويب، لا اختطاف مفتاح التداول الحقيقي أثناء الطلب الجاري.
تعرض أيضًا: بطاقة اتصال باينانس الحية، زر التداول الحقيقي (مثل V9)، الحالة
الورقية، الصفقات المفتوحة/المعلقة بتتبع حي وفرز حقيقية/ورقية، إغلاق/إلغاء يدوي،
المغلقة، التقاطات الموجات، الإشعارات، شارة مصدر كل سعر (⚡WS/REST)، البقاء الحي
والذاكرة.
"""

BOT_VERSION = "FE1.9.9"

PANEL_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fibo-Elio — إليوت + فيبوناتشي</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Share+Tech+Mono&display=swap');
  :root {
    --bg:#010104; --panel:rgba(2,14,11,.78); --panel2:rgba(0,9,14,.82);
    --line:rgba(0,255,156,.22); --line2:rgba(0,229,255,.16);
    --neon:#00ff9c; --cyan:#00e5ff; --mag:#ff2bd6; --yel:#ffe600; --red:#ff3355; --vio:#b026ff;
    --txt:#c9f7e5; --mut:#5f8a80;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--txt); font-family:'Segoe UI',Tahoma,Arial,sans-serif;
         padding:18px; overflow-x:hidden; min-height:100vh; }
  /* ── الخلفية السوداء المتحركة: شبكة نيون + هالات نابضة + خطوط مسح ── */
  .bg-grid { position:fixed; inset:0; z-index:-3;
    background-image:linear-gradient(rgba(0,255,156,.06) 1px,transparent 1px),
                     linear-gradient(90deg,rgba(0,255,156,.06) 1px,transparent 1px);
    background-size:44px 44px;
    animation:gridmove 14s linear infinite;
    -webkit-mask-image:radial-gradient(ellipse at 50% 0%,#000 25%,transparent 78%);
    mask-image:radial-gradient(ellipse at 50% 0%,#000 25%,transparent 78%); }
  @keyframes gridmove { from{background-position:0 0} to{background-position:0 44px} }
  .orb { position:fixed; border-radius:50%; filter:blur(95px); z-index:-2; opacity:.15;
         animation:orbfloat 12s ease-in-out infinite alternate; }
  .orb1 { width:430px; height:430px; background:var(--neon); top:-130px; left:-110px; }
  .orb2 { width:390px; height:390px; background:var(--cyan); bottom:-150px; right:-90px; animation-delay:-4s; }
  .orb3 { width:310px; height:310px; background:var(--mag); top:38%; right:28%; opacity:.09; animation-delay:-8s; }
  @keyframes orbfloat { from{transform:translate(0,0) scale(1)} to{transform:translate(60px,44px) scale(1.14)} }
  .scanlines { position:fixed; inset:0; z-index:70; pointer-events:none; opacity:.30;
    background:repeating-linear-gradient(0deg,rgba(0,0,0,.28) 0 1px,transparent 1px 3px); }
  .scanbar { position:fixed; left:0; right:0; height:110px; z-index:71; pointer-events:none;
    background:linear-gradient(180deg,transparent,rgba(0,255,156,.05),transparent);
    animation:scanmove 7s linear infinite; }
  @keyframes scanmove { from{top:-120px} to{top:100%} }
  .wrap { max-width:1200px; margin:0 auto; position:relative; }
  header { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin-bottom:12px;
    padding:12px 14px; border:1px solid var(--line); border-radius:14px;
    background:var(--panel); backdrop-filter:blur(5px);
    box-shadow:0 0 24px rgba(0,255,156,.08), inset 0 0 22px rgba(0,255,156,.03); }
  h1 { font-family:'Orbitron','Share Tech Mono',monospace; font-size:1.45rem; color:var(--neon);
    text-shadow:0 0 10px rgba(0,255,156,.85), 0 0 28px rgba(0,255,156,.4);
    letter-spacing:1px; animation:flicker 6s infinite; }
  h1 small { color:var(--mut); font-weight:400; font-size:.72rem; text-shadow:none; display:block; margin-top:2px; }
  @keyframes flicker { 0%,100%{opacity:1} 91%{opacity:1} 92%{opacity:.55} 93%{opacity:1} 96%{opacity:.7} 97%{opacity:1} }
  .badge { padding:4px 12px; border-radius:999px; font-size:.74rem; font-weight:700; border:1px solid;
    text-shadow:0 0 6px currentColor; white-space:nowrap; }
  .b-orig { background:rgba(0,229,255,.08); color:var(--cyan); border-color:var(--cyan); }
  .b-paper { background:rgba(0,229,255,.06); color:var(--cyan); border-color:var(--cyan); border-style:dashed; }
  .b-real { background:rgba(255,51,85,.12); color:var(--red); border-color:var(--red); animation:realpulse 1.6s infinite; }
  .b-on { background:rgba(0,255,156,.1); color:var(--neon); border-color:var(--neon); }
  .b-off { background:rgba(95,138,128,.1); color:var(--mut); border-color:var(--mut); text-shadow:none; }
  .b-bin-ok { background:rgba(0,255,156,.08); color:var(--neon); border-color:var(--neon); }
  .b-bin-bad { background:rgba(255,51,85,.1); color:var(--red); border-color:var(--red); }
  .b-ws { background:rgba(0,229,255,.08); color:var(--cyan); border-color:var(--cyan); }
  .b-ws-off { background:rgba(95,138,128,.1); color:var(--mut); border-color:var(--mut); text-shadow:none; }
  @keyframes realpulse { 0%,100%{box-shadow:0 0 6px rgba(255,51,85,.5)} 50%{box-shadow:0 0 18px rgba(255,51,85,.95)} }
  .spacer { flex:1; }
  button.act { background:rgba(0,255,156,.05); border:1px solid var(--neon); color:var(--neon);
    border-radius:10px; padding:8px 14px; cursor:pointer; font-size:.82rem;
    font-family:'Share Tech Mono',monospace; text-shadow:0 0 6px currentColor;
    box-shadow:0 0 10px rgba(0,255,156,.12); transition:.2s; }
  button.act:hover { background:rgba(0,255,156,.14); box-shadow:0 0 18px rgba(0,255,156,.45); }
  button.act:disabled { opacity:.55; cursor:wait; }
  button.act.danger { border-color:var(--red); color:var(--red); box-shadow:0 0 10px rgba(255,51,85,.12); }
  button.act.danger:hover { background:rgba(255,51,85,.14); box-shadow:0 0 18px rgba(255,51,85,.45); }
  /* ── زر التداول الحقيقي: مفتاح نيون أحمر مثل V9 ── */
  .real-ctl { display:flex; align-items:center; gap:10px; padding:6px 12px; border-radius:12px;
    border:1px solid rgba(255,51,85,.4); background:rgba(255,51,85,.05); }
  .real-ctl .rlbl { font-size:.8rem; font-weight:700; color:var(--red); text-shadow:0 0 6px rgba(255,51,85,.6); white-space:nowrap; }
  .switch { position:relative; display:inline-block; width:52px; height:27px; flex:none; }
  .switch input { opacity:0; width:0; height:0; }
  .slider { position:absolute; inset:0; background:#0a0f14; border:1px solid var(--red); border-radius:999px;
    transition:.25s; box-shadow:inset 0 0 8px rgba(255,51,85,.35); cursor:pointer; }
  .slider::before { content:''; position:absolute; width:19px; height:19px; top:3px; right:4px; border-radius:50%;
    background:#3a4a52; transition:.25s; }
  .switch input:checked + .slider { background:rgba(255,51,85,.28); border-color:var(--red);
    box-shadow:0 0 16px rgba(255,51,85,.8), inset 0 0 8px rgba(255,51,85,.4); }
  .switch input:checked + .slider::before { transform:translateX(-24px); background:var(--red);
    box-shadow:0 0 10px var(--red); }
  .banner { width:100%; text-align:center; font-size:.8rem; font-weight:700; padding:9px 12px;
    border-radius:10px; margin-bottom:14px; }
  .banner-paper { color:var(--cyan); border:1px dashed var(--cyan); background:rgba(0,229,255,.05);
    text-shadow:0 0 6px rgba(0,229,255,.5); }
  .banner-real { color:var(--red); border:1px solid var(--red); background:rgba(255,51,85,.07);
    text-shadow:0 0 8px rgba(255,51,85,.7); animation:realpulse 1.6s infinite; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(165px,1fr)); gap:12px; margin-bottom:16px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:13px 15px;
    position:relative; overflow:hidden; transition:.25s; backdrop-filter:blur(4px); }
  .card::before { content:''; position:absolute; top:0; right:0; left:0; height:1px;
    background:linear-gradient(90deg,transparent,var(--neon),transparent); opacity:.65; }
  .card:hover { border-color:var(--neon); box-shadow:0 0 18px rgba(0,255,156,.22), inset 0 0 14px rgba(0,255,156,.04);
    transform:translateY(-2px); }
  .card .lbl { color:var(--cyan); font-family:'Share Tech Mono',monospace; font-size:.7rem;
    letter-spacing:.5px; margin-bottom:6px; text-shadow:0 0 6px rgba(0,229,255,.45); }
  .card .val { font-family:'Share Tech Mono',monospace; font-size:1.2rem; font-weight:700;
    text-shadow:0 0 8px currentColor; word-break:break-all; }
  .pos { color:var(--neon); } .neg { color:var(--red); } .gld { color:var(--yel); } .tealc { color:var(--cyan); }
  .vioc { color:var(--vio); }
  section { background:var(--panel); border:1px solid var(--line2); border-radius:14px; padding:14px 16px;
    margin-bottom:16px; backdrop-filter:blur(4px); box-shadow:0 0 16px rgba(0,229,255,.04); }
  section h2 { font-size:.92rem; color:var(--cyan); margin-bottom:10px; display:flex; align-items:center;
    flex-wrap:wrap; gap:8px; text-shadow:0 0 8px rgba(0,229,255,.5); border-bottom:1px dashed rgba(0,229,255,.22);
    padding-bottom:8px; }
  table { width:100%; border-collapse:collapse; font-size:.78rem; }
  th { color:var(--cyan); text-align:right; padding:6px 8px; border-bottom:1px solid rgba(0,229,255,.3);
    font-weight:600; white-space:nowrap; font-family:'Share Tech Mono',monospace; font-size:.7rem; }
  td { padding:7px 8px; border-bottom:1px solid rgba(0,255,156,.07); white-space:nowrap; }
  tr:hover td { background:rgba(0,255,156,.05); }
  .pill { padding:2px 10px; border-radius:999px; font-size:.7rem; font-weight:700;
    border:1px solid; text-shadow:0 0 5px currentColor; }
  .p-pending { background:rgba(255,230,0,.1); color:var(--yel); border-color:var(--yel); }
  .p-open { background:rgba(0,229,255,.12); color:var(--cyan); border-color:var(--cyan); }
  .p-bull { background:rgba(0,255,156,.12); color:var(--neon); border-color:var(--neon); }
  .p-bear { background:rgba(255,51,85,.12); color:var(--red); border-color:var(--red); }
  .p-win { background:rgba(0,255,156,.12); color:var(--neon); border-color:var(--neon); }
  .p-loss { background:rgba(255,51,85,.12); color:var(--red); border-color:var(--red); }
  .p-real { background:rgba(255,51,85,.14); color:var(--red); border-color:rgba(255,51,85,.6); }
  .p-exp { background:rgba(160,160,170,.12); color:var(--mut); border-color:var(--mut); text-shadow:none; }
  .p-cxl { background:rgba(255,51,85,.1); color:var(--red); border-color:rgba(255,51,85,.5); }
  .p-mcr { background:rgba(255,51,85,.22); color:#ff6685; border-color:var(--red); font-weight:800; animation:mcrPulse 1.6s ease-in-out infinite; }
  @keyframes mcrPulse { 0%,100%{opacity:1} 50%{opacity:.55} }  /* [FE1.9.8] تنبيه نابض — غلق يدوي مطلوب */
  .p-paper { background:rgba(0,229,255,.08); color:var(--cyan); border-color:rgba(0,229,255,.4); }
  .zone-ok { color:var(--neon); font-weight:700; } .zone-no { color:var(--mut); }
  .mut { color:var(--mut); } .small { font-size:.7rem; }
  .empty { color:var(--mut); text-align:center; padding:14px; font-size:.84rem; }
  .notif { padding:7px 10px; border-right:3px solid var(--line); margin-bottom:6px; background:var(--panel2);
    border-radius:8px; font-size:.76rem; }
  .notif.warn { border-color:var(--yel); } .notif.err { border-color:var(--red); }
  .tbl-wrap { overflow-x:auto; }
  .prog { background:var(--panel2); border:1px solid var(--line2); border-radius:999px; height:10px;
    min-width:90px; position:relative; overflow:hidden; }
  .prog-fill { height:100%; border-radius:999px; transition:width .4s;
    background:linear-gradient(90deg,var(--cyan),var(--neon)); box-shadow:0 0 8px rgba(0,255,156,.6); }
  .prog-fill.pneg { background:linear-gradient(90deg,var(--mag),var(--red)); box-shadow:0 0 8px rgba(255,51,85,.6); }
  .prog-lbl { font-size:.66rem; color:var(--mut); margin-top:2px; }
  button.mini { background:var(--panel2); border:1px solid var(--line); color:var(--txt); border-radius:8px;
    padding:4px 10px; cursor:pointer; font-size:.7rem; white-space:nowrap; transition:.2s; }
  button.mini:hover { border-color:var(--neon); color:var(--neon); text-shadow:0 0 6px currentColor; }
  button.mini.cxl:hover { border-color:var(--red); color:var(--red); }
  .liveprice { font-weight:700; color:var(--cyan); text-shadow:0 0 6px rgba(0,229,255,.5); }
  .src { font-size:.58rem; padding:1px 6px; border-radius:6px; margin-left:6px; border:1px solid;
    font-weight:700; vertical-align:middle; }
  .src-ws { background:rgba(0,229,255,.1); color:var(--cyan); border-color:var(--cyan); }
  .src-rest { background:rgba(95,138,128,.1); color:var(--mut); border-color:var(--mut); }
  .dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-left:6px;
    background:currentColor; box-shadow:0 0 9px currentColor; animation:dotpulse 1.8s infinite; }
  @keyframes dotpulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  footer { text-align:center; color:var(--mut); font-size:.7rem; padding:8px 0 20px; line-height:1.9; }
  footer a { color:var(--cyan); text-decoration:none; }
  footer b { color:var(--neon); }
  #toast { position:fixed; bottom:18px; left:50%; transform:translateX(-50%); background:var(--panel2);
    border:1px solid var(--cyan); color:var(--cyan); padding:10px 20px; border-radius:12px; display:none;
    z-index:99; max-width:90vw; font-size:.8rem; text-shadow:0 0 6px rgba(0,229,255,.6);
    box-shadow:0 0 18px rgba(0,229,255,.35); }
  .tf-ctl { display:flex; align-items:center; gap:4px; margin-inline-start:10px; }
  .tf-ctl .rlbl { font-size:.7rem; color:var(--mut); }
  button.tf-btn { background:rgba(0,229,255,.04); border:1px solid var(--line2); color:var(--cyan);
    border-radius:8px; padding:6px 9px; cursor:pointer; font-size:.72rem;
    font-family:'Share Tech Mono',monospace; transition:.2s; }
  button.tf-btn:hover { border-color:var(--cyan); box-shadow:0 0 8px rgba(0,229,255,.3); }
  button.tf-btn.on { background:rgba(0,229,255,.14); border-color:var(--cyan); font-weight:bold;
    box-shadow:0 0 12px rgba(0,229,255,.35); }
  @media (max-width:640px){ body{padding:10px} .grid{grid-template-columns:repeat(auto-fit,minmax(135px,1fr))}
    h1{font-size:1.1rem} button.act{padding:7px 10px; font-size:.74rem} }
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="orb orb1"></div><div class="orb orb2"></div><div class="orb orb3"></div>
<div class="scanlines"></div><div class="scanbar"></div>
<div class="wrap">
  <header>
    <h1>🌊 Fibo-Elio <small id="ver"></small></h1>
    <span class="badge b-orig">Elliott_Fibonacci (MIT)</span>
    <span class="badge" id="mode-badge">الوضع: —</span>
    <span class="badge" id="bin-badge" title="اتصال باينانس الحي">باينانس: —</span>
    <span class="badge" id="trade-badge"></span>
    <span class="badge" id="feed-badge" title="مصدر الأسعار الحية للصفقات النشطة">التغذية الحية: —</span>
    <div class="spacer"></div>
    <div class="real-ctl" title="تشغيل التداول الحقيقي على باينانس مثل V9">
      <span class="rlbl" id="real-status-text">التداول الحقيقي: —</span>
      <label class="switch"><input type="checkbox" id="real-toggle" onchange="toggleReal(this)"><div class="slider"></div></label>
    </div>
    <button class="act" onclick="toggleTrading()">تشغيل/إيقاف التوليد</button>
    <div class="tf-ctl" title="فريم الكشف والتنفيذ — التبديل يلغي الأوامر الورقية المعلقة ويبدأ فحصًا جديدًا على الفريم المختار (الاختيار محفوظ ويصمد عبر إعادة النشر)">
      <span class="rlbl">الفريم:</span>
      <button class="tf-btn" data-tf="5m" onclick="setTimeframe('5m')">5m</button>
      <button class="tf-btn" data-tf="15m" onclick="setTimeframe('15m')">15m</button>
      <button class="tf-btn" data-tf="1h" onclick="setTimeframe('1h')">1h</button>
      <button class="tf-btn" data-tf="4h" onclick="setTimeframe('4h')">4h</button>
    </div>
    <button class="act danger" onclick="resetStats()">تصفير الإحصائيات</button>
  </header>

  <div id="mode-banner"></div>
  <div id="err-banner" style="display:none" class="banner banner-real"></div>
  <div class="grid" id="cards"></div>

  <section>
    <h2>🛰 فحص أزواج باينانس (الكون الكامل) <span class="mut small">— فلترة سيولة/سبريد/مدى على كل أسواق USDT ثم تحليل موجات زيجزاج 15م بعتبة الاستراتيجية نفسها — أعلى النتائج تُطبَّق تلقائيًا على قائمة المراقبة</span>
      <span class="spacer"></span><button class="act" id="scan-btn" onclick="scanNow()">🛰 فحص الآن</button></h2>
    <div id="scan-status" class="mut small" style="margin-bottom:8px">—</div>
    <div id="scan-box"></div>
  </section>

  <section>
    <h2>📈 الصفقات المفتوحة والأوامر المعلقة <span class="mut small">— تتبع حي: الأسعار من ويب سوكت ⚡ (REST احتياطًا) · الحقيقية تُدار مباشرة من باينانس</span></h2>
    <div id="open-box"></div>
  </section>

  <section>
    <h2>🧾 آخر الصفقات المغلقة</h2>
    <div id="closed-box"></div>
  </section>

  <section>
    <h2>📊 لوحة الأداء <span class="mut small">— مقتبسة من لوحة أداء V9.34.0 (اقتباسات OctoBot): صافي الربح · معدل الربح · عامل الربح · منحنى تراكمي بأعمدة الربح/الخسارة لكل صفقة</span></h2>
    <div class="grid" id="perf-cards"></div>
    <div id="pnl-chart-meta" class="mut small" style="margin:8px 0 4px"></div>
    <div id="pnl-chart"></div>
  </section>

  <section>
    <h2>🔍 آخر التقاطات الموجات (صاعدة تُنفَّذ — هابطة للاطلاع فقط في السبوت)</h2>
    <div id="gates-strip" class="mut small" style="margin-bottom:8px">—</div>
    <div id="det-box"></div>
  </section>

  <section>
    <h2>🔔 آخر الإشعارات</h2>
    <div id="notif-box"></div>
  </section>

  <footer>
    استراتيجية واحدة فقط: <b>موجة إليوت (دافع 5 موجات، قواعد صارمة ثلاث)</b> + <b>مستويات فيبوناتشي</b>
    (دخول 0.382 لتراجع الموجة 3 · وقف بنيوي خلف P0 · أهداف متدرجة TP1→TP3 لا تتجاوز قمة آخر 7 أيام — سكالبينج واقعي [FE1.9.9]) —
    ماسح الكون [FE1.5.0]: فحص أولي لكل أزواج باينانس USDT واختيار الأنسب للاستراتيجية تلقائيًا —
    التداول الحقيقي [FE1.4.0]: أمر LIMIT حقيقي عند فيبو 0.382 ← بيع سوق عند الوقف/الهدف، بقواعد باينانس
    (LOT_SIZE · NOTIONAL · دقة السعر/الكمية · كفاية الرصيد) —
    تتبع حي + إغلاق/إلغاء يدوي [FE1.1.0] + أسعار حية من ويب سوكت [FE1.2.0] + مضاد نوم محصّن [FE1.3.0]<br>
    المحرك منقول حرفيًا من <a href="https://github.com/dtwijesekara/Elliott_Waves_Algo_TradingBot" target="_blank">Elliott_Waves_Algo_TradingBot</a>
    (MIT) — مستودع المشروع: <a href="https://github.com/salah55t/fibo-elio" target="_blank">salah55t/fibo-elio</a>
  </footer>
</div>
<div id="toast"></div>

<script>
const $ = id => document.getElementById(id);
const fmt = (v, d=4) => (v===null||v===undefined||isNaN(v)) ? '—' : Number(v).toLocaleString('en-US',{maximumFractionDigits:d});
const pct = v => (v===null||v===undefined||isNaN(v)) ? '—' : (v>=0?'+':'') + Number(v).toFixed(2) + '%';
const usd = v => (v===null||v===undefined||isNaN(v)) ? '—' : ((v>=0?'+':'') + Number(v).toFixed(2) + '$');
const cls = v => (v===null||v===undefined||isNaN(v)) ? '' : (v>=0 ? 'pos' : 'neg');
const dt = s => s ? String(s).replace('T',' ').replace('Z','') : '—';
// [FE1.5.0] تهريب HTML لكل بيانات API — كانت innerHTML مكشوفة على XSS مخزّن
const esc = s => String(s??'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

let WSSTATE = null;    // حالة تغذية الويب سوكت [FE1.2.0] — من /api/ws/status
let REAL_MODE = false; // حالة زر التداول الحقيقي [FE1.4.0]
let REAL_BUSY = false; // [FE1.5.0] لا اختطاف للمفتاح أثناء طلب التبديل الجاري
let REFRESHING = false;

function toast(msg){ const t=$('toast'); t.textContent=msg; t.style.display='block'; setTimeout(()=>t.style.display='none',2500); }

async function api(path, opts){ const r = await fetch(path, opts); if(!r.ok) throw new Error(await r.text()); return r.json(); }

function renderFeed(ws){
  const b = $('feed-badge');
  if(!ws || !ws.enabled){ b.textContent='التغذية الحية: REST'; b.className='badge b-ws-off'; return; }
  if(!ws.loop_alive){ b.textContent='التغذية الحية: ويب سوكت متوقف — REST مؤقتًا'; b.className='badge b-ws-off'; return; }
  // [FE1.9.7] شارة تيك باينانس الخام: حيّ = أقصى لحظية (سعر على كل صفقة فعلية)
  const raw = ws.raw || {};
  const tickTag = raw.connected
    ? ` + تيك خام ⚡⚡ (${(raw.ticks||0).toLocaleString('en-US')} تيك، عمر ${raw.age_sec ?? '—'}ث)`
    : (raw.enabled ? ' + تيك خام يعيد الاتصال' : '');
  b.textContent = `التغذية الحية: ويب سوكت ⚡ (${ws.live_streams||0} تيار حي)${tickTag}`;
  b.className = 'badge b-ws';
}

function srcBadge(sym){
  const p = (WSSTATE && WSSTATE.enabled && WSSTATE.prices) ? WSSTATE.prices[sym] : null;
  if(p && p.age_sec !== undefined && p.age_sec < 90)
    return `<span class="src src-ws" title="ويب سوكت عبر ${esc(p.source)} — عمر آخر تحديث ${p.age_sec} ث">⚡WS</span>`;
  return '<span class="src src-rest" title="طلبات REST (احتياط عند غياب التيار)">REST</span>';
}

// [FE1.9.9] سطر الأهداف المتدرجة تحت الهدف النهائي — tp_stages من الخادم (صاعدة صارمة)
// + سقف الأسبوع إن توفر — «الهدف لا يتجاوز ما لمسته العملة خلال 7 أيام»
function stagesLine(s){
  const st = s.tp_stages || [];
  let html = '';
  if(st.length > 1){
    const chips = st.map((t,i)=>`<span class="mut small">هدف ${i+1}: ${fmt(t)}</span>`).join(' · ');
    html = `<div class="small mut">↳ ${chips}</div>`;
  }
  if(s.weekly_high)
    html += `<div class="small mut">⌈ سقف أسبوع: ${fmt(s.weekly_high)}</div>`;
  return html;
}

function renderCards(d){
  const s = d.stats || {};
  const eq = (d.paper_balance||0) + (s.unrealized||0);
  // [FE1.4.0] بطاقة اتصال باينانس + رصيد USDT الحقيقي + وضع التنفيذ
  const bn = d.binance || {};
  let bnTxt, bnCls, binBadge;
  if (bn.connected) {
    bnTxt = (bn.latency_ms !== null && bn.latency_ms !== undefined) ? bn.latency_ms + 'ms' : 'متصل';
    if (bn.usdt_free !== null && bn.usdt_free !== undefined) bnTxt += ' · ' + fmt(bn.usdt_free,2) + '$';
    bnCls = 'pos';
    binBadge = 'باينانس: <span class="dot"></span>متصل ' + (bn.latency_ms ?? '') + 'ms' + (bn.keys_present ? ' 🔑' : '');
    $('bin-badge').className = 'badge b-bin-ok';
  } else {
    bnTxt = bn.keys_present ? 'فشل الاتصال' : 'بلا مفاتيح API';
    // [FE1.8.5] نص الخطأ الحقيقي في البطاقة — كانت «فشل الاتصال» بلا أي تفاصيل وبلا أثر في السجل
    const bnErr = (bn.error || '').replace(/\s+/g,' ').slice(0, 90);
    if (bn.keys_present && bnErr) bnTxt += ' · ' + bnErr;
    bnCls = bn.keys_present ? 'neg' : '';
    binBadge = 'باينانس: ' + (bn.keys_present ? 'غير متصل ⚠' : 'بلا مفاتيح');
    if (bn.keys_present && bnErr) binBadge += ' — ' + esc(bnErr);
    $('bin-badge').className = 'badge ' + (bn.keys_present ? 'b-bin-bad' : 'b-off');
  }
  if (bn.testnet) binBadge += ' 🧪TESTNET';
  $('bin-badge').innerHTML = binBadge;
  const cards = [
    ['الرصيد الورقي', fmt(d.paper_balance,2)+'$', 'gld'],
    ['الإيجوتي (مع غير المحقق)', fmt(eq,2)+'$', eq>=d.paper_balance?'pos':'neg'],
    ['غير المحقق (مفتوح)', usd(s.unrealized||0), cls(s.unrealized||0)],
    ['اتصال باينانس', bnTxt, bnCls],
    ['رصيد USDT الحقيقي', (bn.usdt_free!==null&&bn.usdt_free!==undefined)? fmt(bn.usdt_free,2)+'$' : '—', bn.keys_present?'tealc':''],
    ['وضع التنفيذ', d.real_mode ? '🔴 حقيقي' : '🧪 ورقي', d.real_mode ? 'neg' : 'tealc'],
    ['نشطة / معلقة', `${s.open_n||0} / ${s.pending_n||0}`, 'tealc'],
    ['صفقات مغلقة', s.closed_n||0, ''],
    ['نسبة الفوز', (s.win_rate!==null&&s.win_rate!==undefined)? Number(s.win_rate).toFixed(1)+'%':'—', 'tealc'],
    ['عامل الربح PF', (s.profit_factor!==null&&s.profit_factor!==undefined)? Number(s.profit_factor).toFixed(2):'—', (s.profit_factor||0)>=1?'pos':'neg'],
    ['صافي الربح', usd(s.total_pnl||0), cls(s.total_pnl||0)],
    ['مزود البيانات', esc((d.data&&d.data.active)? d.data.active.toUpperCase() : '—'), 'tealc'],
    // [FE1.8.7] بطاقة حارس الوزن — اقتباس V9: شفافية كاملة لوزن باينانس والحظر
    (function(){
      const rg = d.rate_guard || {};
      let rgTxt = '—', rgCls = 'tealc';
      if (rg.budget_per_min) {
        if (rg.banned) {
          rgTxt = '🚫 حظر حتى ' + esc(((rg.banned_until_iso||'').slice(11,16)) || '—') + ' UTC';
          rgCls = 'neg';
        } else {
          rgTxt = (rg.used_weight_last_min||0) + '/' + rg.budget_per_min + ' وزن·د';
          if (rg.ban_count) rgTxt += ' · ' + rg.ban_count + ' حظرات سابقة';
        }
      }
      return ['حارس وزن باينانس (V9)', rgTxt, rgCls];
    })(),
    ['آخر مسح', s.last_scan_at? esc(s.last_scan_at.slice(11,16))+' UTC' : '—', ''],
  ];
  // [FE1.3.0] بطاقة البقاء الحي — دليل مرئي أن مضاد النوم يعمل
  const ka = d.keep_alive || {};
  let kaTxt = 'معطل', kaCls = '';
  if (ka.enabled) {
    kaTxt = (ka.last_ok === false ? '⚠ فشل آخر نبضة! كل ' : '💓 كل ') + Math.round((ka.interval_sec||600)/60) + ' د';
    kaCls = (ka.last_ok === false ? 'neg' : 'pos');
    if (ka.last_ping_at) kaTxt += ' · ' + ka.last_ping_at.slice(11,19) + ' UTC';
  }
  cards.push(['البقاء الحي (مضاد النوم)', kaTxt, kaCls]);
  // [FE1.3.1] بطاقة الذاكرة — العتبات من السيرفر نفسه (كانت افتراضيات قديمة 450/380)
  const mem = d.memory || {};
  let memTxt = '—', memCls = '';
  if (mem.rss_mb) {
    const crit = mem.critical_mb || 440, gc = mem.gc_threshold_mb || 360;
    memTxt = Math.round(mem.rss_mb) + ' / 512 MB';
    memCls = mem.rss_mb >= crit ? 'neg' : (mem.rss_mb >= gc ? 'gld' : 'pos');
  }
  cards.push(['الذاكرة (RAM)', memTxt, memCls]);
  // [FE1.5.0] بطاقة ماسح الكون
  const sc = d.scanner || {};
  let scTxt = 'معطل', scCls = '';
  if (sc.enabled) {
    if (sc.running) { scTxt = '⏳ جارٍ الآن...'; scCls = 'gld'; }
    else {
      const n = (sc.results && sc.results.length) || 0;
      scTxt = sc.last_scan_at ? sc.last_scan_at.slice(11,16) + ' UTC · ' + n + ' زوجًا' : 'بانتظار أول فحص';
      scCls = 'vioc';
    }
    if (sc.error) { scTxt = '⚠ فشل آخر فحص'; scCls = 'neg'; }
  }
  cards.push(['🛰 فحص أزواج باينانس', scTxt, scCls]);
  $('cards').innerHTML = cards.map(c =>
    `<div class="card"><div class="lbl">${c[0]}</div><div class="val ${c[2]}">${c[1]}</div></div>`).join('');
  const tb = $('trade-badge');
  tb.textContent = d.trading_enabled ? 'توليد الإشارات: مفعّل' : 'توليد الإشارات: معطّل';
  tb.className = 'badge ' + (d.trading_enabled ? 'b-on' : 'b-off');
  // [FE1.4.0] زر التداول الحقيقي + شارة الوضع + لافتة الوضع — [FE1.5.0] بلا اختطاف أثناء الطلب
  REAL_MODE = !!d.real_mode;
  const rt = $('real-toggle');
  if (!REAL_BUSY && rt.checked !== REAL_MODE) rt.checked = REAL_MODE;
  $('real-status-text').textContent = 'التداول الحقيقي: ' + (REAL_MODE ? 'مُفعّل ⚠' : 'متوقف');
  const mb = $('mode-badge');
  mb.textContent = 'الوضع: ' + (REAL_MODE ? 'حقيقي 🔴' : 'ورقي 🧪');
  mb.className = 'badge ' + (REAL_MODE ? 'b-real' : 'b-paper');
  $('mode-banner').innerHTML = REAL_MODE
    ? '<div class="banner banner-real">⚠ التداول الحقيقي نشط — الإشارات الجديدة تُنفَّذ بأوامر فعلية على حسابك في Binance (شراء LIMIT عند فيبو 0.382 ← بيع سوق عند الوقف/الهدف)</div>'
    : '<div class="banner banner-paper">🧪 وضع ورقي — الصفقات المعروضة للتقييم فقط، لا أوامر حقيقية على Binance · فعّل مفتاح التداول الحقيقي للتنفيذ الفعلي</div>';
  $('ver').textContent = (d.version||'—') + ' — ' + (d.strategy||'');
}

function modePill(isReal){
  return isReal ? '<span class="pill p-real">حقيقية 🔴</span>' : '<span class="pill p-paper">ورقية</span>';
}

// [FE1.5.0] قسم فحص الكون — جدول النتائج + حالة الفحص
function renderScanner(d){
  const sc = d.scanner || {};
  const st = $('scan-status');
  let txt = sc.enabled ? 'الفحص التلقائي مفعّل (كل 6 ساعات افتراضيًا)' : 'الفحص التلقائي معطل — استخدم «فحص الآن»';
  if (sc.running) txt = '⏳ فحص جارٍ الآن — يستغرق نحو دقيقة...';
  else if (sc.last_scan_at) txt += ' · آخر فحص: ' + dt(sc.last_scan_at) + ' UTC'
    + (sc.duration_ms ? ` · استغرق ${(sc.duration_ms/1000).toFixed(0)} ث` : '');
  if (sc.universe) txt += ` · الكون ${sc.universe} زوج ← ${sc.passed ?? '—'} مرشحًا ← حُلل ${sc.candidates ?? '—'}`;
  if (sc.next_scan_at && !sc.running) txt += ' · الفحص القادم: ' + dt(sc.next_scan_at) + ' UTC';
  if (sc.error) txt = '⚠ ' + esc(sc.error);
  st.innerHTML = txt;
  const list = sc.results || [];
  if(!list.length){ $('scan-box').innerHTML = '<div class="empty">لا نتائج فحص بعد — اضغط «🛰 فحص الآن» أو انتظر الفحص التلقائي</div>'; return; }
  let rows = list.map((r,i) => `<tr>
    <td class="mut">${i+1}</td>
    <td><b>${esc(r.symbol||'')}</b></td>
    <td><span class="pill ${r.final>=70?'p-bull':(r.final>=45?'p-pending':'p-loss')}">${fmt(r.final,1)}</span></td>
    <td>${fmt(r.pivots,0)}</td>
    <td>${fmt(r.atr_pct,2)}%</td>
    <td>${fmt(r.avg_wave_pct,2)}%</td>
    <td>${fmt(r.trend_eff,2)}</td>
    <td>${fmt(r.range_pct,2)}%</td>
    <td>${fmt(r.qv,0)}$</td>
    <td>${sc.applied ? '<span class="pill p-open">مطبق ✓</span>' : '<span class="mut small">نتيجة فقط</span>'}</td>
  </tr>`).join('');
  $('scan-box').innerHTML = `<div class="tbl-wrap"><table><thead><tr>
    <th>#</th><th>الزوج</th><th>درجة الملاءمة</th><th>انعكاسات الزيجزاج</th><th>ATR%</th>
    <th>متوسط الموجة</th><th>كفاءة الاتجاه</th><th>مدى 24h</th><th>سيولة 24h</th><th>الحالة</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderOpen(list){
  if(!list.length){ $('open-box').innerHTML = '<div class="empty">لا صفقات مفتوحة ولا أوامر معلقة حاليا — البوت يراقب السوق بحثا عن دافع صالح ✨</div>'; return; }
  let rows = list.map(s => {
    const isPend = s.status==='pending';
    // [FE1.9.8] شارة «غلق يدوي مطلوب» — علم meta من الخادم (فشل غلق حقيقي عند بلوغ الوقف/الهدف)
    const mcr = (!isPend && s.meta && s.meta.manual_close_required)
      ? ' <span class="pill p-mcr" title="وصلت الصفقة مستوى خروجها وعجز البوت عن الغلق — أغلقها من باينانس أو أرسل /close في تلغرام">🚨 غلق يدوي</span>' : '';
    const st = isPend ? '<span class="pill p-pending">معلق</span>' : '<span class="pill p-open">مفتوح</span>'+mcr;
    const fib = s.fib || {};
    // تتبع حي [FE1.1.0] + شارة المصدر [FE1.2.0]
    const cp = s.current_price ? `${srcBadge(esc(s.symbol))}<span class="liveprice">${fmt(s.current_price)}</span>` : '<span class="mut">—</span>';
    let live;
    if(!isPend){
      const u = s.unrealized_usdt;
      const up = (u===null||u===undefined) ? '<span class="mut small">حسب السعر</span>'
        : `<span class="${cls(u)}"><b>${usd(u)}</b> <span class="small">(${pct(s.unrealized_pct)})</span></span>`;
      const pr = (s.progress_pct===null||s.progress_pct===undefined) ? '<span class="mut small">—</span>'
        : `<div class="prog"><div class="prog-fill ${s.progress_pct<0?'pneg':''}" style="width:${Math.max(2,Math.min(100,Math.abs(s.progress_pct)))}%"></div></div>` +
          `<div class="prog-lbl">${s.progress_pct>=0?'نحو الهدف':'تحت الدخول'} ${s.progress_pct.toFixed(0)}% · للهدف ${pct(s.dist_tp_pct)} · للوقف ${pct(s.dist_sl_pct)}</div>`;
      live = [cp, up, pr];
    } else {
      const de = (s.dist_entry_pct===null||s.dist_entry_pct===undefined) ? '<span class="mut small">—</span>'
        : `<span class="small">${s.dist_entry_pct>=0?'السعر تحت الدخول بـ':'فوق الدخول بـ'} <b class="${s.dist_entry_pct>=0?'tealc':'gld'}">${Math.abs(s.dist_entry_pct).toFixed(2)}%</b></span>`;
      live = [cp, '<span class="mut small">أمر منتظر</span>', de];
    }
    const act = isPend
      ? `<button class="mini cxl" onclick="cancelOrder(${s.id},'${esc(s.symbol)}')">✖ إلغاء</button>`
      : `<button class="mini" onclick="closeTrade(${s.id},'${esc(s.symbol)}')">🔒 إغلاق</button>`;
    return `<tr>
      <td><b>${esc(s.symbol)}</b></td><td>${st}</td><td>${modePill(s.is_real)}</td>
      <td>${live[0]}</td><td>${live[1]}</td><td>${live[2]}</td>
      <td>${fmt(isPend?s.entry_price:s.fill_price)}</td>
      <td class="neg">${fmt(s.stop_loss)}</td><td class="pos">${fmt(s.take_profit)}${stagesLine(s)}</td>
      <td>${s.rr_ratio?Number(s.rr_ratio).toFixed(2):'—'}</td>
      <td>${fmt(s.quantity,6)}</td>
      <td class="mut small">${dt(s.created_at)}</td>
      <td class="mut small">${isPend?('تنتهي: '+dt(s.expires_at)):'—'}</td>
      <td>${act}</td>
    </tr>`;
  }).join('');
  $('open-box').innerHTML = `<div class="tbl-wrap"><table><thead><tr>
    <th>الزوج</th><th>الحالة</th><th>الوضع</th><th>السعر الآن</th><th>غير المحقق</th><th>التقدم نحو الهدف</th>
    <th>دخول/ملء</th><th>وقف</th><th>الأهداف (متدرجة)</th>
    <th>R:R</th><th>الكمية</th><th>أُنشئ</th><th>الصلاحية</th><th>إجراء</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderClosed(list){
  if(!list.length){ $('closed-box').innerHTML = '<div class="empty">لا صفقات مغلقة بعد</div>'; return; }
  // [FE1.9.6] لا اختفاء صامت: المنتهية/الملغاة تظهر بشاراتها — دورة حياة المعلق كاملة مرئية
  const stPill = s => s.status==='expired' ? '<span class="pill p-exp">منتهية</span>'
                  : s.status==='cancelled' ? '<span class="pill p-cxl">ملغاة</span>'
                  : '<span class="pill p-open">مغلقة</span>';
  let rows = list.map(s => {
    const inP = (s.fill_price===null||s.fill_price===undefined||isNaN(s.fill_price)) ? s.entry_price : s.fill_price;
    return `<tr>
    <td><b>${esc(s.symbol)}</b></td><td>${modePill(s.is_real)}</td>
    <td>${stPill(s)}</td>
    <td>${fmt(inP)} → ${fmt(s.close_price)}</td>
    <td class="${cls(s.pnl_usdt)}"><b>${usd(s.pnl_usdt)}</b></td>
    <td class="${cls(s.pnl_pct)}">${pct(s.pnl_pct)}</td>
    <td class="mut small">${esc(s.close_reason||'')}</td>
    <td class="mut small">${dt(s.closed_at)}</td>
  </tr>`;
  }).join('');
  // [FE1.5.0] داخل .tbl-wrap — كانت تفيض على الموبايل بلا تمرير
  $('closed-box').innerHTML = `<div class="tbl-wrap"><table><thead><tr>
    <th>الزوج</th><th>الوضع</th><th>الحالة</th><th>دخول → خروج</th><th>النتيجة</th><th>%</th><th>السبب</th><th>التاريخ</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

// ================= [FE1.8.1] حكم الالتقاط + شريط البوابات + لوحة الأداء =================
// الحكم: لماذا لم تصبح التقاطة توصية معلقة — من _reject_reason في الخادم
// (نسخة خفيفة من بطاقة «لماذا لا يتداول؟» المخطط لها في FE1.9.0)
function verdictCell(x){
  if(x.traded) return '<span class="pill p-open">أمر معلق بانتظار الدخول</span>';
  if(x.direction==='BEARISH') return '<span class="mut small">متابعة فقط — لا بيع في السبوت</span>';
  const v = x.verdict || 'مرفوض';
  return '<span class="small gld" title="بوابة الرفض الأخيرة">'+esc(v)+'</span>';
}

function renderGates(st){
  const el = $('gates-strip');
  if(!el) return;
  st = st || {};
  const gates = [['rejected_stale_premise','فرضية ميتة'],['rejected_old_structure','بنية قديمة'],
    ['rejected_deep_retrace','تصحيح عميق'],['rejected_cooldown','تبريد رمز'],['rejected_symbol_busy','رمز مشغول'],
    ['rejected_cluster','عنقود'],['rejected_active_limit','خانات ممتلئة'],['rejected_htf_bias','HTF هابط'],
    ['rejected_far_entry','مطاردة'],['rejected_target_invalid','هدف محقق'],
    ['rejected_no_target','لا هدف R:R'],['rejected_weekly_cap','فوق سقف الأسبوع'],
    ['rejected_rr_net','R:R صافٍ منخفض'],['rejected_daily_loss','حد يومي'],['rejected_risk_pause','تبريد مخاطر']];
  const parts = gates.filter(g=>st[g[0]]).map(g=>g[1]+' <b>'+st[g[0]]+'</b>');
  el.innerHTML = '🚦 بوابات هذه الفترة: ' + (parts.length? parts.join(' · ') : 'لا رفضات بعد') +
    ' — دورات المسح: <b>'+(st.cycles||0)+'</b> · رموز ممسوحة: <b>'+(st.scanned||0)+'</b>' +
    ' · ⚡ نبض الحركة (كشف لحظي): <b>'+(st.momentum_kicks||0)+'</b>';
}

// لوحة الأداء — اقتباس من V9.34.0 (اقتباسات OctoBot: /api/stats + pnl_history):
// بطاقات أساسية + تمديدات، ومنحنى أرباح تراكمي SVG خالص بلا CDN
// (خط تراكمي + أعمدة خضراء/حمراء لكل صفقة) بألوان هذه اللوحة
function renderPnlChart(trades){
  const box = document.getElementById('pnl-chart');
  if(!box) return;
  if(!trades || !trades.length){
    box.innerHTML = '<div class="empty">لا صفقات مغلقة بعد — المنحنى يُبنى من أول إغلاق</div>';
    return;
  }
  const W = 900, H = 260, PAD_L = 52, PAD_R = 12, PAD_T = 14, PAD_B = 26;
  const cums = trades.map(t => t.cum_usdt);
  let lo = Math.min(0, ...cums), hi = Math.max(0, ...cums);
  if(hi - lo < 0.5){ hi += 0.25; lo -= 0.25; }
  const rng = hi - lo;
  const x = i => PAD_L + (i / Math.max(1, trades.length - 1)) * (W - PAD_L - PAD_R);
  const y = v => PAD_T + (1 - (v - lo) / rng) * (H - PAD_T - PAD_B);
  const barW = Math.max(1.5, (W - PAD_L - PAD_R) / trades.length * 0.6);
  const bars = trades.map((t, i) => {
    const cx = x(i), v = t.net_usdt, y0 = y(0), y1 = y(v);
    const top = Math.min(y0, y1), h = Math.max(1, Math.abs(y0 - y1));
    const col = v > 0 ? 'rgba(0,255,156,.65)' : v < 0 ? 'rgba(255,51,85,.55)' : 'rgba(120,140,150,.4)';
    const tip = '#'+t.i+' '+(t.symbol||'')+' · '+(t.net_usdt>=0?'+':'')+t.net_usdt+'$ · تراكمي '+t.cum_usdt+'$';
    return '<rect x="'+(cx-barW/2).toFixed(1)+'" y="'+top.toFixed(1)+'" width="'+barW.toFixed(1)+'" height="'+h.toFixed(1)+'" fill="'+col+'"><title>'+esc(tip)+'</title></rect>';
  }).join('');
  const path = trades.map((t,i)=>(i===0?'M':'L')+x(i).toFixed(1)+','+y(t.cum_usdt).toFixed(1)).join(' ');
  const last = trades[trades.length-1];
  const lastCol = last.cum_usdt >= 0 ? '#00ff9c' : '#ff3355';
  const grid = [hi, (hi+lo)/2, lo].map(v =>
    '<line x1="'+PAD_L+'" y1="'+y(v).toFixed(1)+'" x2="'+(W-PAD_R)+'" y2="'+y(v).toFixed(1)+'" stroke="rgba(0,255,156,.12)" stroke-dasharray="3,4" stroke-width="1"/>'+
    '<text x="'+(PAD_L-4)+'" y="'+(y(v)+3).toFixed(1)+'" fill="#5d8f6d" font-size="10" font-family="Share Tech Mono,monospace" text-anchor="end">'+v.toFixed(2)+'</text>').join('');
  const zero = '<line x1="'+PAD_L+'" y1="'+y(0).toFixed(1)+'" x2="'+(W-PAD_R)+'" y2="'+y(0).toFixed(1)+'" stroke="rgba(120,140,150,.5)" stroke-width="1"/>';
  box.innerHTML = '<svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:260px" preserveAspectRatio="none">'+
    grid+zero+bars+
    '<path d="'+path+'" fill="none" stroke="'+lastCol+'" stroke-width="2.2" opacity=".95"/>'+
    '<circle cx="'+x(trades.length-1).toFixed(1)+'" cy="'+y(last.cum_usdt).toFixed(1)+'" r="4" fill="'+lastCol+'"/>'+
    '<text x="'+(W-PAD_R)+'" y="'+(y(last.cum_usdt)-8).toFixed(1)+'" fill="'+lastCol+'" font-size="12" font-family="Share Tech Mono,monospace" text-anchor="end">'+(last.cum_usdt>=0?'+':'')+last.cum_usdt.toFixed(2)+'$</text>'+
  '</svg>';
}

function renderPerformance(d){
  const p = d.performance || {};
  const cards = $('perf-cards');
  if(!cards) return;
  const pfTxt = (p.profit_factor == null) ? '—' : (p.profit_factor >= 99 ? '∞' : parseFloat(p.profit_factor).toFixed(2));
  const net = parseFloat(p.net_profit_usdt || 0);
  const arr = [
    ['💵 صافي الربح', (net>=0?'+':'') + net.toFixed(2) + '$', net>0?'pos':(net<0?'neg':'')],
    ['🎯 معدل الربح', (p.win_rate==null?'—':parseFloat(p.win_rate).toFixed(1)+'%'), (p.win_rate!=null&&p.win_rate>=50)?'pos':'gld'],
    ['⚖️ عامل الربح', pfTxt, (p.profit_factor!=null&&p.profit_factor>=1.15)?'pos':(p.profit_factor!=null&&p.profit_factor<0.85?'neg':'gld')],
    ['🧾 الصفقات المغلقة', p.total_closed_trades||0, ''],
    ['📊 متوسط رابح/خاسر', (p.avg_win!=null?'+'+parseFloat(p.avg_win).toFixed(2):'—')+' / '+(p.avg_loss!=null?parseFloat(p.avg_loss).toFixed(2):'—')+'$', 'mut'],
    ['📉 أقصى تراجع', '-'+parseFloat(p.max_drawdown_usdt||0).toFixed(2)+'$', 'neg'],
    ['🗓 ربح اليوم', (parseFloat(p.today_pnl||0)>=0?'+':'')+parseFloat(p.today_pnl||0).toFixed(2)+'$', parseFloat(p.today_pnl||0)>=0?'pos':'neg'],
    ['⏱ متوسط المدة', p.avg_duration_min!=null?parseFloat(p.avg_duration_min).toFixed(0)+' دقيقة':'—', 'mut'],
  ];
  cards.innerHTML = arr.map(c =>
    `<div class="card"><div class="lbl">${c[0]}</div><div class="val ${c[2]}">${c[1]}</div></div>`).join('');
  const best = p.best_trade, worst = p.worst_trade;
  $('pnl-chart-meta').innerHTML =
    (best?'أفضل صفقة: <b class="pos">'+esc(best.symbol||'—')+' +'+parseFloat(best.pnl).toFixed(2)+'$</b>':'') +
    (worst?' · أسوأ صفقة: <b class="neg">'+esc(worst.symbol||'—')+' '+parseFloat(worst.pnl).toFixed(2)+'$</b>':'') +
    (p.expectancy!=null?' · توقع الصفقة: '+parseFloat(p.expectancy).toFixed(2)+'$':'');
  renderPnlChart(p.trades || []);
}

function renderDetections(list){
  if(!list.length){ $('det-box').innerHTML = '<div class="empty">لا التقاطات بعد — بانتظار تكوّن موجات دافعة صالحة على فريم الكشف</div>'; return; }
  let rows = list.map(x => {
    const pivs = Array.isArray(x.pivots) ? x.pivots.map(p=>fmt(p)).join(' · ') : '—';
    return `<tr>
    <td><b>${esc(x.symbol)}</b> <span class="mut small">${esc(x.timeframe||'')}</span></td>
    <td><span class="pill ${x.direction==='BULLISH'?'p-bull':'p-bear'}">${x.direction==='BULLISH'?'صاعدة ↑':'هابطة ↓'}</span></td>
    <td class="small mut">P0…P5: ${pivs}</td>
    <td>${x.w2_retrace!==null&&x.w2_retrace!==undefined?(x.w2_retrace*100).toFixed(1)+'%':'—'} <span class="${x.w2_in_zone?'zone-ok':'zone-no'}">${x.w2_in_zone?'✔':''}</span></td>
    <td>${x.w4_retrace!==null&&x.w4_retrace!==undefined?(x.w4_retrace*100).toFixed(1)+'%':'—'} <span class="${x.w4_in_zone?'zone-ok':'zone-no'}">${x.w4_in_zone?'✔':''}</span></td>
    <td>${fmt(x.entry_zone_low)}</td><td class="neg small">${fmt(x.stop_loss)}</td><td class="pos small">${fmt(x.take_profit)}</td>
    <td>${verdictCell(x)}</td>
    <td class="mut small">${dt(x.detected_at)}</td>
  </tr>`; }).join('');
  // [FE1.5.0] داخل .tbl-wrap + pivots محمية ضد null (كان خطأ واحد يجمّد اللوحة)
  $('det-box').innerHTML = `<div class="tbl-wrap"><table><thead><tr>
    <th>الزوج</th><th>الاتجاه</th><th>المحاور</th><th>W2</th><th>W4</th>
    <th>منطقة الدخول</th><th>وقف</th><th>هدف</th><th>الحكم</th><th>وقت الالتقاط</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderNotifs(list){
  if(!list.length){ $('notif-box').innerHTML = '<div class="empty">لا إشعارات</div>'; return; }
  $('notif-box').innerHTML = list.map(n =>
    `<div class="notif ${n.level==='warning'?'warn':(n.level==='error'||n.level==='critical')?'err':''}">
      <b class="mut small">${dt(n.created_at)}</b> — ${esc(n.message)}</div>`).join('');
}

async function refresh(){
  if (REFRESHING || document.hidden) return;  // [FE1.5.0] بلا تداخل طلبات ولا ضغط والإخفاء
  REFRESHING = true;
  try {
    const d = await api('/api/all');
    $('err-banner').style.display = 'none';
    try { WSSTATE = await api('/api/ws/status'); } catch(e){ WSSTATE = null; }
    renderFeed(WSSTATE);
    // [FE1.5.0] كل عارضة في حماية مستقلة — خطأ في جدول لا يجمّد البطاقات
    const safe = fn => { try { fn(); } catch(e){ console.error(e); } };
    safe(()=>renderCards(d)); safe(()=>renderScanner(d));
    safe(()=>paintTf(d.signal_timeframe || '15m'));  // [FE1.8.9] تلوين الفريم النشط
    safe(()=>renderOpen(d.open_signals)); safe(()=>renderClosed(d.closed_signals));
    safe(()=>renderDetections(d.detections)); safe(()=>renderNotifs(d.notifications));
    safe(()=>renderPerformance(d)); safe(()=>renderGates(d.stats));
  } catch(e){
    console.error(e);
    const eb = $('err-banner');
    eb.style.display = 'block';
    eb.textContent = '⚠ فشل تحديث البيانات — ' + String(e.message||'').slice(0,140);
  } finally { REFRESHING = false; }
}

async function toggleTrading(){
  try {
    const d = await api('/api/trading/toggle', {method:'POST'});
    toast(d.message); refresh();
  } catch(e){ toast('فشل التبديل: '+e.message); }
}

// [FE1.8.9] تبديل فريم الكشف/التنفيذ حيًا (5m/15m/1h/4h) — يحفظ في السيرفر ويصمد عبر النشر
function paintTf(cur){
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.toggle('on', b.dataset.tf===cur));
}
async function setTimeframe(tf){
  if (!confirm('تبديل فريم التحليل إلى '+tf+'؟\n\n• الأوامر الورقية المعلقة تُلغى فورًا (بلا تبريد على الرموز)\n• تُبدأ دورة كشف جديدة على الفريم المختار خلال ثوانٍ\n• الاختيار محفوظ ويصمد عبر إعادة النشر')) return;
  document.querySelectorAll('.tf-btn').forEach(b=>b.disabled=true);
  try {
    const d = await api('/api/config/timeframe', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({preset: tf})});
    toast(d.message || ('الفريم: '+tf));
    if (d.signal_timeframe) paintTf(d.signal_timeframe);
    refresh();
  } catch(e){ toast('فشل تبديل الفريم: '+e.message); }
  finally { document.querySelectorAll('.tf-btn').forEach(b=>b.disabled=false); }
}

// [FE1.4.0] زر التداول الحقيقي — مثل V9: تفعيل يتطلب مفاتيح + فحص اتصال ناجح من السيرفر
async function toggleReal(el){
  const target = el.checked;
  if (target && !confirm('⚠ تشغيل التداول الحقيقي؟\n\nستُنفَّذ الإشارات الجديدة بأوامر فعلية على حسابك في Binance:\n• شراء LIMIT حقيقي عند فيبو 0.382\n• بيع سوق حقيقي عند الوقف/الهدف\n• بقواعد باينانس الكاملة وسقف أمان لكل أمر\n\nتأكد من ضبط المفاتيح (BINANCE_API_KEY / SECRET) وتوفر رصيد USDT.')) {
    el.checked = REAL_MODE; return;
  }
  if (!target && !confirm('إيقاف التداول الحقيقي والعودة للوضع الورقي الآمن؟\n(الصفقات الحقيقية المفتوحة ستستمر بالإدارة حتى إغلاقها)')) {
    el.checked = REAL_MODE; return;
  }
  REAL_BUSY = true;  // [FE1.5.0] الاستقصاء لا يعيد ضبط المفتاح أثناء الطلب
  try {
    const d = await api('/api/trading/real', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({enable: target})});
    toast(d.message || 'تم التبديل'); refresh();
  } catch(e){ el.checked = !target; toast('فشل التبديل: ' + e.message); }
  finally { REAL_BUSY = false; }
}

// [FE1.5.0] زر فحص الكون — يبدأ الفحص في خيط منفصل بالسيرفر والنتائج تظهر تدريجيًا
let SCAN_BUSY = false;
async function scanNow(){
  if (SCAN_BUSY) { toast('الفحص بدأ بالفعل — انتظر النتائج'); return; }
  SCAN_BUSY = true;
  const btn = $('scan-btn');
  btn.disabled = true; btn.textContent = '⏳ جارٍ الفحص...';
  try {
    const d = await api('/api/scan/run', {method:'POST'});
    toast(d.message || 'بدأ الفحص');
    setTimeout(refresh, 5000); setTimeout(refresh, 25000); setTimeout(refresh, 55000);
  } catch(e){ toast('فشل بدء الفحص: '+e.message); }
  finally { SCAN_BUSY = false; btn.disabled = false; btn.textContent = '🛰 فحص الآن'; }
}

async function closeTrade(id, symbol){
  if(!confirm('إغلاق صفقة '+symbol+' بسعر السوق الحالي؟\n(الحقيقية: بيع سوق فعلي على باينانس)')) return;
  try {
    const d = await api('/api/trades/close', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id})});
    toast(d.message || 'أُغلقت الصفقة'); refresh();
  } catch(e){ toast('فشل الإغلاق: '+e.message); }
}

async function cancelOrder(id, symbol){
  if(!confirm('إلغاء الأمر المعلق على '+symbol+'؟\n(الحقيقية: إلغاء الأمر الفعلي على باينانس)')) return;
  try {
    const d = await api('/api/trades/cancel', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id})});
    toast(d.message || 'أُلغي الأمر'); refresh();
  } catch(e){ toast('فشل الإلغاء: '+e.message); }
}

async function resetStats(){
  if(!confirm('تصفير كل الإحصائيات والصفقات وإرجاع الرصيد الورقي للبداية؟\n(تُأرشف الصفقات تلقائيًا — آخر 3 أرشيفات)')) return;
  const word = (prompt('للتأكيد اكتب RESET ثم اضغط موافق:') || '').trim().toUpperCase();
  if(word !== 'RESET'){ toast('لم يُؤكد التصفير — أُلغي'); return; }
  try {
    const d = await api('/api/stats/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({confirm:'RESET'})});
    toast(d.message || d.error || 'تم'); refresh();
  } catch(e){ toast('فشل التصفير: '+e.message); }
}

refresh();
setInterval(refresh, 30000);
// [FE1.5.0] إيقاف الضغط والإخفاء + تحديث فوري عند العودة للتبويب
document.addEventListener('visibilitychange', () => { if(!document.hidden) refresh(); });
</script>
</body>
</html>"""
