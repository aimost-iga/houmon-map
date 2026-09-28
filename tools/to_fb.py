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
    const drawAreas = () => {
      areaBox.textContent = '';
      if (f.role !== 'contractor') return;
      const sel = el('select', { style: 'padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:var(--card);max-width:260px' }, el('option', { value: '' }, '市区町村を選んで追加'), cityOpts.filter(([cc]) => !f.areas.includes(cc)).map(([cc, n]) => el('option', { value: cc }, n)));
      sel.addEventListener('change', () => { if (sel.value) { f.areas.push(sel.value); drawAreas(); } });
      areaBox.append(el('div', { class: 'flab', text: '担当エリア（ここに入れた市区町村の建物だけ見られます）' }),
        el('div', { class: 'ctl', style: 'gap:6px' }, f.areas.map(cc => el('button', { class: 'btn', title: '押すと外します', onclick: () => { f.areas = f.areas.filter(x => x !== cc); drawAreas(); } }, ((CITY[cc] && CITY[cc].short) || cc) + ' ×'))), sel);
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

open(os.path.join('/home/claude/houmon-map', 'index.html'), 'w', encoding='utf-8').write(s)
print('ok', len(s))
