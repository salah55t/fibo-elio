#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
panel.py — لوحة تحكم Fibo-Elio (عربية RTL، داكنة، تحديث تلقائي 30 ثانية)
تعرض: الحالة الورقية، الرصيد، الصفقات المفتوحة/المعلقة بتتبع حي (السعر الآن،
غير المحقق، التقدم نحو الهدف)، إغلاق/إلغاء يدوي، المغلقة، أداء
استراتيجية Elliott_Fibonacci، آخر التقاطات الموجات (صاعدة/هابطة)، والإشعارات.
"""

BOT_VERSION = "FE1.1.1"

PANEL_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fibo-Elio — إليوت + فيبوناتشي</title>
<style>
  :root {
    --bg:#0b1220; --card:#121b2e; --card2:#0e1626; --line:#22304d;
    --txt:#e6edf7; --mut:#8ba0bf; --gold:#f0b429; --teal:#2dd4bf;
    --green:#34d399; --red:#f87171; --blue:#60a5fa; --violet:#a78bfa;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--txt); font-family:'Segoe UI',Tahoma,Arial,sans-serif; padding:18px; }
  .wrap { max-width:1180px; margin:0 auto; }
  header { display:flex; flex-wrap:wrap; align-items:center; gap:12px; margin-bottom:16px; }
  h1 { font-size:1.35rem; color:var(--gold); }
  h1 small { color:var(--mut); font-weight:400; font-size:.8rem; }
  .badge { padding:4px 12px; border-radius:999px; font-size:.78rem; font-weight:700; border:1px solid; }
  .b-paper { background:rgba(248,113,113,.12); color:var(--red); border-color:var(--red); }
  .b-orig { background:rgba(45,212,191,.1); color:var(--teal); border-color:var(--teal); }
  .b-on { background:rgba(52,211,153,.12); color:var(--green); border-color:var(--green); }
  .b-off { background:rgba(139,160,191,.12); color:var(--mut); border-color:var(--mut); }
  .spacer { flex:1; }
  button.act { background:var(--card); color:var(--txt); border:1px solid var(--line); border-radius:10px;
    padding:8px 14px; cursor:pointer; font-size:.85rem; }
  button.act:hover { border-color:var(--gold); color:var(--gold); }
  button.act.danger:hover { border-color:var(--red); color:var(--red); }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
  .card .lbl { color:var(--mut); font-size:.75rem; margin-bottom:6px; }
  .card .val { font-size:1.25rem; font-weight:800; }
  .pos { color:var(--green); } .neg { color:var(--red); } .gld { color:var(--gold); } .tealc { color:var(--teal); }
  section { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px; margin-bottom:16px; }
  section h2 { font-size:.95rem; color:var(--blue); margin-bottom:10px; display:flex; align-items:center; gap:8px; }
  table { width:100%; border-collapse:collapse; font-size:.8rem; }
  th { color:var(--mut); text-align:right; padding:6px 8px; border-bottom:1px solid var(--line); font-weight:600; white-space:nowrap; }
  td { padding:7px 8px; border-bottom:1px solid rgba(34,48,77,.5); white-space:nowrap; }
  tr:hover td { background:rgba(96,165,250,.05); }
  .pill { padding:2px 10px; border-radius:999px; font-size:.72rem; font-weight:700; }
  .p-pending { background:rgba(240,180,41,.15); color:var(--gold); }
  .p-open { background:rgba(45,212,191,.15); color:var(--teal); }
  .p-bull { background:rgba(52,211,153,.15); color:var(--green); }
  .p-bear { background:rgba(248,113,113,.15); color:var(--red); }
  .p-win { background:rgba(52,211,153,.15); color:var(--green); }
  .p-loss { background:rgba(248,113,113,.15); color:var(--red); }
  .zone-ok { color:var(--green); font-weight:700; }
  .zone-no { color:var(--mut); }
  .mut { color:var(--mut); } .small { font-size:.72rem; }
  .empty { color:var(--mut); text-align:center; padding:14px; font-size:.85rem; }
  .notif { padding:7px 10px; border-right:3px solid var(--line); margin-bottom:6px; background:var(--card2);
    border-radius:8px; font-size:.78rem; }
  .notif.warn { border-color:var(--gold); } .notif.err { border-color:var(--red); }
  .tbl-wrap { overflow-x:auto; }
  .prog { background:var(--card2); border:1px solid var(--line); border-radius:999px; height:10px;
    min-width:90px; position:relative; overflow:hidden; }
  .prog-fill { height:100%; border-radius:999px; background:var(--teal); transition:width .4s; }
  .prog-fill.pneg { background:var(--red); }
  .prog-lbl { font-size:.68rem; color:var(--mut); margin-top:2px; }
  button.mini { background:var(--card2); border:1px solid var(--line); color:var(--txt); border-radius:8px;
    padding:4px 10px; cursor:pointer; font-size:.72rem; white-space:nowrap; }
  button.mini:hover { border-color:var(--gold); color:var(--gold); }
  button.mini.cxl:hover { border-color:var(--red); color:var(--red); }
  .liveprice { font-weight:700; color:var(--blue); }
  footer { text-align:center; color:var(--mut); font-size:.72rem; padding:8px 0 20px; line-height:1.8; }
  footer a { color:var(--blue); text-decoration:none; }
  #toast { position:fixed; bottom:18px; left:50%; transform:translateX(-50%); background:var(--card);
    border:1px solid var(--gold); color:var(--gold); padding:10px 20px; border-radius:12px; display:none; z-index:99; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🌊 Fibo-Elio <small id="ver"></small></h1>
    <span class="badge b-orig">المنطق الأصلي: Elliott_Waves_Algo_TradingBot (MIT)</span>
    <span class="badge b-paper">وضع ورقي — لا أوامر حقيقية</span>
    <span class="badge" id="trade-badge"></span>
    <div class="spacer"></div>
    <button class="act" onclick="toggleTrading()">تشغيل/إيقاف التوليد</button>
    <button class="act danger" onclick="resetStats()">تصفير الإحصائيات</button>
  </header>

  <div class="grid" id="cards"></div>

  <section>
    <h2>📈 الصفقات المفتوحة والأوامر المعلقة <span class="mut small">— تتبع حي: السعر الآن وغير المحقق يتحدثان مع كل تحديث</span></h2>
    <div id="open-box"></div>
  </section>

  <section>
    <h2>🧾 آخر الصفقات المغلقة</h2>
    <div id="closed-box"></div>
  </section>

  <section>
    <h2>🔍 آخر التقاطات الموجات (صاعدة تُنفَّذ ورقيًا — هابطة للاطلاع فقط في السبوت)</h2>
    <div id="det-box"></div>
  </section>

  <section>
    <h2>🔔 آخر الإشعارات</h2>
    <div id="notif-box"></div>
  </section>

  <footer>
    استراتيجية واحدة فقط: <b>موجة إليوت (دافع 5 موجات، قواعد صارمة ثلاث)</b> + <b>مستويات فيبوناتشي</b>
    (دخول 0.382 لتراجع الموجة 3 · وقف بنيوي خلف P0 · هدف امتداد 1.618 للموجة 1) —
    تتبع حي + إغلاق/إلغاء يدوي [FE1.1.0] + إغلاق آلي عند الوقف/الهدف كل 60 ثانية<br>
    المحرك منقول حرفيًا من <a href="https://github.com/dtwijesekara/Elliott_Waves_Algo_TradingBot" target="_blank">Elliott_Waves_Algo_TradingBot</a>
    (MIT) — مستودع المشروع: <a href="https://github.com/salah55t/fibo-elio" target="_blank">salah55t/fibo-elio</a>
  </footer>
</div>
<div id="toast"></div>

<script>
const $ = id => document.getElementById(id);
const fmt = (v, d=4) => (v===null||v===undefined||isNaN(v)) ? '—' : Number(v).toLocaleString('en-US',{maximumFractionDigits:d});
const pct = v => (v===null||v===undefined) ? '—' : (v>=0?'+':'') + v.toFixed(2) + '%';
const usd = v => (v>=0?'+':'') + v.toFixed(2) + '$';
const cls = v => v>=0 ? 'pos' : 'neg';
const dt = s => s ? s.replace('T',' ').replace('Z','') : '—';

function toast(msg){ const t=$('toast'); t.textContent=msg; t.style.display='block'; setTimeout(()=>t.style.display='none',2500); }

async function api(path, opts){ const r = await fetch(path, opts); if(!r.ok) throw new Error(await r.text()); return r.json(); }

function renderCards(d){
  const s = d.stats;
  const eq = d.paper_balance + (s.unrealized||0);
  const cards = [
    ['الرصيد الورقي', fmt(d.paper_balance,2)+'$', 'gld'],
    ['الإيجوتي (مع غير المحقق)', fmt(eq,2)+'$', eq>=d.paper_balance?'pos':'neg'],
    ['غير المحقق (مفتوح)', usd(s.unrealized||0), cls(s.unrealized||0)],
    ['نشطة / معلقة', `${s.open_n} / ${s.pending_n}`, 'tealc'],
    ['صفقات مغلقة', s.closed_n||0, ''],
    ['نسبة الفوز', (s.win_rate!==null&&s.win_rate!==undefined)? s.win_rate.toFixed(1)+'%':'—', 'tealc'],
    ['عامل الربح PF', (s.profit_factor!==null&&s.profit_factor!==undefined)? s.profit_factor.toFixed(2):'—', (s.profit_factor||0)>=1?'pos':'neg'],
    ['صافي الربح', usd(s.total_pnl||0), cls(s.total_pnl||0)],
    ['دورات المسح', s.cycles||0, ''],
    ['التقاطات صالحة', s.setups_valid||0, ''],
    ['مزود البيانات', (d.data&&d.data.active)? d.data.active.toUpperCase() : '—', 'tealc'],
    ['آخر مسح', s.last_scan_at? s.last_scan_at.slice(11,16)+' UTC' : '—', ''],
  ];
  $('cards').innerHTML = cards.map(c =>
    `<div class="card"><div class="lbl">${c[0]}</div><div class="val ${c[2]}">${c[1]}</div></div>`).join('');
  const tb = $('trade-badge');
  tb.textContent = d.trading_enabled ? 'توليد الإشارات: مفعّل' : 'توليد الإشارات: معطّل';
  tb.className = 'badge ' + (d.trading_enabled ? 'b-on' : 'b-off');
  $('ver').textContent = d.version + ' — ' + d.strategy;
}

function renderOpen(list){
  if(!list.length){ $('open-box').innerHTML = '<div class="empty">لا صفقات مفتوحة ولا أوامر معلقة حاليا — البوت يراقب السوق بحثا عن دافع صالح ✨</div>'; return; }
  let rows = list.map(s => {
    const isPend = s.status==='pending';
    const st = isPend ? '<span class="pill p-pending">معلق</span>' : '<span class="pill p-open">مفتوح</span>';
    const fib = s.fib || {};
    // تتبع حي [FE1.1.0]
    const cp = s.current_price ? `<span class="liveprice">${fmt(s.current_price)}</span>` : '<span class="mut">—</span>';
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
      ? `<button class="mini cxl" onclick="cancelOrder(${s.id},'${s.symbol}')">✖ إلغاء</button>`
      : `<button class="mini" onclick="closeTrade(${s.id},'${s.symbol}')">🔒 إغلاق</button>`;
    return `<tr>
      <td><b>${s.symbol}</b></td><td>${st}</td>
      <td>${live[0]}</td><td>${live[1]}</td><td>${live[2]}</td>
      <td>${fmt(isPend?s.entry_price:s.fill_price)}</td>
      <td class="neg">${fmt(s.stop_loss)}</td><td class="pos">${fmt(s.take_profit)}</td>
      <td>${s.rr_ratio?Number(s.rr_ratio).toFixed(2):'—'}</td>
      <td>${fmt(s.quantity,6)}</td>
      <td class="mut small">${dt(s.created_at)}</td>
      <td class="mut small">${isPend?('تنتهي: '+dt(s.expires_at)):'—'}</td>
      <td>${act}</td>
    </tr>`;
  }).join('');
  $('open-box').innerHTML = `<div class="tbl-wrap"><table><thead><tr>
    <th>الزوج</th><th>الحالة</th><th>السعر الآن</th><th>غير المحقق</th><th>التقدم نحو الهدف</th>
    <th>${'دخول/ملء'}</th><th>وقف</th><th>هدف 1.618</th>
    <th>R:R</th><th>الكمية</th><th>أُنشئ</th><th>الصلاحية</th><th>إجراء</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderClosed(list){
  if(!list.length){ $('closed-box').innerHTML = '<div class="empty">لا صفقات مغلقة بعد</div>'; return; }
  let rows = list.map(s => `<tr>
    <td><b>${s.symbol}</b></td>
    <td>${fmt(s.fill_price)} → ${fmt(s.close_price)}</td>
    <td class="${cls(s.pnl_usdt)}"><b>${usd(s.pnl_usdt)}</b></td>
    <td class="${cls(s.pnl_pct)}">${pct(s.pnl_pct)}</td>
    <td class="mut small">${s.close_reason||''}</td>
    <td class="mut small">${dt(s.closed_at)}</td>
  </tr>`).join('');
  $('closed-box').innerHTML = `<table><thead><tr>
    <th>الزوج</th><th>دخول → خروج</th><th>النتيجة</th><th>%</th><th>السبب</th><th>أُغلقت</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}

function renderDetections(list){
  if(!list.length){ $('det-box').innerHTML = '<div class="empty">لا التقاطات بعد — بانتظار تكوّن موجات دافعة صالحة على فريم الكشف</div>'; return; }
  let rows = list.map(x => `<tr>
    <td><b>${x.symbol}</b> <span class="mut small">${x.timeframe}</span></td>
    <td><span class="pill ${x.direction==='BULLISH'?'p-bull':'p-bear'}">${x.direction==='BULLISH'?'صاعدة ↑':'هابطة ↓'}</span></td>
    <td class="small mut">P0…P5: ${x.pivots.map(p=>fmt(p)).join(' · ')}</td>
    <td>${x.w2_retrace!==null&&x.w2_retrace!==undefined?(x.w2_retrace*100).toFixed(1)+'%':'—'} <span class="${x.w2_in_zone?'zone-ok':'zone-no'}">${x.w2_in_zone?'✔':''}</span></td>
    <td>${x.w4_retrace!==null&&x.w4_retrace!==undefined?(x.w4_retrace*100).toFixed(1)+'%':'—'} <span class="${x.w4_in_zone?'zone-ok':'zone-no'}">${x.w4_in_zone?'✔':''}</span></td>
    <td>${fmt(x.entry_zone_low)}</td><td class="neg small">${fmt(x.stop_loss)}</td><td class="pos small">${fmt(x.take_profit)}</td>
    <td>${x.traded?'<span class="pill p-open">نُفذت ورقيًا</span>':'<span class="mut small">للاطلاع</span>'}</td>
    <td class="mut small">${dt(x.detected_at)}</td>
  </tr>`).join('');
  $('det-box').innerHTML = `<table><thead><tr>
    <th>الزوج</th><th>الاتجاه</th><th>المحاور</th><th>W2</th><th>W4</th>
    <th>منطقة الدخول</th><th>وقف</th><th>هدف</th><th>التنفيذ</th><th>وقت الالتقاط</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}

function renderNotifs(list){
  if(!list.length){ $('notif-box').innerHTML = '<div class="empty">لا إشعارات</div>'; return; }
  $('notif-box').innerHTML = list.map(n =>
    `<div class="notif ${n.level==='warning'?'warn':(n.level==='error'||n.level==='critical')?'err':''}">
      <b class="mut small">${dt(n.created_at)}</b> — ${n.message}</div>`).join('');
}

async function refresh(){
  try {
    const d = await api('/api/all');
    renderCards(d); renderOpen(d.open_signals); renderClosed(d.closed_signals);
    renderDetections(d.detections); renderNotifs(d.notifications);
  } catch(e){ console.error(e); }
}

async function toggleTrading(){
  try {
    const d = await api('/api/trading/toggle', {method:'POST'});
    toast(d.message); refresh();
  } catch(e){ toast('فشل التبديل: '+e.message); }
}

async function closeTrade(id, symbol){
  if(!confirm('إغلاق صفقة '+symbol+' بسعر السوق الحالي (ورقي)؟')) return;
  try {
    const d = await api('/api/trades/close', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id})});
    toast(d.message || 'أُغلقت الصفقة'); refresh();
  } catch(e){ toast('فشل الإغلاق: '+e.message); }
}

async function cancelOrder(id, symbol){
  if(!confirm('إلغاء الأمر المعلق على '+symbol+'؟')) return;
  try {
    const d = await api('/api/trades/cancel', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id})});
    toast(d.message || 'أُلغي الأمر'); refresh();
  } catch(e){ toast('فشل الإلغاء: '+e.message); }
}

async function resetStats(){
  if(!confirm('تصفير كل الإحصائيات والصفقات وإرجاع الرصيد الورقي للبداية؟')) return;
  try {
    const d = await api('/api/stats/reset', {method:'POST'});
    toast(d.message); refresh();
  } catch(e){ toast('فشل التصفير: '+e.message); }
}

refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>"""
