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
  c = el('div', { id: 'gotBand', class: n >= 2 ? 'kami' : '', role: 'status', 'aria-live': 'polite', onclick: () => c.classList.remove('show') },
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

open(os.path.join('/home/claude/houmon-map', 'index.html'), 'w', encoding='utf-8').write(s)
print('ok', len(s))
