#!/usr/bin/env python3
"""訪問マップ（Claudeの成果物版 template.html）→ Google（Firebase）版 index.html に変換する。"""
import sys, os
SP = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SP, 'app/template.html'), encoding='utf-8').read()
css = open(os.path.join(SP, 'package/dist/leaflet.css'), encoding='utf-8').read()
s = src

def rep(a, b, n=1):
    global s
    c = s.count(a)
    if c != n: sys.exit(f'置換対象の数が違います（{c}件）: {a[:80]!r}')
    s = s.replace(a, b)

# ---------- ページの骨組み ----------
s = ('<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
     '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
     '<meta name="robots" content="noindex,nofollow">\n') + s
rep('/*LEAFLET_CSS*/', css)
rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>',
    '<script type="module" src="fb.js?v=' + __import__('hashlib').md5(open('/home/claude/houmon-map/fb.js','rb').read()).hexdigest()[:8] + '"></script>\n<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>')
# head と body の区切り：最初の </style> のあとで head を閉じる
i = s.index('</style>') + len('</style>')
s = s[:i] + '\n</head>\n<body>' + s[i:]
s = s.rstrip() + '\n</body>\n</html>\n'

# ---------- ログイン画面 ----------
rep('#loading{position:absolute;inset:0;display:grid;place-items:center;background:var(--bg);z-index:3000;color:var(--ink2);font-size:14px}',
    '#loading{position:absolute;inset:0;display:grid;place-items:center;background:var(--bg);z-index:3000;color:var(--ink2);font-size:14px}\n'
    '#gate{position:absolute;inset:0;display:grid;place-items:center;background:var(--bg);z-index:3100;padding:16px}\n'
    '#gate .gbox{max-width:360px;width:100%;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px 20px;text-align:center;display:flex;flex-direction:column;gap:12px}\n'
    '#gate h1{margin:0;font-size:20px}#gate p{margin:0;color:var(--ink2);font-size:13.5px;line-height:1.6}\n'
    '#gate .gbtn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 16px;border-radius:10px;border:1px solid var(--line);background:var(--card);font-size:15px;font-weight:700;color:var(--ink);cursor:pointer}\n'
    '#gate .gbtn:hover{background:var(--soft)}')
rep('  <div id="loading">建物リストを読み込んでいます…</div>',
    '  <div id="loading">建物リストを読み込んでいます…</div>\n'
    '  <div id="gate" hidden><div class="gbox"><h1>訪問マップ</h1><div id="gateMsg"></div></div></div>')

# ---------- 起動：ログイン → 建物リスト（Google から） ----------
rep("""async function boot(){
  const [bj, aj, rj] = await Promise.all([fetch('buildings.json').then(r => r.json()), fetch('areas.json').then(r => r.json()), fetch('rail.json').then(r => r.json())]);
  META = bj; B = bj.buildings; B.forEach(b => byId[b.id] = b);""",
"""function fbReady(){ return window.FB ? Promise.resolve(window.FB) : new Promise(r => window.addEventListener('fb-ready', () => r(window.FB), { once: true })); }
function showGate(kind, email){
  const g = $('#gate'), m = $('#gateMsg'); g.hidden = false; m.textContent = ''; $('#loading').hidden = true;
  if (kind === 'out') {
    m.append(el('p', { text: '会社で許可されたGoogleアカウントでログインしてください。' }),
      el('button', { class: 'gbtn', onclick: async e => { e.target.disabled = true; try { await FB.signIn(); location.reload(); } catch(err){ e.target.disabled = false; toast('ログインできませんでした。もう一度お試しください。'); } } }, 'Googleでログイン'),
      el('a', { href: 'guide.html', style: 'color:var(--accent);font-size:13.5px' }, '使い方を見る'));
  } else if (kind === 'denied') {
    m.append(el('p', null, el('b', { text: email || '' }), ' は、まだこのアプリを使えるように登録されていません。'),
      el('p', { text: '管理者に、このアドレスを登録してもらってください。' }),
      el('button', { class: 'gbtn', onclick: () => FB.signOut() }, '別のアカウントでログインし直す'));
  } else {
    m.append(el('p', { text: kind }), el('button', { class: 'gbtn', onclick: () => location.reload() }, '開き直す'));
  }
}
async function boot(){
  await fbReady();
  const st = await FB.whenSignedIn();
  if (st.state !== 'in') { showGate(st.state, st.email); return; }
  updateStrip();
  const [mj, aj, rj] = await Promise.all([
    FB.loadMaster((n, all) => { $('#loading').textContent = `建物リストを読み込んでいます…（${n}/${all}）`; }),
    fetch('areas.json').then(r => r.json()), fetch('rail.json').then(r => r.json())]);
  const bj = Object.assign({ month: '', source: '', history: [], baseline: true }, mj.meta || {}, { buildings: mj.buildings });
  if (!mj.meta) {
    if (FB.isAdmin()) { showGate('建物リストがまだ入っていません。取り込みファイルを選んでください。'); $('#gateMsg').append(importSection()); }
    else showGate('建物リストがまだ入っていません。管理者に連絡してください。');
    return;
  }
  META = bj; B = bj.buildings; B.forEach(b => byId[b.id] = b);""")
rep("""boot().catch(e => { $('#loading').textContent = '建物リストを読み込めませんでした。ページを開き直してください。'; });""",
    """boot().catch(e => { console.error(e); if (e && e.code === 'permission_denied') showGate('このアカウントでは建物リストを読めませんでした。管理者に連絡してください。'); else $('#loading').textContent = '建物リストを読み込めませんでした。ページを開き直してください。'; });""")

# 地図の最初の表示範囲：業務委託は担当エリアに合わせる
rep("""  map.fitBounds([[35.05, 138.8], [36.3, 140.5]]);""",
    """  { const bb = B.length && !FB.isStaff() ? L.latLngBounds(B.map(b => [b.la, b.lo])) : null; if (bb && bb.isValid()) map.fitBounds(bb.pad(0.1)); else map.fitBounds([[35.05, 138.8], [36.3, 140.5]]); }""")

rep("""async function connect(){
  const banner = $('#banner');
  if (!window.claude || !window.claude.use) { banner.hidden = false; banner.textContent = '保存機能につながっていません。地図とリストの閲覧のみできます。'; return; }
  const [d, u] = await Promise.all([claude.use('db'), claude.use('user')]);
  db = d; user = u;""",
"""async function connect(){
  const banner = $('#banner');
  db = FB.db; user = FB.user;""")
rep("""  if (!db) { banner.hidden = false; banner.textContent = '保存機能につながっていません。地図とリストの閲覧のみできます。'; if (openId) renderSheetDynamic(); return; }
  if (canWrite === false) { banner.hidden = false; banner.textContent = '閲覧のみの権限で開いています。結果を登録するには、共有設定で「参加者」以上にしてもらってください。'; }
  watchPerm();""", """  PERM = {}; updateVacUI();""")
rep("""  db.doc('meta/days').onSnapshot(s => { DOCN.days = s.exists ? Object.keys(s.data() || {}).length : 0; usageBanner(); if (panelKind === 'set') renderSet(); }, () => {});\n""", '')

# ---------- 日付の控え（meta/days）はもう使わない ----------
rep("""      try { await upsert(db.doc('meta/days'), { [ymd(t)]: 1 }); } catch(e){}\n""", '')
rep("""    try { await upsert(db.doc('meta/days'), { [ymd(t)]: 1 }); } catch(e){}\n""", '')

# ---------- 活動記録：act/<日付>_<人> ----------
rep("""      await upsert(db.doc('act/' + ymd(t)), { [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) });""",
    """      await upsert(FB.act.ref(ymd(t)), { u: me.id, d: ymd(t), [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) });""")
rep("""    try { await upsert(db.doc('act/' + ymd(t)), { [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) }); } catch(e){}""",
    """    try { await upsert(FB.act.ref(ymd(t)), { u: me.id, d: ymd(t), [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) }); } catch(e){}""")
rep("""      await db.doc('act/' + ymd(aw.t)).update({ [k]: { x: 1 } });""",
    """      await FB.act.ref(ymd(aw.t)).update({ [k]: Object.assign({}, aw, { x: 1 }) });""")
rep("""    try { await db.doc('act/' + ymd(x.t)).update({ [k]: { x: 1 } }); } catch(e){}""",
    """    try { await FB.act.ref(ymd(x.t)).update({ [k]: Object.assign({}, x, { x: 1 }) }); } catch(e){}""")
rep("""  todayUnsub = db.doc('act/' + d).onSnapshot(s => {
    const by = {}; const data = s.exists ? (s.data() || {}) : {};
    for (const k in data) { const v = data[k]; if (v && v.r === 'away' && !v.x && v.bid) (by[v.bid] = by[v.bid] || {})[k] = v; }""",
"""  todayUnsub = FB.act.watchDay(d, docs => {
    const by = {};
    for (const data of docs) for (const k in data) { const v = data[k]; if (v && v.r === 'away' && !v.x && v.bid) (by[v.bid] = by[v.bid] || {})[k] = v; }""")
rep("""    if (openId) renderSheetDynamic();
  }, () => {});
}
function todayAway""", """    if (openId) renderSheetDynamic();
  });
}
function todayAway""")
rep("""    actUnsub = db.doc('act/' + days[0]).onSnapshot(s => { actEntries = take([s.exists ? s.data() : null]); resolveNames(actEntries.map(x => x.u)).then(renderAct); renderAct(); }, () => renderAct());""",
    """    actUnsub = FB.act.watchDay(days[0], docs => { actEntries = take(docs); resolveNames(actEntries.map(x => x.u)).then(renderAct); renderAct(); });""")
rep("""    const snaps = await Promise.all(days.map(d => db.doc('act/' + d).get().catch(() => null)));
    actEntries = take(snaps.map(s => s && s.exists ? s.data() : null));""",
    """    const per = await Promise.all(days.map(d => FB.act.getDay(d)));
    actEntries = take(per.flat());""")

# ---------- 特記事項：市区町村ごとに Google から ----------
rep("""  const p = b.cc.slice(0, 2);
  try {
    if (!notesCache[p]) notesCache[p] = fetch('notes_' + p + '.json').then(r => r.json());
    const all = await notesCache[p];""",
"""  try {
    const all = await FB.loadNotes(b.cc);""")

# ---------- 未入居リスト：管理者が許可した人（users の vac） ----------
rep("""const canVac = () => isOwner || !!(me.id && PERM[me.id]);""",
    """const canVac = () => isOwner || !!(window.FB && FB.me() && FB.me().vac);""")

# ---------- 設定画面：保存の残り → ログイン中の人 / 使える人の管理 ----------
rep("""  if (db) body.append(usageBox());""", """  if (db) body.append(accountBox());""")
rep("""  if (isOwner && db) { const holder = el('div'); body.append(holder); permSection().then(s => holder.append(s)); }""",
    """  if (isOwner && db) { const holder = el('div'); body.append(holder); usersSection().then(s => { holder.append(s); holder.append(importSection()); }); }""")
rep("""function watchPerm(){""", r"""function accountBox(){
  const m = FB.me() || {};
  const roleL = { admin: '管理者', staff: '社員', contractor: '業務委託' }[m.role] || '';
  return el('section', { class: 'sec' }, el('h3', { text: 'ログイン中' }),
    el('div', { class: 'ctl', style: 'justify-content:space-between' }, el('span', null, el('b', { text: m.name || '' }), `　${m.email || ''}　${roleL}`),
      el('span', { style: 'display:inline-flex;gap:6px' }, el('a', { class: 'btn', href: 'guide.html', target: '_blank', rel: 'noopener', style: 'text-decoration:none' }, '使い方'), el('button', { class: 'btn', onclick: () => FB.signOut() }, 'ログアウト'))),
    m.role === 'contractor' ? el('div', { class: 'muted', text: '担当エリア：' + (m.areas || []).map(cc => (CITY[cc] && CITY[cc].short) || cc).join('、') }) : null);
}
const ROLE_L = { admin: '管理者', staff: '社員', contractor: '業務委託' };
// 招待メール：Gmail の作成画面を、宛先・件名・本文を入れた状態で開く（送信は自分で押す）
function inviteMail(u){
  const url = location.origin + location.pathname;
  const body = `${u.name ? u.name + 'さん\n\n' : ''}訪問マップを使えるように登録しました。\n\n下のアドレスを開いて「Googleでログイン」を押し、このメールが届いたアドレス（${u.email}）でログインしてください。\n${url}\n\nスマホは、開いたあと「ホーム画面に追加」しておくと、アプリのように使えて便利です。\n\n使い方（3分で読めます）：\n${url}guide.html`;
  const g = 'https://mail.google.com/mail/?view=cm&fs=1&to=' + encodeURIComponent(u.email) + '&su=' + encodeURIComponent('訪問マップの招待') + '&body=' + encodeURIComponent(body);
  window.open(g, '_blank', 'noopener');
}
async function usersSection(){
  const sec = el('section', { class: 'sec' }, el('h3', { text: 'アプリを使える人（管理者だけが変更できます）' }));
  const list = el('div'); sec.append(list);
  const cityOpts = Object.keys(CITY).filter(cc => CITY[cc].ids && CITY[cc].ids.length).sort().map(cc => [cc, CITY[cc].name || cc]);
  const draw = async () => {
    list.textContent = '';
    let us = [];
    try { us = await FB.admin.list(); } catch(e){ list.append(el('p', { class: 'muted', text: '一覧を読めませんでした。' })); return; }
    us.sort((a, c) => (a.role || '').localeCompare(c.role || '') || a.email.localeCompare(c.email));
    if (!us.length) list.append(el('p', { class: 'muted', text: 'まだ誰も登録していません（あなたは最初の管理者として入れます）。' }));
    us.forEach(u => list.append(el('div', { style: 'padding:8px 0;border-bottom:1px solid var(--soft);display:flex;flex-direction:column;gap:4px' },
      el('div', { class: 'ctl', style: 'justify-content:space-between' },
        el('span', null, el('b', { text: u.name || '（名前なし）' }), `　${u.email}`),
        el('span', { class: 'muted', text: (ROLE_L[u.role] || '社員') + (u.vac ? '・未入居リスト可' : '') + (u.active === false ? '・停止中' : '') })),
      u.role === 'contractor' ? el('div', { class: 'muted', text: '担当エリア：' + ((u.areas || []).map(cc => (CITY[cc] && CITY[cc].short) || cc).join('、') || 'なし') }) : null,
      el('div', { class: 'ctl', style: 'gap:6px' },
        el('button', { class: 'btn', onclick: () => edit(u) }, '変更'),
        el('button', { class: 'btn', onclick: () => inviteMail(u) }, '招待メール'),
        el('button', { class: 'btn', onclick: async e => { if (e.target.dataset.arm !== '1') { e.target.dataset.arm = '1'; e.target.textContent = 'もう一度押すと外します'; return; } try { await FB.admin.remove(u.email); toast(`${u.email} を外しました。記録は残ります`); draw(); } catch(err){ toast('変更できませんでした'); } } }, '外す')))));
    list.append(el('button', { class: 'btn primary', style: 'margin-top:8px', onclick: () => edit(null) }, '＋ 人を追加'));
  };
  const edit = (u) => {
    const f = { email: u ? u.email : '', name: u ? u.name || '' : '', role: u ? u.role || 'staff' : 'staff', areas: u ? (u.areas || []).slice() : [], vac: u ? !!u.vac : false };
    const box = el('div', { class: 'note-box', style: 'display:flex;flex-direction:column;gap:8px;margin-top:8px' });
    const inp = (label, key, type, ph) => el('label', { class: 'field' }, label, el('input', { type, value: f[key], placeholder: ph || '', disabled: key === 'email' && !!u, style: 'padding:7px 9px;border:1px solid var(--line);border-radius:7px;background:var(--card)', oninput: e => f[key] = e.target.value }));
    const areaBox = el('div');
    // 担当エリア：都県ごとにまとめて選べる。検索・都県まるごと選択・まとめて外す
    const prefOf = cc => (CITY[cc] && CITY[cc].name || '').split(' ')[0] || 'その他';
    const cntOf = cc => (CITY[cc] && CITY[cc].ids ? CITY[cc].ids.length : 0);
    const openPref = new Set();
    let areaQ = '';
    const drawAreas = () => {
      areaBox.textContent = '';
      if (f.role !== 'contractor') return;
      const sel = new Set(f.areas);
      const total = f.areas.reduce((a, cc) => a + cntOf(cc), 0);
      const summary = el('div', { class: 'apick-sum' },
        el('div', null, el('b', { text: `${f.areas.length}市区町村` }), `・約${total.toLocaleString()}棟を選択中`),
        f.areas.length ? el('button', { class: 'linkbtn', onclick: () => { f.areas = []; drawAreas(); } }, 'すべて外す') : null);
      const chips = el('div', { class: 'apick-chips' }, f.areas.map(cc => el('button', { class: 'apick-chip', title: '押すと外します', onclick: () => { f.areas = f.areas.filter(x => x !== cc); drawAreas(); } }, ((CITY[cc] && CITY[cc].short) || cc) + ' ×')));
      const q = el('input', { type: 'search', placeholder: '市区町村名でさがす（例：世田谷、川崎）', value: areaQ, style: 'width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card)' });
      const list = el('div', { class: 'apick-list' });
      const drawList = () => {
        list.textContent = '';
        const qq = nzq(areaQ);
        const groups = {};
        for (const [cc, n] of cityOpts) { if (qq && !nzq(n).includes(qq)) continue; (groups[prefOf(cc)] = groups[prefOf(cc)] || []).push(cc); }
        const prefs = Object.keys(groups);
        if (!prefs.length) list.append(el('p', { class: 'muted', text: '見つかりません。' }));
        for (const p of prefs) {
          const ccs = groups[p]; const on = ccs.filter(cc => sel.has(cc)).length; const all = on === ccs.length;
          const det = el('details', { class: 'apick-pref', open: !!qq || openPref.has(p) });
          det.addEventListener('toggle', () => { if (det.open) openPref.add(p); else openPref.delete(p); });
          det.append(el('summary', null, el('span', null, el('b', { text: p }), el('span', { class: 'muted', text: `　${on}/${ccs.length}` })),
            el('button', { class: 'btn', onclick: e => { e.preventDefault(); if (all) f.areas = f.areas.filter(x => !ccs.includes(x)); else ccs.forEach(cc => { if (!sel.has(cc)) f.areas.push(cc); }); openPref.add(p); drawAreas(); } }, all ? (qq ? '出ているものを外す' : 'この都県を外す') : (qq ? '出ているものを全部選ぶ' : 'この都県を全部選ぶ'))),
            el('div', { class: 'apick-grid' }, ccs.map(cc => el('label', { class: 'apick-c' + (sel.has(cc) ? ' on' : '') },
              el('input', { type: 'checkbox', checked: sel.has(cc), onchange: e => { if (e.target.checked) { if (!f.areas.includes(cc)) f.areas.push(cc); } else f.areas = f.areas.filter(x => x !== cc); openPref.add(p); drawAreas(); } }),
              el('span', { text: (CITY[cc] && CITY[cc].short) || cc }), el('small', { text: cntOf(cc) + '棟' })))));
          list.append(det);
        }
      };
      q.addEventListener('input', () => { areaQ = q.value; drawList(); });
      areaBox.append(el('div', { class: 'flab', text: '担当エリア（ここで選んだ市区町村の建物だけ見られます）' }), summary, chips, q, list);
      drawList();
    };
    const roleSel = el('select', { style: 'padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:var(--card);max-width:220px', onchange: e => { f.role = e.target.value; drawAreas(); } },
      ['staff', 'contractor', 'admin'].map(r => el('option', { value: r, selected: r === f.role }, ROLE_L[r])));
    box.append(el('b', { text: u ? '使える人を変更' : '使える人を追加' }),
      inp('Googleアカウント（Gmailなど）のアドレス', 'email', 'email', '例 tanaka@gmail.com'), inp('名前（アプリに表示されます）', 'name', 'text', '例 田中'),
      el('label', { class: 'field' }, '立場', roleSel), areaBox,
      el('label', { class: 'chk' }, el('input', { type: 'checkbox', checked: f.vac, onchange: e => f.vac = e.target.checked }), '未入居リストを使ってよい'),
      el('div', { class: 'ctl', style: 'gap:6px' },
        el('button', { class: 'btn primary', onclick: async () => {
          const email = f.email.trim().toLowerCase();
          if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { toast('アドレスの形が正しくありません'); return; }
          if (f.role === 'contractor' && !f.areas.length) { toast('業務委託の人には担当エリアを1つ以上入れてください'); return; }
          try { await FB.admin.save(email, { name: f.name.trim(), role: f.role, areas: f.role === 'contractor' ? f.areas : [], vac: f.vac, active: true, by: me.id, at: Date.now() }); toast('保存しました。招待メールの画面を開きます'); box.remove(); draw(); if (!u) inviteMail({ email, name: f.name.trim() }); }
          catch(e){ toast('保存できませんでした'); }
        } }, '保存'),
        el('button', { class: 'btn', onclick: () => box.remove() }, 'やめる')));
    drawAreas();
    list.append(box); box.scrollIntoView({ block: 'nearest' });
  };
  await draw();
  sec.append(el('div', { class: 'muted', style: 'margin-top:6px', text: '「外す」とその日から入れなくなります。その人が付けた記録は会社のデータとして残ります。' }));
  return sec;
}
function importSection(){
  const st = el('div', { class: 'muted' });
  const inp = el('input', { type: 'file', accept: '.gz,.json', style: 'max-width:100%' });
  inp.addEventListener('change', async () => {
    const f = inp.files && inp.files[0]; if (!f) return;
    inp.disabled = true; st.textContent = '取り込んでいます…';
    try { const n = await FB.admin.putFile(f, (a, b) => { st.textContent = `取り込んでいます…（${a}/${b}）`; }); st.textContent = `${n}件を取り込みました。ページを開き直すと新しい建物リストになります。`; toast('取り込みが終わりました'); }
    catch(e){ st.textContent = '取り込めませんでした：' + (e && e.message || ''); }
    inp.disabled = false; inp.value = '';
  });
  return el('section', { class: 'sec' }, el('h3', { text: '建物リストの取り込み（管理者）' }),
    el('div', { class: 'muted', text: '毎月、Claudeが作った取り込みファイル（houmon_import_….json.gz）をここで選ぶと、建物リストが新しくなります。' }), inp, st);
}
function watchPerm(){""")
rep("""function usageBanner(){
  if (DOCN.days == null) return;""", """function usageBanner(){
  return;""")

# ---------- 文言：Claude の共有設定の案内を外す ----------
rep("""    else if (!db) sec.append(el('p', { class: 'muted', text: '保存機能につながっていないため、この画面では登録できません（見るだけ）。' }));
    else if (canWrite === false) sec.append(el('p', { class: 'muted', text: '閲覧のみの権限です。登録するには共有設定で「参加者」以上にしてもらってください。' }));""",
    """    else if (!db) sec.append(el('p', { class: 'muted', text: '保存機能につながっていないため、この画面では登録できません（見るだけ）。' }));""")
rep("""  if (e && e.code === 'invalid_argument' && canWrite !== true) { canWrite = false; renderSheetDynamic(); return new Error('この画面の権限では登録できません。共有設定で「参加者」以上にしてもらってください。'); }""",
    """  if (e && e.code === 'permission_denied') return new Error('この建物は、あなたのアカウントでは登録できません。管理者に確認してください。');""")
rep("""    if (!notesCache[p])""", """    if (!notesCache[p])""", 0)


# ---------- スマホの画面（幅760px以下） ----------
MOBILE_CSS = """
@media (max-width:760px){
  /* 下に固定したメニュー（親指で押せる位置・文字つき） */
  #app{box-sizing:border-box;padding-bottom:calc(58px + env(safe-area-inset-bottom,0px))}
  .tabs{position:fixed;left:0;right:0;bottom:0;z-index:1300;margin:0;gap:0;background:var(--card);border-top:1px solid var(--line);padding:4px 2px calc(4px + env(safe-area-inset-bottom,0px));box-shadow:0 -4px 14px rgba(20,40,45,.08)}
  .tb{flex:1 1 0;min-width:0;flex-direction:column;gap:2px;padding:6px 0 4px;border:0;border-radius:10px;background:none;font-size:10.5px;line-height:1.1;position:relative;color:var(--ink2)}
  .tb svg{width:21px;height:21px}
  .tb .lb{display:block!important;white-space:nowrap}
  .tb[aria-pressed="true"]{background:var(--accent-soft);color:var(--accent)}
  .tb .cnt{position:absolute;top:2px;left:calc(50% + 6px);font-size:10px;padding:0 5px}
  .tb[aria-pressed="true"] .cnt{background:var(--accent);color:var(--accent-ink)}
  /* 上の帯は細く。さがす画面では消して、広く使う */
  .top{padding:6px 10px}
  .brand b{font-size:15px}
  .homeMode .top{padding:0;border:0;min-height:0}
  .homeMode .brand{display:none}
  /* 建物の画面は全面に */
  .sheet{top:0;max-height:none;border-radius:0;border-top:0}
  .panel{width:100%}
  /* 文字入力で画面が勝手に拡大しないように（iPhone） */
  input,select,textarea{font-size:16px!important}
  select{padding:8px 10px!important;border-radius:8px}
  /* 押しやすい大きさ */
  .chk{min-height:40px;display:inline-flex;align-items:center;gap:8px}
  .chk input{width:20px;height:20px}
  .btn{min-height:40px}
  .x{width:40px;height:40px}
  /* 部屋の登録：「登録する」ボタンを常に下に見せる */
  .rform{max-height:92%}
  .rform .btn.primary{position:sticky;bottom:0;z-index:2;box-shadow:0 -6px 12px var(--card)}
  .res button{min-height:56px;font-size:15px}
  /* さがす画面 */
  .home-in{padding-top:10px}
  .hstats{gap:6px}
  .hstats > div{padding:8px 4px}
  .hstats span{font-size:11px}
  .hfilt{display:none}
  .home.filtOpen .hfilt{display:flex}
  .hfiltBtn{display:flex!important}
  .lrow{min-height:56px}
  .gmap,.addr{width:42px;height:42px}
  .legend{bottom:8px}
}
.hfiltBtn{display:none;width:100%;justify-content:space-between;align-items:center;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);font-size:14px;margin:4px 0}
.hfiltBtn b{color:var(--accent)}
"""
i = s.index('</style>')
s = s[:i] + MOBILE_CSS + s[i:]

# 町・並び順などの「しぼりこみ」を、スマホでは1つのボタンの中にしまう
rep("""  body.append(el('div', { class: 'ctl' }, el('label', { for: 'homeSort', text: '並び順' }), sel,""",
    """  { const nOn = (homeSort !== 'addr' ? 1 : 0) + (homeTy ? 1 : 0) + (homeNf ? 1 : 0) + (homeOnlyNew ? 1 : 0) + (homeHideNG ? 1 : 0);
    body.append(el('button', { class: 'hfiltBtn', onclick: () => { $('#home').classList.toggle('filtOpen'); } }, el('span', null, '並び順・しぼりこみ', nOn ? el('b', { text: `（${nOn}つ使用中）` }) : null), el('span', { class: 'muted', text: '開く／閉じる' }))); }
  body.append(el('div', { class: 'ctl hfilt' }, el('label', { for: 'homeSort', text: '並び順' }), sel,""")

# スマホでは検索欄の例を短く
rep("""function fbReady(){""", """if (matchMedia('(max-width:760px)').matches) { const h = document.getElementById('hq'); if (h) h.placeholder = '市区町村・町名・建物名でさがす'; const q = document.getElementById('q'); if (q) q.placeholder = '駅・町名・建物名でさがす'; }
function fbReady(){""")


# ---------- 自社の見た目（AImost のロゴと色） ----------
rep('<meta name="robots" content="noindex,nofollow">\n',
    '<meta name="robots" content="noindex,nofollow">\n'
    '<meta name="theme-color" content="#1B1FA8">\n'
    '<meta name="apple-mobile-web-app-title" content="訪問マップ">\n'
    '<link rel="icon" type="image/png" href="img/favicon.png">\n'
    '<link rel="apple-touch-icon" href="img/apple-touch-icon.png">\n'
    '<link rel="manifest" href="manifest.webmanifest">\n')
BRAND_CSS = """
/* AImost の色：ロゴの紺（#1B1FA8）と空色（#5CC2F2）。状態の色（緑・黄・赤など）は意味を守るため変えない */
:root{
  --ink:#1b2233; --ink2:#4a5468; --ink3:#7a8396;
  --bg:#f4f5f9; --card:#ffffff; --line:#d8dce8; --soft:#eceff6;
  --accent:#1f2bab; --accent-ink:#ffffff; --accent-soft:#e6e9fb;
  --brand-navy:#1B1FA8; --brand-mid:#2E51C0; --brand-sky:#5CC2F2;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --ink:#e8ebf4; --ink2:#b6bdcf; --ink3:#8c94a8;
  --bg:#12151f; --card:#1b2030; --line:#323a52; --soft:#242b3e;
  --accent:#9aa8ff; --accent-ink:#10132b; --accent-soft:#262d57;
}}
:root[data-theme="dark"]{
  --ink:#e8ebf4; --ink2:#b6bdcf; --ink3:#8c94a8;
  --bg:#12151f; --card:#1b2030; --line:#323a52; --soft:#242b3e;
  --accent:#9aa8ff; --accent-ink:#10132b; --accent-soft:#262d57;
}
/* 上の帯：ロゴの色の細い線 */
.top{border-top:3px solid transparent;border-image:linear-gradient(90deg,var(--brand-navy),var(--brand-mid) 45%,var(--brand-sky)) 1}
.brand{align-items:center}
.brand img{width:26px;height:22px;object-fit:contain;flex:none}
.brand b{color:var(--ink)}
.brand .co{font-size:11px;color:var(--ink3);font-weight:700;letter-spacing:.06em}
/* さがす画面の見出し */
.hbrand{display:flex;align-items:center;gap:10px;margin:2px 2px 12px}
.hbrand img{width:40px;height:34px;object-fit:contain}
.hbrand .t{display:flex;flex-direction:column;line-height:1.25}
.hbrand b{font-size:19px;letter-spacing:.04em}
.hbrand small{font-size:11.5px;color:var(--ink3);font-weight:700;letter-spacing:.08em}
.hbrand .who{margin-left:auto;font-size:12px;color:var(--ink2);text-align:right;line-height:1.3}
/* ログイン画面 */
#gate .glogo{width:132px;height:auto;margin:0 auto 4px;display:block}
#gate .gbtn{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
#gate .gbtn:hover{background:var(--brand-mid)}
#gate .gbox{border-top:4px solid var(--brand-navy)}
.apick-sum{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:14px}
.apick-chips{display:flex;flex-wrap:wrap;gap:6px;max-height:120px;overflow:auto}
.apick-chip{border:1px solid var(--accent);background:var(--accent-soft);color:var(--accent);border-radius:16px;padding:4px 10px;font-size:13px}
.apick-list{display:flex;flex-direction:column;gap:6px;max-height:55vh;overflow:auto;margin-top:4px}
.apick-pref{border:1px solid var(--line);border-radius:10px;background:var(--card)}
.apick-pref summary{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 10px;cursor:pointer;list-style:none}
.apick-pref summary::-webkit-details-marker{display:none}
.apick-pref summary .btn{font-size:12.5px;padding:5px 10px;min-height:34px}
.apick-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:6px;padding:0 10px 10px}
.apick-c{display:flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:8px;padding:8px;min-height:44px;cursor:pointer}
.apick-c.on{border-color:var(--accent);background:var(--accent-soft)}
.apick-c input{width:18px;height:18px;flex:none}
.apick-c span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.apick-c small{color:var(--ink3);font-size:11px}
#gate .gbox > div{display:flex;flex-direction:column;align-items:center;gap:10px}
#gate .gbtn{min-width:220px;min-height:48px}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]) .hbrand img, :root:not([data-theme="light"]) .brand img, :root:not([data-theme="light"]) #gate .glogo{background:#fff;border-radius:8px;padding:3px} }
"""
i = s.index('</style>')
s = s[:i] + BRAND_CSS + s[i:]
rep('<div class="brand"><b>訪問マップ</b><small id="srcInfo"></small></div>',
    '<div class="brand"><img src="img/mark.png" alt=""><b>訪問マップ</b><span class="co">AImost</span><small id="srcInfo"></small></div>')
rep('<section class="home" id="home"><div class="home-in">',
    '<section class="home" id="home"><div class="home-in">\n      <div class="hbrand"><img src="img/mark.png" alt="AImost"><div class="t"><b>訪問マップ</b><small>AImost</small></div><div class="who" id="hWho"></div></div>')
rep('<div id="gate" hidden><div class="gbox"><h1>訪問マップ</h1><div id="gateMsg"></div></div></div>',
    '<div id="gate" hidden><div class="gbox"><img class="glogo" src="img/logo.png" alt="AImost"><h1>訪問マップ</h1><div id="gateMsg"></div></div></div>')
# ログイン中の人の名前を、さがす画面の右上に
rep("""  META = bj; B = bj.buildings; B.forEach(b => byId[b.id] = b);""",
    """  META = bj; B = bj.buildings; B.forEach(b => byId[b.id] = b);
  { const m = FB.me() || {}; const w = document.getElementById('hWho'); if (w) w.textContent = (m.name || '') + ({ admin: '（管理者）', contractor: '（業務委託）' }[m.role] || ''); }""")


# ---------- 獲得したら：花火・帯・活動記録の豪華さ（すぐ出す） ----------
CELEB_CSS = """
/* 今日の獲得の帯：上の帯のすぐ下に横長で出す（スマホでは画面のいちばん上） */
#gotBand{position:fixed;left:0;right:0;top:var(--bandTop,0px);z-index:4000;height:58px;display:flex;align-items:center;gap:14px;padding:0 16px;color:#fff;cursor:pointer;overflow:hidden;
  background:linear-gradient(100deg,#1B1FA8 0%,#2a3db5 100%);box-shadow:inset 0 -4px 0 #5CC2F2,0 8px 24px rgba(27,31,168,.35);
  transform:translateY(-110%);transition:transform .32s cubic-bezier(.2,1.3,.4,1)}
#gotBand.show{transform:translateY(0)}
#gotBand{pointer-events:none}
@media (max-width:760px){
  /* スマホ：下のメニューと「本日の獲得」の帯のすぐ上に出す（建物の名前や閉じるボタンを隠さない） */
  #gotBand{top:auto;bottom:calc(58px + 32px + env(safe-area-inset-bottom,0px));height:54px;transform:translateY(130%);box-shadow:inset 0 -4px 0 #5CC2F2,0 -6px 20px rgba(27,31,168,.3)}
  #gotBand.kami{box-shadow:inset 0 -4px 0 #ffd54a,0 -6px 20px rgba(27,31,168,.3)}
  #gotBand.show{transform:translateY(0)}
}
#gotBand .lab{font-size:12px;letter-spacing:.12em;font-weight:700;opacity:.92;white-space:nowrap}
#gotBand .num{font-size:34px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1;white-space:nowrap;text-shadow:0 2px 8px rgba(0,0,0,.25)}
#gotBand .num small{font-size:15px;margin-left:2px}
#gotBand .msg{margin-left:auto;font-size:24px;font-weight:700;letter-spacing:.05em;white-space:nowrap;text-shadow:0 2px 8px rgba(0,0,0,.25)}
#gotBand.kami .msg{font-size:30px;color:#ffd54a}
#gotBand.kami{background:linear-gradient(100deg,#14178a 0%,#2a3db5 100%);box-shadow:inset 0 -4px 0 #ffd54a,0 8px 24px rgba(27,31,168,.35)}
#gotBand.kami .num{color:#ffd54a}
#gotBand .shine{position:absolute;inset:0;background:linear-gradient(100deg,transparent 40%,rgba(255,255,255,.22) 50%,transparent 60%);transform:translateX(-100%);pointer-events:none}
#gotBand.show .shine{animation:gotShine 1s .2s ease-out}
@keyframes gotShine{to{transform:translateX(100%)}}
#fw{position:fixed;inset:0;z-index:3900;pointer-events:none}
/* 活動記録の「獲得」：件数で豪華に（1件・2件・3件以上） */
.kpi.g1{background:var(--accent-soft);box-shadow:inset 0 0 0 2px #5CC2F2}
.kpi.g1 b{color:var(--accent)}
.kpi.g2{background:linear-gradient(135deg,#1B1FA8,#2a3db5);color:#fff;box-shadow:inset 0 -3px 0 #5CC2F2,0 4px 14px rgba(27,31,168,.35)}
.kpi.g2 b,.kpi.g2 span{color:#fff}
.kpi.g3{position:relative;overflow:hidden;background:linear-gradient(135deg,#14178a,#2a3db5);color:#fff;box-shadow:0 0 0 2px #ffd54a,0 6px 18px rgba(201,154,24,.45);animation:gotGlow 2.4s ease-in-out infinite}
.kpi.g3 b{color:#ffd54a;font-size:24px}
.kpi.g3 span{color:#fff}
.kpi.g3 > *{position:relative;z-index:1}
.kpi.g3::after{content:"";position:absolute;inset:0;z-index:0;background:linear-gradient(100deg,transparent 40%,rgba(255,255,255,.18) 50%,transparent 60%);transform:translateX(-100%);animation:gotShine 2.4s ease-in-out infinite}
.kpi .tag{display:block;font-size:10.5px;font-weight:700;letter-spacing:.08em;margin-top:1px}
.kpi.g1 .tag{color:var(--accent)}
.kpi.g2 .tag{color:#fff}
.kpi.g3 .tag{color:#ffd54a}
@keyframes gotGlow{50%{box-shadow:0 0 0 2px #ffd54a,0 6px 26px rgba(255,213,74,.7)}}
@media (prefers-reduced-motion:reduce){#gotBand{transition:none}#gotBand .shine,.kpi.g3,.kpi.g3::after{animation:none}}
"""
i = s.index('</style>')
s = s[:i] + CELEB_CSS + s[i:]

# 今日の自分の獲得を数える（その日の活動記録から。取り消したものは除く）
rep("""  todayUnsub = FB.act.watchDay(d, docs => {
    const by = {};
    for (const data of docs) for (const k in data) { const v = data[k]; if (v && v.r === 'away' && !v.x && v.bid) (by[v.bid] = by[v.bid] || {})[k] = v; }""",
"""  todayUnsub = FB.act.watchDay(d, docs => {
    const by = {}; const got = new Set(), gone = new Set(); let doors = 0;
    for (const data of docs) for (const k in data) { const v = data[k]; if (v && v.r === 'away' && !v.x && v.bid) (by[v.bid] = by[v.bid] || {})[k] = v;
      if (v && v.r === 'got' && v.u === me.id) (v.x ? gone : got).add(k);
      if (v && v.r && v.u === me.id && !v.x) doors++; }
    TODAY.myDoors = doors;
    TODAY.got = got; TODAY.gotGone = gone;""")
rep("""    try { await upsert(FB.act.ref(ymd(t)), { u: me.id, d: ymd(t), [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) }); } catch(e){}""",
    """    try { await upsert(FB.act.ref(ymd(t)), { u: me.id, d: ymd(t), [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) }); } catch(e){}
    if (f.r === 'got') { TODAY.gotLocal = TODAY.gotLocal || new Set(); TODAY.gotLocal.add(k); }""")
rep("""function todayAway(bid){""", """function myGotToday(){
  const s = new Set([...(TODAY.got || []), ...(TODAY.gotLocal || [])]);
  for (const k of (TODAY.gotGone || [])) s.delete(k);
  return s.size + (TODAY.pending || 0);
}
const GOT_MSG = n => n <= 1 ? 'もう1件!!' : n === 2 ? '神!!' : '伝説!!';
const reduceMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
// 花火（軽い描画。0.1秒以内に始まる）
function fireworks(big){
  if (reduceMotion()) return;
  let cv = document.getElementById('fw'); if (cv) cv.remove();
  cv = document.createElement('canvas'); cv.id = 'fw'; document.body.append(cv);
  const dpr = Math.min(2, window.devicePixelRatio || 1), W = innerWidth, H = innerHeight;
  cv.width = W * dpr; cv.height = H * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr);
  const cols = ['#ffd54a', '#ffffff', '#5CC2F2', '#ff7aa2', '#8ef0b0', '#9aa8ff', '#ffb04a'];
  const parts = []; const shells = big ? 5 : 3;
  for (let s = 0; s < shells; s++) {
    const x = W * (0.2 + 0.6 * Math.random()), y = H * (0.18 + 0.3 * Math.random()), c = cols[(s * 2 + (Math.random() * 3 | 0)) % cols.length], n = 46, delay = s * (big ? 160 : 210);
    for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2 + Math.random() * 0.2, v = 2.2 + Math.random() * 2.6;
      parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, c: Math.random() < 0.25 ? '#ffffff' : c, t0: delay, life: 900 + Math.random() * 500 }); }
  }
  const start = performance.now();
  const tick = now => {
    const t = now - start; g.globalCompositeOperation = 'destination-out'; g.globalAlpha = 1; g.fillStyle = 'rgba(0,0,0,0.3)'; g.fillRect(0, 0, W, H); g.globalCompositeOperation = 'lighter'; let alive = false;
    for (const p of parts) { const lt = t - p.t0; if (lt < 0) { alive = true; continue; } if (lt > p.life) continue; alive = true;
      const k = lt / 16; const x = p.x + p.vx * k * 2.2, y = p.y + p.vy * k * 2.2 + 0.0009 * lt * lt;
      g.globalAlpha = 1 - lt / p.life; g.fillStyle = p.c; g.beginPath(); g.arc(x, y, 2.8, 0, Math.PI * 2); g.fill(); }
    if (alive && t < 3000) requestAnimationFrame(tick); else cv.remove();
  };
  requestAnimationFrame(tick);
}
// 今日の獲得の帯
function gotBand(n){
  if (!n) return;
  const top = document.querySelector('.top'); const r = top && top.offsetHeight ? top.getBoundingClientRect() : null;
  let c = document.getElementById('gotBand'); if (c) c.remove();
  c = el('div', { id: 'gotBand', class: n >= 2 ? 'kami' : '', role: 'status', 'aria-live': 'polite' },
    el('div', { class: 'shine' }), el('div', { class: 'lab', text: '本日の獲得' }),
    el('div', { class: 'num' }, String(n), el('small', { text: '件' })), el('div', { class: 'msg', text: GOT_MSG(n) }));
  c.style.setProperty('--bandTop', (r && r.bottom > 0 ? Math.round(r.bottom) : 0) + 'px');
  document.body.append(c);
  requestAnimationFrame(() => c.classList.add('show'));
  if (navigator.vibrate) { try { navigator.vibrate(n >= 2 ? [60, 40, 60, 40, 120] : [80]); } catch(e){} }
  clearTimeout(gotBand._t); gotBand._t = setTimeout(() => { c.classList.remove('show'); setTimeout(() => c.remove(), 400); }, 4500);
}
function todayAway(bid){""")
# 獲得ボタンを押した瞬間に花火
rep("""  const resRow = el('div', { class: 'res' }, RES_ORDER.map(k => el('button', { 'data-r': k, 'aria-pressed': String(form.r === k), onclick: () => {""",
    """  const resRow = el('div', { class: 'res' }, RES_ORDER.map(k => el('button', { 'data-r': k, 'aria-pressed': String(form.r === k), onclick: () => {
    if (k === 'got' && form.r !== 'got') fireworks(myGotToday() >= 1);""")
# 「登録する」：通信を待たずに帯を出す（失敗したら引っ込める）
rep("""      await register(b, r, form);
      toast(`${r}号室を「${RES[form.r]}」で登録しました`);
      closeRoom();""",
"""      const wasGot = form.r === 'got';
      if (wasGot) { TODAY.pending = (TODAY.pending || 0) + 1; updateStrip(); gotBand(myGotToday()); fireworks(myGotToday() >= 2); }
      try { await register(b, r, form); if (wasGot) { TODAY.pending = Math.max(0, TODAY.pending - 1); updateStrip(); } }
      catch(err){ if (wasGot) { TODAY.pending = Math.max(0, TODAY.pending - 1); updateStrip(); const c = document.getElementById('gotBand'); if (c) c.remove(); } throw err; }
      toast(`${r}号室を「${RES[form.r]}」で登録しました`);
      closeRoom();""")
# 活動記録：獲得のタイルを件数で豪華に
rep("""    [['訪問', c.doors], ['対面', c.face], ['獲得', c.got], ['棟数', c.bld]].map(([t, v]) => el('div', { class: 'kpi' }, el('b', { text: v }), el('span', { text: t })))));""",
    """    [['訪問', c.doors], ['対面', c.face], ['獲得', c.got], ['棟数', c.bld]].map(([t, v]) => {
      const lv = t === '獲得' ? Math.min(3, v) : 0;
      return el('div', { class: 'kpi' + (lv ? ' g' + lv : '') }, el('b', { text: v }), el('span', { text: t }), lv ? el('span', { class: 'tag', text: GOT_MSG(v) }) : null);
    })));""")

# ---------- いつも出ている「今日の獲得」の細い帯（メニューにくっつけて、ほかの画面を隠さない） ----------
STRIP_CSS = """
.gstrip{display:flex;align-items:center;gap:10px;height:32px;padding:0 12px;font-size:13.5px;font-weight:700;letter-spacing:.02em;-webkit-font-smoothing:antialiased;cursor:pointer;flex:none;
  background:var(--accent-soft);color:var(--accent);border-bottom:1px solid var(--line);white-space:nowrap;overflow:hidden}
.gstrip .gs-lab{font-size:11.5px;letter-spacing:.08em;opacity:.85}
.gstrip .gs-num{font-size:18px;font-variant-numeric:tabular-nums;line-height:1}
.gstrip .gs-num small{font-size:11.5px;margin-left:1px}
.gstrip .gs-msg{margin-left:auto;overflow:hidden;text-overflow:ellipsis}
@media (max-width:420px){.gstrip{gap:8px;padding:0 10px}.gstrip .gs-msg{font-size:12.5px}.gstrip .gs-lab{font-size:11px}}
.gstrip.l1{background:linear-gradient(90deg,#1B1FA8,#2a3db5);color:#fff;border-bottom-color:transparent;box-shadow:inset 0 -3px 0 #5CC2F2}
.gstrip.l2{background:linear-gradient(90deg,#14178a,#2a3db5);color:#fff;border-bottom-color:transparent;box-shadow:inset 0 -3px 0 #ffd54a}
.gstrip.l2 .gs-num,.gstrip.l2 .gs-msg{color:#ffd54a}
.gstrip.night:not(.l1):not(.l2){background:linear-gradient(90deg,#10132b,#1B1FA8);color:#fff;border-bottom-color:transparent}
@media (max-width:760px){
  #app{padding-bottom:calc(58px + 32px + env(safe-area-inset-bottom,0px))!important}
  .gstrip{position:fixed;left:0;right:0;bottom:calc(58px + env(safe-area-inset-bottom,0px));z-index:1290;border-bottom:0;border-top:1px solid var(--line)}
  .gstrip.l1,.gstrip.l2,.gstrip.night{border-top-color:transparent}
}
"""
i = s.index('</style>')
s = s[:i] + STRIP_CSS + s[i:]
rep('  <div id="banner" class="banner" hidden></div>',
    '  <div id="gotStrip" class="gstrip" hidden role="button" aria-label="今日の獲得（押すと活動記録）"></div>\n  <div id="banner" class="banner" hidden></div>')
rep("""function todayAway(bid){""", """// 時間帯と件数で、ひとことを変える（夜は「ラスト気合い」）
function stripMsg(n){
  const h = new Date().getHours();
  const night = h >= 19 || h < 4, eve = h >= 17;
  if (n >= 3) return night ? '伝説!! 最高の締めを!' : '伝説!! まだ伸ばせる!';
  if (n === 2) return night ? '神!! ラスト気合いでもう1件!' : '神!! この勢いで3件目!';
  if (n === 1) return night ? 'ラスト気合い!! あと1件!' : eve ? '夕方は会える時間! もう1件!!' : 'もう1件!!';
  // 0件：いつでもこの一言
  return '次のピンポンでくるかも！？';
}
function updateStrip(){
  const c = document.getElementById('gotStrip'); if (!c) return;
  let n = myGotToday(); const h = new Date().getHours(); const today = ymd(Date.now());
  if (!db) { try { const x = JSON.parse(localStorage.getItem('hm_got') || 'null'); n = x && x.d === today ? x.n : 0; } catch(e){ n = 0; } }
  else { try { localStorage.setItem('hm_got', JSON.stringify({ d: today, n })); } catch(e){} }
  c.hidden = false;
  c.className = 'gstrip' + (n >= 2 ? ' l2' : n === 1 ? ' l1' : '') + (h >= 19 || h < 4 ? ' night' : '');
  c.textContent = '';
  c.append(el('span', { class: 'gs-lab', text: matchMedia('(max-width:420px)').matches ? '今日' : '本日の獲得' }), el('span', { class: 'gs-num' }, String(n), el('small', { text: '件' })), el('span', { class: 'gs-msg', text: stripMsg(n) }));
}
function todayAway(bid){""")
rep("""    TODAY.got = got; TODAY.gotGone = gone;""", """    TODAY.got = got; TODAY.gotGone = gone; if (!TODAY.pending) updateStrip();""")
rep("""    if (f.r === 'got') { TODAY.gotLocal = TODAY.gotLocal || new Set(); TODAY.gotLocal.add(k); }""",
    """    if (f.r === 'got') { TODAY.gotLocal = TODAY.gotLocal || new Set(); TODAY.gotLocal.add(k); }""")
rep("""  watchToday(); setInterval(watchToday, 5 * 60000);""",
    """  watchToday(); setInterval(watchToday, 5 * 60000);
  updateStrip(); setInterval(updateStrip, 60000);
  { const gs = document.getElementById('gotStrip'); if (gs) gs.addEventListener('click', () => openPanel('act')); }""")


# ---------- 活動記録：回ったマンション一覧 ／ 2巡目リスト ／ 再訪のお知らせ ----------
NEXT_CSS = """
.atabs{display:flex;gap:6px;margin-bottom:8px}
.atabs button{flex:1;padding:9px 6px;border:1px solid var(--line);border-radius:9px;background:var(--card);font-weight:700;font-size:14px;color:var(--ink2);position:relative}
.atabs button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.atabs .bdg{position:absolute;top:-6px;right:-4px;background:#d24a3a;color:#fff;border-radius:10px;font-size:11px;padding:0 6px;line-height:18px}
.vrow{display:grid;grid-template-columns:1fr auto auto;gap:6px 8px;align-items:center;padding:9px 2px;border-bottom:1px solid var(--soft)}
.vrow .nm{font-weight:700;cursor:pointer;min-width:0}
.vrow .nm small{display:block;font-weight:400;color:var(--ink3);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vrow .facts2{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:4px 6px;font-size:12.5px}
.vrow .facts2 span{background:var(--soft);border-radius:6px;padding:1px 7px;color:var(--ink2)}
.vrow .facts2 .hot{background:#fdecea;color:#b3261e;font-weight:700}
.vrow .facts2 .rv{background:#e8f1fd;color:#1d4f9a;font-weight:700}
.vrow .facts2 .g{background:#e5f5ec;color:#1f7a45;font-weight:700}
.rvlist{grid-column:1/-1;display:flex;flex-direction:column;gap:3px;font-size:13px}
.rvlist div{display:flex;gap:8px;align-items:baseline}
.rvlist b{min-width:3.2em}
.rvlist .now{color:#b3261e;font-weight:700}
.hotbox{border:2px solid #d24a3a;border-radius:10px;padding:8px 10px;margin:6px 0 10px;background:var(--card)}
.hotbox h3{margin:0 0 4px;font-size:14px;color:#b3261e}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]) .vrow .facts2 .hot{background:#3d1f1b;color:#ff9b8f} :root:not([data-theme="light"]) .vrow .facts2 .rv{background:#1d2d4a;color:#9cc2ff} :root:not([data-theme="light"]) .vrow .facts2 .g{background:#173326;color:#8fe0b0} :root:not([data-theme="light"]) .rvlist .now,:root:not([data-theme="light"]) .hotbox h3{color:#ff9b8f} }
"""
i = s.index('</style>')
s = s[:i] + NEXT_CSS + s[i:]

# 建物のまとめに「会えた部屋の数（m）」と「再訪の部屋（rv：部屋→いつ・誰・メモ）」を足す
rep("""  return { l: last.t, n: arr.length, g: arr.filter(x => x.r === 'got').length, r: last.r, u: last.u || '', v, fn, pn };""",
    """  const rv = {}; for (const r in latest) if (latest[r].r === 'again') rv[r] = { w: latest[r].when || '', t: latest[r].t, u: latest[r].u || '', m: String(latest[r].m || '').slice(0, 60) };
  return { l: last.t, n: arr.length, g: arr.filter(x => x.r === 'got').length, r: last.r, u: last.u || '', v, fn, pn, m: Object.keys(latest).length, rv };""")
# 不在だけの日も「この建物に行った日（a）」は残す（1つの値を上書きするだけ。部屋の記録は増えない）
s = s.replace("""    const se = sumEntry(cur);""", """    const se = sumEntry(cur); { const pa = ((SUM[b.cc] || {})[b.id] || {}).a; if (pa) se.a = pa; }""", 1)
rep("""    const se = sumEntry(d.log);""", """    const se = sumEntry(d.log); { const pa = ((SUM[b.cc] || {})[b.id] || {}).a; if (pa) se.a = pa; }""")
rep("""      await upsert(FB.act.ref(ymd(t)), { u: me.id, d: ymd(t), [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) });
      watchToday();""",
"""      await upsert(FB.act.ref(ymd(t)), { u: me.id, d: ymd(t), [k]: Object.assign({ bid: b.id, cc: b.cc }, entry) });
      try { const se = Object.assign(sumEntry({}), (SUM[b.cc] || {})[b.id] || {}, { a: t }); await upsert(db.doc('sum/' + b.cc), { [b.id]: se }); SUM[b.cc] = Object.assign({}, SUM[b.cc] || {}, { [b.id]: se }); } catch(e){}
      watchToday();""")

# 活動記録：上に「その日の記録」「2巡目リスト」の切り替え
rep("""  const body = $('#pBody'); body.textContent = '';
  const iso = `${actState.date.slice(0, 4)}-${actState.date.slice(4, 6)}-${actState.date.slice(6, 8)}`;""",
"""  const body = $('#pBody'); body.textContent = '';
  const hotN = revisits(true).length;
  body.append(el('div', { class: 'atabs' },
    el('button', { 'aria-pressed': String(actState.tab !== 'next'), onclick: () => { actState.tab = ''; renderAct(); } }, 'その日の記録'),
    el('button', { 'aria-pressed': String(actState.tab === 'next'), onclick: () => { actState.tab = 'next'; renderAct(); } }, '2巡目・再訪', hotN ? el('span', { class: 'bdg', text: hotN }) : null)));
  if (actState.tab === 'next') { $('#pSub').textContent = '最近回った建物と、もう一度行く部屋'; renderNext(body); drawAct([]); return; }
  const iso = `${actState.date.slice(0, 4)}-${actState.date.slice(4, 6)}-${actState.date.slice(6, 8)}`;""")
# その日の記録：回ったマンションの一覧
rep("""  // per person table
  if (people.length) {""",
"""  // 回ったマンション
  if (list.length) {
    const g = {};
    for (const x of list) { const o = g[x.bid] = g[x.bid] || { bid: x.bid, n: 0, away: 0, face: 0, got: 0, t0: x.t, t1: x.t }; o.n++; if (x.r === 'away') o.away++; if (FACE.includes(x.r)) o.face++; if (x.r === 'got') o.got++; o.t0 = Math.min(o.t0, x.t); o.t1 = Math.max(o.t1, x.t); }
    const rows = Object.values(g).sort((a, b2) => a.t0 - b2.t0);
    const hm = t => { const d = new Date(t); return d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0'); };
    const sec = el('section', { class: 'sec' }, el('h3', { text: `回ったマンション（${rows.length}棟・回った順）` }));
    rows.forEach(o => { const b = byId[o.bid]; if (!b) return; sec.append(vRow(b, [
      el('span', { text: `${hm(o.t0)}${o.t1 - o.t0 > 60000 ? '〜' + hm(o.t1) : ''}` }), el('span', { text: `${o.n}室` }),
      o.face ? el('span', { text: `会えた ${o.face}` }) : null, o.away ? el('span', { text: `不在 ${o.away}` }) : null, o.got ? el('span', { class: 'g', text: `獲得 ${o.got}` }) : null])); });
    const ids = rows.map(o => o.bid).filter(id => byId[id] && !route.includes(id));
    if (ids.length) sec.append(el('button', { class: 'btn', style: 'margin-top:8px', onclick: () => { route.push(...ids); saveRoute(); drawRouteLine(); toast(`${ids.length}棟をルートに追加しました（2巡目用）`); renderAct(); } }, 'この建物をまとめてルートに追加（2巡目用）'));
    body.append(sec);
  }
  // per person table
  if (people.length) {""")

rep("""function todayAway(bid){""", r"""// ---- 2巡目・再訪 ----
function lastVisit(st){ return st ? Math.max(st.l || 0, st.a || 0) : 0; }
function unmetOf(b, st){ const met = st ? (st.m != null ? st.m : Object.keys(st.v || {}).length + (st.n ? 1 : 0)) : 0; return Math.max(0, (b.t || 0) - met - (b.kn || []).length - (b.in || []).length); }
// 再訪の「いつ」が今に合っているか
function revNow(w, t){
  const now = new Date(), h = now.getHours(), wd = now.getDay(), we = wd === 0 || wd === 6;
  if (w === '今日の夜') return ymd(t) === ymd(Date.now()) && h >= 17;
  if (w === '平日の昼') return !we && h >= 10 && h < 17;
  if (w === '平日の夜') return !we && h >= 17;
  if (w === '土日') return we;
  return false;
}
// 再訪の一覧（onlyNow：今が狙い目だけ）。60日より前のものは出さない
function revisits(onlyNow, mine){
  const out = [];
  for (const cc in SUM) for (const id in SUM[cc]) { const st = SUM[cc][id]; const b = byId[id]; if (!b || !st || !st.rv) continue;
    for (const r in st.rv) { const x = st.rv[r]; if (Date.now() - (x.t || 0) > 60 * DAY) continue; if (mine && x.u !== me.id) continue;
      const now = revNow(x.w, x.t); if (onlyNow && !now) continue; out.push({ b, r, w: x.w, t: x.t, u: x.u, m: x.m, now }); } }
  return out;
}
function vRow(b, facts, extra){
  const inR = route.includes(b.id);
  const gm = el('a', { class: 'gmap', href: gmapsLink(b), target: '_blank', rel: 'noopener', title: 'Googleマップで開く', 'aria-label': 'Googleマップで開く' });
  gm.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>';
  return el('div', { class: 'vrow' },
    el('div', { class: 'nm', onclick: () => pickFromPanel(b.id) }, b.n, el('small', { text: restOf(b) || b.a || '' })), gm,
    el('button', { class: 'addr' + (inR ? ' on' : ''), 'aria-label': inR ? 'ルートから外す' : 'ルートに追加', onclick: () => { toggleRoute(b.id); renderAct(); } }, inR ? '✓' : '＋'),
    el('div', { class: 'facts2' }, facts.filter(Boolean)), extra || null);
}
function renderNext(body){
  const nd = actState.nd || 7, sort = actState.ns || 'rv', onlyRv = !!actState.nrv;
  // 今が狙い目の再訪
  const hot = revisits(true).sort((a, c) => a.t - c.t);
  if (hot.length) {
    const hb = el('div', { class: 'hotbox' }, el('h3', { text: `今が狙い目の再訪 ${hot.length}室` }));
    hot.slice(0, 30).forEach(x => hb.append(el('div', { class: 'vrow', style: 'border:0;padding:4px 0' },
      el('div', { class: 'nm', onclick: () => pickFromPanel(x.b.id) }, `${x.b.n} ${x.r}号室`, el('small', { text: `${x.w}・${fmtDate(x.t).replace(/\(.\)/, '')}に${nameOf(x.u)}${x.m ? '・' + x.m : ''}` })))));
    body.append(hb);
  }
  body.append(el('div', { class: 'ctl' },
    el('select', { onchange: e => { actState.nd = +e.target.value; renderAct(); } }, [[3, '3日以内に回った'], [7, '7日以内に回った'], [14, '14日以内に回った'], [30, '30日以内に回った']].map(([v, t]) => el('option', { value: v, selected: v === nd }, t))),
    el('select', { onchange: e => { actState.ns = e.target.value; renderAct(); } }, [['rv', '再訪がある建物を先に'], ['unmet', '会えていない部屋が多い順'], ['old', '回った日が古い順'], ...(HERE ? [['near', '現在地から近い順']] : [])].map(([v, t]) => el('option', { value: v, selected: v === sort }, t))),
    el('label', { class: 'chk' }, el('input', { type: 'checkbox', checked: onlyRv, onchange: e => { actState.nrv = e.target.checked; renderAct(); } }), '再訪がある建物だけ')));
  const since = Date.now() - nd * DAY;
  let rows = [];
  for (const b of B) { if (b.x) continue; const st = statOf(b); const lv = lastVisit(st); if (!lv || lv < since) continue;
    const rv = st && st.rv ? Object.entries(st.rv).filter(([r, x]) => Date.now() - (x.t || 0) <= 60 * DAY) : [];
    if (onlyRv && !rv.length) continue;
    rows.push({ b, st, lv, rv, unmet: unmetOf(b, st), hot: rv.some(([r, x]) => revNow(x.w, x.t)) }); }
  const key = { rv: o => -(o.hot ? 1000 : 0) - o.rv.length * 10 - o.unmet / 1000, unmet: o => -o.unmet, old: o => o.lv, near: o => metersTo(o.b) };
  rows.sort((a, c) => key[sort](a) - key[sort](c));
  body.append(el('div', { class: 'muted', text: `${rows.length}棟。「まだ会えていない」は、総戸数から、結果が残っている部屋・勧誘禁止・開通済みを引いた目安です。` }));
  const ids = rows.map(o => o.b.id).filter(id => !route.includes(id)).slice(0, 10);
  if (ids.length) body.append(el('button', { class: 'btn primary', style: 'margin:6px 0', onclick: () => { route.push(...ids); saveRoute(); drawRouteLine(); toast(`上から${ids.length}棟をルートに追加しました`); renderAct(); } }, `上から${ids.length}棟をルートに追加`));
  const box = el('section', { class: 'sec' });
  rows.slice(0, 200).forEach(o => {
    const rvl = o.rv.length ? el('div', { class: 'rvlist' }, o.rv.sort((a, c) => a[1].t - c[1].t).map(([r, x]) => el('div', null, el('b', { text: r }), el('span', { class: revNow(x.w, x.t) ? 'now' : '', text: (x.w || 'いつでも') + (revNow(x.w, x.t) ? '（今が狙い目）' : '') }), el('span', { class: 'muted', text: `${fmtDate(x.t).replace(/\(.\)/, '')} ${nameOf(x.u)}${x.m ? '・' + x.m : ''}` })))) : null;
    box.append(vRow(o.b, [el('span', { text: `最終 ${ago(o.lv)}` }), el('span', { class: o.unmet ? 'hot' : '', text: `まだ会えていない 約${o.unmet}室` }), o.rv.length ? el('span', { class: 'rv', text: `再訪 ${o.rv.length}室` }) : null, o.st && o.st.g ? el('span', { class: 'g', text: `獲得 ${o.st.g}` }) : null], rvl));
  });
  if (!rows.length) box.append(el('p', { class: 'muted', text: 'この期間に回った建物はありません。' }));
  body.append(box);
}
// 開いたとき：自分の再訪で「今が狙い目」があれば、時間帯ごとに1回だけ知らせる
function checkRevReminder(){
  const mine = revisits(true, true); if (!mine.length) return;
  const h = new Date().getHours(); const slot = ymd(Date.now()) + (h < 12 ? 'a' : h < 17 ? 'b' : 'c');
  if (store.get('revSlot', '') === slot) return; store.set('revSlot', slot);
  const bn = $('#banner'); bn.hidden = false; bn.textContent = '';
  bn.append(el('b', { text: `今が狙い目の再訪が${mine.length}室あります　` }), el('button', { class: 'linkbtn', onclick: () => { bn.hidden = true; actState.tab = 'next'; if (panelKind !== 'act') openPanel('act'); else renderAct(); } }, '見る'), '　', el('button', { class: 'linkbtn', onclick: () => { bn.hidden = true; } }, '閉じる'));
}
function todayAway(bid){""")
rep("""    SUM = next;
    usageBanner();""", """    SUM = next;
    usageBanner();
    if (!checkRevReminder._done) { checkRevReminder._done = true; checkRevReminder(); }
    if (panelKind === 'act' && actState.tab === 'next') renderAct();""")


# ---------- 獲得の演出を豪華に（打ち上げ花火・金の柳・紙吹雪・光・大きな文字）。画面は押せるまま ----------
SHOW_CSS = """
#gotFlash{position:fixed;inset:0;z-index:3950;pointer-events:none;opacity:0;background:radial-gradient(circle at 50% 45%,rgba(255,255,255,.85),rgba(255,213,74,.35) 35%,rgba(27,31,168,0) 70%)}
#gotFlash.on{animation:gotFlash .55s ease-out}
@keyframes gotFlash{0%{opacity:0}15%{opacity:1}100%{opacity:0}}
#gotEdge{position:fixed;inset:0;z-index:3940;pointer-events:none;opacity:0;box-shadow:inset 0 0 0 4px #ffd54a,inset 0 0 60px 10px rgba(255,213,74,.55)}
#gotEdge.on{animation:gotEdge 1.8s ease-out}
@keyframes gotEdge{0%{opacity:0}12%{opacity:1}60%{opacity:.8}100%{opacity:0}}
#gotStamp{position:fixed;left:50%;top:38%;z-index:3960;pointer-events:none;transform:translate(-50%,-50%) scale(.2);opacity:0;
  padding:10px 26px 12px;border-radius:18px;background:rgba(16,19,60,.86);border:3px solid #ffd54a;box-shadow:0 10px 40px rgba(0,0,0,.35);text-align:center;white-space:nowrap}
#gotStamp .s1{display:block;font-size:46px;font-weight:700;line-height:1.1;color:#fff;letter-spacing:.06em}
#gotStamp .s2{display:block;font-size:15px;font-weight:700;color:#ffd54a;letter-spacing:.12em;margin-top:2px}
#gotStamp.gold .s1{color:#ffd54a}
#gotStamp.on{animation:gotStamp 1.9s cubic-bezier(.2,1.5,.35,1) forwards}
@keyframes gotStamp{0%{opacity:0;transform:translate(-50%,-50%) scale(.2) rotate(-8deg)}18%{opacity:1;transform:translate(-50%,-50%) scale(1.12) rotate(2deg)}30%{transform:translate(-50%,-50%) scale(1) rotate(0)}78%{opacity:1;transform:translate(-50%,-50%) scale(1)}100%{opacity:0;transform:translate(-50%,-60%) scale(.9)}}
@media (prefers-reduced-motion:reduce){#gotFlash,#gotEdge{display:none}#gotStamp.on{animation:none;opacity:1;transform:translate(-50%,-50%)}}
"""
i = s.index('</style>')
s = s[:i] + SHOW_CSS + s[i:]
a0 = s.index("function fireworks(big){")
a1 = s.index("// 今日の獲得の帯")
s = s[:a0] + r"""function fireworks(level){
  // level：0＝獲得ボタンを押したとき（小さめ）、1＝1件目、2＝2件目、3＝3件目以上
  if (reduceMotion()) return;
  level = level === true ? 2 : level === false ? 1 : (level || 0);
  let cv = document.getElementById('fw'); if (cv) cv.remove();
  cv = document.createElement('canvas'); cv.id = 'fw'; document.body.append(cv);
  const dpr = Math.min(1.5, window.devicePixelRatio || 1), W = innerWidth, H = innerHeight;
  cv.width = W * dpr; cv.height = H * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr);
  const COL = ['#ffd54a', '#ffffff', '#5CC2F2', '#ff7aa2', '#8ef0b0', '#9aa8ff', '#ffb04a', '#ff5e5e'];
  const rnd = (a, b) => a + Math.random() * (b - a);
  const P = [];      // 火花
  const R = [];      // 打ち上げ中の玉
  const C = [];      // 紙吹雪
  const burst = (x, y, kind, col) => {
    if (kind === 'willow') { for (let i = 0; i < 90; i++) { const a = rnd(0, Math.PI * 2), v = rnd(0.6, 3.2); P.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 0.6, c: Math.random() < .7 ? '#ffd54a' : '#fff1b0', life: rnd(1400, 2100), t: 0, gr: 0.035, dr: 0.985, r: 1.9, tw: true }); } return; }
    const n = kind === 'ring' ? 64 : 80, c2 = COL[(Math.random() * COL.length) | 0];
    for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2 + rnd(-.05, .05), v = kind === 'ring' ? 4.2 : rnd(1.5, 5.2);
      P.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, c: i % 3 === 0 ? c2 : col, life: rnd(900, 1400), t: 0, gr: 0.06, dr: 0.97, r: 2.6, tw: Math.random() < .3 }); }
    for (let i = 0; i < 26; i++) { const a = rnd(0, Math.PI * 2), v = rnd(.5, 2); P.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, c: '#ffffff', life: rnd(500, 900), t: 0, gr: 0.03, dr: 0.95, r: 1.6, tw: true }); }
  };
  const shells = [0, 3, 5, 7, 9][Math.min(4, level + (level ? 1 : 0))] || 3;
  for (let s2 = 0; s2 < shells; s2++) {
    const x = W * rnd(0.15, 0.85), ty = H * rnd(0.14, 0.38), kind = level >= 2 && s2 % 3 === 2 ? 'willow' : s2 % 2 ? 'ring' : 'peony';
    R.push({ x: x + rnd(-30, 30), y: H + 10, tx: x, ty, t0: s2 * (level >= 2 ? 170 : 230), dur: rnd(520, 700), kind, col: COL[(s2 * 3 + 1) % COL.length], done: false });
  }
  if (level >= 1) { const nC = level >= 3 ? 150 : level >= 2 ? 110 : 70;
    const cc = level >= 2 ? ['#ffd54a', '#ffe9a0', '#ffffff', '#5CC2F2', '#9aa8ff'] : ['#5CC2F2', '#ffffff', '#9aa8ff', '#ffd54a', '#ff7aa2'];
    for (let i = 0; i < nC; i++) C.push({ x: rnd(0, W), y: rnd(-H * 0.6, -10), vy: rnd(1.6, 3.4), sw: rnd(0.6, 1.8), ph: rnd(0, 6.28), rot: rnd(0, 6.28), vr: rnd(-0.2, 0.2), w: rnd(6, 10), h: rnd(9, 15), c: cc[i % cc.length], t0: rnd(0, 500) }); }
  const start = performance.now(); let last = start;
  const tick = now => {
    const t = now - start, dt = Math.min(40, now - last) / 16.7; last = now;
    g.globalCompositeOperation = 'destination-out'; g.globalAlpha = 1; g.fillStyle = 'rgba(0,0,0,0.26)'; g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'lighter';
    for (const r of R) { if (r.done || t < r.t0) continue; const k = Math.min(1, (t - r.t0) / r.dur), e = 1 - Math.pow(1 - k, 3);
      const x = r.x + (r.tx - r.x) * e, y = r.y + (r.ty - r.y) * e;
      g.globalAlpha = 1; g.fillStyle = '#fff3c4'; g.beginPath(); g.arc(x, y, 2.6, 0, 6.28); g.fill();
      if (Math.random() < .8) P.push({ x, y: y + 4, vx: rnd(-.3, .3), vy: rnd(.5, 1.2), c: '#ffcf70', life: 380, t: 0, gr: .02, dr: .96, r: 1.4 });
      if (k >= 1) { r.done = true; burst(x, y, r.kind, r.col); } }
    for (const p of P) { if (p.t > p.life) continue; p.t += dt * 16.7; p.vx *= Math.pow(p.dr, dt); p.vy = p.vy * Math.pow(p.dr, dt) + p.gr * dt; p.x += p.vx * dt; p.y += p.vy * dt;
      let a = 1 - p.t / p.life; if (p.tw) a *= .55 + .45 * Math.sin(p.t / 40); g.globalAlpha = Math.max(0, a); g.fillStyle = p.c; g.beginPath(); g.arc(p.x, p.y, p.r, 0, 6.28); g.fill(); }
    g.globalCompositeOperation = 'source-over';
    for (const c of C) { if (t < c.t0) continue; c.y += c.vy * dt; c.ph += 0.06 * dt; c.rot += c.vr * dt; if (c.y > H + 20) continue;
      const x = c.x + Math.sin(c.ph) * 18 * c.sw; g.save(); g.translate(x, c.y); g.rotate(c.rot); g.scale(1, Math.abs(Math.cos(c.ph * 1.7)) * .8 + .2);
      g.globalAlpha = t > 2600 ? Math.max(0, 1 - (t - 2600) / 600) : 1; g.fillStyle = c.c; g.fillRect(-c.w / 2, -c.h / 2, c.w, c.h); g.restore(); }
    if (t < (level >= 2 ? 3400 : 3000)) requestAnimationFrame(tick); else cv.remove();
  };
  requestAnimationFrame(tick);
}
// 光・金のふち・大きな文字（文字は濃い紺の板の上なので読みやすい）
function gotShow(n){
  const lv = Math.min(3, n);
  fireworks(lv);
  const mk = (id) => { let e = document.getElementById(id); if (e) e.remove(); e = document.createElement('div'); e.id = id; document.body.append(e); return e; };
  if (!reduceMotion()) { const f = mk('gotFlash'); requestAnimationFrame(() => f.classList.add('on')); setTimeout(() => f.remove(), 700);
    if (lv >= 2) { const ed = mk('gotEdge'); requestAnimationFrame(() => ed.classList.add('on')); setTimeout(() => ed.remove(), 2000); } }
  const st = mk('gotStamp'); st.className = lv >= 2 ? 'gold' : '';
  st.append(el('span', { class: 's1', text: lv >= 3 ? '伝説!!' : lv === 2 ? '神!!' : '獲得!!' }), el('span', { class: 's2', text: `本日 ${n}件目` }));
  requestAnimationFrame(() => st.classList.add('on')); setTimeout(() => st.remove(), reduceMotion() ? 1500 : 2000);
  if (navigator.vibrate) { try { navigator.vibrate(lv >= 3 ? [70, 40, 70, 40, 70, 40, 200] : lv === 2 ? [60, 40, 60, 40, 140] : [90, 50, 90]); } catch(e){} }
}
""" + s[a1:]
# 獲得を押したとき：小さめの花火／登録したとき：豪華なフルセット
rep("""    if (k === 'got' && form.r !== 'got') fireworks(myGotToday() >= 1);""",
    """    if (k === 'got' && form.r !== 'got') fireworks(0);""")
rep("""      if (wasGot) { TODAY.pending = (TODAY.pending || 0) + 1; updateStrip(); gotBand(myGotToday()); fireworks(myGotToday() >= 2); }""",
    """      if (wasGot) { TODAY.pending = (TODAY.pending || 0) + 1; updateStrip(); gotBand(myGotToday()); gotShow(myGotToday()); }""")
# 帯の中の震えは gotShow に任せる（二重にならないように）
rep("""  if (navigator.vibrate) { try { navigator.vibrate(n >= 2 ? [60, 40, 60, 40, 120] : [80]); } catch(e){} }
  clearTimeout(gotBand._t);""", """  clearTimeout(gotBand._t);""")


# ---------- 獲得の文字を豪華に：太い見出し用の字体・金属のような光沢・キラキラ・光の走り ----------
# 字体は使う文字だけを小さく読み込む（すぐ出るように）
GLYPHS = '獲得神伝説本日件目もう0123456789!！'
rep('<link rel="manifest" href="manifest.webmanifest">\n',
    '<link rel="manifest" href="manifest.webmanifest">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&display=swap&text=' + __import__('urllib.parse').parse.quote(GLYPHS) + '">\n')
LUX_CSS = """
#gotStamp{padding:14px 30px 14px;border-radius:20px;border:0;overflow:visible;
  background:radial-gradient(120% 140% at 50% 0%,#2a3db5 0%,#14178a 55%,#0b0d3a 100%);
  box-shadow:0 0 0 3px #ffd54a,0 0 0 6px rgba(255,213,74,.25),0 12px 44px rgba(0,0,0,.45),0 0 40px rgba(255,213,74,.35)}
#gotStamp::before{content:"";position:absolute;inset:-3px;border-radius:22px;padding:3px;pointer-events:none;
  background:conic-gradient(from var(--ga,0deg),#fff6c2,#ffd54a,#f5b700,#fff6c2,#ffd54a,#f5b700,#fff6c2);
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;animation:gaSpin 1.6s linear infinite}
@property --ga{syntax:'<angle>';inherits:false;initial-value:0deg}
@keyframes gaSpin{to{--ga:360deg}}
#gotStamp .s1{font-family:'Dela Gothic One',var(--font);font-weight:400;font-size:56px;line-height:1.05;letter-spacing:.04em;position:relative;
  background:linear-gradient(180deg,#ffffff 0%,#e3f4ff 45%,#9fdcff 55%,#ffffff 100%);-webkit-background-clip:text;background-clip:text;color:transparent;
  -webkit-text-stroke:1.5px rgba(8,10,40,.55);paint-order:stroke fill;filter:drop-shadow(0 3px 0 #0b0d3a) drop-shadow(0 0 14px rgba(159,220,255,.6))}
#gotStamp.gold .s1{background:linear-gradient(180deg,#fffbe6 0%,#ffe27a 42%,#f5b700 56%,#fff0a8 100%);-webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 3px 0 #0b0d3a) drop-shadow(0 0 16px rgba(255,213,74,.7))}
#gotStamp .s2{font-family:'Dela Gothic One',var(--font);font-weight:400;font-size:16px;color:#ffd54a;letter-spacing:.14em;margin-top:4px}
/* 文字の上を光が走る */
#gotStamp .gl{position:absolute;inset:0;border-radius:20px;overflow:hidden;pointer-events:none}
#gotStamp .gl::after{content:"";position:absolute;top:-20%;bottom:-20%;width:38%;left:-50%;transform:skewX(-20deg);
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent);animation:glSweep 1.1s .35s ease-out 2}
@keyframes glSweep{to{left:120%}}
/* キラキラ */
#gotStamp .spk{position:absolute;color:#fff6c2;font-size:18px;line-height:1;text-shadow:0 0 8px #ffd54a,0 0 16px #ffd54a;opacity:0;animation:spk 1.2s ease-in-out infinite}
#gotStamp.gold .spk{color:#fff}
@keyframes spk{0%,100%{opacity:0;transform:scale(.3) rotate(0)}50%{opacity:1;transform:scale(1.15) rotate(45deg)}}
/* 下の帯の数字とひとことも同じ字体で */
#gotBand .num,#gotBand .msg{font-family:'Dela Gothic One',var(--font);font-weight:400}
#gotBand.kami .msg,#gotBand.kami .num{color:#ffd54a;text-shadow:0 0 10px rgba(255,213,74,.55),0 2px 0 #0b0d3a}
#gotBand .msg{text-shadow:0 0 10px rgba(159,220,255,.5),0 2px 0 #0b0d3a}
@media (prefers-reduced-motion:reduce){#gotStamp::before,#gotStamp .gl::after,#gotStamp .spk{animation:none}#gotStamp .spk{opacity:.9}}
"""
i = s.index('</style>')
s = s[:i] + LUX_CSS + s[i:]
rep("""  st.append(el('span', { class: 's1', text: lv >= 3 ? '伝説!!' : lv === 2 ? '神!!' : '獲得!!' }), el('span', { class: 's2', text: `本日 ${n}件目` }));""",
    """  st.append(el('span', { class: 'gl' }), el('span', { class: 's1', text: lv >= 3 ? '伝説!!' : lv === 2 ? '神!!' : '獲得!!' }), el('span', { class: 's2', text: `本日 ${n}件目` }));
  // キラキラを板のまわりに散らす（件数が多いほど多く）
  const spots = [[-6, 10], [104, 8], [-4, 82], [102, 86], [20, -14], [80, -12], [50, 104], [8, 48], [96, 46]];
  spots.slice(0, lv >= 3 ? 9 : lv === 2 ? 7 : 5).forEach(([x, y], i) => st.append(el('span', { class: 'spk', text: '✦', style: `left:${x}%;top:${y}%;animation-delay:${(i * 0.13).toFixed(2)}s;font-size:${14 + (i % 3) * 5}px` })));""")


# ---------- パチンコの「当たり」風：虹の光線・金のメダル・虹色の極太文字・ゆれ ----------
JP_CSS = """
#jp{position:fixed;inset:0;z-index:3955;pointer-events:none;overflow:hidden;opacity:1;transition:opacity .35s}
#jp.out{opacity:0}
#jp .rays{position:absolute;left:50%;top:44%;width:260vmax;height:260vmax;transform:translate(-50%,-50%);opacity:.92;
  background:repeating-conic-gradient(from 0deg,#ff1f5a 0 7.5deg,#ff9a00 7.5deg 15deg,#ffe600 15deg 22.5deg,#2bff88 22.5deg 30deg,#00c8ff 30deg 37.5deg,#7a5cff 37.5deg 45deg,#ff3bd4 45deg 52.5deg,#ffffff 52.5deg 54deg);
  -webkit-mask:radial-gradient(circle at 50% 50%,#000 0 9%,rgba(0,0,0,.9) 16%,rgba(0,0,0,.55) 24%,transparent 36%);mask:radial-gradient(circle at 50% 50%,#000 0 9%,rgba(0,0,0,.9) 16%,rgba(0,0,0,.55) 24%,transparent 36%);
  animation:jpSpin 2.6s linear,jpHue 1.3s linear infinite}
@keyframes jpSpin{to{transform:translate(-50%,-50%) rotate(140deg)}}
@keyframes jpHue{to{filter:hue-rotate(360deg)}}
#jp .glow{position:absolute;left:50%;top:44%;width:120vmin;height:120vmin;transform:translate(-50%,-50%);border-radius:50%;
  background:radial-gradient(circle,rgba(255,255,255,.95) 0%,rgba(255,240,170,.85) 18%,rgba(255,200,40,.45) 34%,rgba(255,120,0,0) 60%);animation:jpPulse .5s ease-in-out infinite alternate}
@keyframes jpPulse{to{transform:translate(-50%,-50%) scale(1.08)}}
#jp .disc{position:absolute;left:50%;top:44%;width:min(78vw,420px);aspect-ratio:1;transform:translate(-50%,-50%) scale(.2);border-radius:50%;
  background:radial-gradient(circle at 35% 30%,#fff7c8 0%,#ffd54a 30%,#e0a100 58%,#a86b00 80%,#ffd54a 100%);
  box-shadow:0 0 0 6px #fff1a8,0 0 0 12px #c98a00,0 0 40px 10px rgba(255,213,74,.9),inset 0 0 40px rgba(120,60,0,.6);animation:jpDisc .5s cubic-bezier(.2,1.5,.4,1) forwards}
@keyframes jpDisc{to{transform:translate(-50%,-50%) scale(1)}}
#jp .word{position:absolute;left:50%;top:44%;transform:translate(-50%,-50%);text-align:center;white-space:nowrap}
#jp .w1{display:block;font-family:'Dela Gothic One',var(--font);font-weight:400;font-size:min(24vw,130px);line-height:1;letter-spacing:.02em;
  background:linear-gradient(180deg,#ffffff 0%,#fff35c 16%,#ffb300 30%,#ff3b5c 46%,#ff3bd4 58%,#7a5cff 72%,#00c8ff 86%,#7dffb0 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-stroke:4px #2b1200;paint-order:stroke fill;
  filter:drop-shadow(0 3px 0 #ffd54a) drop-shadow(0 6px 0 #b8860b) drop-shadow(0 10px 0 #5a3200) drop-shadow(0 0 22px rgba(255,240,120,.95));
  transform:skewX(-8deg) rotate(-5deg);animation:jpSlam .55s cubic-bezier(.2,1.7,.35,1) both,jpBeat .42s .6s ease-in-out infinite alternate}
@keyframes jpSlam{0%{opacity:0;transform:skewX(-8deg) rotate(-5deg) scale(3.2)}60%{opacity:1}100%{opacity:1;transform:skewX(-8deg) rotate(-5deg) scale(1)}}
@keyframes jpBeat{to{transform:skewX(-8deg) rotate(-5deg) scale(1.06)}}
#jp .rib{display:inline-block;margin-top:10px;padding:6px 22px 7px;font-family:'Dela Gothic One',var(--font);font-weight:400;font-size:min(6.2vw,28px);letter-spacing:.12em;color:#fff;
  background:linear-gradient(180deg,#ff4d4d,#c80018);border:3px solid #ffd54a;border-radius:10px;box-shadow:0 4px 0 #7a0010,0 0 18px rgba(255,80,80,.7);
  text-shadow:0 2px 0 #6a0010;transform:rotate(-3deg) scale(0);animation:jpRib .4s .35s cubic-bezier(.2,1.6,.4,1) forwards}
@keyframes jpRib{to{transform:rotate(-3deg) scale(1)}}
#jp .st{position:absolute;color:#fff;text-shadow:0 0 10px #ffe600,0 0 20px #ff9a00;opacity:0;animation:spk .9s ease-in-out infinite}
#fw{z-index:3970!important}
#app.jpShake{animation:jpShake .38s linear}
@keyframes jpShake{10%{transform:translate(-6px,3px)}20%{transform:translate(6px,-4px)}30%{transform:translate(-5px,-3px)}40%{transform:translate(5px,4px)}50%{transform:translate(-3px,2px)}60%{transform:translate(3px,-2px)}75%{transform:translate(-2px,1px)}100%{transform:none}}
@media (prefers-reduced-motion:reduce){#jp .rays,#jp .glow,#jp .w1,#jp .st{animation:none}#jp .rays{display:none}#jp .disc,#jp .rib{animation:none;transform:translate(-50%,-50%)}#jp .rib{transform:none}#app.jpShake{animation:none}}
"""
i = s.index('</style>')
s = s[:i] + JP_CSS + s[i:]
rep("""  const st = mk('gotStamp'); st.className = lv >= 2 ? 'gold' : '';""",
"""  // パチンコの当たり風の全画面演出（押せるまま・2秒少々で消える）
  { const jp = mk('jp'); const word = lv >= 3 ? '伝説!!' : lv === 2 ? '神!!' : '獲得!!';
    jp.append(el('div', { class: 'rays' }), el('div', { class: 'glow' }), el('div', { class: 'disc' }),
      el('div', { class: 'word' }, el('span', { class: 'w1', text: word }), el('span', { class: 'rib', text: `本日 ${n}件目` })));
    for (let i = 0; i < (lv >= 3 ? 22 : lv === 2 ? 16 : 11); i++) jp.append(el('span', { class: 'st', text: '✦', style: `left:${(Math.random() * 92 + 2).toFixed(1)}%;top:${(Math.random() * 70 + 8).toFixed(1)}%;font-size:${14 + Math.random() * 26 | 0}px;animation-delay:${(Math.random() * .8).toFixed(2)}s` }));
    const app = document.getElementById('app'); if (app && !reduceMotion()) { app.classList.remove('jpShake'); void app.offsetWidth; app.classList.add('jpShake'); setTimeout(() => app.classList.remove('jpShake'), 450); }
    const dur = lv >= 3 ? 2600 : lv === 2 ? 2300 : 2000;
    setTimeout(() => jp.classList.add('out'), dur); setTimeout(() => jp.remove(), dur + 400); }
  const st = mk('gotStamp'); st.className = lv >= 2 ? 'gold' : ''; st.style.display = 'none';""")


# ---------- 当たり演出 第2版：描画で作る本格版（暗転→衝撃→光線・玉ボケ・衝撃波・彫りの深いメダル・立体のクロム文字・光沢） ----------
rep("""  // パチンコの当たり風の全画面演出（押せるまま・2秒少々で消える）
  { const jp = mk('jp');""", """  jackpot(n, lv);
  if (false) { const jp = mk('jp');""")
rep("""function fbReady(){""", r"""// 当たり演出用の字体を先に読み込んでおく（初回でもすぐ出るように）
try { document.fonts && document.fonts.load("80px 'Dela Gothic One'", '獲得神伝説本日件目0123456789!'); } catch(e){}
function fbReady(){""")
rep("""// 光・金のふち・大きな文字""", r"""// ===== 当たり演出（キャンバスで描く） =====
function jackpot(n, lv){
  if (reduceMotion()) return;
  let cv = document.getElementById('jpc'); if (cv) cv.remove();
  cv = document.createElement('canvas'); cv.id = 'jpc';
  cv.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;z-index:3955;pointer-events:none';
  document.body.append(cv);
  const dpr = Math.min(1.5, window.devicePixelRatio || 1), W = innerWidth, H = innerHeight;
  cv.width = W * dpr; cv.height = H * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr);
  const cx = W / 2, cy = H * 0.44, R = Math.min(W * 0.46, 250);
  const FONT = "'Dela Gothic One', 'BIZ UDPGothic', sans-serif";
  const word = lv >= 3 ? '伝説!!' : lv === 2 ? '神!!' : '獲得!!';
  const gold = lv >= 2;
  const DUR = lv >= 3 ? 3000 : lv === 2 ? 2700 : 2400;
  const rnd = (a, b) => a + Math.random() * (b - a);

  // --- 文字を一度だけ別の紙に描いておく（立体の厚み・二重のふち・光沢のある中身） ---
  const fs = Math.min(W * (word.length > 3 ? 0.2 : 0.26), 150);
  const tc = document.createElement('canvas'), tg = tc.getContext('2d');
  tg.font = `${fs}px ${FONT}`; const tw = tg.measureText(word).width;
  const PAD = fs * 0.45, TW = Math.ceil(tw + PAD * 2), TH = Math.ceil(fs * 1.75);
  tc.width = TW * dpr; tc.height = TH * dpr; tg.scale(dpr, dpr);
  tg.font = `${fs}px ${FONT}`; tg.textAlign = 'center'; tg.textBaseline = 'middle'; tg.lineJoin = 'round';
  const tx = TW / 2, ty = TH * 0.46, depth = Math.round(fs * 0.11);
  // 後ろの光（1回だけ描く）
  tg.save(); tg.shadowColor = gold ? 'rgba(255,200,40,.95)' : 'rgba(140,220,255,.95)'; tg.shadowBlur = fs * .3; tg.fillStyle = gold ? 'rgba(255,200,40,.6)' : 'rgba(140,220,255,.6)'; tg.lineWidth = fs * .2; tg.strokeStyle = tg.fillStyle; tg.strokeText(word, tx, ty); tg.restore();
  // 厚み（下に向かって濃くなる金）
  for (let d = depth; d >= 1; d--) { const k = d / depth; tg.fillStyle = `rgb(${Math.round(120 - 70 * k)},${Math.round(70 - 45 * k)},${Math.round(10)})`; tg.strokeStyle = tg.fillStyle; tg.lineWidth = fs * 0.16; tg.strokeText(word, tx, ty + d); tg.fillText(word, tx, ty + d); }
  // 外側の濃いふち → 金のふち → 細い濃いふち
  tg.lineWidth = fs * 0.2; tg.strokeStyle = '#140600'; tg.strokeText(word, tx, ty);
  const gs = tg.createLinearGradient(0, ty - fs * 0.6, 0, ty + fs * 0.6);
  [['0', '#fffbe0'], ['.25', '#ffd54a'], ['.5', '#9a6400'], ['.62', '#ffe680'], ['.85', '#c98a00'], ['1', '#fff2a8']].forEach(([o, c]) => gs.addColorStop(+o, c));
  tg.lineWidth = fs * 0.12; tg.strokeStyle = gs; tg.strokeText(word, tx, ty);
  tg.lineWidth = fs * 0.035; tg.strokeStyle = '#2a1000'; tg.strokeText(word, tx, ty);
  // 中身：1件目は虹のクロム、2件目からは金のクロム（上が明るく、真ん中に反射の線）
  const fg = tg.createLinearGradient(0, ty - fs * 0.5, 0, ty + fs * 0.5);
  if (gold) [['0', '#ffffff'], ['.18', '#fff3b0'], ['.42', '#ffc928'], ['.5', '#a86a00'], ['.56', '#ffe680'], ['.8', '#ffb300'], ['1', '#fff0b0']].forEach(([o, c]) => fg.addColorStop(+o, c));
  else [['0', '#ffffff'], ['.14', '#fff36b'], ['.3', '#ffaa00'], ['.46', '#ff3d6e'], ['.5', '#ffffff'], ['.55', '#d24dff'], ['.72', '#3d8bff'], ['.88', '#22e0ff'], ['1', '#b8ffd8']].forEach(([o, c]) => fg.addColorStop(+o, c));
  tg.fillStyle = fg; tg.fillText(word, tx, ty);
  // 上半分のつや
  tg.save(); tg.globalCompositeOperation = 'source-atop';
  const gl = tg.createLinearGradient(0, ty - fs * 0.5, 0, ty); gl.addColorStop(0, 'rgba(255,255,255,.55)'); gl.addColorStop(1, 'rgba(255,255,255,0)');
  tg.fillStyle = gl; tg.fillRect(0, ty - fs * 0.55, TW, fs * 0.5); tg.restore();
  // 文字の形（光沢を走らせるときの型）
  const mc = document.createElement('canvas'); mc.width = tc.width; mc.height = tc.height; const mg = mc.getContext('2d'); mg.scale(dpr, dpr);
  mg.font = `${fs}px ${FONT}`; mg.textAlign = 'center'; mg.textBaseline = 'middle'; mg.fillStyle = '#fff'; mg.fillText(word, tx, ty);
  const sh = document.createElement('canvas'); sh.width = tc.width; sh.height = tc.height; const sg = sh.getContext('2d');

  // --- 「本日 ○件目」のリボン ---
  const rbText = `本日 ${n}件目`; const rfs = Math.min(W * 0.06, 28);
  const drawRibbon = (y, sc) => {
    g.save(); g.translate(cx, y); g.scale(sc, sc); g.rotate(-0.04);
    g.font = `${rfs}px ${FONT}`; const rw = g.measureText(rbText).width + rfs * 1.8, rh = rfs * 1.7;
    // 折り返しの端
    g.fillStyle = '#7a0010';
    [[-1], [1]].forEach(([s2]) => { g.beginPath(); g.moveTo(s2 * rw / 2, -rh * .2); g.lineTo(s2 * (rw / 2 + rfs * 1.1), -rh * .2); g.lineTo(s2 * (rw / 2 + rfs * .7), rh * .35); g.lineTo(s2 * (rw / 2 + rfs * 1.1), rh * .85); g.lineTo(s2 * rw / 2, rh * .85); g.closePath(); g.fill(); });
    const rg = g.createLinearGradient(0, -rh / 2, 0, rh / 2); rg.addColorStop(0, '#ff6b6b'); rg.addColorStop(.45, '#e0001f'); rg.addColorStop(1, '#8a0012');
    g.fillStyle = rg; g.beginPath(); g.roundRect(-rw / 2, -rh / 2, rw, rh, 8); g.fill();
    g.lineWidth = 3; g.strokeStyle = '#ffd54a'; g.stroke();
    g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round'; g.lineWidth = 5; g.strokeStyle = '#4a0008'; g.strokeText(rbText, 0, 1); g.fillStyle = '#fff'; g.fillText(rbText, 0, 1);
    g.restore();
  };

  // --- 彫りの深いメダル ---
  const drawMedal = (sc, rot) => {
    g.save(); g.translate(cx, cy); g.scale(sc, sc);
    // 外の光
    const og = g.createRadialGradient(0, 0, R * .6, 0, 0, R * 1.35); og.addColorStop(0, 'rgba(255,214,90,.65)'); og.addColorStop(1, 'rgba(255,170,0,0)');
    g.fillStyle = og; g.beginPath(); g.arc(0, 0, R * 1.35, 0, 7); g.fill();
    // 縁（金属）
    const rim = g.createLinearGradient(-R, -R, R, R); [['0', '#fff6c8'], ['.2', '#d99a00'], ['.45', '#fff1a0'], ['.6', '#9a6200'], ['.8', '#ffd54a'], ['1', '#7a4a00']].forEach(([o, c]) => rim.addColorStop(+o, c));
    g.fillStyle = rim; g.beginPath(); g.arc(0, 0, R, 0, 7); g.fill();
    // 縁のギザギザ（回る）
    g.save(); g.rotate(rot); g.strokeStyle = 'rgba(90,50,0,.55)'; g.lineWidth = 2;
    for (let i = 0; i < 72; i++) { const a = i / 72 * Math.PI * 2; g.beginPath(); g.moveTo(Math.cos(a) * R * .9, Math.sin(a) * R * .9); g.lineTo(Math.cos(a) * R * .985, Math.sin(a) * R * .985); g.stroke(); }
    g.restore();
    // 内側の盤
    const inner = g.createRadialGradient(-R * .25, -R * .3, R * .05, 0, 0, R * .86);
    if (gold) { inner.addColorStop(0, '#fff8d0'); inner.addColorStop(.35, '#ffcf40'); inner.addColorStop(.75, '#c47f00'); inner.addColorStop(1, '#6a3c00'); }
    else { inner.addColorStop(0, '#d8f4ff'); inner.addColorStop(.35, '#4fb0ff'); inner.addColorStop(.75, '#1f2bab'); inner.addColorStop(1, '#0b0d3a'); }
    g.fillStyle = inner; g.beginPath(); g.arc(0, 0, R * .86, 0, 7); g.fill();
    g.lineWidth = R * .03; g.strokeStyle = '#3a2000'; g.stroke();
    // 内側の放射の線
    g.save(); g.rotate(-rot * .6); g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 36; i++) { const a = i / 36 * Math.PI * 2; g.strokeStyle = `rgba(255,255,255,${i % 2 ? .07 : .14})`; g.lineWidth = R * .05; g.beginPath(); g.moveTo(Math.cos(a) * R * .2, Math.sin(a) * R * .2); g.lineTo(Math.cos(a) * R * .84, Math.sin(a) * R * .84); g.stroke(); }
    g.restore();
    // 縁を回る光
    g.save(); g.rotate(rot * 2.2); const sw = g.createLinearGradient(-R, 0, R, 0); sw.addColorStop(0, 'rgba(255,255,255,0)'); sw.addColorStop(.5, 'rgba(255,255,255,.75)'); sw.addColorStop(1, 'rgba(255,255,255,0)');
    g.strokeStyle = sw; g.lineWidth = R * .06; g.beginPath(); g.arc(0, 0, R * .93, -0.6, 0.6); g.stroke(); g.restore();
    g.restore();
  };

  // --- 背景の部品 ---
  const bokeh = Array.from({ length: 46 }, () => ({ x: rnd(0, W), y: rnd(0, H), r: rnd(6, 26), vx: rnd(-.25, .25), vy: rnd(-.6, -.1), c: Math.random() < .6 ? [255, 214, 90] : Math.random() < .5 ? [255, 255, 255] : [120, 200, 255], a: rnd(.15, .45), ph: rnd(0, 6) }));
  const glints = Array.from({ length: lv >= 3 ? 34 : lv === 2 ? 26 : 18 }, () => ({ x: rnd(.04, .96) * W, y: rnd(.06, .8) * H, s: rnd(6, 16), d: rnd(0, 1600), p: rnd(500, 900) }));
  const star = (x, y, s, a) => { g.save(); g.globalAlpha = a; g.translate(x, y); g.fillStyle = '#fff';
    const sg2 = g.createRadialGradient(0, 0, 0, 0, 0, s * 1.6); sg2.addColorStop(0, 'rgba(255,240,180,.9)'); sg2.addColorStop(1, 'rgba(255,200,60,0)'); g.fillStyle = sg2; g.beginPath(); g.arc(0, 0, s * 1.6, 0, 7); g.fill();
    g.fillStyle = '#fff'; g.beginPath(); g.moveTo(0, -s * 2); g.lineTo(s * .22, -s * .22); g.lineTo(s * 2, 0); g.lineTo(s * .22, s * .22); g.lineTo(0, s * 2); g.lineTo(-s * .22, s * .22); g.lineTo(-s * 2, 0); g.lineTo(-s * .22, -s * .22); g.closePath(); g.fill(); g.restore(); };

  const L = Math.hypot(W, H);
  const RC = document.createElement('canvas'), RS = Math.ceil(L * 1.5); RC.width = RS; RC.height = RS; const rg2 = RC.getContext('2d');
  rg2.globalCompositeOperation = 'lighter';
  for (let i = 0, rays = 28; i < rays; i++) { const a = i / rays * Math.PI * 2, w = (i % 2 ? .05 : .085), hue = i * 360 / rays;
    const lg = rg2.createRadialGradient(RS / 2, RS / 2, R * .3, RS / 2, RS / 2, RS / 2);
    lg.addColorStop(0, `hsla(${gold ? 42 + (i % 3) * 6 : hue},100%,${gold ? 62 : 60}%,.55)`); lg.addColorStop(1, `hsla(${gold ? 40 : hue},100%,55%,0)`);
    rg2.fillStyle = lg; rg2.beginPath(); rg2.moveTo(RS / 2, RS / 2); rg2.arc(RS / 2, RS / 2, RS / 2, a - w, a + w); rg2.closePath(); rg2.fill(); }
  // 玉ボケ：1つだけ描いておき、使い回す
  const BK = {}; const bokehImg = c => { const key = c.join(','); if (BK[key]) return BK[key]; const bc = document.createElement('canvas'); bc.width = bc.height = 64; const bg2 = bc.getContext('2d');
    const gr = bg2.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, `rgba(${key},1)`); gr.addColorStop(.7, `rgba(${key},.5)`); gr.addColorStop(1, `rgba(${key},0)`); bg2.fillStyle = gr; bg2.fillRect(0, 0, 64, 64); return BK[key] = bc; };
  const start = performance.now();
  const ease = k => 1 - Math.pow(1 - k, 3);
  const back = k => { const c1 = 2.2, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
  const tick = now => {
    const t = now - start; if (t > DUR) { cv.remove(); return; }
    const fade = t > DUR - 380 ? (DUR - t) / 380 : 1;
    g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H); g.globalAlpha = fade; g.globalCompositeOperation = 'source-over';
    // 暗転（色が映えるように）
    const dk = Math.min(1, t / 120) * .78; const bg = g.createRadialGradient(cx, cy, 0, cx, cy, Math.max(W, H) * .8);
    bg.addColorStop(0, `rgba(60,10,90,${dk * .55})`); bg.addColorStop(1, `rgba(5,3,20,${dk})`); g.fillStyle = bg; g.fillRect(0, 0, W, H);
    // 光線（やわらかく、色が回る）
    g.globalCompositeOperation = 'lighter';
    g.save(); g.translate(cx, cy); g.rotate(t / 1400); g.drawImage(RC, -RS / 2, -RS / 2); g.restore();
    // 玉ボケ
    for (const b of bokeh) { b.x += b.vx; b.y += b.vy; g.globalAlpha = fade * b.a * (.6 + .4 * Math.sin(t / 300 + b.ph)); g.drawImage(bokehImg(b.c), b.x - b.r, b.y - b.r, b.r * 2, b.r * 2); }
    g.globalAlpha = fade;
    // 衝撃波（ドンの瞬間に2重の輪）
    for (const [d0, col] of [[160, '255,240,170'], [260, '160,220,255']]) { const k = (t - d0) / 700; if (k < 0 || k > 1) continue;
      g.strokeStyle = `rgba(${col},${(1 - k) * .9})`; g.lineWidth = 14 * (1 - k) + 2; g.beginPath(); g.arc(cx, cy, R * (.6 + k * 2.4), 0, 7); g.stroke(); }
    // 横に伸びる光（レンズの光）
    { const a = Math.max(0, 1 - Math.abs(t - 260) / 900) * .9; if (a > 0) { const fl = g.createLinearGradient(0, cy, W, cy); fl.addColorStop(0, 'rgba(255,255,255,0)'); fl.addColorStop(.5, `rgba(255,250,220,${a})`); fl.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = fl; g.fillRect(0, cy - 3, W, 6); g.fillStyle = `rgba(255,240,200,${a * .25})`; g.fillRect(0, cy - 14, W, 28); } }
    g.globalCompositeOperation = 'source-over';
    // メダル
    const mk2 = Math.min(1, Math.max(0, (t - 60) / 420)); drawMedal(back(mk2) * (1 + .02 * Math.sin(t / 120)), t / 900);
    // 文字（大きいところから叩きつけ → 脈打つ）
    const k = Math.min(1, Math.max(0, (t - 120) / 380));
    if (k > 0) { const sc = k < 1 ? 2.6 - 1.6 * back(k) : 1 + .045 * Math.sin((t - 500) / 95);
      // 光沢の帯を文字の型の上に走らせる
      sg.setTransform(1, 0, 0, 1, 0, 0); sg.clearRect(0, 0, sh.width, sh.height); sg.drawImage(mc, 0, 0); sg.globalCompositeOperation = 'source-in';
      const sx = ((t - 520) % 1100) / 1100 * (sh.width * 1.8) - sh.width * .4; const sgd = sg.createLinearGradient(sx, 0, sx + sh.width * .25, sh.height);
      sgd.addColorStop(0, 'rgba(255,255,255,0)'); sgd.addColorStop(.5, 'rgba(255,255,255,.85)'); sgd.addColorStop(1, 'rgba(255,255,255,0)'); sg.fillStyle = sgd; sg.fillRect(0, 0, sh.width, sh.height); sg.globalCompositeOperation = 'source-over';
      g.save(); g.translate(cx, cy - fs * .05); g.rotate(-0.07); g.scale(sc, sc); g.transform(1, 0, -0.14, 1, 0, 0);
      g.globalAlpha = fade * Math.min(1, k * 2);
      g.drawImage(tc, -TW / 2, -TH * .46, TW, TH);
      if (t > 520) g.drawImage(sh, -TW / 2, -TH * .46, TW, TH);
      g.restore(); }
    // リボン
    const rk = Math.min(1, Math.max(0, (t - 420) / 320)); if (rk > 0) { g.globalAlpha = fade; drawRibbon(cy + fs * .78, back(rk)); }
    // キラッと光る星
    g.globalCompositeOperation = 'lighter';
    for (const s3 of glints) { const lt = (t - s3.d) % (s3.p * 2); if (t < s3.d || lt > s3.p) continue; const a = Math.sin(lt / s3.p * Math.PI); star(s3.x, s3.y, s3.s * (.6 + .6 * a), a * fade); }
    g.globalCompositeOperation = 'source-over';
    // 最初の白い光
    if (t < 220) { g.globalAlpha = (1 - t / 220) * .85; g.fillStyle = '#fff'; g.fillRect(0, 0, W, H); }
    g.globalAlpha = 1;
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
// 光・金のふち・大きな文字""")

open(os.path.join('/home/claude/houmon-map', 'index.html'), 'w', encoding='utf-8').write(s)
print('ok', len(s))
