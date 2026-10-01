// 業務：今日の予定申告・開始/終了・お題・配布報告・反響対応・日報、今月の成績、チームの一覧。
// 表はゲームのように楽しく、裏では時間あたりの生産性をきっちり記録する。
// データ：Firebase の day/<日付>_<人>（1日1人1文書）。訪問数は訪問マップの記録（今日は act、前日までは day の v）から自動で入る。
(function(){
'use strict';

const KIND = { door: '訪販', call: '反響対応', post: '配布', other: 'その他' };
const KIND_ORDER = ['door', 'call', 'post', 'other'];
const KIND_C = { door: 'var(--accent)', call: 'var(--r-again)', post: 'var(--r-ihng)', other: 'var(--ink3)' };
// お題の基準（1日＝基準の時間あたりの数）。管理者が「チーム」から変えられる
const GOAL_DEF = { std: 6, door: 60, face: 10, call: 15, post: 500, got: 1, monthGot: 20 };
// 点の付け方
const PT = { door: 1, face: 3, got: 30, call: 2, conn: 1, post100: 2 };
const RANKS = [[0, '見習い'], [300, '駆け出し'], [800, '一人前'], [1500, '腕利き'], [2500, '達人'], [4000, '名人']];
const FACE = ['fng', 'again', 'got'];
const WEEK = '日月火水木金土';

let C = null; // 本体から受け取る道具（el, $, toast, FB, upsert, ...）
const S = {
  today: '', doc: null, ydoc: null, yday: '', acts: [], goal: Object.assign({}, GOAL_DEF),
  mine: null, team: null, teamKey: '', users: null,
  tab: 'today', draft: null, teamPeriod: 'today', pending: false, unsub: [], okShown: ''
};

// ---------- 小さな道具 ----------
const pad = n => String(n).padStart(2, '0');
const ymd = t => { const d = new Date(t); return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()); };
const toDate = s => new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8));
const clock = ms => { ms = Math.max(0, ms); const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, s = Math.floor(ms / 1000) % 60; return `${h}:${pad(m)}:${pad(s)}`; };
const hm = ms => { ms = Math.max(0, ms); const h = Math.floor(ms / 3600000), m = Math.round(ms / 60000) % 60; return h ? `${h}時間${m ? m + '分' : ''}` : `${m}分`; };
const hours1 = ms => (ms / 3600000).toFixed(1);
const toMin = t => { if (!t) return null; const [h, m] = t.split(':').map(Number); return h * 60 + m; };
const timeOf = ms => { const d = new Date(ms); return `${d.getHours()}:${pad(d.getMinutes())}`; };
const md = s => { const d = toDate(s); return `${d.getMonth() + 1}/${d.getDate()}(${WEEK[d.getDay()]})`; };
const pct = (a, b) => b ? Math.round(a / b * 100) : null;
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
const myId = () => (C.me() || {}).id || '';
const el = (...a) => C.el(...a);
// 開いた「詳しく」は、書き直しても開いたままにする
const keepOpen = (key, d) => { if (S.open && S.open[key]) d.open = true; d.addEventListener('toggle', () => { S.open = S.open || {}; S.open[key] = d.open; }); return d; };

// ---------- 数字の計算 ----------
function visitsOf(entries){
  const v = { doors: 0, face: 0, got: 0 };
  for (const x of entries) { v.doors++; if (FACE.includes(x.r)) v.face++; if (x.r === 'got') v.got++; }
  return v;
}
function actEntries(u){
  const out = [];
  for (const d of S.acts) for (const k in d) { const v = d[k]; if (v && v.t && !v.x && v.r && (!u || v.u === u)) out.push(v); }
  return out;
}
// 1日の数字。live=今日（訪問数は今の記録から、実行中の時間は今まで）
function statOf(doc, live, u){
  doc = doc || {};
  const now = Date.now();
  const h = { door: 0, call: 0, post: 0, other: 0 };
  let running = null;
  for (const id in (doc.ses || {})) {
    const s = doc.ses[id]; if (!s || !s.st) continue;
    const en = s.en || (live ? now : s.st);
    h[s.k] = (h[s.k] || 0) + Math.max(0, en - s.st);
    if (!s.en) running = Object.assign({ id }, s);
  }
  const v = live ? visitsOf(actEntries(u || doc.u || myId())) : Object.assign({ doors: 0, face: 0, got: 0 }, doc.v || {});
  const post = Object.values(doc.post || {}).reduce((a, p) => a + (+p.n || 0), 0);
  const han = Object.assign({ call: 0, conn: 0, prop: 0, got: 0 }, doc.han || {});
  const got = (v.got || 0) + (han.got || 0);
  const work = Object.values(h).reduce((a, b) => a + b, 0);
  const pts = v.doors * PT.door + v.face * PT.face + got * PT.got + han.call * PT.call + han.conn * PT.conn + Math.floor(post / 100) * PT.post100;
  const plan = Object.values(doc.plan || {});
  const ph = { door: 0, call: 0, post: 0, other: 0 };
  for (const p of plan) { const a = toMin(p.s), b = toMin(p.e); if (a != null && b != null && b > a) ph[p.k] = (ph[p.k] || 0) + (b - a) * 60000; }
  return { h, work, running, v, post, han, got, pts, plan, ph, off: !!doc.off, sub: doc.sub || 0, has: !!(plan.length || work || doc.off || doc.sub) };
}
// お題：予定した時間に合わせて数を決める（基準の時間で1日分）
function targetsOf(st){
  const g = S.goal; const out = [];
  const hrs = k => (st.ph[k] || st.h[k] || 0) / 3600000;
  const sc = k => hrs(k) / (g.std || 6);
  const n = (base, s) => Math.max(1, Math.round(base * s));
  if (hrs('door') > 0) { out.push({ key: 'doors', label: '訪問', val: st.v.doors, tgt: n(g.door, sc('door')) }); out.push({ key: 'face', label: '対面', val: st.v.face, tgt: n(g.face, sc('door')) }); }
  if (hrs('call') > 0) out.push({ key: 'call', label: '反響電話', val: st.han.call, tgt: n(g.call, sc('call')) });
  if (hrs('post') > 0) out.push({ key: 'post', label: '配布枚数', val: st.post, tgt: n(g.post, sc('post')) });
  if (hrs('door') > 0 || hrs('call') > 0) out.push({ key: 'got', label: '獲得', val: st.got, tgt: n(g.got, sc('door') + sc('call')) });
  return out;
}
const achieved = ts => ts.length > 0 && ts.every(t => t.val >= t.tgt);
function rankOf(p){ let i = 0; for (let j = 0; j < RANKS.length; j++) if (p >= RANKS[j][0]) i = j; return { i, name: RANKS[i][1], next: RANKS[i + 1] || null, base: RANKS[i][0] }; }

// 自分の全日分（今日は今の記録で置き換え）
function myDays(){
  const m = {}; for (const d of (S.mine || [])) if (d && d.d) m[d.d] = d;
  if (S.doc) m[S.today] = S.doc; else delete m[S.today];
  if (S.ydoc) m[S.yday] = S.ydoc;
  return m;
}
const statDay = (days, d) => statOf(days[d], d === S.today);
function sumRange(days, from, to, u){
  const t = { h: { door: 0, call: 0, post: 0, other: 0 }, work: 0, doors: 0, face: 0, got: 0, doorGot: 0, post: 0, call: 0, conn: 0, hgot: 0, pts: 0, days: 0, ok: 0, off: 0 };
  for (const d in days) {
    if (d < from || d > to) continue;
    const st = statOf(days[d], d === S.today, u);
    for (const k in t.h) t.h[k] += st.h[k] || 0;
    t.work += st.work; t.doors += st.v.doors; t.face += st.v.face; t.doorGot += st.v.got; t.got += st.got; t.post += st.post;
    t.call += st.han.call; t.conn += st.han.conn; t.hgot += st.han.got; t.pts += st.pts;
    if (st.work || st.v.doors) t.days++;
    if (st.off) t.off++;
    if (achieved(targetsOf(st))) t.ok++;
  }
  return t;
}
// 連続：日報の提出か、休みの申告がある日が途切れずに続いている日数
function streak(days){
  let n = 0; const t0 = toDate(S.today);
  const okd = d => days[d] && (days[d].sub || days[d].off);
  if (okd(S.today)) n++;
  for (let i = 1; i < 400; i++) { const d = ymd(t0.getTime() - i * 86400000); if (okd(d)) n++; else break; }
  return n;
}
function monthStart(s){ return s.slice(0, 6) + '01'; }
function lastMonthSame(s){ const d = toDate(s); const a = new Date(d.getFullYear(), d.getMonth() - 1, 1); const b = new Date(d.getFullYear(), d.getMonth() - 1, Math.min(d.getDate(), new Date(d.getFullYear(), d.getMonth(), 0).getDate())); return [ymd(a), ymd(b)]; }
function weekStart(s, back){ const d = toDate(s); const w = (d.getDay() + 6) % 7; return ymd(d.getTime() - (w + 7 * (back || 0)) * 86400000); }

// ---------- 書き込み ----------
async function save(patch, quiet){
  const base = { u: myId(), d: S.today };
  S.doc = Object.assign({}, S.doc || base, base, patch);
  rerender();
  try { await C.upsert(C.FB.day.ref(S.today), Object.assign({}, base, patch)); }
  catch (e) { C.toast(e && e.code === 'permission_denied' ? '保存できませんでした。管理者に「業務の記録」の設定を確認してもらってください。' : '保存できませんでした。通信状態を確認してもう一度お試しください。'); }
  if (!quiet) checkAchieve();
}
async function saveY(patch){
  if (!S.ydoc) return;
  S.ydoc = Object.assign({}, S.ydoc, patch); rerender();
  try { await C.upsert(C.FB.day.ref(S.yday), Object.assign({ u: myId(), d: S.yday }, patch)); } catch (e) { C.toast('保存できませんでした。'); }
}
function startWork(k, pid){
  const ses = Object.assign({}, (S.doc && S.doc.ses) || {});
  const now = Date.now();
  for (const id in ses) if (!ses[id].en) ses[id] = Object.assign({}, ses[id], { en: now });
  const id = uid(); ses[id] = { k, st: now, en: null }; if (pid) ses[id].pid = pid;
  save({ ses }, true);
  C.toast(`${KIND[k]}を開始しました。いってらっしゃい！`);
}
function stopWork(){
  const ses = Object.assign({}, (S.doc && S.doc.ses) || {});
  const now = Date.now(); let k = null, st = 0;
  for (const id in ses) if (!ses[id].en) { k = ses[id].k; st = ses[id].st; ses[id] = Object.assign({}, ses[id], { en: now }); }
  if (!k) return;
  save({ ses });
  C.toast(`${KIND[k]}を終了しました（${hm(now - st)}）。おつかれさまです`);
}

// ---------- お祝いの演出 ----------
function confetti(){
  if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const box = el('div', { class: 'ss-confetti', 'aria-hidden': 'true' });
  const cols = ['#1B1FA8', '#5CC2F2', '#1f9a55', '#c9920e', '#e0861c', '#d24a3a'];
  for (let i = 0; i < 46; i++) {
    const s = el('i'); s.style.left = Math.random() * 100 + '%'; s.style.background = cols[i % cols.length];
    s.style.animationDelay = (Math.random() * .5) + 's'; s.style.animationDuration = (1.6 + Math.random() * 1.2) + 's';
    s.style.transform = `rotate(${Math.random() * 360}deg)`; box.append(s);
  }
  document.body.append(box); setTimeout(() => box.remove(), 3400);
}
function cheer(title, sub){
  const o = el('div', { class: 'ss-cheer', role: 'status' }, el('b', { text: title }), sub ? el('span', { text: sub }) : null);
  document.body.append(o); confetti(); setTimeout(() => o.classList.add('out'), 2200); setTimeout(() => o.remove(), 2700);
}
function checkAchieve(){
  if (!S.doc) return;
  const st = statOf(S.doc, true);
  const ts = targetsOf(st);
  let seen = ''; try { seen = localStorage.getItem('hm_ssOk') || ''; } catch (e) {}
  if (achieved(ts) && seen !== S.today) {
    try { localStorage.setItem('hm_ssOk', S.today); } catch (e) {}
    cheer('今日のお題 達成！', `${st.pts}点・この調子です`);
  }
}

// ---------- 読み込み ----------
function stopWatch(){ S.unsub.forEach(u => { try { u(); } catch (e) {} }); S.unsub = []; }
function watch(){
  stopWatch();
  const FB = C.FB;
  S.today = ymd(Date.now()); S.yday = ymd(Date.now() - 86400000);
  S.doc = null; S.ydoc = null; S.acts = [];
  S.unsub.push(FB.day.watch(S.today, d => { S.doc = d; rerender(); }));
  S.unsub.push(FB.day.watch(S.yday, d => { S.ydoc = d; rerender(); }));
  S.unsub.push(FB.act.watchDay(S.today, docs => { S.acts = docs || []; rerender(); checkAchieve(); }));
  S.unsub.push(FB.cfg.watch('goal', d => { S.goal = Object.assign({}, GOAL_DEF, d || {}); rerender(); }));
  loadMine();
}
async function loadMine(){ const r = await C.FB.day.mine(); if (r) { S.mine = r; rerender(); } }
async function loadTeam(force){
  if (!C.FB.isStaff()) return;
  const [from, to] = periodRange(S.teamPeriod);
  const key = from + to;
  if (!force && S.teamKey === key && S.team) return;
  S.teamKey = key; S.team = null; rerender();
  if (!S.users) { try { S.users = (await C.FB.admin.list()).filter(u => u.active !== false); } catch (e) { S.users = []; } }
  const r = await C.FB.day.range(from, to);
  S.team = r || [];
  rerender();
}
function periodRange(p){
  const t = S.today;
  if (p === 'today') return [t, t];
  if (p === 'yday') { const y = ymd(toDate(t).getTime() - 86400000); return [y, y]; }
  if (p === 'week') return [weekStart(t), t];
  if (p === 'month') return [monthStart(t), t];
  if (p === 'last') { const d = toDate(t); return [ymd(new Date(d.getFullYear(), d.getMonth() - 1, 1)), ymd(new Date(d.getFullYear(), d.getMonth(), 0))]; }
  return [t, t];
}

// ---------- 画面：組み立て ----------
let rT = 0;
function rerender(){
  clearTimeout(rT);
  rT = setTimeout(() => {
    if (C.isOpen()) {
      const b = C.$('#pBody'); const a = document.activeElement;
      if (b && a && b.contains(a) && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) { S.pending = true; return; }
      render();
    }
    C.homeRefresh();
  }, 60);
}
document.addEventListener('focusout', () => { if (S.pending) { S.pending = false; setTimeout(rerender, 200); } });

function render(){
  const body = C.$('#pBody'); if (!body) return;
  const keep = body.scrollTop;
  C.$('#pTitle').textContent = '業務';
  const days = myDays(); const mp = sumRange(days, monthStart(S.today), S.today).pts; const rk = rankOf(mp); const sk = streak(days);
  C.$('#pSub').textContent = `${rk.name}・今月${mp.toLocaleString()}点・連続${sk}日`;
  body.textContent = '';
  const tabs = [['today', '今日'], ['month', '今月の成績']];
  if (C.FB.isStaff()) tabs.push(['team', 'チーム']);
  body.append(el('div', { class: 'seg ss-tabs', role: 'group' }, tabs.map(([k, t]) => el('button', { 'aria-pressed': String(S.tab === k), onclick: () => { S.tab = k; if (k === 'team') loadTeam(); if (k === 'month' && !S.mine) loadMine(); render(); C.$('#pBody').scrollTop = 0; } }, t))));
  if (!C.FB.day) { body.append(el('div', { class: 'note-box', text: '保存の仕組みにつながると使えます。' })); return; }
  if (S.tab === 'today') renderToday(body);
  else if (S.tab === 'month') renderMonth(body, days);
  else renderTeam(body);
  body.scrollTop = keep;
}

// ----- 今日 -----
function heroBox(st, compact){
  const box = el('div', { class: 'ss-hero' + (st.running ? ' on' : '') });
  if (st.running) {
    box.append(el('div', { class: 'ss-hk' }, el('span', { class: 'ss-dot', style: `background:${KIND_C[st.running.k]}` }), `${KIND[st.running.k]} 実行中`),
      el('div', { class: 'ss-clock', 'data-st': st.running.st, text: clock(Date.now() - st.running.st) }),
      el('div', { class: 'ss-hsub', text: `${timeOf(st.running.st)} 開始・今日の合計 ${hm(st.work)}` }),
      el('button', { class: 'btn primary ss-big ss-stop', onclick: e => { e.stopPropagation(); stopWork(); } }, '終了する'));
    return box;
  }
  if (st.off) { box.append(el('div', { class: 'ss-hk', text: '今日は休みで申告済みです' }), el('div', { class: 'ss-hsub', text: 'ゆっくり休んでください。' })); return box; }
  if (!st.plan.length && !st.work) {
    box.append(el('div', { class: 'ss-hk', text: 'まず、今日やることを申告しましょう' }), el('div', { class: 'ss-hsub', text: '予定はGoogleカレンダーにも自動で入ります。' }));
    if (compact) box.append(el('button', { class: 'btn primary ss-big', onclick: e => { e.stopPropagation(); C.openMe('today'); } }, '今日の予定を申告する'));
    return box;
  }
  if (st.sub) {
    box.append(el('div', { class: 'ss-hk', text: `日報を提出しました。おつかれさまでした！` }), el('div', { class: 'ss-hsub', text: `今日の合計 ${hm(st.work)}・${st.pts}点` }));
    return box;
  }
  const next = nextPlan(st);
  box.append(el('div', { class: 'ss-hk', text: st.work ? `今日の合計 ${hm(st.work)}・${st.pts}点` : '準備ができたら開始を押しましょう' }),
    el('div', { class: 'ss-hsub', text: next ? `次の予定：${next.s}〜${next.e} ${KIND[next.k]}${next.m ? '（' + next.m + '）' : ''}` : st.sub ? '日報を提出しました。おつかれさまでした！' : '予定はすべて終わりました。日報を出しましょう。' }));
  if (!st.sub) box.append(el('button', { class: 'btn primary ss-big', onclick: e => { e.stopPropagation(); startWork(next ? next.k : 'door', next ? next.id : null); } }, next ? `${KIND[next.k]}を開始する` : '開始する'));
  return box;
}
function nextPlan(st){
  const ses = Object.values((S.doc && S.doc.ses) || {});
  const used = new Set(ses.map(s => s.pid).filter(Boolean));
  const list = Object.entries((S.doc && S.doc.plan) || {}).map(([id, p]) => Object.assign({ id }, p)).sort((a, b) => (toMin(a.s) || 0) - (toMin(b.s) || 0));
  const left = list.filter(p => !used.has(p.id));
  const d = new Date(); const nowM = d.getHours() * 60 + d.getMinutes();
  return left.find(p => toMin(p.e) > nowM) || left[left.length - 1] || null;
}
function goalBox(st){
  const ts = targetsOf(st);
  if (!ts.length) return null;
  const ok = achieved(ts);
  return el('section', { class: 'ss-card' + (ok ? ' ok' : '') },
    el('h3', null, '今日のお題', ok ? el('span', { class: 'ss-stamp', text: '達成' }) : el('small', { text: `達成すると +お祝い` })),
    ts.map(t => {
      const p = Math.min(100, Math.round(t.val / t.tgt * 100));
      return el('div', { class: 'ss-bar' + (t.val >= t.tgt ? ' done' : '') },
        el('div', { class: 'ss-bl' }, el('span', { text: t.label }), el('b', { text: `${t.val.toLocaleString()} / ${t.tgt.toLocaleString()}` })),
        el('div', { class: 'ss-track' }, el('i', { style: `width:${p}%` })),
        t.val < t.tgt ? el('small', { class: 'muted', text: `あと${(t.tgt - t.val).toLocaleString()}` }) : null);
    }),
    el('div', { class: 'muted', text: '数は予定した時間に合わせて決まります。訪問・対面・獲得は、建物の画面で登録した結果から自動で数えます。' }));
}
function planEditor(){
  if (!S.draft) {
    const cur = Object.entries((S.doc && S.doc.plan) || {}).map(([id, p]) => Object.assign({ id }, p)).sort((a, b) => (toMin(a.s) || 0) - (toMin(b.s) || 0));
    S.draft = cur.length ? cur : [{ id: uid(), k: 'door', s: '10:00', e: '13:00', m: '' }, { id: uid(), k: 'door', s: '14:00', e: '18:00', m: '' }];
  }
  const sec = el('section', { class: 'ss-card' }, el('h3', { text: '今日の予定' }));
  S.draft.forEach((p, i) => {
    sec.append(el('div', { class: 'ss-pedit' },
      el('div', { class: 'ss-pline' },
        el('select', { 'aria-label': 'やること', onchange: e => { p.k = e.target.value; } }, KIND_ORDER.map(k => el('option', { value: k, selected: p.k === k }, KIND[k]))),
        el('input', { type: 'time', value: p.s, 'aria-label': '開始', onchange: e => { p.s = e.target.value; } }),
        el('span', { class: 'ss-tilde', text: '〜' }),
        el('input', { type: 'time', value: p.e, 'aria-label': '終了', onchange: e => { p.e = e.target.value; } }),
        el('button', { class: 'x ss-del', 'aria-label': 'この予定を消す', onclick: () => { S.draft.splice(i, 1); render(); } }, '×')),
      el('input', { type: 'text', class: 'ss-memo', placeholder: 'メモ（エリア・物件など）', value: p.m || '', onchange: e => { p.m = e.target.value; } })));
  });
  const last = days => { const ds = Object.keys(days).filter(d => d < S.today && days[d].plan && Object.keys(days[d].plan).length).sort(); return ds.length ? days[ds[ds.length - 1]] : null; };
  const prev = last(myDays());
  sec.append(el('div', { class: 'btnrow' },
    el('button', { class: 'btn', onclick: () => { const lp = S.draft[S.draft.length - 1]; S.draft.push({ id: uid(), k: lp ? lp.k : 'door', s: lp ? lp.e : '10:00', e: lp && toMin(lp.e) != null ? (pad(Math.min(23, Math.floor(toMin(lp.e) / 60) + 2)) + ':' + pad(toMin(lp.e) % 60)) : '12:00', m: '' }); render(); } }, '＋ 予定を足す'),
    prev ? el('button', { class: 'btn', onclick: () => { S.draft = Object.values(prev.plan).map(p => Object.assign({}, p, { id: uid() })).sort((a, b) => (toMin(a.s) || 0) - (toMin(b.s) || 0)); render(); } }, '前回と同じにする') : null));
  sec.append(el('div', { class: 'btnrow' },
    el('button', { class: 'btn primary', onclick: () => {
      const bad = S.draft.find(p => toMin(p.s) == null || toMin(p.e) == null || toMin(p.e) <= toMin(p.s));
      if (!S.draft.length) { C.toast('予定を1つ以上入れてください'); return; }
      if (bad) { C.toast('終わりの時刻は、始まりより後にしてください'); return; }
      const plan = {}; S.draft.forEach(p => { plan[p.id] = { k: p.k, s: p.s, e: p.e, m: (p.m || '').trim() }; });
      S.draft = null; S.editing = false; save({ plan, off: false }, true); C.toast('今日の予定を申告しました。Googleカレンダーにも入ります');
    } }, 'この予定で申告する'),
    el('button', { class: 'btn', onclick: () => { if (confirm('今日は休みとして申告しますか？')) { S.draft = null; S.editing = false; save({ off: true }, true); } } }, '今日は休み'),
    (S.doc && S.doc.plan && Object.keys(S.doc.plan).length) ? el('button', { class: 'btn', onclick: () => { S.draft = null; S.editing = false; render(); } }, 'やめる') : null));
  sec.append(el('div', { class: 'muted', text: '予定はGoogleカレンダー「AImost 業務予定」に自動で入ります（反映まで10分ほど）。' }));
  return sec;
}
function planList(st){
  const ses = Object.values((S.doc && S.doc.ses) || {});
  const list = Object.entries((S.doc && S.doc.plan) || {}).map(([id, p]) => Object.assign({ id }, p)).sort((a, b) => (toMin(a.s) || 0) - (toMin(b.s) || 0));
  const sec = el('section', { class: 'ss-card' }, el('h3', null, '今日の予定', el('button', { class: 'linkbtn', onclick: () => { S.editing = true; S.draft = null; render(); } }, '予定を直す')));
  for (const p of list) {
    const mine = ses.filter(s => s.pid === p.id);
    const run = mine.find(s => !s.en);
    const used = mine.reduce((a, s) => a + ((s.en || Date.now()) - s.st), 0);
    const state = run ? '実行中' : mine.length ? `済み（${hm(used)}）` : '';
    sec.append(el('div', { class: 'ss-pitem' + (run ? ' on' : mine.length ? ' done' : '') },
      el('span', { class: 'ss-dot', style: `background:${KIND_C[p.k]}` }),
      el('div', { class: 'ss-pt' }, el('b', { text: `${p.s}〜${p.e} ${KIND[p.k]}` }), p.m ? el('small', { class: 'muted', text: p.m }) : null),
      state ? el('span', { class: 'ss-pst', text: state }) : null,
      !run && !st.sub ? el('button', { class: 'btn', onclick: () => startWork(p.k, p.id) }, mine.length ? '再開' : '開始') : null));
  }
  if (!st.sub && !st.running) {
    sec.append(keepOpen('adhoc', el('details', { class: 'ss-adhoc' }, el('summary', { text: '予定にない仕事を開始する' }),
      el('div', { class: 'btnrow' }, KIND_ORDER.map(k => el('button', { class: 'btn', onclick: () => { S.open && (S.open.adhoc = false); startWork(k); } }, KIND[k]))))));
  }
  return sec;
}
function counter(label, key, han){
  const v = han[key] || 0;
  // 続けて押されても数え漏れないよう、いまの記録から足し引きする
  const add = dlt => { const h = Object.assign({ call: 0, conn: 0, prop: 0, got: 0 }, (S.doc && S.doc.han) || {}); h[key] = Math.max(0, (h[key] || 0) + dlt); save({ han: h }); };
  return el('div', { class: 'ss-cnt' }, el('span', { text: label }),
    el('button', { class: 'ss-cb', 'aria-label': label + 'を1減らす', onclick: () => add(-1) }, '−'),
    el('b', { text: v }),
    el('button', { class: 'ss-cb plus', 'aria-label': label + 'を1増やす', onclick: () => add(1) }, '＋'));
}
function hanBox(st){
  return el('section', { class: 'ss-card' }, el('h3', { text: '反響対応（ポスティングの反響への電話）' }),
    el('div', { class: 'ss-cnts' }, counter('電話した', 'call', st.han), counter('つながった', 'conn', st.han), counter('提案できた', 'prop', st.han), counter('獲得', 'got', st.han)),
    st.han.call ? el('div', { class: 'muted', text: `つながった率 ${pct(st.han.conn, st.han.call)}%・つながってからの獲得 ${st.han.conn ? pct(st.han.got, st.han.conn) : 0}%` }) : null);
}
function postBox(st){
  const list = Object.entries((S.doc && S.doc.post) || {}).sort((a, b) => a[1].t - b[1].t);
  const area = el('input', { type: 'text', placeholder: '配ったエリア（例：横浜市青葉区 美しが丘）', list: 'ssAreas', class: 'ss-in' });
  const num = el('input', { type: 'number', inputmode: 'numeric', min: 1, placeholder: '枚数', class: 'ss-in ss-num' });
  const dl = el('datalist', { id: 'ssAreas' }, (C.cityNames() || []).map(n => el('option', { value: n })));
  return el('section', { class: 'ss-card' }, el('h3', null, '配布報告', st.post ? el('small', { text: `今日 ${st.post.toLocaleString()}枚` }) : null),
    list.map(([id, p]) => el('div', { class: 'ss-plist' }, el('span', { text: p.a || 'エリア未記入' }), el('b', { text: `${(+p.n).toLocaleString()}枚` }),
      el('button', { class: 'x ss-del', 'aria-label': 'この報告を消す', onclick: () => { if (!confirm('この配布報告を消しますか？')) return; const m = Object.assign({}, S.doc.post); delete m[id]; save({ post: m }); } }, '×'))),
    el('div', { class: 'ss-prow' }, area, num, dl,
      el('button', { class: 'btn primary', onclick: () => {
        const n = parseInt(num.value, 10); if (!(n > 0)) { C.toast('枚数を入れてください'); return; }
        const m = Object.assign({}, (S.doc && S.doc.post) || {}); m[uid()] = { a: area.value.trim(), n, t: Date.now() };
        area.value = ''; num.value = ''; area.blur(); num.blur(); S.pending = false; save({ post: m }); C.toast(`${n.toLocaleString()}枚の配布を記録しました`);
      } }, '記録')));
}
function reportBox(st){
  const sec = el('section', { class: 'ss-card' + (st.sub ? ' ok' : '') }, el('h3', null, '日報', st.sub ? el('span', { class: 'ss-stamp', text: '提出済み' }) : null));
  const sm = el('div', { class: 'kpis ss-kpis' }, [['稼働', hours1(st.work) + 'h'], ['訪問', st.v.doors], ['対面', st.v.face], ['獲得', st.got], ['配布', st.post.toLocaleString()], ['反響電話', st.han.call], ['今日の点', st.pts]].map(([t, v]) => el('div', { class: 'kpi' }, el('b', { text: v }), el('span', { text: t }))));
  sec.append(sm);
  if (st.work) {
    const parts = KIND_ORDER.filter(k => st.h[k]).map(k => `${KIND[k]} ${hm(st.h[k])}`);
    const per = st.h.door > 600000 ? `・訪販1時間あたり ${(st.v.doors / (st.h.door / 3600000)).toFixed(1)}部屋` : '';
    sec.append(el('div', { class: 'muted', text: parts.join('・') + per }));
  }
  if (st.sub && !S.editRep) {
    if (S.doc.refl) sec.append(el('div', { class: 'ss-q' }, el('small', { text: '振り返り' }), el('div', { text: S.doc.refl })));
    if (S.doc.tmr) sec.append(el('div', { class: 'ss-q' }, el('small', { text: '明日やること' }), el('div', { text: S.doc.tmr })));
    sec.append(el('div', { class: 'btnrow' }, el('button', { class: 'btn', onclick: () => { S.editRep = true; render(); } }, '日報を直す')));
    return sec;
  }
  const refl = el('textarea', { rows: 2, class: 'ss-ta', placeholder: '今日の振り返りをひとこと（うまくいったこと・次に変えること）' }); refl.value = (S.doc && S.doc.refl) || '';
  const tmr = el('textarea', { rows: 2, class: 'ss-ta', placeholder: '明日やること（任意）' }); tmr.value = (S.doc && S.doc.tmr) || '';
  sec.append(refl, tmr, el('div', { class: 'btnrow' }, el('button', { class: 'btn primary', onclick: () => {
    if (!refl.value.trim()) { C.toast('振り返りをひとこと書いてください'); refl.focus(); return; }
    const first = !st.sub;
    const ses = Object.assign({}, (S.doc && S.doc.ses) || {}); const now = Date.now(); let stopped = false;
    for (const id in ses) if (!ses[id].en) { ses[id] = Object.assign({}, ses[id], { en: now }); stopped = true; }
    S.editRep = false; S.pending = false; document.activeElement && document.activeElement.blur();
    save(Object.assign({ refl: refl.value.trim(), tmr: tmr.value.trim(), sub: st.sub || now }, stopped ? { ses } : {}), true);
    if (first) {
      const days = myDays(); let best = 0; for (const d in days) if (d !== S.today) best = Math.max(best, statOf(days[d], false).pts);
      const pts = statOf(S.doc, true).pts;
      cheer('日報 提出！', pts > best && best > 0 ? `今日は${pts}点・自己最高を更新！` : `今日は${pts}点・連続${streak(myDays())}日`);
    } else C.toast('日報を直しました');
  } }, st.sub ? '直して保存' : '日報を提出する（終了も押されます）')));
  return sec;
}
function renderToday(body){
  const st = statOf(S.doc, true);
  // 昨日の押し忘れ
  const yst = S.ydoc ? statOf(S.ydoc, false) : null;
  if (S.ydoc && Object.values(S.ydoc.ses || {}).some(s => !s.en)) {
    const s = Object.entries(S.ydoc.ses).find(([, x]) => !x.en);
    const inp = el('input', { type: 'time', value: '19:00', class: 'ss-in' });
    body.append(el('section', { class: 'ss-card warn' }, el('h3', { text: '昨日の「終了」が押されていません' }),
      el('div', { class: 'muted', text: `${KIND[s[1].k]}を${timeOf(s[1].st)}に開始したままです。終わった時刻を入れてください。` }),
      el('div', { class: 'ss-prow' }, inp, el('button', { class: 'btn primary', onclick: () => {
        const m = toMin(inp.value); if (m == null) return; const d = toDate(S.yday); const en = d.getTime() + m * 60000;
        if (en <= s[1].st) { C.toast('開始より後の時刻にしてください'); return; }
        const ses = Object.assign({}, S.ydoc.ses); ses[s[0]] = Object.assign({}, s[1], { en }); saveY({ ses }); C.toast('昨日の終了時刻を直しました');
      } }, '終了時刻を入れる'))));
  }
  if (yst && yst.has && !yst.sub && !yst.off && !S.ydoc.late) {
    body.append(el('div', { class: 'note-box ss-warnline' }, '昨日の日報がまだです。', el('button', { class: 'linkbtn', onclick: () => { S.tab = 'today'; lateYesterday(body); } }, '昨日の日報を出す')));
  }
  body.append(heroBox(st));
  const editing = S.editing || (!st.off && !st.plan.length && !st.work);
  if (st.off && !editing) body.append(el('section', { class: 'ss-card' }, el('h3', { text: '今日は休み' }), el('div', { class: 'btnrow' }, el('button', { class: 'btn', onclick: () => { S.editing = true; save({ off: false }, true); } }, '休みを取り消して予定を申告'))));
  else if (editing) body.append(planEditor());
  else body.append(planList(st));
  if (st.off && !editing) return;
  const g = goalBox(st); if (g) body.append(g);
  const used = k => (st.ph[k] || st.h[k]);
  if (used('call') || st.han.call) body.append(hanBox(st));
  if (used('post') || st.post) body.append(postBox(st));
  const rest = [];
  if (!(used('call') || st.han.call)) rest.push(hanBox(st));
  if (!(used('post') || st.post)) rest.push(postBox(st));
  if (rest.length) body.append(keepOpen('more', el('details', { class: 'ss-more' }, el('summary', { text: '予定にない記録（反響対応・配布）' }), rest)));
  if (st.plan.length || st.work) body.append(reportBox(st));
  body.append(el('button', { class: 'btn', onclick: () => C.openPanel('act') }, '訪問の明細を地図で見る'));
}
function lateYesterday(body){
  const refl = prompt('昨日の振り返りをひとこと');
  if (refl == null || !refl.trim()) return;
  saveY({ refl: refl.trim(), sub: Date.now(), late: 1 });
  C.toast('昨日の日報を出しました');
}

// ----- 今月 -----
function arrow(now, before, unit){
  if (before == null || !isFinite(before)) return null;
  if (!before && !now) return null;
  const d = before ? Math.round((now - before) / before * 100) : 100;
  if (d === 0) return el('small', { class: 'ss-ar', text: '先月と同じ' });
  return el('small', { class: 'ss-ar ' + (d > 0 ? 'up' : 'dn'), text: `${d > 0 ? '▲' : '▼'}${Math.abs(d)}%` });
}
function insights(days, cur, prev){
  const out = [];
  const t = S.today;
  const tw = sumRange(days, weekStart(t), t), lw0 = weekStart(t, 1);
  const lwEnd = ymd(toDate(lw0).getTime() + (toDate(t) - toDate(weekStart(t))));
  const lw = sumRange(days, lw0, lwEnd);
  if (lw.work > 3600000) {
    const d = Math.round((tw.work - lw.work) / lw.work * 100);
    if (d <= -20) out.push(['dn', `今週の稼働時間は、先週の同じ曜日までより${Math.abs(d)}%少ないペースです（${hours1(tw.work)}時間／先週${hours1(lw.work)}時間）。`]);
    else if (d >= 20) out.push(['up', `今週の稼働時間は先週より${d}%多いペースです。いい流れです。`]);
  }
  if (cur.doors >= 30 && prev.doors >= 30) {
    const a = cur.face / cur.doors, b = prev.face / prev.doors;
    if (a - b >= 0.03) out.push(['up', `対面率が先月より上がっています（${Math.round(b * 100)}%→${Math.round(a * 100)}%）。`]);
    else if (b - a >= 0.03) out.push(['dn', `対面率が先月より下がっています（${Math.round(b * 100)}%→${Math.round(a * 100)}%）。回る時間帯を見直すと上がるかもしれません。`]);
  }
  if (cur.h.door > 3600000 && prev.h.door > 3600000) {
    const a = cur.doors / (cur.h.door / 3600000), b = prev.doors / (prev.h.door / 3600000);
    if (b && (a - b) / b <= -0.15) out.push(['dn', `訪販1時間あたりの訪問数が先月より減っています（${b.toFixed(1)}→${a.toFixed(1)}部屋）。移動や待ち時間が増えていないか見てみましょう。`]);
  }
  // 申告のない日
  let none = 0; const from = toDate(monthStart(t));
  for (let x = from.getTime(); ymd(x) < t; x += 86400000) { const d = days[ymd(x)]; if (!d || (!d.off && !(d.plan && Object.keys(d.plan).length) && !(d.ses && Object.keys(d.ses).length))) none++; }
  if (none) out.push(['dn', `今月、予定も休みも申告がない日が${none}日あります。休みの日も「今日は休み」を押しておくと連続が途切れません。`]);
  // 目標の逆算
  const g = S.goal.monthGot;
  if (g) {
    const d0 = toDate(t); const last = new Date(d0.getFullYear(), d0.getMonth() + 1, 0).getDate(); const left = last - d0.getDate() + 1;
    const rem = g - cur.got;
    if (rem > 0) out.push(['', `今月の獲得の目安${g}件まであと${rem}件。残り${left}日なので、1日あたり約${(rem / left).toFixed(1)}件です。${cur.face && cur.doorGot ? `今の自分の割合なら、あと約${Math.ceil(rem / (cur.doorGot / cur.face))}件の対面が目安です。` : ''}`]);
    else out.push(['up', `今月の獲得の目安${g}件を達成しています！`]);
  }
  if (!out.length) out.push(['', 'まだ比べられるだけの記録がたまっていません。毎日つけると、ここに自分の気づきが出てきます。']);
  return out;
}
function renderMonth(body, days){
  const t = S.today; const from = monthStart(t);
  const [pf, pt] = lastMonthSame(t);
  const cur = sumRange(days, from, t), prev = sumRange(days, pf, pt);
  const rk = rankOf(cur.pts);
  let best = { pts: 0, d: '' }; for (const d in days) { const p = statDay(days, d).pts; if (p > best.pts) best = { pts: p, d }; }
  const nx = rk.next;
  body.append(el('section', { class: 'ss-card ss-rank' },
    el('div', { class: 'ss-rk' }, el('span', { class: 'ss-badge', text: rk.name }), el('b', { text: `${cur.pts.toLocaleString()}点` }), el('small', { class: 'muted', text: `今月（${toDate(t).getMonth() + 1}月）` })),
    nx ? el('div', { class: 'ss-bar' }, el('div', { class: 'ss-track' }, el('i', { style: `width:${Math.min(100, Math.round((cur.pts - rk.base) / (nx[0] - rk.base) * 100))}%` })), el('small', { class: 'muted', text: `「${nx[1]}」まであと${(nx[0] - cur.pts).toLocaleString()}点` })) : el('small', { class: 'muted', text: '最高の階級です！' }),
    el('div', { class: 'ss-mini' }, el('span', null, '連続 ', el('b', { text: streak(days) + '日' })), el('span', null, 'お題達成 ', el('b', { text: cur.ok + '日' })), best.d ? el('span', null, '自己最高 ', el('b', { text: best.pts + '点' }), ` (${md(best.d)})`) : null),
    el('div', { class: 'muted', text: '点の付け方：訪問1・対面3・獲得30・反響電話2・つながった1・配布100枚で2。階級は毎月1日にまた見習いから。' })));
  body.append(el('section', { class: 'ss-card' }, el('h3', { text: '気づき' }), insights(days, cur, prev).map(([c, x]) => el('div', { class: 'ss-ins ' + c, text: x }))));
  const early = +t.slice(6) < 3;
  const k = (label, v, p, fmt) => el('div', { class: 'kpi' }, el('b', { text: fmt ? fmt(v) : v.toLocaleString() }), el('span', { text: label }), early ? null : arrow(v, p));
  body.append(el('section', { class: 'ss-card' }, el('h3', null, '今月の数字', el('small', { text: early ? '3日目から先月と比べます' : '先月の同じ日までと比べて' })),
    el('div', { class: 'kpis ss-k3' }, k('稼働時間', cur.work, prev.work, v => hours1(v) + 'h'), k('訪問', cur.doors, prev.doors), k('対面', cur.face, prev.face), k('獲得', cur.got, prev.got), k('配布枚数', cur.post, prev.post), k('反響電話', cur.call, prev.call))));
  const rate = (a, b) => b ? Math.round(a / b * 100) + '%' : '—';
  const per = (a, ms) => ms > 600000 ? (a / (ms / 3600000)).toFixed(1) : '—';
  const team = S.teamAvg;
  const rows = [
    ['対面率（対面÷訪問）', rate(cur.face, cur.doors), rate(prev.face, prev.doors), team ? rate(team.face, team.doors) : null],
    ['獲得率（獲得÷対面）', rate(cur.doorGot, cur.face), rate(prev.doorGot, prev.face), team ? rate(team.doorGot, team.face) : null],
    ['反響 つながった率', rate(cur.conn, cur.call), rate(prev.conn, prev.call), team ? rate(team.conn, team.call) : null],
    ['反響 獲得率（÷つながった）', rate(cur.hgot, cur.conn), rate(prev.hgot, prev.conn), team ? rate(team.hgot, team.conn) : null],
    ['訪販1時間あたり訪問', per(cur.doors, cur.h.door), per(prev.doors, prev.h.door), team ? per(team.doors, team.h.door) : null],
    ['反響1時間あたり電話', per(cur.call, cur.h.call), per(prev.call, prev.h.call), team ? per(team.call, team.h.call) : null],
    ['配布1時間あたり枚数', per(cur.post, cur.h.post), per(prev.post, prev.h.post), team ? per(team.post, team.h.post) : null]
  ];
  body.append(el('section', { class: 'ss-card' }, el('h3', { text: '自分の流れと生産性' }),
    el('div', { class: 'ss-tw' }, el('table', { class: 'ss-tbl' },
      el('thead', null, el('tr', null, el('th', { text: '' }), el('th', { text: '今月' }), el('th', { text: '先月' }), team ? el('th', { text: 'チーム平均' }) : null)),
      el('tbody', null, rows.map(r => el('tr', null, el('th', { text: r[0] }), el('td', null, el('b', { text: r[1] })), el('td', { text: r[2] }), team ? el('td', { text: r[3] }) : null))))),
    el('div', { class: 'muted', text: '弱いところが一目でわかります。訪問数は多いのに対面率が低い、など。' })));
  if (C.FB.isStaff() && !S.teamAvg && !S.teamAvgLoading) loadTeamAvg();
  // 日別の棒
  const d0 = toDate(t); const last = new Date(d0.getFullYear(), d0.getMonth() + 1, 0).getDate();
  const arr = []; let max = 1;
  for (let i = 1; i <= last; i++) { const d = ymd(new Date(d0.getFullYear(), d0.getMonth(), i)); const st = d <= t ? statDay(days, d) : null; arr.push([d, st]); if (st) max = Math.max(max, st.pts); }
  body.append(el('section', { class: 'ss-card' }, el('h3', null, '日ごとの点', el('small', { text: '濃い色＝お題達成' })),
    el('div', { class: 'ss-chart', role: 'img', 'aria-label': '今月の日ごとの点の棒グラフ' }, arr.map(([d, st]) => {
      const ok = st && achieved(targetsOf(st));
      const h = st ? Math.round(st.pts / max * 100) : 0;
      return el('div', { class: 'ss-col' + (d === t ? ' today' : ''), title: st ? `${md(d)} ${st.pts}点${st.off ? '（休み）' : ''}` : md(d) },
        el('i', { class: ok ? 'ok' : '', style: `height:${st && st.pts ? Math.max(3, h) : 0}%` }), el('span', { text: st && st.off ? '休' : String(+d.slice(6)) }));
    })),
    el('div', { class: 'muted', text: '前日までの訪問数は、毎晩0時15分の書き写しのときに入ります。' })));
}
async function loadTeamAvg(){
  S.teamAvgLoading = true;
  const r = await C.FB.day.range(monthStart(S.today), S.today);
  if (r && r.length) {
    const days = {}; const t = { h: { door: 0, call: 0, post: 0, other: 0 }, doors: 0, face: 0, doorGot: 0, call: 0, conn: 0, hgot: 0, post: 0 };
    for (const d of r) { const st = statOf(d, d.d === S.today, d.u); for (const k in t.h) t.h[k] += st.h[k]; t.doors += st.v.doors; t.face += st.v.face; t.doorGot += st.v.got; t.call += st.han.call; t.conn += st.han.conn; t.hgot += st.han.got; t.post += st.post; }
    S.teamAvg = t; rerender();
  }
}

// ----- チーム（社員・管理者だけ） -----
function renderTeam(body){
  const sel = el('select', { onchange: e => { S.teamPeriod = e.target.value; loadTeam(true); } }, [['today', '今日'], ['yday', '昨日'], ['week', '今週'], ['month', '今月'], ['last', '先月']].map(([v, t]) => el('option', { value: v, selected: v === S.teamPeriod }, t)));
  body.append(el('div', { class: 'ctl' }, el('label', { text: '期間' }), sel, el('button', { class: 'btn', onclick: () => loadTeam(true) }, '更新')));
  if (!S.team) { body.append(el('div', { class: 'muted', text: '読み込み中…' })); return; }
  const [from, to] = periodRange(S.teamPeriod);
  const byU = {};
  for (const d of S.team) (byU[d.u] = byU[d.u] || {})[d.d] = d;
  const people = new Set(Object.keys(byU));
  (S.users || []).forEach(u => people.add(u.email));
  for (const d of S.acts) for (const k in d) { const v = d[k]; if (v && v.u) people.add(v.u); }
  const nameOf = id => { const u = (S.users || []).find(x => x.email === id); return (u && u.name) || C.nameOf(id); };
  const single = from === to;
  const rows = [...people].map(u => {
    const days = byU[u] || {};
    if (to === S.today && !days[S.today]) days[S.today] = { u, d: S.today };
    const t = { work: 0, doors: 0, face: 0, got: 0, post: 0, call: 0, doorH: 0, subs: 0, need: 0, ok: 0, pts: 0 };
    for (const d in days) {
      if (d < from || d > to) continue;
      const st = statOf(days[d], d === S.today, u);
      t.work += st.work; t.doors += st.v.doors; t.face += st.v.face; t.got += st.got; t.post += st.post; t.call += st.han.call; t.doorH += st.h.door; t.pts += st.pts;
      if (st.sub) t.subs++; if (st.has && !st.off && d < S.today) t.need++;
      if (achieved(targetsOf(st))) t.ok++;
    }
    let state = '';
    if (single) {
      const st = statOf(days[from], from === S.today, u);
      state = st.running ? `${KIND[st.running.k]}中` : st.off ? '休み' : st.sub ? '日報済み' : st.work ? '中断中' : st.plan.length ? '未開始' : '未申告';
    } else state = `日報 ${t.subs}日`;
    return { u, name: nameOf(u), t, state };
  }).sort((a, b) => b.t.pts - a.t.pts);
  const cls = s => /中$/.test(s) && s !== '中断中' ? 'run' : s === '未申告' ? 'bad' : s === '未開始' || s === '中断中' ? 'warn' : '';
  body.append(el('div', { class: 'ss-tw' }, el('table', { class: 'ss-tbl ss-team' },
    el('thead', null, el('tr', null, ['名前', single ? '状態' : '日報', '稼働', '訪問', '対面', '獲得', '配布', '反響電話', '訪問/時', '点'].map(h => el('th', { text: h })))),
    el('tbody', null, rows.map(r => el('tr', null,
      el('th', { text: r.name }), el('td', null, el('span', { class: 'ss-st ' + cls(r.state), text: r.state })),
      el('td', { text: hours1(r.t.work) + 'h' }), el('td', { text: r.t.doors }), el('td', { text: r.t.face }), el('td', { text: r.t.got }),
      el('td', { text: r.t.post.toLocaleString() }), el('td', { text: r.t.call }),
      el('td', { text: r.t.doorH > 600000 ? (r.t.doors / (r.t.doorH / 3600000)).toFixed(1) : '—' }), el('td', null, el('b', { text: r.t.pts.toLocaleString() }))))))));
  body.append(el('div', { class: 'muted', text: '「未申告」は今日まだ予定も休みも申告していない人です。前日までの訪問数は毎晩0時15分に入ります。' }));
  if (C.FB.isAdmin()) body.append(goalEditor());
}
function goalEditor(){
  const g = S.goal; const inputs = {};
  const f = (k, label, step) => { inputs[k] = el('input', { type: 'number', min: 0, step: step || 1, value: g[k], class: 'ss-in ss-num' }); return el('label', { class: 'ss-gf' }, el('span', { text: label }), inputs[k]); };
  return keepOpen('goal', el('details', { class: 'ss-card ss-goal' }, el('summary', { text: 'お題の基準を変える（管理者）' }),
    el('div', { class: 'muted', text: '下の数は「1日＝基準の時間」働いたときの数です。予定の時間が短ければ、お題もその分少なくなります。' }),
    f('std', '基準の時間（時間）', 0.5), f('door', '訪販：訪問数'), f('face', '訪販：対面数'), f('call', '反響対応：電話した数'), f('post', '配布：枚数', 10), f('got', '獲得数'), f('monthGot', '1か月の獲得の目安'),
    el('div', { class: 'btnrow' }, el('button', { class: 'btn primary', onclick: async () => {
      const d = {}; for (const k in inputs) { const v = parseFloat(inputs[k].value); d[k] = isFinite(v) && v >= 0 ? v : GOAL_DEF[k]; }
      try { await C.FB.cfg.set('goal', d); C.toast('お題の基準を保存しました（全員に反映）'); } catch (e) { C.toast('保存できませんでした'); }
    } }, '保存する'))));
}

// ---------- さがす画面の上に出す「今日の業務」 ----------
function homeCard(){
  if (!C || !C.FB.day) return null;
  const st = statOf(S.doc, true);
  const ts = targetsOf(st);
  const card = el('div', { class: 'hcard ss-home', role: 'button', tabindex: 0, onclick: () => C.openMe('today'), onkeydown: e => { if (e.key === 'Enter') C.openMe('today'); } },
    el('h3', null, '今日の業務', el('small', { text: `連続${streak(myDays())}日・${st.pts}点` })), heroBox(st, true));
  if (ts.length && !st.off) card.append(el('div', { class: 'ss-hbars' }, ts.map(t => el('div', { class: 'ss-hb' + (t.val >= t.tgt ? ' done' : '') }, el('span', { text: `${t.label} ${t.val}/${t.tgt}` }), el('div', { class: 'ss-track' }, el('i', { style: `width:${Math.min(100, Math.round(t.val / t.tgt * 100))}%` }))))));
  return card;
}

// 1秒ごとに時計だけ書き換える。日付が変わったら読み直す
setInterval(() => {
  document.querySelectorAll('.ss-clock[data-st]').forEach(e => { e.textContent = clock(Date.now() - +e.dataset.st); });
  if (C && S.today && ymd(Date.now()) !== S.today) { S.draft = null; S.editing = false; watch(); }
}, 1000);
// 1分ごとに時間の合計を書き換える
setInterval(() => { if (C && S.doc && Object.values(S.doc.ses || {}).some(s => !s.en)) rerender(); }, 60000);

window.Seiseki = {
  start(ctx){ C = ctx; if (!C.FB.day) return; watch(); },
  render(tab){ if (tab) S.tab = tab; if (S.tab === 'team') loadTeam(); render(); },
  homeCard
};
})();
